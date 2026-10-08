"""Platform: gateway (auth, invites, isolation of routing, admin, account) and provisioner
(locked-down container spec, subnets, API auth, upgrade rollback). No Docker, no network."""
import importlib
import ipaddress
import json

import httpx
import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def gw(tmp_path, monkeypatch):
    monkeypatch.setenv("CF_TEAM_DOMAIN", "team.cloudflareaccess.com")
    monkeypatch.setenv("CF_ACCESS_AUD", "aud")
    monkeypatch.setenv("PLATFORM_SECRET", "s3cret")
    monkeypatch.setenv("PROVISIONER_TOKEN", "tok")
    monkeypatch.setenv("ADMIN_EMAILS", "admin@example.org")
    monkeypatch.setenv("PLATFORM_DB", str(tmp_path / "p.db"))
    monkeypatch.setenv("MAX_TENANTS", "3")
    from jobplatform import db, gateway
    importlib.reload(db)
    g = importlib.reload(gateway)
    calls = []

    def prov(method, path, **kw):
        calls.append((method, path, kw.get("json")))
        if path == "/tenants":
            return [{"slug": t["slug"], "web": "running (healthy)", "sched": "running", "image": "swiss-job-agent:latest"}
                    for t in db.tenants()]
        if path.endswith("/export"):
            return b"\x1f\x8bdata"
        if method == "DELETE":
            return {"archive": "/archives/x.tar.gz"}
        return {}
    monkeypatch.setattr(g, "prov", prov)
    monkeypatch.setattr(g, "tenant_summary", lambda slug: {})          # no workspace to ask in these tests
    # stands in for the verified Cloudflare Access email (tests only; the gateway has no such header)
    monkeypatch.setattr(g, "identify", lambda request: (request.headers.get("x-test-user") or "").lower() or None)
    seen = []

    def upstream(request):                      # stands in for every tenant container
        request.read()
        seen.append(request)
        return httpx.Response(200, text=f"tenant page {request.url.host} {request.url.path}",
                              headers={"x-upstream": "1"})
    g._http = httpx.AsyncClient(transport=httpx.MockTransport(upstream))
    c = TestClient(g.app)
    c.calls, c.seen, c.g, c.db = calls, seen, g, db
    with c:
        yield c


def as_(email):
    return {"X-Test-User": email}


def csrf(c, email):
    return c.g.csrf_token(email)


def test_real_auth_rejects_missing_or_forged_tokens(gw, monkeypatch):
    monkeypatch.setattr(gw.g, "identify", gw.g.user_email)
    assert gw.get("/", headers={"X-Test-User": "admin@example.org"}).status_code == 403
    assert gw.get("/", headers={"Cf-Access-Jwt-Assertion": "not.a.jwt"}).status_code == 403


def test_no_identity_no_access_and_healthz_open(gw):
    assert gw.get("/jobs").status_code == 403
    assert gw.get("/_platform/healthz").status_code == 200
    r = gw.get("/jobs", headers=as_("stranger@example.org"))
    assert r.status_code == 403 and "by invitation" in r.text and not gw.seen


def test_invite_flow_creates_an_isolated_tenant_and_routes_by_identity(gw):
    admin = as_("admin@example.org")
    r = gw.post("/_platform/admin/invite", headers=admin, data={"csrf": csrf(gw, "admin@example.org"),
                                                               "note": "Marie", "days": "7"}, follow_redirects=False)
    token = r.headers["location"].split("new=")[1]
    assert token in gw.get(r.headers["location"], headers=admin).text        # link shown to the admin
    assert gw.db.invites()[0]["token_hash"] != token                           # only the hash is stored

    marie = as_("Marie@Example.org")
    assert "Create my workspace" in gw.get(f"/_platform/invite/{token}", headers=marie).text
    # a forged form (wrong token) or a cross-site post is refused
    assert gw.post(f"/_platform/invite/{token}", headers=marie, data={"csrf": "x"}).status_code == 403
    assert gw.post(f"/_platform/invite/{token}", headers=dict(marie, Origin="https://evil.example"),
                   data={"csrf": csrf(gw, "marie@example.org")}).status_code == 403
    r = gw.post(f"/_platform/invite/{token}", headers=marie, data={"csrf": csrf(gw, "marie@example.org")},
                follow_redirects=False)
    assert r.status_code == 303 and r.headers["location"] == "/"
    assert ("PUT", "/tenants/marie", {"email": "marie@example.org"}) in gw.calls
    # single use
    assert "not valid" in gw.get(f"/_platform/invite/{token}", headers=as_("other@example.org")).text

    # requests go to marie's container, whatever the URL says
    r = gw.post("/job/1/status?x=1", headers=marie, data={"status": "applied"})
    assert r.text == "tenant page jat-marie-web /job/1/status" and r.headers["x-frame-options"] == "DENY"
    fwd = gw.seen[-1]
    assert fwd.url.query == b"x=1" and b"status=applied" in fwd.content
    assert gw.get("/_platform/admin", headers=marie).status_code == 403        # not an admin


def test_invite_restricted_to_an_email_and_tenant_cap(gw):
    admin = as_("admin@example.org")
    tok = gw.db.create_invite("admin@example.org", "Bob", 7, "bob@example.org")
    assert gw.get(f"/_platform/invite/{tok}", headers=as_("eve@example.org")).status_code == 403
    for i in range(3):
        gw.db.add_tenant(f"t{i}xx", f"t{i}@example.org")
    r = gw.post(f"/_platform/invite/{tok}", headers=as_("bob@example.org"), data={"csrf": csrf(gw, "bob@example.org")})
    assert r.status_code == 503 and gw.db.invite(tok)                           # full: invite not consumed


