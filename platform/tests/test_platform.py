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
        image = Img("old")

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
    assert not gw.seen                                                 # nothing reached a tenant


def test_signed_in_without_a_workspace_sees_how_to_get_one(gw):
    r = gw.get("/", headers=as_("new@example.org"))
    assert r.status_code == 403 and "don't have a workspace yet" in r.text and "new@example.org" in r.text
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
