"""Gateway: the platform's only public entry point.

Who you are comes from Cloudflare Access (a signed JWT: Google or one-time email code); which
tenant you reach comes only from that verified email, so nobody can address someone else's
space. The tenant app checks the same JWT again (ALLOWED_EMAILS = its owner).

/welcome            public home page (what this is, link to the source): the only page without a login
/welcome/cal/...    a person's calendar feed: no login either (a calendar app can't), the long key in
                    the address is checked by that person's own workspace
/_platform/...      gateway pages: invite, account (export / delete my data), admin
everything else     forwarded to the caller's own tenant container
"""
import concurrent.futures
import contextlib
import hashlib
import hmac
import os
import re
import threading
import time
import urllib.parse

import httpx
import jwt
from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse, PlainTextResponse, RedirectResponse, Response, StreamingResponse
from fastapi.templating import Jinja2Templates
from starlette.background import BackgroundTask

from . import db, health, i18n, league, locales, notify


class Config:
    def __init__(self):
        e = os.environ.get
        self.team = e("CF_TEAM_DOMAIN", "")
        self.aud = e("CF_ACCESS_AUD", "")
        self.admins = {x.strip().lower() for x in e("ADMIN_EMAILS", "").split(",") if x.strip()}
        self.secret = e("PLATFORM_SECRET", "")
        self.provisioner = e("PROVISIONER_URL", "http://provisioner:8091")
        self.token = e("PROVISIONER_TOKEN", "")
        self.max_tenants = int(e("MAX_TENANTS", "25"))
        self.public_url = e("PUBLIC_URL", "").rstrip("/")
        self.max_body = int(e("MAX_BODY_MB", "30")) * 1024 * 1024
        self.project_url = e("PROJECT_URL", "https://github.com/nigifabio/swiss-job-agent")
        self.contact = e("CONTACT_EMAIL", "").strip()      # shown on the home page to ask for an invite
        self.health_hours = float(e("HEALTH_CHECK_HOURS", "6") or 0)


C = Config()
@contextlib.asynccontextmanager
async def lifespan(_app):
    _startup()
    yield


app = FastAPI(title="Swiss Job Agent", docs_url=None, redoc_url=None, openapi_url=None, lifespan=lifespan)
# one set of templates per interface language (the visitor's browser decides; the admin page stays English)
templates = {lang: Jinja2Templates(env=env) for lang, env in i18n.environments(
    os.path.join(os.path.dirname(__file__), "templates"), locales.TEMPLATES, locales.STRINGS).items()}
_jwks = None
HOP = {"connection", "keep-alive", "proxy-authenticate", "proxy-authorization", "te", "trailers",
       "transfer-encoding", "upgrade", "host", "content-length"}
SECURITY_HEADERS = {"X-Frame-Options": "DENY", "X-Content-Type-Options": "nosniff",
                    "Referrer-Policy": "same-origin", "Strict-Transport-Security": "max-age=31536000",
                    "Content-Security-Policy": "frame-ancestors 'none'; base-uri 'self'; object-src 'none'"}


def _startup():
    if not (C.team and C.aud):
        raise RuntimeError("CF_TEAM_DOMAIN and CF_ACCESS_AUD are required: the gateway only runs behind Cloudflare Access")
    if not C.secret or not C.token:
        raise RuntimeError("PLATFORM_SECRET and PROVISIONER_TOKEN are required")
    db.init()
    try:
        prov("POST", "/sync")                  # re-join tenant networks after a gateway restart
    except Exception as e:  # noqa: BLE001
        print(f"[gateway] provisioner sync failed: {e}")
    if C.health_hours > 0 and notify.configured():
        threading.Thread(target=_watch, daemon=True).start()


def user_email(request):
    """The verified email from the Cloudflare Access JWT, or None. There is no other way in."""
    global _jwks
    token = request.headers.get("cf-access-jwt-assertion") or request.cookies.get("CF_Authorization")
    if not token:
        return None
    if _jwks is None:
        _jwks = jwt.PyJWKClient(f"https://{C.team}/cdn-cgi/access/certs", cache_keys=True, lifespan=3600)
    try:
        key = _jwks.get_signing_key_from_jwt(token).key
        claims = jwt.decode(token, key, algorithms=["RS256"], audience=C.aud, issuer=f"https://{C.team}")
    except Exception:  # noqa: BLE001
        return None
    return (claims.get("email") or "").lower() or None


