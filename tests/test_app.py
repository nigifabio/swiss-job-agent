from pathlib import Path


def test_filters(env):
    f = env.filters
    assert f.title_ok("Senior Cloud Architect")
    assert not f.title_ok("Junior Cloud Architect")
    assert not f.title_ok("Accountant")
    assert not f.title_ok("Architecture Intern")
    assert f.location_ok("Genève, Switzerland")
    assert f.location_ok("Remote - EMEA")
    assert f.location_ok("Remote")
    assert f.location_ok("Paris; Geneva")
    assert not f.location_ok("Zurich")
    assert not f.location_ok("Remote, US only")
    assert not f.location_ok("US-NC-Remote")
    assert not f.location_ok("Colombia, Remote")
    assert not f.location_ok("Dublin", "Fully remote team, based in Geneva")
    assert f.location_ok("", "Office in Lausanne")


def test_score_whole_words(env):
    f = env.filters
    job = {"title": "Cloud Architect AWS", "description": "Terraform and laws, rapid delivery"}
    assert f.matched(job) == ["aws", "terraform"]
    assert f.score(job) == 67  # aws in title (3) + terraform (1) = 4 / 6


def test_upsert_dedupes_and_scores(env):
    job = {"content_hash": "h1", "title": "Cloud Architect", "description": "aws", "source": "t"}
    job["score"], job["score_rationale"] = env.fetch.score_job(job)
    assert env.store.upsert_jobs([job, dict(job)]) == 1
    assert env.store.upsert_jobs([job]) == 0
    [row] = env.store.list_jobs("new")
    assert row["score"] == 17 and row["score_rationale"] == "matches: aws"


def test_web_routes_and_safe_url(env):
    from fastapi.testclient import TestClient
    c = TestClient(env.web.app)
    assert c.get("/healthz").json() == {"ok": True}
    r = c.post("/add", data={"title": "X", "url": "javascript:alert(1)"}, follow_redirects=False)
    assert r.status_code == 303
    page = c.get(r.headers["location"]).text
    assert "javascript:" not in page
    assert c.get("/jobs?status=shortlisted").status_code == 200


def test_access_enforced(env, monkeypatch):
    monkeypatch.setattr(env.auth, "ENABLED", True)
    monkeypatch.setattr(env.auth, "user_email", lambda t: "a@b.c" if t == "good" else None)
    from fastapi.testclient import TestClient
    c = TestClient(env.web.app)
    assert c.get("/healthz").status_code == 200
    assert c.get("/jobs").status_code == 403
    r = c.get("/jobs", headers={"cf-access-jwt-assertion": "good"})
    assert r.status_code == 200 and "a@b.c" in r.text


def test_prefix_keywords(env, monkeypatch):
    monkeypatch.setattr(env.config, "TITLE_KEYWORDS", ["coordinat*", "réception*"])
    f = env.filters
    assert f.title_ok("Coordinatrice logistique 80%")
    assert f.title_ok("Réceptionniste bilingue")
    assert not f.title_ok("Accoordinated")  # prefix still needs a word start


def test_tailored_cv(env, tmp_path):
    import json
    from fastapi.testclient import TestClient
    Path(env.config.PROFILE_PATH).write_text(json.dumps({"name": "Sam Test", "summary": "Ops", "expertise": ["Customer Operations"],
               "experience": [{"title": "Coordinator", "org": "X", "loc": "Y", "dates": "2020", "bullets": ["Did <things> & more"]}]}))
    jid = env.store.add_manual({"title": "Architect", "company": "Acme SA"})
    c = TestClient(env.web.app)
    assert c.get(f"/job/{jid}/cv").status_code == 404
    assert c.post(f"/job/{jid}/cv", follow_redirects=False).status_code == 303
    r = c.get(f"/job/{jid}/cv?dl=1")
    assert r.status_code == 200 and r.content[:4] == b"%PDF"
    assert "Sam_Test_CV_Acme_SA.pdf" in r.headers["content-disposition"]
    assert b"Alex" not in r.content


