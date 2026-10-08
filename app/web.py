import datetime
import hmac
import os
import re
import json
import threading

from urllib.parse import urlparse

from fastapi import FastAPI, Request, Form
from fastapi.responses import RedirectResponse, HTMLResponse, PlainTextResponse, FileResponse, Response
from fastapi.templating import Jinja2Templates

from . import (agenda, auth, commute, compose, config, docs, enrich, fetch, filters, i18n, listfilter, locales, letter, onboard, places, prefs,
               prep, report, requirements, roles, skills, store, strength, suggest, tailor, tune, twins, weekly)
from .importers import cvparse, extract, linkedin

store.init_db()

app = FastAPI(title="Swiss Job Agent", docs_url=None, redoc_url=None, openapi_url=None)
_envs = i18n.environments(os.path.join(os.path.dirname(__file__), "templates"), locales.TEMPLATES)
templates = {lang: Jinja2Templates(env=env) for lang, env in _envs.items()}       # one per interface language


SECURITY_HEADERS = {"X-Frame-Options": "DENY", "X-Content-Type-Options": "nosniff",
                    "Referrer-Policy": "same-origin", "Content-Security-Policy": "frame-ancestors 'none'; base-uri 'self'; object-src 'none'"}


def _cross_site(request):
    """A state-changing request sent by another site (CSRF), judged from Sec-Fetch-Site / Origin."""
    if request.method in ("GET", "HEAD", "OPTIONS"):
        return False
    if request.headers.get("sec-fetch-site", "same-origin") not in ("same-origin", "none"):
        return True
    origin = request.headers.get("origin")
    host = request.headers.get("x-forwarded-host") or request.headers.get("host")
    return bool(origin) and re.sub(r"^https?://", "", origin) != host


@app.middleware("http")
async def require_access(request: Request, call_next):
    i18n.use(ui_lang(request))
    if _cross_site(request):
        return PlainTextResponse("Cross-site request refused", status_code=403)
    resp = await _guarded(request, call_next)
    for k, v in SECURITY_HEADERS.items():
        resp.headers.setdefault(k, v)
    return resp


async def _guarded(request, call_next):
    if request.url.path.startswith("/calendar/") or request.url.path == "/ops/summary":
        return await call_next(request)         # no sign-in possible there: each checks its own key in the route
    if auth.ENABLED and request.url.path != "/healthz":
        token = (request.headers.get("cf-access-jwt-assertion")
                 or request.cookies.get("CF_Authorization"))
        email = auth.user_email(token)
        if not email:
            return PlainTextResponse("Forbidden", status_code=403)
        request.state.user = email
    if onboard.needed() and not request.url.path.startswith(("/onboarding", "/healthz", "/cv/role/", "/lang")):
        return RedirectResponse("/onboarding", status_code=303)
    return await call_next(request)


def _safe_url(u):
    """Only keep http(s) links so a stored URL can't become a javascript: href."""
    u = (u or "").strip()
    return u if urlparse(u).scheme in ("http", "https") else ""


for _env in _envs.values():
    _env.filters["safe_url"] = _safe_url        # every rendered link goes through this


def ui_lang(request):
    """Interface language of this request: the person's setting, else the browser's."""
    return i18n.pick(config.UI_LANG or request.cookies.get("lang", ""), request.headers.get("accept-language", ""))


def render(request, name, ctx):
    ctx["user"] = getattr(request.state, "user", "")
    ctx["platform"] = config.PLATFORM_TENANT      # runs behind the platform gateway
    lang = ui_lang(request)
    i18n.use(lang)
    return templates[lang].TemplateResponse(request, name, ctx)


@app.post("/lang")
def set_lang(lang: str = Form(""), next: str = Form("")):
    """The flags of the top bar: the language of the site, kept as the person's setting (and in a
    cookie, so the sign-up and account pages of a platform follow)."""
    lang = lang if lang in i18n.LANGS else ""
    if not onboard.needed():                           # (the wizard writes the settings itself at its end)
        config.save_settings({**{k: getattr(config, k) for k in config.EDITABLE}, "UI_LANG": lang})
    resp = RedirectResponse(_local(next, "/"), status_code=303)
    resp.set_cookie("lang", lang, max_age=365 * 86400, path="/", samesite="lax", httponly=True)
    return resp


@app.get("/", response_class=HTMLResponse)
def root():
    return RedirectResponse("/jobs?status=new")


def _visit():
    """When the person was last here before this visit ("" the first time). A visit lasts 4 hours:
    coming back later the same day shows what arrived in between as new."""
    meta = store.get_meta()
    last, prev = meta.get("visit_at", ""), meta.get("visit_prev", "")
    try:
        old = not last or (datetime.datetime.fromisoformat(store.now()) - datetime.datetime.fromisoformat(last)).total_seconds() > 4 * 3600
    except ValueError:
        old = True
    if old:
        store.set_meta(visit_prev=last, visit_at=store.now())
        return last
    return prev


BEST = 10        # how many postings "Best new" shows


@app.get("/jobs", response_class=HTMLResponse)
def jobs(request: Request, status: str = "new", view: str = "", done: int = -1, q: str = "", role: str = "",
         days: str = "", km: str = "", sort: str = "best"):
    if status not in store.STATUSES:
        status = "new"
    meta = store.get_meta()
    rows = store.list_jobs(status)
    if status in ("new", "shortlisted"):
        rows = twins.group(rows)                 # the same job from several agencies: one card
    since = _visit() or (datetime.datetime.fromisoformat(store.now()) - datetime.timedelta(hours=48)).isoformat()
    for j in rows:
        j["fresh"] = status == "new" and j.get("origin") != "manual" and (j.get("created_at") or "") > since
    fresh = [j for j in rows if j["fresh"]] if status == "new" else []
    best = view == "best" and status == "new"
    if best:
        rows = fresh[:BEST]
    num = lambda v: int(v) if str(v).isdigit() else 0  # noqa: E731
    shown, flt = listfilter.apply(rows, q, role, num(days), num(km), sort, ui_lang(request))
    if not best:
        rows = shown                              # search and filters of the bar on top of the list
    return render(request, "dashboard.html", {
        "f": flt,
        "view": "best" if best else "", "fresh_n": min(BEST, len(fresh)), "done": done,
        "bulk": status in ("new", "shortlisted") and len(rows) > 1,
        "scanning": fetch.is_running(),
        "meta": meta,
        "scan_report": _json(meta.get("last_scan_report"), {}),
        "scan_warnings": _json(meta.get("last_scan_warnings"), []),
        "jobs": rows,
        "status": status,
        "statuses": store.STATUSES,
        "counts": store.counts(),
        "reasons": store.DISCARD_REASONS,
        "orp": report.month_progress(), "assigned": store.assignments_open(), "waiting": store.awaiting_answer(),
        "followups": store.followups_due(14),
    })