def test_slugs_are_unique_and_safe(gw):
    gw.db.add_tenant("jane-doe", "jane.doe@example.org")
    assert gw.db.new_slug("Jane.Doe@other.ch") == "jane-doe-2"
    assert gw.db.new_slug("a@b.c") == "a-user" and gw.db.new_slug("../..@x.y") == "user"


def test_account_export_and_self_delete(gw):
    gw.db.add_tenant("marie", "marie@example.org")
    m = as_("marie@example.org")
    assert "Download my data" in gw.get("/_platform/me", headers=m).text
    r = gw.get("/_platform/me/export", headers=m)
    assert r.content == b"\x1f\x8bdata" and "jobsearch-marie.tar.gz" in r.headers["content-disposition"]
    assert "Type DELETE" in gw.post("/_platform/me/delete", headers=m, data={"csrf": csrf(gw, "marie@example.org"),
                                                                            "confirm": "no"}).text
    r = gw.post("/_platform/me/delete", headers=m, data={"csrf": csrf(gw, "marie@example.org"), "confirm": "delete"})
    assert "were deleted" in r.text and ("DELETE", "/tenants/marie", None) in gw.calls and not gw.db.tenants()


def test_admin_pause_resume_delete(gw):
    gw.db.add_tenant("marie", "marie@example.org")
    a, tok = as_("admin@example.org"), csrf(gw, "admin@example.org")
    page = gw.get("/_platform/admin", headers=a).text
    assert "marie@example.org" in page and "running (healthy)" in page
    gw.post("/_platform/admin/tenant/marie/stop", headers=a, data={"csrf": tok})
    assert gw.db.tenant("marie")["status"] == "suspended"
    assert "paused" in gw.get("/jobs", headers=as_("marie@example.org")).text
    gw.post("/_platform/admin/tenant/marie/start", headers=a, data={"csrf": tok})
    assert "Type the workspace id" in gw.post("/_platform/admin/tenant/marie/delete", headers=a,
                                              data={"csrf": tok, "confirm": "x"}).text
    gw.post("/_platform/admin/tenant/marie/delete", headers=a, data={"csrf": tok, "confirm": "marie"})
    assert not gw.db.tenants() and [x["action"] for x in gw.db.audit_log()][:3] == [
        "tenant.delete", "tenant.start", "tenant.stop"]


def test_tenant_not_up_yet_shows_starting_page(gw):
    gw.db.add_tenant("marie", "marie@example.org")

    def down(request):
        raise httpx.ConnectError("refused")
    gw.g._http = httpx.AsyncClient(transport=httpx.MockTransport(down))
    r = gw.get("/", headers=as_("marie@example.org"))
    assert r.status_code == 503 and "Starting your workspace" in r.text


# ---- provisioner ---------------------------------------------------------------------------------
@pytest.fixture
def prov(monkeypatch, tmp_path):
    monkeypatch.setenv("PROVISIONER_TOKEN", "tok")
    monkeypatch.setenv("CF_TEAM_DOMAIN", "team.cloudflareaccess.com")
    monkeypatch.setenv("CF_ACCESS_AUD", "aud")
    monkeypatch.setenv("JOOBLE_API_KEY", "jk")
    monkeypatch.setenv("ARCHIVE_DIR", str(tmp_path / "arch"))
    from jobplatform import provisioner
    return importlib.reload(provisioner)


def test_container_spec_is_locked_down(prov):
    web = prov.spec("marie", "marie@example.org", "web", "img")
    sched = prov.spec("marie", "marie@example.org", "sched", "img")
    for s in (web, sched):
        assert s["user"] == "1000:1000" and s["read_only"] is True and s["cap_drop"] == ["ALL"]
        assert s["security_opt"] == ["no-new-privileges:true"] and s["pids_limit"] == 128
        assert s["network"] == "jat-marie" and s["volumes"] == {"jat-marie-data": {"bind": "/data", "mode": "rw"}}
        assert "privileged" not in s and "ports" not in s and "docker.sock" not in json.dumps(s, default=str)
        e = s["environment"]
        assert e["ALLOWED_EMAILS"] == "marie@example.org" and e["CF_ACCESS_AUD"] == "aud" and e["ONBOARDING"] == e["PLATFORM_TENANT"] == "1"
        assert e["JOOBLE_API_KEY"] == "jk" and "PROVISIONER_TOKEN" not in e
    assert web["name"] == "jat-marie-web" and sched["command"] == ["python", "-m", "app.scheduler"]


class FakeNet:
    def __init__(self, subnet):
        self.attrs = {"IPAM": {"Config": [{"Subnet": subnet}]}}


class FakeNets:
    def __init__(self, subnets):
        self.items = [FakeNet(s) for s in subnets]

    def list(self, **kw):
        return self.items


def test_subnets_never_overlap(prov):
    class D:
        networks = FakeNets(["172.31.0.0/28", "172.31.0.32/28"])
    assert str(prov.free_subnet(D())) == "172.31.0.16/28"
    prov.S.subnet_pool = ipaddress.ip_network("172.31.0.0/27")
    D.networks = FakeNets(["172.31.0.0/28", "172.31.0.16/28"])
    with pytest.raises(Exception, match="no free"):
        prov.free_subnet(D())