def test_quick_status_and_apply_prompt(env):
    from fastapi.testclient import TestClient
    c = TestClient(env.web.app)
    job = {"content_hash": "q1", "title": "Cloud Architect", "url": "https://example.com/j", "source": "t"}
    env.store.upsert_jobs([job])
    [row] = env.store.list_jobs("new")
    page = c.get("/jobs?status=new").text
    assert 'class="btn small apply-link"' in page and f'id="prompt-{row["id"]}"' in page
    r = c.post(f"/job/{row['id']}/status", data={"status": "applied", "next": "/jobs?status=new"},
               follow_redirects=False)
    assert r.headers["location"] == "/jobs?status=new"
    [applied] = env.store.list_jobs("applied")
    assert applied["applied_date"]
    # next must stay on this site
    r = c.post(f"/job/{row['id']}/status", data={"status": "new", "next": "//evil.example"},
               follow_redirects=False)
    assert r.headers["location"] == f"/job/{row['id']}"


def test_scan_now_runs_once(env, monkeypatch):
    from fastapi.testclient import TestClient
    monkeypatch.setattr(env.fetch, "_run", lambda: 3)
    assert env.fetch.run() == 3
    assert env.store.get_meta()["last_scan_new"] == "3"
    with env.fetch._single_run() as got:
        assert got
        assert env.fetch.is_running() and env.fetch.run() is None
    c = TestClient(env.web.app)
    assert "Last scan" in c.get("/jobs?status=new").text
    assert c.post("/scan", follow_redirects=False).status_code == 303


def _profile(env):
    import json
    p = {"name": "Alex Test", "headline": "Cloud Architect", "summary": "Cloud and infrastructure architect.",
         "contact": {"email": "a@b.c", "location": "Geneva, Switzerland"},
         "expertise": ["Cloud Architecture", "Security & Compliance"],
         "experience": [{"title": "Technical Manager", "org": "GTT", "loc": "CH", "dates": "2020 – now",
                         "bullets": ["Led vendor evaluation.", "Automated AWS landing zones with Terraform."]}]}
    Path(env.config.PROFILE_PATH).write_text(json.dumps(p))
    return p


def test_skill_highlight(env):
    html, have, missing, _ = env.skills.analyse("We need AWS, Terraform & Kubernetes. Allemand un atout. <script>")
    assert "aws" in have and "terraform" in have
    assert "kubernetes" in missing and "german" in missing
    assert '<mark class="have"' in html and '<mark class="miss"' in html
    assert "<script>" not in html and "&lt;script&gt;" in html


def test_enrich_jsonld(env, monkeypatch):
    import types
    page = ('<script type="application/ld+json">{"@type":"JobPosting","description":'
            '"<p>Full <b>text</b></p><ul><li>AWS</li></ul>"}</script>')
    monkeypatch.setattr(env.enrich.httpx, "get", lambda *a, **k: types.SimpleNamespace(
        text=page, raise_for_status=lambda: None))
    assert env.enrich.full_description("https://x") == "Full text\n\nAWS"
    # Greenhouse sends entity-escaped HTML
    assert env.enrich.html_to_text("&lt;p&gt;About &lt;strong&gt;us&lt;/strong&gt;&lt;/p&gt;&lt;p&gt;Two&lt;/p&gt;") == "About us\n\nTwo"


def test_report_and_stats(env):
    import datetime
    today = datetime.date.today()
    jid = env.store.add_manual({"title": "Coordinatrice 80-100%", "company": "Acme SA", "location": "Lausanne"})
    env.store.update_status(jid, "applied")
    env.store.update_fields(jid, {"contact": "Mme Dupont", "orp_assigned": 1})
    kind, key, s, e, label = env.report.period()
    [row] = env.report.rows(s, e)
    assert row["Taux"] == "80-100%" and row["Assign. ORP"] == "Oui" and row["Résultat"] == "En suspens"
    assert row["Type de candidature"].startswith("Écrite")
    assert "Coordinatrice" in env.report.to_csv([row])
    env.store.update_status(jid, "interview")
    st = env.report.stats()
    assert st["applied"] == 1 and st["interviews"] == 1 and st["this_month"] == 1
    assert env.report.shift("month", "2026-01", -1) == "2025-12"
    assert env.report.shift("week", "2026-W01", -1) == "2025-W52"
    from fastapi.testclient import TestClient
    c = TestClient(env.web.app)
    assert c.get("/stats").status_code == 200
    assert "Mme Dupont" in c.get(f"/report?month={today:%Y-%m}").text
    assert c.get(f"/report.pdf?month={today:%Y-%m}").content[:4] == b"%PDF"
    assert c.get("/report?month=bogus").status_code == 200


