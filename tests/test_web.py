"""Web layer end to end: Cloudflare Access JWT check, Claude cover letters (mocked API),
and a crawl of every page, link, download and form the app renders."""
import datetime
import json
import time
import types
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urljoin, urlparse

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi.testclient import TestClient

TEAM, AUD = "team.cloudflareaccess.com", "aud-tag-123"


# ---- Cloudflare Access -------------------------------------------------------------------
@pytest.fixture
def access(env, monkeypatch):
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    monkeypatch.setattr(env.config, "CF_TEAM_DOMAIN", TEAM)
    monkeypatch.setattr(env.config, "CF_ACCESS_AUD", AUD)
    monkeypatch.setattr(env.config, "ALLOWED_EMAILS", ["alex@example.com"])
    monkeypatch.setattr(env.auth, "ENABLED", True)
    monkeypatch.setattr(env.auth, "_jwks", types.SimpleNamespace(
        get_signing_key_from_jwt=lambda token: types.SimpleNamespace(key=key.public_key())))

    def token(email="alex@example.com", aud=AUD, iss=f"https://{TEAM}", exp=3600, signer=key):
        now = int(time.time())
        return jwt.encode({"email": email, "aud": aud, "iss": iss, "iat": now, "exp": now + exp},
                          signer, algorithm="RS256")
    return token


def test_access_jwt_is_really_verified(env, access):
    c = TestClient(env.web.app)
    ok = c.get("/jobs", headers={"cf-access-jwt-assertion": access()})
    assert ok.status_code == 200 and "alex@example.com" in ok.text
    browser = TestClient(env.web.app)
    browser.cookies.set("CF_Authorization", access())
    assert browser.get("/jobs").status_code == 200
    other = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    for bad in (access(aud="someone-else"), access(iss="https://evil.example"), access(exp=-60),
                access(email="stranger@example.com"), access(signer=other), "not-a-jwt"):
        assert c.get("/jobs", headers={"cf-access-jwt-assertion": bad}).status_code == 403
    assert c.get("/jobs").status_code == 403
    assert c.get("/healthz").status_code == 200          # monitoring stays open


def test_cross_site_posts_are_refused_and_headers_set(env):
    c = TestClient(env.web.app)
    jid = env.store.add_manual({"title": "Architect", "company": "Acme SA"})
    for evil in ({"origin": "https://evil.example"}, {"sec-fetch-site": "cross-site"}):
        assert c.post(f"/job/{jid}/status", data={"status": "discarded"}, headers=evil).status_code == 403
    assert env.store.get_job(jid)["status"] != "discarded"
    ok = c.post(f"/job/{jid}/status", data={"status": "discarded"}, follow_redirects=False,
                headers={"origin": "http://testserver", "sec-fetch-site": "same-origin"})
    assert ok.status_code == 303 and env.store.get_job(jid)["status"] == "discarded"
    r = c.get("/jobs")
    assert r.headers["x-frame-options"] == "DENY" and r.headers["x-content-type-options"] == "nosniff"


# ---- Cover letters via Claude --------------------------------------------------------------
PROFILE = {"name": "Alex Test", "headline": "Cloud Architect", "summary": "Cloud and infrastructure architect.",
           "contact": {"email": "a@example.com", "location": "Geneva, Switzerland"},
           "expertise": ["Cloud Architecture"],
           "experience": [{"title": "Technical Manager", "org": "GTT", "loc": "CH", "dates": "2020 – now",
                           "bullets": ["Automated AWS landing zones with Terraform."]}]}
FR_JOB = {"id": 1, "title": "Architecte cloud", "company": "Acme SA", "location": "Genève",
          "description": "Nous recherchons un architecte cloud pour concevoir nos plateformes AWS à Genève."}