@app.get("/job/{jid}", response_class=HTMLResponse)
def job_detail(request: Request, jid: int):
    job = store.get_job(jid)
    if not job:
        return RedirectResponse("/jobs?status=new")
    job["url"] = _safe_url(job.get("url"))
    if job["url"] and not job.get("enriched_at") and job.get("origin") != "manual":
        full = enrich.full_description(job["url"])
        if full and len(full) > len(job.get("description") or ""):
            job["description"] = full
        if enrich.looks_like_html(job.get("description")):
            job["description"] = enrich.html_to_text(job["description"])
        if full is not None:          # fetch failed -> leave unmarked, retry next view
            store.set_description(jid, job.get("description") or "")
    elif enrich.looks_like_html(job.get("description")):
        job["description"] = enrich.html_to_text(job["description"])
        store.set_description(jid, job["description"])
    desc_html, have, missing, avoided = skills.analyse(job.get("description") or "")
    if job.get("commute_min") is None and job.get("status") not in ("discarded", "rejected"):
        try:                                        # travel time from home, asked once per town
            m = commute.minutes(commute.home(), commute.town(job.get("location")))
            if m is not None:
                job["commute_min"] = m
                with store.conn() as c:
                    c.execute("UPDATE jobs SET commute_min=? WHERE id=?", (m, jid))
        except Exception:  # noqa: BLE001  (timetable unreachable: the page still opens)
            pass
    profile = tailor.load_profile()
    _base_letter(profile)
    follow = ""
    if profile and job.get("status") == "applied" and job.get("applied_date"):
        cv, lang = tailor.localized(profile, job)
        follow = compose.followup(cv, job, lang)
    return render(request, "detail.html", {
        "flags": requirements.flags(job.get("description") or ""), "followup_text": follow, "docs": docs.checklist(job),
        "cv_versions": store.cv_versions(), "kept": request.query_params.get("kept", ""),
        "letter_versions": store.cv_versions("letter"), "lkept": request.query_params.get("lkept", ""),
        "home_town": commute.home(), "blocked": not filters.company_ok(job.get("company")),
        "job": job, "statuses": store.STATUSES, "reasons": store.DISCARD_REASONS, "desc_html": desc_html, "have": have, "missing": missing,
        "avoided": avoided,
        "methods": store.APPLY_METHODS, "letter_engine": letter.config_note(), "cv_note": tailor.cv_note(),
        "can_tailor": tailor.load_profile() is not None,
        "has_cv": os.path.exists(tailor.cv_path(jid)),
    })


@app.post("/job/{jid}/cv")
def make_cv(jid: int, source: str = Form("")):
    """Write the CV of a job as text: from the profile, tailored to the posting, or from one of
    the person's named versions (source = its id), as it is."""
    job, profile = store.get_job(jid), tailor.load_profile()
    if not job or not profile:
        return PlainTextResponse("No job or no candidate profile configured.", status_code=404)
    version = store.cv_version(int(source)) if source.isdigit() else None
    text = version["text"] if version else tailor.draft_text(job, profile)     # written out first: the person can edit it
    store.update_fields(jid, {"cv_text": text, **({"cv_version": version["name"]} if version else {})})
    tailor.build_from_text(job, profile, text)
    return RedirectResponse(f"/job/{jid}#cv", status_code=303)


@app.post("/job/{jid}/cv/save")
def save_cv(jid: int, text: str = Form(""), then: str = Form(""), name: str = Form("")):
    """The edited text of a job's CV: kept, and the PDF is made again from it, as written.
    then = "version": also keep it as a named version; "default": as the version new CVs start from."""
    job, profile = store.get_job(jid), tailor.load_profile()
    if not job or not profile:
        return PlainTextResponse("No job or no candidate profile configured.", status_code=404)
    text = text[:tailor.MAX_CV_TEXT]
    fields, kept = {"cv_text": text}, ""
    if then in ("version", "default"):
        name = " ".join(name.split())[:60] or ((store.default_cv_version() or {}).get("name") if then == "default" else "") \
            or (job.get("title") or "CV")[:60]
        if store.save_cv_version(name, text, default=True if then == "default" else None):
            fields["cv_version"], kept = name, "&kept=1"
        else:
            kept = "&kept=0"
    store.update_fields(jid, fields)
    tailor.build_from_text(job, profile, text)
    return RedirectResponse(f"/job/{jid}?{kept[1:]}#cv" if kept else f"/job/{jid}#cv", status_code=303)


BASE_LETTER = {"fr": "Lettre de base", "de": "Basisbrief", "it": "Lettera di base", "en": "Base letter"}


def _base_letter(profile):
    """Once per person: a base letter written from their profile, kept under "My letters" to adapt and
    reuse. Made the first time the letters are shown; deleting it doesn't bring it back."""
    if not profile or store.get_meta().get("base_letter") or store.cv_versions("letter"):
        return
    store.set_meta(base_letter=store.now())
    store.save_cv_version(BASE_LETTER.get(tailor._profile_lang(profile), BASE_LETTER["en"]), letter.blank(profile), kind="letter")