def test_api_requires_the_token_and_valid_ids(prov, monkeypatch):
    monkeypatch.setattr(prov, "client", lambda: None)
    monkeypatch.setattr(prov, "create", lambda d, slug, email, image=None, extra=None: {"slug": slug, "email": email})
    c = TestClient(prov.app)
    assert c.get("/tenants").status_code == 401
    assert c.get("/tenants", headers={"Authorization": "Bearer nope"}).status_code == 401
    h = {"Authorization": "Bearer tok"}
    assert c.put("/tenants/Bad_Slug", headers=h, json={"email": "a@b.co"}).status_code == 400
    assert c.put("/tenants/..", headers=h, json={"email": "a@b.co"}).status_code in (400, 404, 405)
    assert c.put("/tenants/marie", headers=h, json={"email": "not-an-email"}).status_code == 400
    assert c.put("/tenants/marie", headers=h, json={"email": "Marie@Example.org"}).json() == \
        {"slug": "marie", "email": "marie@example.org"}
    assert c.post("/tenants/marie/exec", headers=h).status_code == 404


def test_upgrade_rolls_back_an_unhealthy_tenant_and_stops(prov, monkeypatch):
    class Img:
        def __init__(self, i):
            self.id = i

    class Web:
        attrs = {"Image": "old"}

        @property
        def image(self):                       # the store no longer lists the image the container runs
            raise RuntimeError("No such image")

    class D:
        containers = None

        class images:
            @staticmethod
            def get(name):
                return Img("new")
    monkeypatch.setattr(prov, "tenants", lambda d: [
        {"slug": "a", "email": "a@x.ch", "web": "running (healthy)"},
        {"slug": "b", "email": "b@x.ch", "web": "running (healthy)"}])
    monkeypatch.setattr(prov, "_get", lambda coll, name: Web())
    made = []
    monkeypatch.setattr(prov, "create", lambda d, slug, email, image=None, extra=None: made.append((slug, image)))
    monkeypatch.setattr(prov, "healthy", lambda d, name, timeout=90: made[-1][1] == "old")
    logs = []
    assert prov.upgrade(D(), log=logs.append) is False
    assert made == [("a", "new"), ("a", "old")]                   # rolled back, b untouched
    assert logs[-1] == "a: rolled back"


def test_archives_are_pruned(prov, tmp_path):
    import os
    d = tmp_path / "arch"
    d.mkdir()
    (d / "old.tar.gz").write_bytes(b"x")
    (d / "new.tar.gz").write_bytes(b"x")
    os.utime(d / "old.tar.gz", (1, 1))
    assert prov.prune_archives(30) == ["old.tar.gz"] and (d / "new.tar.gz").exists()


def test_public_home_page_is_the_only_page_without_a_login(gw):
    r = gw.get("/welcome")
    assert r.status_code == 200 and "github.com" in r.text and "Sign in" in r.text
    assert r.headers["x-frame-options"] == "DENY" and "csrf" not in r.text.lower()
    for path in ("/", "/jobs", "/welcome/x", "/_platform/admin", "/_platform/me", "/_platform/invite/abc"):
        assert gw.get(path).status_code == 403, path
    assert gw.post("/welcome").status_code == 403                       # reading only
    assert gw.head("/welcome").status_code == 200
    assert not gw.seen                                                 # nothing reached a tenant


def test_signed_in_without_a_workspace_sees_how_to_get_one(gw):
    r = gw.get("/", headers=as_("new@example.org"))
    assert r.status_code == 403 and "don't have a workspace yet" in r.text and "new@example.org" in r.text
    # stuck on the wrong address for a month otherwise: sign out of Access and come back to the sign-in
    assert "team.cloudflareaccess.com/cdn-cgi/access/logout?returnTo=http" in r.text and "Sign in with another address" in r.text
    assert "cdn-cgi/access/logout" not in gw.get("/welcome").text and 'href="/">Sign in' in gw.get("/welcome").text
    gw.db.add_tenant("marie", "marie@example.org")
    r = gw.get("/welcome", headers=as_("marie@example.org"))
    assert r.status_code == 200 and "Open my workspace" in r.text


def test_one_invite_link_for_several_people(gw):
    admin = as_("admin@example.org")
    r = gw.post("/_platform/admin/invite", headers=admin, follow_redirects=False,
                data={"csrf": csrf(gw, "admin@example.org"), "note": "job club", "uses": "2", "days": "7"})
    tok = r.headers["location"].split("new=")[1]
    for who in ("a.one@example.org", "b.two@example.org"):
        assert gw.get(f"/_platform/invite/{tok}", headers=as_(who)).status_code == 200
        r = gw.post(f"/_platform/invite/{tok}", headers=as_(who), data={"csrf": csrf(gw, who)}, follow_redirects=False)
        assert r.status_code == 303 and gw.db.tenant_for(who)
    assert gw.get(f"/_platform/invite/{tok}", headers=as_("c.three@example.org")).status_code == 404   # used up
    assert "2 / 2 used" in gw.get("/_platform/admin", headers=admin).text
    # a link locked to one address is always for one person
    r = gw.post("/_platform/admin/invite", headers=admin, follow_redirects=False,
                data={"csrf": csrf(gw, "admin@example.org"), "email": "x@example.org", "uses": "10"})
    assert gw.db.invite(r.headers["location"].split("new=")[1])["max_uses"] == 1