# ---- Crawl every page, link, download and form -------------------------------------------
class Page(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links, self.forms, self._form, self._select = [], [], None, None

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == "a" and a.get("href"):
            self.links.append(a)
        elif tag == "form":
            self._form = {"action": a.get("action", ""), "method": (a.get("method") or "get").lower(),
                          "fields": {}, "buttons": []}
            self.forms.append(self._form)
        elif self._form is not None and tag == "button" and a.get("name"):
            self._form["buttons"].append((a["name"], a.get("value", "")))   # the clicked one is sent
        elif self._form is not None and tag == "select" and a.get("name"):
            self._select = a["name"]            # a browser sends the selected (else first) option
        elif self._form is not None and tag == "option" and self._select:
            fields = self._form["fields"]
            if self._select not in fields or "selected" in a:
                fields[self._select] = a.get("value", "")
        elif self._form is not None and tag in ("input", "textarea") and a.get("name"):
            if a.get("type") == "checkbox" and "checked" not in a:
                return
            value = a.get("value", "")
            if "required" in a and not value:
                value = "Test value"        # what a user must type before the browser submits
            self._form["fields"].setdefault(a["name"], value)

    def handle_endtag(self, tag):
        if tag == "form":
            self._form = None
        elif tag == "select":
            self._select = None


def _seed(env):
    Path(env.config.PROFILE_PATH).write_text(json.dumps(PROFILE))
    env.store.upsert_jobs([
        {"content_hash": "h1", "title": "Cloud Architect", "company": "Acme SA", "location": "Geneva",
         "url": "https://jobs.example/1", "description": "AWS, Terraform and Kubernetes. Allemand un atout.", "source": "t"},
        {"content_hash": "h2", "title": "DevOps Engineer 80-100%", "company": "Beta", "location": "Lausanne",
         "url": "https://jobs.example/2", "description": "CI/CD", "source": "t"}])
    j1, j2 = [j["id"] for j in env.store.list_jobs("new")]
    env.store.update_status(j1, "applied")
    env.store.update_fields(j1, {"contact": "Mme Dupont", "orp_assigned": 1, "letter": "Lettre de test"})
    env.store.update_status(j2, "applied")
    env.store.update_status(j2, "rejected")
    env.store.add_manual({"title": "Architect via recruiter", "company": "Gamma", "url": "javascript:alert(1)"})
    env.tailor.build(env.store.get_job(j1), PROFILE)
    env.tailor.build_custom(PROFILE, ["terraform"])


def test_every_link_download_and_form_works(env, monkeypatch):
    monkeypatch.setattr(env.enrich, "full_description", lambda url: "")
    _seed(env)
    c = TestClient(env.web.app)
    today = datetime.date.today()
    start = ["/", "/stats", "/report", f"/report?week={today:%G}-W{today:%V}", "/cv", "/add"]
    # report pages link to previous/next periods forever: stay within this period +-1
    wk = [f"{d:%G}-W{d:%V}" for d in (today - datetime.timedelta(weeks=1), today, today + datetime.timedelta(weeks=1))]
    mo = {env.report.shift("month", f"{today:%Y-%m}", n) for n in (-1, 0, 1)}
    in_range = lambda u: (not ("week=" in u or "month=" in u)  # noqa: E731
                          or any(f"week={w}" in u for w in wk) or any(f"month={m}" in u for m in mo))
    seen, queue, external, forms = set(), list(start), [], {}
    while queue:
        url = queue.pop()
        if url in seen or not in_range(url):
            continue
        assert len(seen) < 400, "crawl did not converge"
        seen.add(url)
        r = c.get(url)
        assert r.status_code == 200, f"{url} -> {r.status_code}"
        ctype = r.headers["content-type"]
        if url.split("?")[0].endswith(".pdf") or "/cv" in url and "pdf" in ctype:
            assert r.content[:4] == b"%PDF", url
            continue
        if url.split("?")[0].endswith(".csv"):
            lines = r.content.decode("utf-8-sig").splitlines()
            assert lines[0].startswith("Date;Entreprise, lieu;"), url
            if f"month={today:%Y-%m}" in url:
                assert any("Mme Dupont" in l and ";Oui;" in l for l in lines[1:]), url   # seeded rows
            continue
        if "html" not in ctype:
            assert "pdf" in ctype, f"{url}: unexpected {ctype}"
            assert r.content[:4] == b"%PDF", url
            continue
        for leak in ("ANTHROPIC_API_KEY", "CF_ACCESS_AUD", ".env", "Traceback"):   # end-user UI only
            assert leak not in r.text, f"{url} shows {leak!r} to the user"
        page = Page()
        page.feed(r.text)
        for a in page.links:
            href = a["href"]
            p = urlparse(href)
            if p.scheme in ("http", "https"):
                external.append((url, a))
            elif p.scheme:
                pytest.fail(f"{url}: unsafe link {href}")          # javascript:, data:, ...
            elif not href.startswith("#"):
                queue.append(urljoin(url, href))
        for f in page.forms:
            for press in f["buttons"] or [None]:         # submit once per named button
                data = dict(f["fields"], **({press[0]: press[1]} if press else {}))
                forms[(urljoin(url, f["action"]), f["method"], json.dumps(data, sort_keys=True))] = data
    assert len(seen) > 15, sorted(seen)
    for page_url, a in external:          # external links open in a new tab, safely
        assert a.get("target") == "_blank" and "noopener" in (a.get("rel") or ""), (page_url, a)
    assert any(h["href"] == "https://jobs.example/1" for _, h in external)
    for (action, method, _), data in forms.items():
        r = c.request(method.upper(), action, data=data, follow_redirects=True)
        assert r.status_code == 200, f"form {method} {action} -> {r.status_code}"
    print(f"\ncrawl: {len(seen)} URLs, {len(external)} external links, {len(forms)} forms submitted")


# ---- CV and letter in the posting's language, rule-based ----------------------------------
FR_PROFILE = {"name": "IGNORED", "contact": {"email": "ignored@example.com"},
              "headline": "Architecte cloud",
              "summary": "Architecte cloud et infrastructure. Automatise les plateformes AWS avec Terraform.",
              "expertise": ["Architecture cloud"],
              "experience": [{"title": "Responsable technique", "org": "GTT", "loc": "Suisse", "dates": "2020 – aujourd'hui",
                              "bullets": ["Automatisation des landing zones AWS avec Terraform."]}]}


def test_translated_profile_gives_cv_and_letter_in_posting_language(env):
    Path(env.config.PROFILE_PATH).write_text(json.dumps(PROFILE))
    cv, lang = env.tailor.localized(PROFILE, dict(FR_JOB))
    assert lang == "en" and cv is PROFILE                 # no French version yet: stays English
    text, _ = env.letter.write(PROFILE, dict(FR_JOB))
    assert "I am applying for the Architecte cloud position at Acme SA." in text   # no mixed languages

    Path(env.tailor.translated_path("fr")).write_text(json.dumps(FR_PROFILE))
    cv, lang = env.tailor.localized(PROFILE, dict(FR_JOB))
    assert lang == "fr" and cv["headline"] == "Architecte cloud"
    assert cv["name"] == "Alex Test" and cv["contact"] == PROFILE["contact"]   # identity from profile.json
    assert cv["experience"][0]["org"] == "GTT"
    assert Path(env.tailor.build(dict(FR_JOB), PROFILE)).read_bytes()[:4] == b"%PDF"
    text, how = env.letter.write(PROFILE, dict(FR_JOB))
    assert how == "rules"
    assert "Je vous adresse ma candidature pour le poste de Architecte cloud au sein de Acme SA." in text
    assert "– Automatisation des landing zones AWS avec Terraform." in text
    assert "Madame, Monsieur," in text and text.startswith("Alex Test")
    assert env.tailor.profile_versions() == {"en": "ok (original)", "fr": "ok"}


def test_translation_that_changes_the_facts_is_ignored(env):
    Path(env.config.PROFILE_PATH).write_text(json.dumps(PROFILE))
    bad = json.loads(json.dumps(FR_PROFILE))
    bad["experience"][0]["bullets"].append("Géré une équipe de 40 personnes.")   # extra, invented bullet
    Path(env.tailor.translated_path("fr")).write_text(json.dumps(bad))
    assert env.tailor.localized(PROFILE, dict(FR_JOB)) == (PROFILE, "en")
    assert env.tailor.profile_versions()["fr"].startswith("ignored")
    Path(env.tailor.translated_path("fr")).write_text("{not json")
    assert env.tailor.localized(PROFILE, dict(FR_JOB)) == (PROFILE, "en")


def test_list_button_greys_a_job_then_removes_it(env):
    c = TestClient(env.web.app)
    jid = env.store.add_manual({"title": "Architect", "company": "Acme SA"})
    other = env.store.add_manual({"title": "Planner", "company": "Other SA"})
    st = env.store.get_job(jid)["status"]
    page = c.get(f"/jobs?status={st}").text
    assert f'id="job-{jid}"' in page and f'/job/{jid}/dismiss' in page and 'class="card dim"' not in page
    # first click: greyed out, still in the list
    r = c.post(f"/job/{jid}/dismiss", data={"next": f"/jobs?status={st}#job-{jid}"}, follow_redirects=False)
    assert r.status_code == 303 and r.headers["location"].endswith(f"#job-{jid}")
    j = env.store.get_job(jid)
    assert j["dimmed"] == 1 and j["status"] == st
    assert f'<div class="card dim" id="job-{jid}">' in c.get(f"/jobs?status={st}").text
    # "Keep" undoes it
    assert c.post(f"/job/{jid}/keep", headers={"x-requested-with": "fetch"}).json()["state"] == "kept"
    assert env.store.get_job(jid)["dimmed"] == 0
    # two clicks: gone from the list, into "discarded"; the page gets the new tab counts
    assert c.post(f"/job/{jid}/dismiss", headers={"x-requested-with": "fetch"}).json()["state"] == "dimmed"
    d = c.post(f"/job/{jid}/dismiss", headers={"x-requested-with": "fetch"}).json()
    assert d["state"] == "discarded" and d["counts"]["discarded"] == 1 and d["counts"][st] == 1
    assert env.store.get_job(jid)["status"] == "discarded" and env.store.get_job(other)["status"] == st
    assert c.post(f"/job/{jid}/dismiss", headers={"x-requested-with": "fetch"}).json()["state"] is None   # already gone
    # back from "discarded": normal again, not grey
    page = c.get("/jobs?status=discarded").text
    assert "Back to new" in page and f"/job/{jid}/dismiss" not in page
    c.post(f"/job/{jid}/status", data={"status": "new"})
    assert env.store.get_job(jid)["dimmed"] == 0
    assert c.post("/job/999999/dismiss", follow_redirects=False).status_code == 303                       # unknown job: no error


def test_database_from_before_the_grey_out_gets_the_column(env):
    import sqlite3
    c = sqlite3.connect(env.config.DB_PATH)
    c.execute("ALTER TABLE jobs DROP COLUMN dimmed")
    c.commit(); c.close()
    env.store.init_db()
    jid = env.store.add_manual({"title": "Architect", "company": "Acme SA"})
    assert env.store.dismiss(jid) == "dimmed"