# ---- CV versions: named texts kept to apply to jobs -------------------------------------------
@app.get("/cv/versions", response_class=HTMLResponse)
def cv_versions_page(request: Request, saved: str = ""):
    _base_letter(tailor.load_profile())
    return render(request, "versions.html", {"versions": store.cv_versions(), "letters": store.cv_versions("letter"),
                                             "profile": tailor.load_profile(),
                                             "saved": saved, "limit": store.MAX_CV_VERSIONS})


@app.post("/cv/versions")
def cv_version_new(name: str = Form(""), kind: str = Form("cv")):
    profile = tailor.load_profile()
    if not profile:
        return RedirectResponse("/cv", status_code=303)
    kind = kind if kind in store.KINDS else "cv"
    text = letter.blank(profile) if kind == "letter" else tailor.profile_text(profile)
    vid = store.save_cv_version(name, text, kind=kind) if not any(
        v["name"].lower() == " ".join(name.split()).lower() for v in store.cv_versions(kind)) else None
    return RedirectResponse(f"/cv/versions?saved=1#v{vid}" if vid else "/cv/versions?saved=0", status_code=303)


@app.post("/cv/versions/{vid}")
def cv_version_change(vid: int, action: str = Form("save"), name: str = Form(""), text: str = Form("")):
    v = store.cv_version(vid)
    if not v:
        return RedirectResponse("/cv/versions", status_code=303)
    if action == "delete":
        store.delete_cv_version(vid)
        return RedirectResponse("/cv/versions", status_code=303)
    if action == "default":
        ok = store.save_cv_version(v["name"], v["text"], vid, default=True)
    elif action == "undefault":
        ok = store.save_cv_version(v["name"], v["text"], vid, default=False)
    else:
        ok = store.save_cv_version(name or v["name"], text[:tailor.MAX_CV_TEXT] or v["text"], vid)
    return RedirectResponse(f"/cv/versions?saved={'1' if ok else '0'}#v{vid}", status_code=303)


@app.get("/cv/versions/{vid}.pdf")
def cv_version_pdf(vid: int):
    v, profile = store.cv_version(vid), tailor.load_profile()
    if not v or not profile:
        return PlainTextResponse("No such CV version.", status_code=404)
    if v["kind"] == "letter":
        path = letter.pdf(profile, {"company": v["name"]}, v["text"], os.path.join(tailor.CV_DIR, f"letter-version-{vid}.pdf"))
        return FileResponse(path, media_type="application/pdf", content_disposition_type="inline",
                            filename=tailor.download_name(profile, {"company": v["name"]}).replace("_CV_", "_Letter_"))
    path = tailor.build_version(profile, v)
    return FileResponse(path, media_type="application/pdf", filename=tailor.download_name(profile, {"company": v["name"]}),
                        content_disposition_type="inline")


@app.get("/cv/photo.jpg")
def cv_photo():
    if not os.path.exists(tailor.PHOTO):
        return PlainTextResponse("No photo.", status_code=404)
    return FileResponse(tailor.PHOTO, media_type="image/jpeg", headers={"Cache-Control": "no-store"})


@app.post("/cv/photo")
async def cv_photo_save(request: Request):
    """The portrait shown on every CV: upload one (kept as a small JPEG), or remove it."""
    form = await request.form()
    if form.get("remove"):
        tailor.remove_photo()
        return RedirectResponse("/cv#photo", status_code=303)
    f = form.get("photo")
    data = await f.read(extract.MAX_UPLOAD + 1) if getattr(f, "filename", "") else b""
    ok = bool(data) and len(data) <= extract.MAX_UPLOAD and tailor.save_photo(data)
    return RedirectResponse("/cv?photo=" + ("1" if ok else "0") + "#photo", status_code=303)


@app.get("/job/{jid}/cv")
def get_cv(jid: int, dl: int = 0):
    job, profile, path = store.get_job(jid), tailor.load_profile(), tailor.cv_path(jid)
    if not job or not profile or not os.path.exists(path):
        return PlainTextResponse("No tailored CV for this role yet.", status_code=404)
    return FileResponse(path, media_type="application/pdf", filename=tailor.download_name(profile, job),
                        content_disposition_type="attachment" if dl else "inline")


def _json(raw, default):
    try:
        return json.loads(raw) if raw else default
    except ValueError:
        return default


def _local(path, default):
    """Only follow same-site relative redirects."""
    return path if path.startswith("/") and not path.startswith("//") else default


def _ids(raw):
    return [int(x) for x in re.findall(r"\d+", raw or "")][:30]


@app.post("/job/{jid}/status")
def set_status(jid: int, status: str = Form(...), next: str = Form(""), twins: str = Form("")):
    store.update_status(jid, status)
    for t in _ids(twins) if status in store.STATUSES else []:          # the copies of the same job follow
        store.dismiss(t, "duplicate", True) if status == "applied" else store.update_status(t, status)
    return RedirectResponse(_local(next, f"/job/{jid}"), status_code=303)


def _quick(request, state, next, default):
    """Answer of a one-click list button: JSON when the page asked with fetch, else back to the list."""
    if request.headers.get("x-requested-with") == "fetch":
        return {"state": state, "counts": store.counts()}
    return RedirectResponse(_local(next, default), status_code=303)


@app.post("/job/{jid}/dismiss")
def dismiss(request: Request, jid: int, next: str = Form(""), reason: str = Form(""), now: str = Form(""),
            twins: str = Form("")):
    state = store.dismiss(jid, reason, bool(now))
    for t in _ids(twins):
        store.dismiss(t, reason or "duplicate", True) if state == "discarded" else store.dim(t)
    return _quick(request, state, next, "/jobs?status=new")


@app.post("/jobs/bulk")
async def jobs_bulk(request: Request):
    """Several cards at once: discard the ticked ones (with one reason), shortlist them, or discard
    everything of the list under a score."""
    form = await request.form()
    status = form.get("status") if form.get("status") in ("new", "shortlisted") else "new"
    action, reason = form.get("action"), str(form.get("reason") or "")
    rows = store.list_jobs(status)
    if action == "below":
        try:
            ids = store.below_score(status, min(101, max(0, int(str(form.get("below")).strip()))))
        except ValueError:
            ids = []
    else:
        ids = twins.expand([int(i) for i in form.getlist("ids") if str(i).isdigit()], rows)
    mine, n = {j["id"] for j in rows}, 0
    for i in ids:
        if i in mine:
            store.update_status(i, "shortlisted") if action == "shortlist" else store.dismiss(i, reason, True)
            n += 1
    return RedirectResponse(f"/jobs?status={status}&done={n}", status_code=303)