def test_a_failed_workspace_gives_the_invite_use_back(gw, monkeypatch):
    tok = gw.db.create_invite("admin@example.org", "", 7, "", 1)

    def boom(*a, **k):
        raise RuntimeError("docker down")
    monkeypatch.setattr(gw.g, "prov", boom)
    r = gw.post(f"/_platform/invite/{tok}", headers=as_("d@example.org"), data={"csrf": csrf(gw, "d@example.org")})
    assert r.status_code == 500 and not gw.db.tenant_for("d@example.org") and gw.db.invite(tok)


def test_invites_table_from_before_shareable_links_is_migrated(gw, tmp_path):
    import sqlite3
    old = tmp_path / "old.db"
    c = sqlite3.connect(old)
    c.executescript("""CREATE TABLE invites (id INTEGER PRIMARY KEY AUTOINCREMENT, token_hash TEXT UNIQUE NOT NULL, note TEXT,
        email TEXT, created_by TEXT, created_at TEXT NOT NULL, expires_at TEXT NOT NULL, used_by TEXT, used_at TEXT,
        revoked INTEGER NOT NULL DEFAULT 0);
        INSERT INTO invites (token_hash, created_at, expires_at, used_by, used_at) VALUES ('h1','2026-01-01','2099-01-01','a@b.co','2026-01-02');
        INSERT INTO invites (token_hash, created_at, expires_at) VALUES ('h2','2026-01-01','2099-01-01');""")
    c.commit(); c.close()
    gw.db.PATH = str(old)
    gw.db.init()
    rows = {r["token_hash"]: r for r in gw.db.invites()}
    assert (rows["h1"]["uses"], rows["h1"]["max_uses"], rows["h2"]["uses"]) == (1, 1, 0)


def test_a_second_address_opens_the_same_workspace(gw):
    admin, a = as_("admin@example.org"), {"csrf": None}
    gw.db.add_tenant("marie", "marie@example.org")
    gw.db.add_tenant("bob", "bob@example.org")
    tok = csrf(gw, "admin@example.org")
    assert gw.get("/jobs", headers=as_("marie@gmail.example")).status_code == 403            # not yet
    r = gw.post("/_platform/admin/tenant/marie/address", headers=admin, data={"csrf": tok, "email": "Marie@Gmail.example"},
                follow_redirects=False)
    assert r.status_code == 303 and gw.db.aliases("marie") == ["marie@gmail.example"]
    assert ("PUT", "/tenants/marie", {"email": "marie@example.org", "extra_emails": ["marie@gmail.example"]}) in gw.calls
    for who in ("marie@example.org", "marie@gmail.example"):                                  # both reach marie, only marie
        gw.seen.clear()
        assert gw.get("/jobs", headers=as_(who)).status_code == 200 and gw.seen[0].url.host == "jat-marie-web"
    assert "marie@gmail.example" in gw.get("/_platform/admin", headers=admin).text
    # an address that already opens a workspace can't be added to another one; strangers can't add anything
    for taken in ("bob@example.org", "marie@gmail.example", "marie@example.org"):
        assert gw.post("/_platform/admin/tenant/bob/address", headers=admin, data={"csrf": tok, "email": taken}).status_code == 400
    assert gw.post("/_platform/admin/tenant/marie/address", headers=as_("bob@example.org"),
                   data={"csrf": csrf(gw, "bob@example.org"), "email": "bob@gmail.example"}).status_code == 403
    assert gw.post("/_platform/admin/tenant/marie/address", headers=admin, data={"csrf": tok, "email": "a@b.co,evil@x.y"}).status_code == 400
    # removed again -> no access; deleting the workspace drops its extra addresses
    gw.post("/_platform/admin/tenant/marie/address", headers=admin, data={"csrf": tok, "remove": "marie@gmail.example"})
    assert gw.get("/jobs", headers=as_("marie@gmail.example")).status_code == 403
    gw.db.add_alias("marie", "m2@example.org")
    gw.db.remove_tenant("marie")
    assert gw.db.tenant_for("m2@example.org") is None


def test_extra_addresses_reach_the_tenant_and_survive_an_upgrade(prov):
    e = prov.spec("marie", "marie@example.org", "web", "img", ["marie@gmail.example", "marie@example.org"])
    assert e["environment"]["ALLOWED_EMAILS"] == "marie@example.org,marie@gmail.example"
    assert e["labels"]["jobagent.extra_emails"] == "marie@gmail.example"
    assert prov.spec("marie", "marie@example.org", "web", "img")["environment"]["ALLOWED_EMAILS"] == "marie@example.org"