def identify(request):
    return user_email(request)


def csrf_token(email):
    return hmac.new(C.secret.encode(), f"csrf:{email}".encode(), hashlib.sha256).hexdigest()[:32]


def check_csrf(request, email, token):
    if not hmac.compare_digest(csrf_token(email), token or ""):
        raise PermissionError("bad form token")


def prov(method, path, **kw):
    with httpx.Client(base_url=C.provisioner, timeout=180, headers={"Authorization": f"Bearer {C.token}"}) as c:
        r = c.request(method, path, **kw)
        r.raise_for_status()
        return r.json() if r.headers.get("content-type", "").startswith("application/json") else r.content


def page(request, name, ctx, status=200):
    ctx.update(email=getattr(request.state, "email", ""), csrf=csrf_token(getattr(request.state, "email", "")),
               is_admin=getattr(request.state, "email", "") in C.admins)
    lang = "en" if name == "admin.html" else i18n.pick(request.cookies.get("lang", ""), request.headers.get("accept-language", ""))
    i18n.use(lang)
    return templates[lang].TemplateResponse(request, name, ctx, status_code=status)


PUBLIC_HOME = "/welcome"


def home(request, status=200):
    email = getattr(request.state, "email", "")
    # signing out of Cloudflare Access, then straight back to the sign-in page: the way to change address
    back = urllib.parse.quote((C.public_url or str(request.base_url).rstrip("/")) + "/", safe="")
    req = db.request_for(email) if email else None
    return page(request, "welcome.html", {"project_url": C.project_url, "contact": C.contact,
                                          "req": req, "full": len(db.tenants()) >= C.max_tenants,
                                          "switch_url": f"https://{C.team}/cdn-cgi/access/logout?returnTo={back}",
                                          "has_workspace": bool(email and db.tenant_for(email))}, status)


def message(request, title, text, status=200, link=None):
    return page(request, "message.html", {"title": title, "text": text, "link": link}, status)


@app.middleware("http")
async def gate(request: Request, call_next):
    path = request.url.path
    if path == "/_platform/healthz":
        return await call_next(request)
    if '"scheme":"http"' in request.headers.get("cf-visitor", "").replace(" ", ""):
        # the visitor reached Cloudflare over plain http: everything here is https only
        host = urllib.parse.urlsplit(C.public_url).netloc or request.headers.get("host", "")
        return RedirectResponse(f"https://{host}{path}" + (f"?{request.url.query}" if request.url.query else ""), status_code=308)
    if path.startswith(PUBLIC_HOME + "/lang/") and request.method == "GET":
        return await call_next(request)          # the flags of the top bar: sets a cookie, nothing else
    if path.startswith(PUBLIC_HOME + "/cal/") and request.method == "GET":
        request.state.email = ""                 # a calendar app fetching a feed: no identity, the key is the access
        return await call_next(request)
    if path == PUBLIC_HOME and request.method in ("GET", "HEAD"):
        # the one public page: static text, shows the visitor's email only if they are signed in
        request.state.email = identify(request) or ""
        resp = await call_next(request)
        for k, v in SECURITY_HEADERS.items():
            resp.headers.setdefault(k, v)
        return resp
    email = identify(request)
    if not email:
        return PlainTextResponse("Forbidden", status_code=403)
    request.state.email = email
    # cross-site form posts are refused, for the gateway and the tenants alike
    if request.method not in ("GET", "HEAD", "OPTIONS"):
        origin = request.headers.get("origin")
        host = request.headers.get("x-forwarded-host") or request.headers.get("host")
        if origin and re.sub(r"^https?://", "", origin) != host:
            return PlainTextResponse("Cross-site request refused", status_code=403)
    if not path.startswith("/_platform/"):
        resp = await forward(request, email)
    else:
        resp = await call_next(request)
    for k, v in SECURITY_HEADERS.items():
        resp.headers.setdefault(k, v)
    return resp