@app.post("/job/{jid}/filled")
def filled(request: Request, jid: int, next: str = Form(""), twins: str = Form("")):
    """One click: the position is filled already (refusal if applied to, else out of the list)."""
    for t in _ids(twins):
        store.mark_filled(t)
    return _quick(request, "moved" if store.mark_filled(jid) else None, next, f"/job/{jid}")


@app.post("/job/{jid}/keep")
def keep(request: Request, jid: int, next: str = Form(""), twins: str = Form("")):
    for t in [jid] + _ids(twins):
        store.keep(t)
    return _quick(request, "kept", next, "/jobs?status=new")


def _start_background(fn):
    threading.Thread(target=fn, daemon=True).start()


@app.post("/skills")
def refine_skills(action: str = Form(...), term: str = Form(...), next: str = Form("/cv")):
    """A click on a skill chip: refine the CV skills / avoided words, then rescore open jobs
    so the queue re-orders now; the next scan uses the same lists."""
    if prefs.apply(action, term):
        store.rescore(fetch.score_job)
    return RedirectResponse(_local(next, "/cv"), status_code=303)


SEARCH_KEYS = ("SEARCH_TERMS", "WHERE", "PROVIDERS", "LANGUAGES", "TITLE_KEYWORDS", "TITLE_EXCLUDE", "LOCATION_KEYWORDS",
               "ALLOW_REMOTE", "JOBROOM_CANTONS", "COMPANY_EXCLUDE", "WORK_RATE_MIN", "WORK_RATE_MAX")
RESCAN_GAP = 180        # seconds between two scans started by a change of settings


def _searched():
    return {k: getattr(config, k) for k in SEARCH_KEYS}


def _rescan():
    """What is searched has changed: scan now instead of at the next scheduled time. Several saves
    in a row start one scan, not one each. Returns whether a scan is running or was started."""
    if fetch.is_running():
        return True
    started = store.get_meta().get("scan_started_at", "")
    try:
        recent = bool(started) and (datetime.datetime.fromisoformat(store.now())
                                    - datetime.datetime.fromisoformat(started)).total_seconds() < RESCAN_GAP
    except ValueError:
        recent = False
    if recent:
        return False
    _start_background(fetch.run)
    return True


@app.post("/scan")
def scan_now():
    if not fetch.is_running():
        _start_background(fetch.run)
    return RedirectResponse("/jobs?status=new", status_code=303)


@app.post("/job/{jid}/fields")
def set_fields(
    jid: int,
    contact: str = Form(""),
    recruiter: str = Form(""),
    cv_version: str = Form(""),
    applied_date: str = Form(""),
    followup_date: str = Form(""),
    notes: str = Form(""),
    work_rate: str = Form(""),
    apply_method: str = Form("written"),
    orp_assigned: str = Form(""),
    outcome_note: str = Form(""),
    orp_deadline: str = Form(""),
    interview_at: str = Form(""),
):
    store.update_fields(jid, {
        "interview_at": interview_at if re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}", interview_at or "") else "",
        "orp_deadline": orp_deadline if re.fullmatch(r"\d{4}-\d{2}-\d{2}", orp_deadline or "") else "",
        "contact": contact, "recruiter": recruiter, "cv_version": cv_version,
        "applied_date": applied_date, "followup_date": followup_date, "notes": notes,
        "work_rate": work_rate, "outcome_note": outcome_note, "orp_assigned": 1 if orp_assigned else 0,
        "apply_method": apply_method if apply_method in store.APPLY_METHODS else "written",
    })
    return RedirectResponse(f"/job/{jid}", status_code=303)


@app.post("/job/{jid}/docs")
async def set_docs(request: Request, jid: int):
    """The documents ticked as ready for this application."""
    form = await request.form()
    store.update_fields(jid, {"docs": docs.dump([str(k) for k in form.getlist("docs")])})
    return RedirectResponse(f"/job/{jid}#docs", status_code=303)


# ---- cover letter ------------------------------------------------------------
@app.post("/job/{jid}/letter")
def make_letter(jid: int, source: str = Form("")):
    """Write the letter of a job: from the profile for this posting, or from one of the person's
    kept letters (source = its id) with this job's company, title, place and today's date."""
    job, profile = store.get_job(jid), tailor.load_profile()
    if not job or not profile:
        return PlainTextResponse("No job or no candidate profile configured.", status_code=404)
    version = store.cv_version(int(source), "letter") if source.isdigit() else None
    text = letter.from_template(version["text"], profile, job) if version else letter.write(profile, job)[0]
    store.update_fields(jid, {"letter": text})
    return RedirectResponse(f"/job/{jid}#letter", status_code=303)


@app.post("/job/{jid}/letter/save")
def save_letter(jid: int, text: str = Form(""), then: str = Form(""), name: str = Form("")):
    """then = "version": also keep the letter under a name for other jobs; "default": as the one offered first."""
    job = store.get_job(jid)
    if not job:
        return RedirectResponse("/jobs?status=new", status_code=303)
    text = text[:tailor.MAX_CV_TEXT]
    store.update_fields(jid, {"letter": text})
    kept = ""
    if then in ("version", "default"):
        name = " ".join(name.split())[:60] or ((store.default_cv_version("letter") or {}).get("name") if then == "default" else "") \
            or (job.get("title") or "Letter")[:60]
        ok = store.save_cv_version(name, letter.to_template(text, job), default=True if then == "default" else None, kind="letter")
        kept = "?lkept=1" if ok else "?lkept=0"
    return RedirectResponse(f"/job/{jid}{kept}#letter", status_code=303)