def test_account_request_approval_and_workspace(gw, monkeypatch):
    sent = []
    monkeypatch.setattr(gw.g.notify, "admins", lambda prov, subject, body: sent.append(body))
    who, admin = as_("Zoe@Gmail.example"), as_("admin@example.org")
    assert gw.get("/_platform/request").status_code == 403                      # sign in first: no anonymous requests
    assert "Request an account" in gw.get("/welcome").text and "Request an account" in gw.get("/", headers=who).text
    assert gw.get("/_platform/request", headers=who).status_code == 200
    assert gw.post("/_platform/request", headers=who, data={"csrf": "x", "name": "Zoe"}).status_code == 403
    r = gw.post("/_platform/request", headers=who, follow_redirects=False,
                data={"csrf": csrf(gw, "zoe@gmail.example"), "name": "  Zoe   Test ", "note": "Admin jobs\nin Vaud <b>"})
    assert r.status_code == 303 and gw.db.request_for("zoe@gmail.example")["name"] == "Zoe Test"
    assert "zoe@gmail.example" in sent[0] and "Admin jobs in Vaud" in sent[0] and "/_platform/admin" in sent[0]   # told once
    gw.post("/_platform/request", headers=who, data={"csrf": csrf(gw, "zoe@gmail.example"), "name": "again"})
    assert len(sent) == 1 and gw.db.request_for("zoe@gmail.example")["name"] == "Zoe Test"
    home = gw.get("/", headers=who)
    assert home.status_code == 403 and "waiting for approval" in home.text
    # not approved: no workspace
    assert gw.post("/_platform/request/create", headers=who, data={"csrf": csrf(gw, "zoe@gmail.example")}).status_code == 403
    page = gw.get("/_platform/admin", headers=admin).text
    assert "1 waiting" in page and "Zoe Test" in page and "&lt;b&gt;" in page and "<b>" not in page.split("Admin jobs")[1][:20]
    # only an admin decides
    assert gw.post("/_platform/admin/request", headers=who, data={"csrf": csrf(gw, "zoe@gmail.example"),
                   "email": "zoe@gmail.example", "decision": "approved"}).status_code == 403
    r = gw.post("/_platform/admin/request", headers=admin, follow_redirects=False,
                data={"csrf": csrf(gw, "admin@example.org"), "email": "zoe@gmail.example", "decision": "approved"})
    assert r.status_code == 303 and len(sent) == 1
    assert "Create my workspace" in gw.get("/", headers=who).text
    r = gw.post("/_platform/request/create", headers=who, data={"csrf": csrf(gw, "zoe@gmail.example")}, follow_redirects=False)
    assert r.status_code == 303 and gw.db.tenant_for("zoe@gmail.example") and gw.db.request_for("zoe@gmail.example")["status"] == "done"
    assert gw.get("/jobs", headers=who).status_code == 200
    # declined: nothing to create, and no second request from the same address
    other = as_("max@example.org")
    gw.post("/_platform/request", headers=other, data={"csrf": csrf(gw, "max@example.org"), "name": "Max"})
    gw.post("/_platform/admin/request", headers=admin, data={"csrf": csrf(gw, "admin@example.org"), "email": "max@example.org", "decision": "declined"})
    assert gw.post("/_platform/request/create", headers=other, data={"csrf": csrf(gw, "max@example.org")}).status_code == 403
    assert gw.get("/_platform/request", headers=other, follow_redirects=False).status_code == 303


def test_notice_goes_through_the_provisioner_and_never_breaks_a_request(gw, prov, monkeypatch):
    n = gw.g.notify
    calls = []
    n.admins(lambda *a, **k: calls.append(a), "s", "b")
    assert not n.configured() and not calls                                    # silent until configured
    n._run(lambda m, p, json: calls.append((m, p, json["msg"])), "hello")
    n._run(lambda *a, **k: (_ for _ in ()).throw(RuntimeError("down")), "x")   # a failure is swallowed
    assert calls == [("POST", "/notify", "hello")]
    # provisioner side: nothing without NOTIFY_WEBHOOK, else one POST to the bridge
    assert prov.api_notify(prov.Notice(msg="hi")) == {"sent": False}
    posted = []
    monkeypatch.setenv("NOTIFY_WEBHOOK", "http://bridge.test/alert")
    import httpx as hx
    monkeypatch.setattr(hx, "post", lambda url, json, timeout: posted.append((url, json)) or type("R", (), {"raise_for_status": lambda self: None})())
    assert prov.api_notify(prov.Notice(msg="x" * 3000)) == {"sent": True}
    assert posted[0][0] == "http://bridge.test/alert" and len(posted[0][1]["msg"]) == 1500


def test_plain_http_is_sent_to_https_and_pages_carry_hsts(gw, monkeypatch):
    monkeypatch.setattr(gw.g.C, "public_url", "https://jobs.example.org")
    r = gw.get("/welcome?x=1", headers={"cf-visitor": '{"scheme":"http"}'}, follow_redirects=False)
    assert r.status_code == 308 and r.headers["location"] == "https://jobs.example.org/welcome?x=1"
    r = gw.get("/jobs", headers=dict(as_("admin@example.org"), **{"cf-visitor": '{"scheme": "http"}'}), follow_redirects=False)
    assert r.status_code == 308                                                 # before anything else, signed in or not
    r = gw.get("/welcome", headers={"cf-visitor": '{"scheme":"https"}'})
    assert r.status_code == 200 and r.headers["strict-transport-security"].startswith("max-age=")
    assert "frame-ancestors 'none'" in r.headers["content-security-policy"]