def test_letter_template_and_keyword_cv(env, monkeypatch):
    prof = _profile(env)
    job = {"id": 1, "title": "Cloud Architect", "company": "Acme SA", "location": "Genève",
           "description": "Nous cherchons un architecte cloud avec AWS et Terraform pour notre équipe à Genève."}
    text, how = env.letter.write(prof, job)
    assert how == "rules" and "Application for the position of Cloud Architect" in text   # no FR profile: English
    assert "Alex Test" in text and "AWS" in text
    path, sup, unsup = env.tailor.build_custom(prof, ["terraform", "kubernetes", "vendor"])
    assert sup == ["terraform", "vendor"] and unsup == ["kubernetes"]
    assert Path(path).read_bytes()[:4] == b"%PDF"


def test_skill_clicks_refine_scoring_highlighting_and_next_scan(env):
    from fastapi.testclient import TestClient
    c = TestClient(env.web.app)
    env.store.upsert_jobs([
        {"content_hash": "k1", "title": "Cloud Architect", "source": "t",
         "description": "AWS and Kubernetes. Fluent German required."},
        {"content_hash": "k2", "title": "Cloud Architect II", "source": "t", "description": "AWS and Kubernetes."}])
    c.post("/scan")                                   # nothing configured: just ensures scoring ran once
    env.store.rescore(env.fetch.score_job)
    before = {j["content_hash"]: j["score"] for j in env.store.list_jobs("new")}

    # red "kubernetes" -> I have it: becomes green, both jobs score higher
    r = c.post("/skills", data={"action": "have", "term": "Kubernetes", "next": "/jobs?status=new"}, follow_redirects=False)
    assert r.status_code == 303 and r.headers["location"] == "/jobs?status=new"
    after = {j["content_hash"]: j["score"] for j in env.store.list_jobs("new")}
    assert after["k1"] > before["k1"] and after["k2"] > before["k2"]
    _, have, missing, _ = env.skills.analyse("We use Kubernetes")
    assert "kubernetes" in have and "kubernetes" not in missing

    # red "german" -> avoid: the job asking for it drops below the other one
    c.post("/skills", data={"action": "avoid", "term": "german"})
    ranked = [j["content_hash"] for j in env.store.list_jobs("new")]
    assert ranked == ["k2", "k1"]
    k1 = next(j for j in env.store.list_jobs("new") if j["content_hash"] == "k1")
    assert "avoid: german" in k1["score_rationale"]
    assert env.skills.analyse("German required")[3] == ["german"]

    # green "aws" (profile keyword) -> remove, then restore
    c.post("/skills", data={"action": "remove", "term": "aws"})
    assert "aws" not in env.prefs.skills() and "aws" in env.prefs.summary()["removed"]
    c.post("/skills", data={"action": "restore", "term": "aws"})
    assert "aws" in env.prefs.skills()

    # the next scan (fresh process state) still uses the refined lists
    env.prefs.invalidate()
    assert "kubernetes" in env.prefs.skills() and env.prefs.avoided() == ["german"]
    # bad input is ignored, never a server error
    assert c.post("/skills", data={"action": "drop-table", "term": "x"}).status_code == 200
    assert "Skills &amp; preferences" in c.get("/cv").text


def test_loose_duplicates_across_sources(env):
    lk = env.normalize.loose_key
    assert lk("Coordinateur de commandes (f/m/d)", "dormakaba Schweiz AG", "Le Mont-sur-Lausanne") == \
           lk("<b>Coordinateur</b> de commandes 80-100%", "Dormakaba", "le Mont-sur-Lausanne VD")
    assert lk("Coordinatrice RH (H/F)", "Acme Sàrl", "Genève") == lk("Coordinatrice RH", "ACME", "Geneve, CH")
    assert lk("Cloud Architect", "Acme", "Geneva") != lk("Cloud Engineer", "Acme", "Geneva")
    a = {"content_hash": "a", "title": "Coordinateur (H/F) 80%", "company": "Acme SA", "location": "Lausanne", "source": "jobup.ch"}
    b = {"content_hash": "b", "title": "Coordinateur", "company": "ACME", "location": "Lausanne VD", "source": "job-room"}
    assert env.store.upsert_jobs([a]) == 1 and env.store.upsert_jobs([b]) == 0
    [kept] = env.store.list_jobs("new")
    assert kept["source"] == "jobup.ch"                       # first source wins