@app.get("/job/{jid}/letter.pdf")
def letter_pdf(jid: int):
    job, profile = store.get_job(jid), tailor.load_profile()
    if not job or not profile or not job.get("letter"):
        return PlainTextResponse("No letter for this role yet.", status_code=404)
    out = letter.pdf(profile, job, job["letter"], os.path.join(tailor.CV_DIR, f"letter-{jid}.pdf"))
    name = tailor.download_name(profile, job).replace("_CV_", "_Letter_")
    return FileResponse(out, media_type="application/pdf", filename=name, content_disposition_type="attachment")


# ---- keyword CV ------------------------------------------------------------
def _cv_ctx(profile, **extra):
    targets = onboard.state().get("targets") or {}
    first = (targets.get("roles") or (roles.suggest(profile) if profile else []) or [""])[0]
    asked, of = suggest.missing_skills() if profile else ([], 0)
    own = tailor._profile_lang(profile) if profile else ""
    ctx = {"profile": profile, "keywords": store.get_meta().get("cv_keywords", ""),
           "has_photo": os.path.exists(tailor.PHOTO), "asked": asked, "asked_of": of, "check": strength.report(profile) if profile else None,
           "translatable": [l for l in ("fr", "de", "it", "en") if l != own] if profile else [],
           "built": os.path.exists(tailor.CUSTOM_CV), "prefs": prefs.summary(),
           "versions": tailor.profile_versions(),
           "roles": [{"id": r["id"], "label": roles.label(r, i18n.current())} for r in roles.ROLES], "role_default": first}
    ctx.update(extra)
    return ctx


@app.get("/cv", response_class=HTMLResponse)
def cv_page(request: Request, photo: str = ""):
    return render(request, "cv.html", _cv_ctx(tailor.load_profile(), photo=photo))


@app.post("/cv", response_class=HTMLResponse)
def cv_build(request: Request, keywords: str = Form("")):
    profile = tailor.load_profile()
    if not profile:
        return PlainTextResponse("No candidate profile configured.", status_code=404)
    store.set_meta(cv_keywords=keywords)
    words = [k for k in keywords.replace("\n", ",").split(",") if k.strip()]
    _, sup, unsup = tailor.build_custom(profile, words)
    return render(request, "cv.html", _cv_ctx(profile, keywords=keywords, built=True, supported=sup,
                                              unsupported=unsup))


@app.get("/cv/custom.pdf")
def cv_custom_pdf():
    profile = tailor.load_profile()
    if not profile or not os.path.exists(tailor.CUSTOM_CV):
        return PlainTextResponse("No CV generated yet.", status_code=404)
    name = tailor.download_name(profile, {"company": "keywords"})
    return FileResponse(tailor.CUSTOM_CV, media_type="application/pdf", filename=name,
                        content_disposition_type="inline")


# ---- profile in another language, written next to the original --------------------------------
def _translatable(lang):
    profile = tailor.load_profile()
    return profile if profile and lang in tailor.HEADINGS and lang != tailor._profile_lang(profile) else None


@app.get("/profile/translate/{lang}", response_class=HTMLResponse)
def translate_form(request: Request, lang: str, saved: int = -1):
    profile = _translatable(lang)
    if not profile:
        return RedirectResponse("/cv", status_code=303)
    fields = strength.fields(profile)
    return render(request, "translate.html", {"lang": lang, "fields": fields, "done": strength.translation(profile, lang),
                                              "saved": saved, "total": len(fields)})


@app.post("/profile/translate/{lang}")
async def translate_save(request: Request, lang: str):
    profile = _translatable(lang)
    if not profile:
        return RedirectResponse("/cv", status_code=303)
    n = strength.save_translation(profile, lang, await request.form())
    return RedirectResponse(f"/profile/translate/{lang}?saved={n}", status_code=303)


# ---- the week, and the calendar feed ------------------------------------------------------------
def _base(request):
    host = request.headers.get("x-forwarded-host") or request.headers.get("host", "")
    return f'{request.headers.get("x-forwarded-proto", request.url.scheme)}://{host}'


@app.get("/week", response_class=HTMLResponse)
def week_page(request: Request):
    return render(request, "week.html", {"w": weekly.summary()})


@app.get("/calendar/{name}")
def calendar_feed(request: Request, name: str):
    """The calendar feed. No sign-in (a calendar app can't): the key in the address is the access."""
    if not name.endswith(".ics") or not agenda.valid(name[:-4]) or onboard.needed():
        return PlainTextResponse("Not found", status_code=404)
    return Response(agenda.ics(base=_base(request)), media_type="text/calendar; charset=utf-8",
                    headers={"Cache-Control": "private, max-age=900"})


@app.post("/settings/calendar")
def calendar_reset():
    agenda.reset()
    return RedirectResponse("/settings#calendar", status_code=303)


def _kind(errors):
    """What went wrong with a source, without its text (which may hold search words): "HTTP 403", "Timeout"..."""
    m = re.search(r"HTTP \d{3}|\b\d{3}\b(?= )|[A-Z][A-Za-z]+(?:Error|Timeout|Exception)|timed out|crashed", " ".join(errors or []))
    return (m.group(0) if m else "error") if errors else ""


@app.get("/ops/summary")
def ops_summary(request: Request):
    """Totals for whoever runs the installation (the platform's admin page): how many postings per
    list, when the last scan ran, which sources failed. Counts only: no title, no company, no name.
    Needs OPS_TOKEN (set by the platform for each workspace); without it this address doesn't exist."""
    token = os.environ.get("OPS_TOKEN", "")
    given = request.headers.get("authorization", "")
    if not token or not hmac.compare_digest(given.encode(), f"Bearer {token}".encode()):
        return PlainTextResponse("Not found", status_code=404)
    meta = store.get_meta()
    rep = _json(meta.get("last_scan_report"), {})
    return {"jobs": store.counts(), "last_scan_at": meta.get("last_scan_at", ""), "last_scan_new": meta.get("last_scan_new", ""),
            "last_visit_at": meta.get("visit_at", ""), "setup_done": not onboard.needed(), "scanning": fetch.is_running(),
            "sources": {src: {"count": r.get("count", 0), "errors": len(r.get("errors") or []), "kind": _kind(r.get("errors"))}
                        for src, r in rep.items()}}