@app.exception_handler(PermissionError)
def _forbidden(request, exc):
    return PlainTextResponse(str(exc), status_code=403)


# ---- forwarding to the tenant ------------------------------------------------------------------
_http = None


def http():
    global _http
    if _http is None:
        _http = httpx.AsyncClient(timeout=httpx.Timeout(180, connect=5), follow_redirects=False)
    return _http


def tenant_url(slug):
    return f"http://jat-{slug}-web:8080"


async def forward(request, email):
    t = db.tenant_for(email)
    if not t:                    # signed in, no workspace: the home page says how to get one
        return home(request, 403)
    if t["status"] != "active":
        return message(request, "Workspace paused", "Your workspace is paused. Contact the administrator.", 403)
    _seen(t["slug"])
    if int(request.headers.get("content-length") or 0) > C.max_body:
        return PlainTextResponse("Upload too large", status_code=413)
    url = tenant_url(t["slug"]) + request.url.path + (f"?{request.url.query}" if request.url.query else "")
    headers = [(k, v) for k, v in request.headers.items() if k.lower() not in HOP]
    headers += [("x-forwarded-for", request.client.host if request.client else ""),
                ("x-forwarded-proto", request.headers.get("x-forwarded-proto", request.url.scheme)),
                ("x-forwarded-host", request.headers.get("host", ""))]
    body = await request.body()               # bounded by MAX_BODY_MB above
    if len(body) > C.max_body:
        return PlainTextResponse("Upload too large", status_code=413)
    req = http().build_request(request.method, url, headers=headers, content=body)
    try:
        resp = await http().send(req, stream=True)
    except httpx.TransportError:
        return page(request, "starting.html", {}, 503)
    out = StreamingResponse(resp.aiter_bytes(), status_code=resp.status_code,
                            background=BackgroundTask(resp.aclose))
    for k, v in resp.headers.multi_items():   # keeps repeated headers (Set-Cookie) separate
        if k.lower() not in HOP and k.lower() != "content-encoding":
            out.headers.append(k, v)
    return out


_last_touch = {}


def _seen(slug):
    """Note that the owner is using their workspace, at most once every 10 minutes."""
    if time.time() - _last_touch.get(slug, 0) > 600:
        _last_touch[slug] = time.time()
        db.touch(slug)


@app.get(PUBLIC_HOME + "/lang/{code}")
def set_lang(code: str, next: str = ""):
    """Language of the platform's own pages (home, request, invite, account), chosen with the flags."""
    to = next if re.fullmatch(r"/[A-Za-z0-9_/.-]{0,200}", next or "") and not next.startswith("//") else PUBLIC_HOME
    resp = RedirectResponse(to, status_code=303)
    resp.set_cookie("lang", code if code in i18n.LANGS else "", max_age=365 * 86400, path="/", samesite="lax", httponly=True, secure=True)
    return resp


# ---- calendar feeds ----------------------------------------------------------------------------
CAL_SLUG = re.compile(r"^[a-z0-9][a-z0-9-]{1,30}[a-z0-9]$")
CAL_NAME = re.compile(r"^[A-Za-z0-9_-]{20,80}\.ics$")
_cal_misses = {}          # caller address -> times of wrong keys (guessing is hopeless, and cut short anyway)


def _cal_blocked(who, miss=False):
    now = time.time()
    recent = [t for t in _cal_misses.get(who, []) if now - t < 600]
    if miss:
        recent.append(now)
    _cal_misses[who] = recent
    if len(_cal_misses) > 5000:
        _cal_misses.clear()
    return len(recent) > 20