def test_platform_pages_in_french_german_and_italian(gw):
    from pathlib import Path
    tdir = Path(gw.g.__file__).parent / "templates"
    for name, entries in gw.g.locales.TEMPLATES.items():
        assert gw.g.i18n.missing((tdir / name).read_text(), entries) == [], name
        assert all(len(e) == 4 and all(e) for e in entries), name       # English, French, German, Italian
    assert all(len(v) == 3 and all(v) for v in gw.g.locales.STRINGS.values())
    for lang in ("fr", "de", "it"):
        for p in tdir.glob("*.html"):
            gw.g.templates[lang].get_template(p.name)                   # every page compiles in every language
    fr, de = {"accept-language": "fr-CH,fr;q=0.9"}, {"accept-language": "de"}
    home = gw.get("/welcome", headers=fr).text
    assert "Votre assistant privé pour chercher un emploi en Suisse" in home and "Demander un compte" in home and '<html lang="fr">' in home
    assert "Ihr privater Assistent" in gw.get("/welcome", headers=de).text and "Your private assistant" in gw.get("/welcome").text
    it = {"accept-language": "it-CH,it;q=0.9,de;q=0.5"}
    home = gw.get("/welcome", headers=it).text
    assert "Il tuo assistente privato per cercare lavoro in Svizzera" in home and "Chiedi un account" in home and '<html lang="it">' in home
    assert "Invito non valido" in gw.get("/_platform/invite/nope", headers=dict(as_("zoe@example.org"), **it)).text
    who = dict(as_("zoe@example.org"), **fr)
    assert "vous n'avez pas encore d'espace" in gw.get("/", headers=who).text
    assert "Envoyer ma demande" in gw.get("/_platform/request", headers=who).text
    tok = gw.db.create_invite("admin@example.org", "", 7, "", 1)
    assert "Vous êtes invité·e" in gw.get(f"/_platform/invite/{tok}", headers=who).text
    assert "Invitation non valable" in gw.get("/_platform/invite/nope", headers=who).text          # messages too
    gw.db.add_tenant("zoe", "zoe@example.org")
    assert "Télécharger mes données" in gw.get("/_platform/me", headers=who).text
    assert "Workspaces (" in gw.get("/_platform/admin", headers=dict(as_("admin@example.org"), **fr)).text   # admin: English


def test_listing_and_upgrade_survive_an_image_the_store_no_longer_has(prov, monkeypatch):
    class Gone:
        labels = {"jobagent.tenant": "a", "jobagent.role": "web", "jobagent.email": "a@x.ch"}
        attrs = {"State": {"Status": "running", "Health": {"Status": "healthy"}}, "Image": "sha256:bd760b3b2ab8b8bf58602b750408"}
        status = "running"

        @property
        def image(self):
            raise RuntimeError("404 No such image")

    class D:
        class containers:
            @staticmethod
            def list(all=True, filters=None):
                return [Gone()]

        class volumes:
            @staticmethod
            def list(filters=None):
                return []
    assert prov.LABEL == "jobagent.tenant"
    t = prov.tenants(D())
    assert t == [{"slug": "a", "email": "a@x.ch", "web": "running (healthy)", "sched": "missing", "image": "bd760b3b2ab8"}]
    assert prov.image_id(Gone()) == "sha256:bd760b3b2ab8b8bf58602b750408" and prov.image_id(None) == ""
    # a rollback to an image that is gone is reported, not a crash
    class Img:
        id = "sha256:new"
    D.images = type("I", (), {"get": staticmethod(lambda name: Img())})
    monkeypatch.setattr(prov, "_get", lambda coll, name: Gone())
    calls = []

    def create(d, slug, email, image=None, extra=None):
        calls.append(image)
        if image != "sha256:new":
            raise RuntimeError("No such image")
    monkeypatch.setattr(prov, "create", create)
    monkeypatch.setattr(prov, "healthy", lambda d, name, timeout=90: False)
    logs = []
    assert prov.upgrade(D(), log=logs.append) is False and calls == ["sha256:new", "sha256:bd760b3b2ab8b8bf58602b750408"]
    assert "CAN'T ROLL BACK" in logs[-1]


def test_calendar_feed_is_passed_to_the_workspace_that_checks_the_key(gw):
    gw.db.add_tenant("marie", "marie@example.org")
    key = "k" * 32
    r = gw.get(f"/welcome/cal/marie/{key}.ics")                         # no sign-in: a calendar app can't
    assert r.status_code == 200 and r.headers["content-type"].startswith("text/calendar")
    sent = gw.seen[-1]
    assert str(sent.url) == f"http://jat-marie-web:8080/calendar/{key}.ics"
    assert "cookie" not in sent.headers and "cf-access-jwt-assertion" not in sent.headers
    # nothing else of a workspace is reachable that way
    for bad in ("/welcome/cal/marie/short.ics", f"/welcome/cal/nobody/{key}.ics", f"/welcome/cal/marie/{key}.txt",
                f"/welcome/cal/MARIE/{key}.ics", "/welcome/cal/marie/..%2Fjobs", f"/welcome/cal/marie/{key}.ics/x", "/welcome/other"):
        assert gw.get(bad).status_code in (403, 404), bad
    assert len(gw.seen) == 1
    assert gw.post(f"/welcome/cal/marie/{key}.ics").status_code == 403
    gw.db.set_status("marie", "paused")
    assert gw.get(f"/welcome/cal/marie/{key}.ics").status_code == 404


def test_wrong_calendar_keys_are_cut_short(gw):
    gw.db.add_tenant("marie", "marie@example.org")
    gw.g._http = httpx.AsyncClient(transport=httpx.MockTransport(lambda request: httpx.Response(404)))
    codes = [gw.get(f"/welcome/cal/marie/{'x' * 30}{i:02d}.ics").status_code for i in range(25)]
    assert set(codes) == {404}
    gw.g._http = httpx.AsyncClient(transport=httpx.MockTransport(lambda request: httpx.Response(200, text="BEGIN:VCALENDAR")))
    assert gw.get(f"/welcome/cal/marie/{'k' * 32}.ics").status_code == 404          # still locked out after 20 misses