# ---- stats + ORP report -------------------------------------------------------
@app.get("/stats", response_class=HTMLResponse)
def stats_page(request: Request):
    st = report.stats()
    return render(request, "stats.html", {"s": st, "discards": report.discard_stats(),
                                          "wmax": max([c for _, c in st["weeks"]] + [1]),
                                          "mmax": max([c for _, c in st["months"]] + [1])})


@app.get("/stats/discarded.csv")
def discarded_csv():
    """Every discarded posting with its reason: to keep, or to send to whoever tunes the search."""
    return Response(report.discarded_csv(), media_type="text/csv; charset=utf-8",
                    headers={"Content-Disposition": 'attachment; filename="discarded-jobs.csv"'})


def _period(month, week):
    if week and not re.fullmatch(r"\d{4}-W\d{2}", week):
        week = None
    if month and not re.fullmatch(r"\d{4}-\d{2}", month):
        month = None
    return report.period(month, week)


@app.get("/report", response_class=HTMLResponse)
def report_page(request: Request, month: str = "", week: str = ""):
    kind, key, start, end, label = _period(month, week)
    profile = tailor.load_profile() or {}
    return render(request, "report.html", {
        "rows": report.rows(start, end), "cols": report.COLUMNS, "link_col": report.LINK, "label": label, "kind": kind, "key": key,
        "prev": report.shift(kind, key, -1), "next": report.shift(kind, key, 1),
        "target": report.target(), "name": profile.get("name", ""),
        "qs": f"{kind}={key}"})


@app.get("/report.csv")
def report_csv(month: str = "", week: str = ""):
    kind, key, start, end, _ = _period(month, week)
    return Response(report.to_csv(report.rows(start, end)), media_type="text/csv; charset=utf-8",
                    headers={"Content-Disposition": f'attachment; filename="recherches-{key}.csv"'})


@app.get("/report.pdf")
def report_pdf(month: str = "", week: str = "", official: str = ""):
    kind, key, start, end, label = _period(month, week)
    name = (tailor.load_profile() or {}).get("name", "")
    if official and kind == "month":          # the SECO form 716.007 itself, filled in; else our own report
        from . import official as form
        out = form.fill(store.applications(start.isoformat(), end.isoformat()), name, key,
                        os.path.join(tailor.CV_DIR, f"orp-716.007-{key}.pdf"))
        if out:
            return FileResponse(out, media_type="application/pdf", filename=f"preuves-recherches-716.007-{key}.pdf",
                                content_disposition_type="attachment")
    out = report.to_pdf(report.rows(start, end), label, name, os.path.join(tailor.CV_DIR, f"report-{key}.pdf"))
    return FileResponse(out, media_type="application/pdf", filename=f"recherches-emploi-{key}.pdf",
                        content_disposition_type="attachment")


@app.get("/add", response_class=HTMLResponse)
def add_form(request: Request, kind: str = ""):
    return render(request, "add.html", {"statuses": store.STATUSES, "spontaneous": kind == "spontaneous",
                                        "today": store.today(), "methods": store.APPLY_METHODS})


@app.post("/add/spontaneous")
def add_spontaneous(company: str = Form(...), role: str = Form(""), location: str = Form(""), contact: str = Form(""),
                    applied_date: str = Form(""), apply_method: str = Form("written"), url: str = Form(""),
                    notes: str = Form("")):
    """An application sent without a posting (it counts as a job search for the ORP)."""
    role = " ".join(role.split())
    jid = store.add_manual({
        "title": f"Candidature spontanée – {role}" if role else "Candidature spontanée", "company": company,
        "location": location, "url": _safe_url(url), "source": "spontaneous", "status": "applied",
        "description": notes, "origin": "manual"})
    store.update_status(jid, "applied")
    store.update_fields(jid, {
        "contact": contact, "notes": notes,
        "applied_date": applied_date if re.fullmatch(r"\d{4}-\d{2}-\d{2}", applied_date or "") else store.today(),
        "apply_method": apply_method if apply_method in store.APPLY_METHODS else "written"})
    return RedirectResponse(f"/job/{jid}", status_code=303)


@app.post("/job/{jid}/followed-up")
def followed_up(jid: int):
    """The follow-up was sent: note it and stop reminding for two weeks."""
    store.update_fields(jid, {"followed_up_at": store.today()})
    return RedirectResponse(f"/job/{jid}", status_code=303)


@app.get("/job/{jid}/prep.pdf")
def prep_pdf(jid: int):
    job, profile = store.get_job(jid), tailor.load_profile()
    if not job or not profile:
        return PlainTextResponse("No profile or job.", status_code=404)
    out = prep.build(job, profile)
    return FileResponse(out, media_type="application/pdf", content_disposition_type="inline",
                        filename=tailor.download_name(profile, job).replace("_CV_", "_Interview_"))


@app.post("/tune")
def tune_search(action: str = Form(...), name: str = Form(...), value: str = Form(...), next: str = Form("/stats")):
    """One click from Stats or a job page: skip a title word, stop searching a town, block a company."""
    tune.change(action, name, value)
    return RedirectResponse(_local(next, "/stats"), status_code=303)


@app.post("/add")
def add_submit(
    title: str = Form(...),
    company: str = Form(""),
    location: str = Form(""),
    url: str = Form(""),
    source: str = Form("manual"),
    status: str = Form("shortlisted"),
    description: str = Form(""),
):
    jid = store.add_manual({
        "title": title, "company": company, "location": location, "url": _safe_url(url),
        "source": source, "status": status, "description": description, "origin": "manual",
    })
    return RedirectResponse(f"/job/{jid}", status_code=303)


# ---- onboarding wizard --------------------------------------------------------------------
def _lines(text):
    return [x.strip() for x in (text or "").replace("\r", "").split("\n") if x.strip()]


def _csv_list(text):
    return [x.strip() for x in re.split(r"[,\n;]", text or "") if x.strip()]