@app.get(PUBLIC_HOME + "/cal/{slug}/{name}")
async def calendar_feed(request: Request, slug: str, name: str):
    """Pass a calendar feed request to its workspace, which checks the key. Only this one address
    of a workspace can be reached without signing in, and it only answers with dates."""
    who = request.headers.get("cf-connecting-ip") or (request.client.host if request.client else "")
    t = db.tenant(slug) if CAL_SLUG.match(slug) and CAL_NAME.match(name) else None
    if not t or t["status"] != "active" or _cal_blocked(who):
        _cal_blocked(who, miss=True)
        return PlainTextResponse("Not found", status_code=404)
    host = urllib.parse.urlsplit(C.public_url).netloc or request.headers.get("host", "")
    try:
        r = await http().get(tenant_url(slug) + f"/calendar/{name}", headers={"x-forwarded-host": host, "x-forwarded-proto": "https"})
    except httpx.TransportError:
        return PlainTextResponse("Try again later", status_code=503)
    if r.status_code != 200:
        _cal_blocked(who, miss=True)
        return PlainTextResponse("Not found", status_code=404)
    return Response(r.content, media_type="text/calendar; charset=utf-8", headers={"Cache-Control": "private, max-age=900"})


@app.api_route(PUBLIC_HOME, methods=["GET", "HEAD"], response_class=HTMLResponse)   # HEAD: link previews, monitors
def welcome(request: Request):
    return home(request)


# ---- account requests --------------------------------------------------------------------------
def _create_workspace(request, email, invite_id=None):
    """Shared by invites and approved requests. Returns (slug, None) or (None, error page)."""
    slug = db.new_slug(email)
    db.add_tenant(slug, email, invite_id)
    try:
        prov("PUT", f"/tenants/{slug}", json={"email": email})
    except Exception as e:  # noqa: BLE001
        db.remove_tenant(slug)
        db.audit(email, "tenant.create_failed", f"{slug}: {e}")
        return None, message(request, "Something went wrong", "Your workspace couldn't be created. The administrator "
                                                              "can see it in the log; please try again later.", 500)
    db.audit(email, "tenant.create", slug)
    return slug, None


@app.get("/_platform/request", response_class=HTMLResponse)
def request_form(request: Request):
    email = request.state.email
    if db.tenant_for(email) or db.request_for(email):
        return RedirectResponse("/", status_code=303)
    return page(request, "request.html", {})


@app.post("/_platform/request")
def request_send(request: Request, csrf: str = Form(""), name: str = Form(""), note: str = Form("")):
    email = request.state.email
    check_csrf(request, email, csrf)
    if db.tenant_for(email):
        return RedirectResponse("/", status_code=303)
    name, note = " ".join(name.split())[:80], " ".join(note.split())[:400]
    state = db.add_request(email, name, note)
    if state == "full":
        return message(request, "Not now", "There are many requests waiting already. Please try again in a few days.", 503)
    if state == "created":
        db.audit(email, "request.create", name)
        notify.admins(prov, "🇨🇭 Job platform: account request",
                      f"{name or '(no name)'} <{email}> asks for a workspace.\n\n{note or '(no message)'}\n\n"
                      f"Approve or decline: {C.public_url}/_platform/admin")
    return RedirectResponse("/", status_code=303)


@app.post("/_platform/request/create")
def request_create(request: Request, csrf: str = Form("")):
    """An approved person creates their workspace."""
    email = request.state.email
    check_csrf(request, email, csrf)
    if db.tenant_for(email):
        return RedirectResponse("/", status_code=303)
    req = db.request_for(email)
    if not req or req["status"] != "approved":
        return message(request, "Not approved yet", "Your request hasn't been approved yet.", 403)
    if len(db.tenants()) >= C.max_tenants:
        return message(request, "Full", "The platform has reached its number of workspaces. Contact the administrator.", 503)
    slug, err = _create_workspace(request, email)
    if err:
        return err
    db.close_request(email)
    return RedirectResponse("/", status_code=303)


@app.post("/_platform/admin/request")
def admin_request(request: Request, csrf: str = Form(""), email: str = Form(""), decision: str = Form("")):
    require_admin(request)
    check_csrf(request, request.state.email, csrf)
    if decision not in ("approved", "declined") or not db.decide_request(email, decision, request.state.email):
        return message(request, "Not changed", "No such waiting request.", 400, link=("/_platform/admin", "Back"))
    db.audit(request.state.email, f"request.{decision}", email.lower())
    return RedirectResponse("/_platform/admin", status_code=303)


# ---- invites ------------------------------------------------------------------------------------
@app.get("/_platform/healthz")
def healthz():
    return {"ok": True}