def test_admin_sees_totals_and_what_needs_a_look_never_content(gw, monkeypatch):
    gw.db.add_tenant("marie", "marie@example.org")
    gw.db.add_tenant("paul", "paul@example.org")
    gw.db.add_tenant("zoe", "zoe@example.org")
    gw.db.set_status("zoe", "paused")
    asked = []

    def totals(slug):
        asked.append(slug)
        return {"marie": {"jobs": {"new": 40, "applied": 3, "rejected": 1, "discarded": 9}, "last_scan_at": gw.db.now()[:19], "setup_done": True,
                          "sources": {"jobup": {"count": 120, "errors": 0, "kind": ""}, "ats": {"count": 0, "errors": 2, "kind": "HTTP 403"}}},
                "paul": {"jobs": {}, "last_scan_at": "2020-01-01T00:00:00", "setup_done": True,
                         "sources": {"ats": {"count": 0, "errors": 1, "kind": "HTTP 403"}}}}.get(slug, {})
    monkeypatch.setattr(gw.g, "tenant_summary", totals)
    gw.get("/jobs", headers=as_("marie@example.org"))                      # marie uses her workspace
    page = gw.get("/_platform/admin", headers=as_("admin@example.org")).text
    assert sorted(asked) == ["marie", "paul"]                                # a paused workspace isn't asked
    assert "Activity and scan health" in page and "ats 0 ⚠ HTTP 403" in page and "jobup 120" in page
    assert "source ats: HTTP 403 for 2 of 2 workspaces (marie, paul)" in page and "paul: no scan for" in page
    assert gw.db.tenant("marie")["last_seen"] and not gw.db.tenant("paul")["last_seen"]
    assert ">53<" in page and ">4<" in page and "never" in page             # all jobs, applied, paul never signed in
    # the token a workspace expects is its own, not the platform's
    assert gw.g.ops_token("marie") != gw.g.ops_token("paul") and "tok" not in gw.g.ops_token("marie")


def test_health_lines(gw):
    from jobplatform import health
    now = __import__("datetime").datetime(2026, 10, 8, 12, tzinfo=__import__("datetime").timezone.utc)
    rows = [{"slug": "a", "status": "active", "web": "running (healthy)",
             "ops": {"setup_done": True, "last_scan_at": "2026-10-08T06:00:00", "sources": {"jobup": {"errors": 0}}}},
            {"slug": "b", "status": "active", "web": "exited", "ops": {}},
            {"slug": "c", "status": "active", "web": "running (healthy)", "ops": {"setup_done": False, "last_scan_at": "", "sources": {}}},
            {"slug": "d", "status": "paused", "web": "exited", "ops": {}}]
    assert health.problems(rows, now=now) == ["b: app is exited"]           # wizard not finished: no scan expected; paused: ignored
    assert health.problems(rows[:1], {"hour": 3, "at": "2026-10-08T03:00:10+00:00", "failed": []}, now) == []
    assert health.problems(rows[:1], {"hour": 3, "at": "2026-10-05T03:00:10+00:00", "failed": ["a"]}, now) == [
        "backup: last one 80 h ago", "backup: failed for a"]
    assert health.problems(rows[:1], {"hour": 3}, now) == ["backup: none yet"]
    assert health.problems(rows[:1], {"hour": None}, now) == []              # backups turned off: nothing to say


def test_workspaces_get_their_own_totals_token(prov):
    a = prov.spec("marie", "marie@example.org", "web", "img")["environment"]
    b = prov.spec("paul", "paul@example.org", "web", "img")["environment"]
    assert a["TENANT_SLUG"] == "marie" and a["OPS_TOKEN"] == prov.ops_token("marie") != b["OPS_TOKEN"]
    assert len(a["OPS_TOKEN"]) == 64 and "tok" not in a["OPS_TOKEN"]


def test_nightly_backup_writes_one_archive_per_workspace_and_keeps_the_newest(prov, tmp_path, monkeypatch):
    dest = tmp_path / "bk"
    execs = []

    class C:
        status = "running"

        def __init__(self, name):
            self.name = name

        def exec_run(self, cmd, user=None):
            execs.append((self.name, user))

        def get_archive(self, path):
            return iter([b"platform-db"]), {}

    class Coll:
        def __init__(self, known):
            self.known = known

        def get(self, name):
            if name not in self.known:
                import docker.errors
                raise docker.errors.NotFound(name)
            return C(name)

    class D:
        volumes = Coll({"jat-a-data", "jat-b-data"})
        containers = Coll({"jat-a-web", "jobplatform-gateway"})
    monkeypatch.setattr(prov, "tenants", lambda d: [{"slug": "a"}, {"slug": "b"}, {"slug": "gone"}])
    monkeypatch.setattr(prov, "export", lambda d, slug: (_ for _ in ()).throw(RuntimeError("disk")) if slug == "b" else b"data-" + slug.encode())
    logs = []
    res = prov.backup(D(), str(dest), keep=2, log=logs.append)
    assert res["ok"] == ["a", "platform"] and res["failed"] == ["b"] and any("backup of b failed" in l for l in logs)
    files = sorted(p.name for p in dest.iterdir())
    assert len(files) == 3 and files[0].startswith("a-") and files[1] == "last.json" and files[2].startswith("platform-")
    assert (dest / files[0]).read_bytes() == b"data-a" and oct((dest / files[0]).stat().st_mode)[-3:] == "600"
    assert execs == [("jat-a-web", "1000:1000"), ("jobplatform-gateway", "1000:1000")]      # databases settled before the copy
    assert prov.last_backup(str(dest))["failed"] == ["b"]
    for stamp in ("20200101-030000", "20200102-030000", "20200103-030000"):
        (dest / f"a-{stamp}.tar.gz").write_bytes(b"old")
    prov._keep_newest(str(dest), "a", 2)
    left = sorted(p.name for p in dest.iterdir() if p.name.startswith("a-"))
    assert len(left) == 2 and "a-20200101-030000.tar.gz" not in left and "a-20200102-030000.tar.gz" not in left
    import datetime
    assert prov.seconds_until(3, datetime.datetime(2026, 10, 8, 2, 0)) == 3600
    assert prov.seconds_until(3, datetime.datetime(2026, 10, 8, 3, 0)) == 86400
    monkeypatch.setenv("BACKUP_HOUR", "off")
    assert prov.backup_hour() is None