async def _uploads(form, name):
    """[(filename, bytes)] of a file field (several files allowed)."""
    out = []
    for f in form.getlist(name)[:10]:
        if getattr(f, "filename", ""):
            out.append((f.filename, await f.read(linkedin.MAX_ZIP + 1)))
    return out


def _read_import(filename, data):
    """(draft, kind) for one uploaded file, whatever field it was put in: a ZIP is the LinkedIn export
    (complete or partial), a .csv one file of it, anything else a CV or the LinkedIn profile PDF."""
    if (filename or "").lower().endswith(".csv"):
        return linkedin.parse_csv(filename, data), "linkedin"
    if data[:2] == b"PK" and not (filename or "").lower().endswith(".docx"):
        return linkedin.parse_zip(data), "linkedin"
    return cvparse.parse_any(extract.text_of(filename, data)), "cv"


@app.get("/onboarding", response_class=HTMLResponse)
def onboarding(request: Request):
    st = onboard.state()
    step = st["step"]
    if step == "done":
        return RedirectResponse("/jobs?status=new", status_code=303)
    ctx = {"step": step, "errors": st.pop("errors", []), "d": st["draft"] or onboard.empty_draft(),
           "sources": st.get("sources", [])}
    if st.get("errors") is not None or ctx["errors"]:
        onboard.save_state(st)
    if step == "target":
        t = st["targets"] or onboard.default_targets(st["draft"])
        fams = {}
        for r in roles.ROLES:
            fams.setdefault(FAMILY_LABELS.get(r["family"], r["family"]), []).append(
                {"id": r["id"], "label": roles.label(r, i18n.current())})
        ctx.update(t=t, families=list(fams.items()), towns=places.town_names(),
                   seniority=list(onboard.SENIORITY_LABELS.items()), suggested=roles.suggest(st["draft"]))
    if step == "confirm":
        ctx.update(s=st.get("settings", {}), role_cvs=st.get("role_cvs", []))
    return render(request, "onboarding.html", ctx)


FAMILY_LABELS = {"it": "IT & technology", "business": "Sales & marketing", "retail": "Retail", "services": "Office, customer & operations",
                 "finance": "Finance, legal & banking", "logistics": "Logistics & purchasing", "hospitality": "Hospitality",
                 "design": "Design", "education": "Education & training", "health": "Health care",
                 "engineering": "Engineering & technical"}


@app.post("/onboarding/import")
async def onboarding_import(request: Request):
    form = await request.form()
    st = onboard.state()
    drafts, sources, errors, parts = [], [], [], []
    if not form.get("skip"):
        for field, label in (("cv", "CV"), ("linkedin_zip", "LinkedIn export"), ("linkedin_pdf", "LinkedIn PDF")):
            for name, data in await _uploads(form, field):
                try:
                    draft, kind = _read_import(name, data)
                    if kind == "linkedin":
                        label, found = "LinkedIn export", draft.pop("_parts", [])
                        parts += [p for p in found if p not in parts]
                    drafts.append(draft)
                    if label not in sources:
                        sources.append(label)
                except extract.ImportError_ as e:
                    errors.append(f"{name}: {e}")
                except Exception as e:  # noqa: BLE001
                    errors.append(f"{name}: this file couldn't be read ({type(e).__name__}).")
        if not drafts and not errors:
            errors.append("Choose at least one file, or start from an empty profile.")
        if parts and len(sources) == 1:          # only a partial LinkedIn export: say what is still to fill in
            had, lacks = linkedin.coverage(parts)
            if lacks:
                errors.append(f"Partial LinkedIn export: read {had}. Not in the file: {lacks}. Fill in the rest below, "
                              "or go back and add your CV.")
    if errors and not drafts:
        st["errors"] = errors
        onboard.save_state(st)
        return RedirectResponse("/onboarding", status_code=303)
    st.update(step="review", draft=onboard.merge(drafts) if drafts else onboard.empty_draft(),
              sources=sources, errors=errors, targets={})
    onboard.save_state(st)
    return RedirectResponse("/onboarding", status_code=303)


def _draft_from_form(form):
    langs = []
    for line in _lines(form.get("languages")):
        name, _, level = line.partition(",")
        found = cvparse._languages(name)
        code = found[0]["code"] if found else ""
        canon = found[0]["name"] if found else name.strip()
        langs.append({"name": canon, "code": code, "level": level.strip().lower()})
    exp = []
    for i in range(int(form.get("n_exp") or 0)):
        e = {k: (form.get(f"exp-{i}-{k}") or "").strip() for k in ("title", "org", "loc", "dates")}
        e["bullets"] = _lines(form.get(f"exp-{i}-bullets"))
        exp.append(e)
    return {
        "name": (form.get("name") or "").strip(), "headline": (form.get("headline") or "").strip(),
        "contact": {k: (form.get(k) or "").strip() for k in ("email", "phone", "linkedin", "location")},
        "summary": " ".join((form.get("summary") or "").split()),
        "expertise": _lines(form.get("expertise")), "experience": exp,
        "education": _lines(form.get("education")), "extras_title": (form.get("extras_title") or "").strip(),
        "extras": _lines(form.get("extras")), "skills": [x.lower() for x in _csv_list(form.get("skills"))],
        "languages": langs,
    }


@app.post("/onboarding/review")
async def onboarding_review(request: Request):
    form = await request.form()
    st = onboard.state()
    d = _draft_from_form(form)
    action = form.get("action") or "next"
    if action == "add":
        d["experience"].append({"title": "", "org": "", "loc": "", "dates": "", "bullets": []})
    elif action.startswith("del-") and action[4:].isdigit():
        i = int(action[4:])
        if i < len(d["experience"]):
            d["experience"].pop(i)
    st["draft"] = d
    if action == "back":
        st["step"] = "import"
    elif action == "next":
        if not d["name"]:
            st["errors"] = ["Your name is needed for the CV."]
        elif st.get("editing"):             # "Edit my profile": save it, keep the search as is
            onboard.save_profile(d)
            st.update(step="done", editing=False)
            onboard.save_state(st)
            return RedirectResponse("/cv", status_code=303)
        else:
            st["step"] = "target"
    onboard.save_state(st)
    return RedirectResponse("/onboarding" + ("#experience" if action in ("add",) else ""), status_code=303)