@app.get("/_platform/invite/{token}", response_class=HTMLResponse)
def invite_page(request: Request, token: str):
    email = request.state.email
    if db.tenant_for(email):
        return RedirectResponse("/", status_code=303)
    inv = db.invite(token)
    if not inv:
        return message(request, "Invite not valid", "This invite link was already used, has expired or was revoked. "
                                                     "Ask for a new one.", 404)
    if inv.get("email") and inv["email"] != email:
        return message(request, "Invite for someone else",
                       f"This invite is for another email address. You are signed in as {email}.", 403)
    return page(request, "invite.html", {"token": token, "note": inv.get("note") or ""})


@app.post("/_platform/invite/{token}")
def invite_accept(request: Request, token: str, csrf: str = Form("")):
    email = request.state.email
    check_csrf(request, email, csrf)
    if db.tenant_for(email):
        return RedirectResponse("/", status_code=303)
    inv = db.invite(token)
    if not inv or (inv.get("email") and inv["email"] != email):
        return message(request, "Invite not valid", "This invite link can't be used.", 404)
    if len(db.tenants()) >= C.max_tenants:
        return message(request, "Full", "The platform has reached its number of workspaces. Contact the administrator.", 503)
    if not db.use_invite(inv["id"], email):
        return message(request, "Invite not valid", "This invite was just used.", 409)
    slug = db.new_slug(email)
    db.add_tenant(slug, email, inv["id"])
    try:
        prov("PUT", f"/tenants/{slug}", json={"email": email})
    except Exception as e:  # noqa: BLE001
        db.remove_tenant(slug)
        db.release_invite(inv["id"])
        db.audit(email, "tenant.create_failed", f"{slug}: {e}")
        return message(request, "Something went wrong", "Your workspace couldn't be created. The administrator was "
                                                         "notified in the log; the invite can be reissued.", 500)
    db.audit(email, "tenant.create", slug)
    return RedirectResponse("/", status_code=303)


# ---- my account --------------------------------------------------------------------------------
@app.get("/_platform/me", response_class=HTMLResponse)
def me(request: Request):
    t = db.tenant_for(request.state.email)
    if not t:
        return RedirectResponse("/", status_code=303)
    return page(request, "me.html", {"t": t})


@app.get("/_platform/me/export")
def me_export(request: Request):
    t = db.tenant_for(request.state.email)
    if not t:
        return RedirectResponse("/", status_code=303)
    data = prov("GET", f"/tenants/{t['slug']}/export")
    db.audit(request.state.email, "tenant.export", t["slug"])
    return StreamingResponse(iter([data]), media_type="application/gzip",
                             headers={"Content-Disposition": f'attachment; filename="jobsearch-{t["slug"]}.tar.gz"'})


@app.post("/_platform/me/delete")
def me_delete(request: Request, csrf: str = Form(""), confirm: str = Form("")):
    email = request.state.email
    check_csrf(request, email, csrf)
    t = db.tenant_for(email)
    if not t:
        return RedirectResponse("/", status_code=303)
    if confirm.strip().upper() != "DELETE":
        return message(request, "Not deleted", "Type DELETE to confirm.", 400, link=("/_platform/me", "Back"))
    res = prov("DELETE", f"/tenants/{t['slug']}")
    db.remove_tenant(t["slug"])
    db.audit(email, "tenant.delete_self", f"{t['slug']} archive={bool(res.get('archive'))}")
    return message(request, "Deleted", "Your workspace and its data were deleted. A sealed backup copy is kept by the "
                                       "administrator for 30 days, then removed.")


# ---- the league --------------------------------------------------------------------------------
@app.get("/_platform/league", response_class=HTMLResponse)
def league_page(request: Request, bad: str = ""):
    t = db.tenant_for(request.state.email)
    if not t:
        return RedirectResponse("/", status_code=303)
    members = db.league()
    rows = league.board(members, tenant_summary, t["slug"]) if t.get("league_name") else []
    mine = next((r for r in rows if r["me"]), None)
    ahead = next((r for r in rows if mine and r["week"] > mine["week"]), None)
    return page(request, "league.html", {"t": t, "rows": rows, "mine": mine, "bad": bad, "members": len(members),
                                         "gap": (rows[0]["week"] - mine["week"]) if mine and rows else 0, "leader": rows[0] if rows else None,
                                         "ahead": ahead, "champion": league.champion(rows) if rows else None,
                                         "suggestion": league.suggestion([m["league_name"] for m in members])})