def test_flags_switch_the_language_of_the_platform_pages(gw):
    home = gw.get("/welcome", headers={"accept-language": "fr"}).text
    assert 'href="/welcome/lang/it?next=/welcome"' in home and 'class="on" title="Français"' in home
    r = gw.get("/welcome/lang/it?next=/welcome", follow_redirects=False)              # no sign-in needed
    assert r.status_code == 303 and r.headers["location"] == "/welcome" and "lang=it" in r.headers["set-cookie"]
    gw.cookies.set("lang", "it")
    assert "Il tuo assistente privato" in gw.get("/welcome", headers={"accept-language": "fr"}).text      # the choice wins over the browser
    assert gw.get("/welcome/lang/it?next=//evil.example", follow_redirects=False).headers["location"] == "/welcome"
    assert gw.get("/welcome/lang/it?next=https://evil.example", follow_redirects=False).headers["location"] == "/welcome"
    assert gw.post("/welcome/lang/it").status_code == 403


def test_league_is_joined_by_choice_and_shows_only_nicknames_and_points(gw, monkeypatch):
    for slug in ("marie", "paul", "zoe"):
        gw.db.add_tenant(slug, f"{slug}@example.org")
    asked = []

    def totals(slug):
        asked.append(slug)
        return {"jobs": {"new": 40}, "game": {"marie": {"week": 25, "month": 60, "total": 210, "streak": 3, "level": 2, "badges": ["first", "streak3", "nope"]},
                                              "paul": {"week": 40, "month": 40, "total": 40, "streak": 1, "level": 0, "badges": ["first"]}}.get(slug, {})}
    monkeypatch.setattr(gw.g, "tenant_summary", totals)
    marie, paul, zoe = as_("marie@example.org"), as_("paul@example.org"), as_("zoe@example.org")
    page = gw.get("/_platform/league", headers=marie).text
    assert "Join the league" in page and "a nickname you choose" in page and not asked            # nobody is in it by default
    assert gw.post("/_platform/league/join", headers=marie, data={"csrf": "x", "name": "Marmotte"}).status_code == 403
    for bad in ("x", "marie@example.org", "a" * 21, "<b>hi</b>", " "):
        r = gw.post("/_platform/league/join", headers=marie, data={"csrf": csrf(gw, "marie@example.org"), "name": bad}, follow_redirects=False)
        assert r.headers["location"].endswith("?bad=1"), bad
    gw.post("/_platform/league/join", headers=marie, data={"csrf": csrf(gw, "marie@example.org"), "name": "Marmotte"})
    gw.post("/_platform/league/join", headers=paul, data={"csrf": csrf(gw, "paul@example.org"), "name": "Rösti 2"})
    r = gw.post("/_platform/league/join", headers=zoe, data={"csrf": csrf(gw, "zoe@example.org"), "name": "marmotte"}, follow_redirects=False)
    assert r.headers["location"].endswith("?bad=1")                                                # taken
    asked.clear()
    page = gw.get("/_platform/league", headers=marie).text
    assert sorted(asked) == ["marie", "paul"]                                                      # only members' workspaces are asked
    assert page.index("Rösti 2") < page.index("Marmotte") and "👑" in page and "15 points behind <b>Rösti 2</b>" in page
    assert "🔥 3 weeks in a row" in page and "In the race" in page and 'title="Lift-off"' in page and "nope" not in page
    for private in ("marie@example.org", "paul@example.org", "paul", "example.org"):               # no address, no workspace id of the others
        assert private not in page.replace("marie@example.org", "", 1) or private == "marie@example.org", private
    assert "paul@example.org" not in page and ">paul<" not in page
    assert "You lead the week" in gw.get("/_platform/league", headers=paul).text
    assert "Join the league" in gw.get("/_platform/league", headers=zoe).text and "Rösti" not in gw.get("/_platform/league", headers=zoe).text
    fr = gw.get("/_platform/league", headers=dict(marie, **{"accept-language": "fr"})).text
    assert "La ligue" in fr and "Dans la course" in fr and "Décollage" in fr
    gw.post("/_platform/league/leave", headers=paul, data={"csrf": csrf(gw, "paul@example.org")})
    assert "Rösti" not in gw.get("/_platform/league", headers=marie).text
    assert gw.get("/_platform/league", headers=as_("stranger@example.org"), follow_redirects=False).status_code == 303
    assert gw.get("/_platform/league").status_code == 403


def test_league_remembers_last_weeks_champion(gw):
    import datetime
    from jobplatform import league
    rows = [{"name": "Marmotte", "week": 30}, {"name": "Lynx", "week": 10}]
    assert league.champion(rows, datetime.date(2026, 10, 8)) is None
    assert league.champion([{"name": "Marmotte", "week": 0}, {"name": "Lynx", "week": 0}], datetime.date(2026, 10, 12)) == ["Marmotte", 30]
    assert league.champion(rows, datetime.date(2026, 10, 14)) == ["Marmotte", 30]
    assert league.champion(rows, datetime.date(2026, 10, 19)) == ["Marmotte", 30] and league.suggestion(["Marmotte"]) != "Marmotte"