@app.post("/onboarding/target")
async def onboarding_target(request: Request):
    form = await request.form()
    st = onboard.state()
    t = {"roles": [r for r in form.getlist("roles") if roles.get(r)][:5],
         "extra_titles": _csv_list(form.get("extra_titles"))[:10],
         "seniority": form.get("seniority") if form.get("seniority") in onboard.SENIORITY else "mid",
         "home": (form.get("home") or "").strip()[:60],
         "radius": int(form.get("radius") or 30) if str(form.get("radius") or "30").isdigit() else 30,
         "whole_country": bool(form.get("whole_country")), "remote": bool(form.get("remote")),
         "langs": [x for x in form.getlist("langs") if x in onboard.POSTING_LANGS],
         "avoid": _csv_list(form.get("avoid"))[:20]}
    st["targets"] = t
    if form.get("action") == "back":
        st["step"] = "review"
    elif not t["roles"] and not t["extra_titles"]:
        st["errors"] = ["Pick at least one role, or type a job title."]
    elif not t["langs"]:
        st["errors"] = ["Pick at least one posting language."]
    else:
        st["settings"] = onboard.settings_for(st["draft"], t)
        profile = onboard.profile_from_draft(st["draft"])
        cvs = []
        for rid in t["roles"]:
            _, sup, miss = onboard.build_role_cv(profile, rid)
            cvs.append({"id": rid, "label": roles.label(roles.get(rid), i18n.current()), "missing": miss})
        st["role_cvs"] = cvs
        st["step"] = "confirm"
    onboard.save_state(st)
    return RedirectResponse("/onboarding", status_code=303)


@app.post("/onboarding/back")
def onboarding_back():
    st = onboard.state()
    st["step"] = "target"
    onboard.save_state(st)
    return RedirectResponse("/onboarding", status_code=303)


def _settings_from_form(form):
    out = {}
    for k, kind in config.EDITABLE.items():
        if kind == "bool":
            out[k] = bool(form.get(k))
        elif kind == "hours":
            try:
                out[k] = float(form.get(k) or 12)
            except ValueError:
                out[k] = 12
        elif kind == "int":
            try:
                out[k] = int(float(form.get(k) or getattr(config, k)))
            except ValueError:
                out[k] = getattr(config, k)
        elif kind == "text":
            out[k] = (form.get(k) if form.get(k) is not None else getattr(config, k)).strip()
        elif form.get(k) is not None:
            out[k] = [x.strip() for line in _lines(form.get(k)) for x in line.split(",") if x.strip()]
    return out


@app.post("/onboarding/finish")
async def onboarding_finish(request: Request):
    form = await request.form()
    st = onboard.state()
    if st["step"] != "confirm":
        return RedirectResponse("/onboarding", status_code=303)
    onboard.finish(st["draft"], st["targets"], _settings_from_form(form))
    st["step"] = "done"
    onboard.save_state(st)
    if not fetch.is_running():
        _start_background(fetch.run)
    return RedirectResponse("/jobs?status=new", status_code=303)


@app.post("/onboarding/edit")
def onboarding_edit():
    profile = tailor.load_profile()
    st = onboard.state()
    if profile:
        st.update(step="review", draft=onboard.from_profile(profile), editing=True, sources=[])
    else:
        st.update(step="import")
    onboard.save_state(st)
    return RedirectResponse("/onboarding", status_code=303)


@app.post("/onboarding/restart")
def onboarding_restart():
    st = onboard.state()
    st.update(step="import", editing=False, sources=[])
    onboard.save_state(st)
    return RedirectResponse("/onboarding", status_code=303)


# ---- settings -------------------------------------------------------------------------------
def _current_settings():
    return {k: getattr(config, k) for k in config.EDITABLE}


@app.get("/settings", response_class=HTMLResponse)
def settings_page(request: Request, saved: int = 0, scan: int = 0):
    return render(request, "settings.html", {"s": _current_settings(), "saved": saved, "rescored": saved, "scan": scan,
                                             "feed": agenda.address(_base(request))})


@app.post("/settings")
async def settings_save(request: Request):
    new = _settings_from_form(await request.form())
    before = _searched()
    moved = (new.get("HOME_TOWN", "").lower(), new.get("RADIUS_KM")) != (config.HOME_TOWN.lower(), config.RADIUS_KM)
    if moved:                                   # home or radius changed: the towns follow, travel times too
        new.update(onboard.area_settings(new.get("HOME_TOWN"), new.get("RADIUS_KM")) or {})
        commute.reset()
    config.save_settings(new)
    prefs.invalidate()
    store.rescore(fetch.score_job)
    scan = _searched() != before and _rescan()         # what is searched changed: look for jobs now
    return RedirectResponse("/settings?saved=1" + ("&scan=1" if scan else ""), status_code=303)


# ---- CV for a target role -----------------------------------------------------------------
@app.post("/cv/role")
def cv_role(request: Request, role: str = Form(...)):
    profile = tailor.load_profile()
    if not profile or not roles.get(role):
        return RedirectResponse("/cv", status_code=303)
    _, sup, miss = onboard.build_role_cv(profile, role)
    return render(request, "cv.html", _cv_ctx(profile, role_built={"id": role, "label": roles.label(roles.get(role), i18n.current()),
                                                                   "supported": sup, "missing": miss}))


@app.get("/cv/role/{rid}.pdf")
def cv_role_pdf(rid: str):
    path = onboard.role_cv_path(rid)
    if not roles.get(rid) or not os.path.exists(path):
        return PlainTextResponse("No CV for this role yet.", status_code=404)
    profile = tailor.load_profile() or onboard.profile_from_draft(onboard.state()["draft"])
    name = tailor.download_name(profile, {"company": rid})
    return FileResponse(path, media_type="application/pdf", filename=name, content_disposition_type="inline")


@app.get("/healthz")
def healthz():
    return {"ok": True}