@app.post("/_platform/league/join")
def league_join(request: Request, csrf: str = Form(""), name: str = Form("")):
    email = request.state.email
    check_csrf(request, email, csrf)
    t = db.tenant_for(email)
    if not t:
        return RedirectResponse("/", status_code=303)
    kept = db.join_league(t["slug"], name)
    if kept:
        db.audit(email, "league.join", t["slug"])
    return RedirectResponse("/_platform/league" + ("" if kept else "?bad=1"), status_code=303)


@app.post("/_platform/league/leave")
def league_leave(request: Request, csrf: str = Form("")):
    email = request.state.email
    check_csrf(request, email, csrf)
    t = db.tenant_for(email)
    if t:
        db.leave_league(t["slug"])
        db.audit(email, "league.leave", t["slug"])
    return RedirectResponse("/_platform/league", status_code=303)


# ---- admin ------------------------------------------------------------------------------------
def require_admin(request):
    if request.state.email not in C.admins:
        raise PermissionError("admins only")


def ops_token(slug):
    """Same derivation as the provisioner's: what a workspace expects before it gives its totals."""
    return hmac.new(C.token.encode(), f"ops:{slug}".encode(), hashlib.sha256).hexdigest()


def tenant_summary(slug):
    """A workspace's totals (how many postings per list, last scan, sources that failed), or {}.
    Counts only: the workspace has no address that gives the operator a title or a name."""
    try:
        r = httpx.get(tenant_url(slug) + "/ops/summary", headers={"Authorization": f"Bearer {ops_token(slug)}"}, timeout=4)
        return r.json() if r.status_code == 200 else {}
    except Exception:  # noqa: BLE001  (not running, or still on a version without totals)
        return {}


def overview():
    """(rows, orphans, error): every workspace with its containers' state and its totals."""
    try:
        live = {t["slug"]: t for t in prov("GET", "/tenants")}
        live_err = ""
    except Exception as e:  # noqa: BLE001
        live, live_err = {}, str(e)
    tenants = db.tenants()
    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
        ops = dict(zip([t["slug"] for t in tenants],
                       pool.map(lambda t: tenant_summary(t["slug"]) if t["status"] == "active" else {}, tenants)))
    rows = []
    for t in tenants:
        o = ops.get(t["slug"]) or {}
        jobs = o.get("jobs") or {}
        rows.append(dict(t, aliases=db.aliases(t["slug"]), ops=o, total=sum(jobs.values()),
                         applied=sum(jobs.get(k, 0) for k in ("applied", "interview", "offer", "rejected")),
                         **{k: live.get(t["slug"], {}).get(k, "?") for k in ("web", "sched", "image")}))
    return rows, [s for s in live if not db.tenant(s)], live_err


def backups():
    try:
        return prov("GET", "/backups")
    except Exception:  # noqa: BLE001
        return None


def _watch():
    """Every HEALTH_CHECK_HOURS: tell the operator (NOTIFY_WEBHOOK) when the list of problems changed."""
    time.sleep(120)
    while True:
        try:
            rows, _, err = overview()
            lines = ([f"provisioner unreachable: {err[:80]}"] if err else []) + health.problems(rows, backups())
            digest = "\n".join(lines)
            if digest != db.get_kv("health_digest"):
                db.set_kv("health_digest", digest)
                if digest:
                    notify.admins(prov, "🇨🇭 Job platform: needs a look", f"{digest}\n{C.public_url}/_platform/admin")
        except Exception as e:  # noqa: BLE001
            print(f"[health] check failed: {type(e).__name__}: {str(e)[:160]}")
        time.sleep(max(600, C.health_hours * 3600))


@app.get("/_platform/admin", response_class=HTMLResponse)
def admin(request: Request, new: str = ""):
    require_admin(request)
    rows, orphans, live_err = overview()
    bk = backups()
    link = f"{C.public_url or ''}/_platform/invite/{new}" if new else ""
    return page(request, "admin.html", {"tenants": rows, "orphans": orphans, "invites": db.invites(),
                                        "requests": db.requests(), "notify_on": notify.configured(),
                                        "audit": db.audit_log(30), "new_link": link, "live_err": live_err,
                                        "backup": bk, "problems": health.problems(rows, bk),
                                        "max": C.max_tenants})


@app.post("/_platform/admin/invite")
def admin_invite(request: Request, csrf: str = Form(""), note: str = Form(""), email: str = Form(""),
                 days: int = Form(7), uses: int = Form(1)):
    require_admin(request)
    check_csrf(request, request.state.email, csrf)
    uses = 1 if email.strip() else max(1, min(uses, C.max_tenants))     # a link locked to one email is for one person
    token = db.create_invite(request.state.email, note.strip()[:100], max(1, min(days, 30)), email.strip(), uses)
    db.audit(request.state.email, "invite.create", f"{note.strip()[:60]} {email.strip()} x{uses}")
    # the token goes back once, in the URL of the admin page (only admins can open it)
    return RedirectResponse(f"/_platform/admin?new={token}", status_code=303)


@app.post("/_platform/admin/invite/{iid}/revoke")
def admin_revoke(request: Request, iid: int, csrf: str = Form("")):
    require_admin(request)
    check_csrf(request, request.state.email, csrf)
    db.revoke_invite(iid)
    db.audit(request.state.email, "invite.revoke", str(iid))
    return RedirectResponse("/_platform/admin", status_code=303)


@app.post("/_platform/admin/tenant/{slug}/address")
def admin_address(request: Request, slug: str, csrf: str = Form(""), email: str = Form(""), remove: str = Form("")):
    """Add (or remove) another sign-in address for the same person, e.g. their Gmail next to their Hotmail."""
    require_admin(request)
    check_csrf(request, request.state.email, csrf)
    t = db.tenant(slug)
    email = (remove or email).strip().lower()
    if not t or not re.fullmatch(r"[^@\s,]+@[^@\s,]+\.[^@\s,]+", email):
        return message(request, "Not changed", "Unknown workspace or not an e-mail address.", 400, link=("/_platform/admin", "Back"))
    if remove:
        db.remove_alias(slug, email)
    elif len(db.aliases(slug)) >= 5 or not db.add_alias(slug, email):
        return message(request, "Not added", f"{email} already opens a workspace, or this one has 5 extra addresses.", 400,
                       link=("/_platform/admin", "Back"))
    try:                                   # the workspace re-checks who may enter: tell it
        prov("PUT", f"/tenants/{slug}", json={"email": t["email"], "extra_emails": db.aliases(slug)})
    except Exception as e:  # noqa: BLE001
        if not remove:
            db.remove_alias(slug, email)
        return message(request, "Not changed", f"The workspace couldn't be updated: {e}", 500, link=("/_platform/admin", "Back"))
    db.audit(request.state.email, "tenant.address." + ("remove" if remove else "add"), f"{slug} {email}")
    return RedirectResponse("/_platform/admin", status_code=303)


@app.post("/_platform/admin/tenant/{slug}/{action}")
def admin_tenant(request: Request, slug: str, action: str, csrf: str = Form(""), confirm: str = Form("")):
    require_admin(request)
    check_csrf(request, request.state.email, csrf)
    t = db.tenant(slug)
    if not t or action not in ("stop", "start", "recreate", "delete"):
        return message(request, "Unknown", "No such workspace or action.", 404)
    if action == "delete":
        if confirm.strip() != slug:
            return message(request, "Not deleted", f"Type the workspace id ({slug}) to confirm.", 400,
                           link=("/_platform/admin", "Back"))
        prov("DELETE", f"/tenants/{slug}")
        db.remove_tenant(slug)
    elif action == "recreate":
        prov("PUT", f"/tenants/{slug}", json={"email": t["email"], "extra_emails": db.aliases(slug)})
    else:
        prov("POST", f"/tenants/{slug}/{action}")
        db.set_status(slug, "active" if action == "start" else "suspended")
    db.audit(request.state.email, f"tenant.{action}", slug)
    return RedirectResponse("/_platform/admin", status_code=303)
