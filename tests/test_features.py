"""Features for the Swiss market: ORP reminders and assignments, spontaneous applications, follow-ups,
work-rate and company filters, one-click search fixes, home town + radius, travel time, posting
conditions, closed postings, interview sheet. No network (see conftest.net)."""
import datetime
import json
from pathlib import Path

import httpx
from fastapi.testclient import TestClient

from conftest import jresp

PROFILE = {"name": "Sam Test", "headline": "Coordinator", "summary": "Operations coordinator.",
           "contact": {"email": "sam@example.org", "location": "Pully, Vaud, Suisse"}, "expertise": ["Planning"],
           "experience": [{"title": "Coordinator", "org": "Acme SA", "loc": "Lausanne", "dates": "2020 – 2025",
                           "bullets": ["Planned deliveries for 12 drivers with AWS tools.", "Trained five new colleagues."]}]}


def _profile(env):
    Path(env.config.PROFILE_PATH).write_text(json.dumps(PROFILE))


def _job(env, title="Cloud Architect", status="new", **kw):
    jid = env.store.add_manual(dict({"title": title, "company": "Acme SA", "location": "Lausanne, VD", "source": "jobs.ch"}, **kw))
    env.store.update_status(jid, status)
    with env.store.conn() as c:                      # scraped, not typed in by hand
        c.execute("UPDATE jobs SET origin='scraped' WHERE id=?", (jid,))
    return jid


def test_work_rate_and_company_filters_apply_to_every_source(env, monkeypatch):
    f = env.filters
    assert f.stated_rate("Coordinator 60-80%") == (60, 80) and f.stated_rate("Vendeur 80% à 100%") == (80, 100)
    assert f.stated_rate("Assistant 40 %") == (40, 40) and f.stated_rate("Plan 2025") is None and f.stated_rate("Top 5% team") is None
    monkeypatch.setattr(env.config, "WORK_RATE_MIN", 80)
    assert f.rate_ok("Architect 80-100%") and f.rate_ok("Architect") and not f.rate_ok("Architect 40-60%")
    monkeypatch.setattr(env.config, "WORK_RATE_MIN", 0)
    monkeypatch.setattr(env.config, "WORK_RATE_MAX", 60)
    assert f.rate_ok("Architect 50%") and not f.rate_ok("Architect 80-100%") and f.rate_ok("Architect")   # unstated: kept
    monkeypatch.setattr(env.config, "COMPANY_EXCLUDE", ["adecco", "page personnel"])
    assert not f.company_ok("Adecco Ressources Humaines SA") and not f.company_ok("Page Personnel") and f.company_ok("Adeccor SA")
    # the scan drops them whatever the source
    monkeypatch.setattr(env.config, "PROVIDERS", ["jobup"])
    monkeypatch.setattr(env.fetch, "MODULES", {"jobup": type("M", (), {"fetch": staticmethod(lambda: [
        {"source": "x", "title": "Cloud Architect", "company": "Adecco", "location": "Lausanne", "description": "", "url": "u1", "salary": "", "posted_at": "", "content_hash": "h1"},
        {"source": "x", "title": "Cloud Architect 100%", "company": "Good SA", "location": "Lausanne", "description": "", "url": "u2", "salary": "", "posted_at": "", "content_hash": "h2"},
        {"source": "x", "title": "Cloud Architect", "company": "Fine SA", "location": "Lausanne", "description": "", "url": "u3", "salary": "", "posted_at": "", "content_hash": "h3"}])})})
    assert env.fetch._run() == 1 and [j["company"] for j in env.store.list_jobs("new")] == ["Fine SA"]


def test_one_click_fixes_change_the_setting_and_clear_the_list(env, monkeypatch):
    c = TestClient(env.web.app)
    monkeypatch.setattr(env.config, "TITLE_KEYWORDS", [])
    keep, drop, far, agency = _job(env, "Cloud Architect"), _job(env, "Industrial Architect"), \
        _job(env, "DevOps Engineer", location="Genève"), _job(env, "DevOps Lead", company="Adecco SA")
    mine = env.store.add_manual({"title": "Industrial thing", "company": "X"})          # typed by hand: never touched
    env.store.update_status(mine, "new")
    r = c.post("/tune", data={"action": "add", "name": "TITLE_EXCLUDE", "value": "Industrial"}, follow_redirects=False)
    assert r.status_code == 303 and "industrial" in env.config.TITLE_EXCLUDE
    assert env.store.get_job(drop)["status"] == "discarded" and env.store.get_job(drop)["discard_reason"] == "filtered"
    assert env.store.get_job(keep)["status"] == "new" and env.store.get_job(mine)["status"] == "new"
    c.post("/tune", data={"action": "remove", "name": "LOCATION_KEYWORDS", "value": "genève"})
    assert "genève" not in env.config.LOCATION_KEYWORDS and env.store.get_job(far)["status"] == "discarded"
    c.post("/tune", data={"action": "add", "name": "COMPANY_EXCLUDE", "value": "Adecco SA"})
    assert env.store.get_job(agency)["status"] == "discarded" and not env.filters.company_ok("Adecco SA")
    # not every setting can be changed this way, and the towns can't be emptied
    assert env.tune.change("add", "SCORE_KEYWORDS", "x") is None and env.tune.change("remove", "NOPE", "x") is None
    for t in list(env.config.LOCATION_KEYWORDS):
        env.tune.change("remove", "LOCATION_KEYWORDS", t)
    assert env.config.LOCATION_KEYWORDS
    assert "Removed by a change of the search settings" in c.get("/jobs?status=discarded").text
    assert 'value="filtered"' not in c.get("/jobs?status=new").text            # not offered in the Why? menu


def test_stats_offers_the_fixes(env, monkeypatch):
    c = TestClient(env.web.app)
    monkeypatch.setattr(env.config, "TITLE_KEYWORDS", [])
    for t in ("Constructeur industriel", "Dessinateur industriel"):
        env.store.dismiss(_job(env, t), "wrong_role")
    env.store.dismiss(_job(env, "Planner", location="Genève, GE"), "location")
    env.store.dismiss(_job(env, "Clerk", company="Adecco SA"), "company")
    page = c.get("/stats").text
    assert "skip titles with “industriel” (2)" in page and "stop searching in Genève (1)" in page and "never show Adecco SA (1)" in page
    c.post("/tune", data={"action": "add", "name": "TITLE_EXCLUDE", "value": "industriel"})
    assert "skip titles with “industriel”" not in c.get("/stats").text       # done: no longer offered


def test_home_town_and_radius_recompute_the_search_area(env):
    c = TestClient(env.web.app)
    form = {k: (",".join(map(str, v)) if isinstance(v, list) else str(int(v) if isinstance(v, (bool, float)) else v))
            for k, v in ((k, getattr(env.config, k)) for k in env.config.EDITABLE)}
    form.update(HOME_TOWN="Geneva", RADIUS_KM="15", WORK_RATE_MIN="60", ORP_MONTHLY_TARGET="8", COMMUTE_MAX="45")
    assert c.post("/settings", data=form, follow_redirects=False).status_code == 303
    cfg = env.config
    assert cfg.HOME_TOWN == "Geneva" and cfg.RADIUS_KM == 15 and "carouge" in cfg.LOCATION_KEYWORDS and "lausanne" not in cfg.LOCATION_KEYWORDS
    assert "GE" in cfg.JOBROOM_CANTONS and "Genève" in cfg.WHERE and (cfg.WORK_RATE_MIN, cfg.ORP_MONTHLY_TARGET, cfg.COMMUTE_MAX) == (60, 8, 45)
    assert env.report.target() == 8
    page = c.get("/settings").text
    assert 'name="HOME_TOWN" value="Geneva"' in page and 'name="RADIUS_KM" value="15"' in page
    # same home and radius: towns typed by hand are kept; out-of-range numbers are bounded
    form.update(LOCATION_KEYWORDS="carouge,meyrin", WORK_RATE_MIN="900", RADIUS_KM="15")
    c.post("/settings", data=form)
    assert env.config.LOCATION_KEYWORDS == ["carouge", "meyrin"] and env.config.WORK_RATE_MIN == 100
    # an unknown town keeps what was typed
    form.update(HOME_TOWN="Nowhereville", RADIUS_KM="30", LOCATION_KEYWORDS="x-town")
    c.post("/settings", data=form)
    assert env.config.LOCATION_KEYWORDS == ["x-town"] and env.config.HOME_TOWN == "Nowhereville"


def test_orp_reminders_assignments_and_spontaneous_applications(env, monkeypatch):
    c = TestClient(env.web.app)
    monkeypatch.setattr(env.config, "ORP_MONTHLY_TARGET", 3)
    today = datetime.date.today()
    p = env.report.month_progress(today.replace(day=25))
    assert (p["done"], p["target"], p["missing"]) == (0, 3, 3) and p["urgent"] and p["last_month"] is None
    assert env.report.month_progress(today.replace(day=3))["last_month"]["key"] == (today.replace(day=1) - datetime.timedelta(days=1)).strftime("%Y-%m")
    # a spontaneous application counts
    r = c.post("/add/spontaneous", data={"company": "Atelier SA", "role": "Dessinatrice", "location": "Lausanne", "contact": "Mme X"},
               follow_redirects=False)
    jid = int(r.headers["location"].rsplit("/", 1)[1])
    j = env.store.get_job(jid)
    assert (j["status"], j["title"], j["source"], j["applied_date"], j["contact"]) == \
        ("applied", "Candidature spontanée – Dessinatrice", "spontaneous", today.isoformat(), "Mme X")
    assert env.report.month_progress()["done"] == 1 and any(r["Poste"].startswith("Candidature spontanée") for r in env.report.rows(today.replace(day=1), today))
    assert "Spontaneous application" in c.get("/add?kind=spontaneous").text
    # an ORP assignment with its deadline is shown first
    a = _job(env, "Assigned job")
    c.post(f"/job/{a}/fields", data={"orp_assigned": "1", "orp_deadline": (today + datetime.timedelta(days=2)).isoformat()})
    b = _job(env, "Assigned no date")
    c.post(f"/job/{b}/fields", data={"orp_assigned": "1", "orp_deadline": "not a date"})
    rows = env.store.assignments_open()
    assert [(r["id"], r["days_left"]) for r in rows] == [(a, 2), (b, None)]
    page = c.get("/jobs?status=new").text
    assert "Assigned by the ORP" in page and "2 days left" in page and "no deadline set" in page and "1 / 3" in page
    env.store.update_status(a, "applied")
    assert [r["id"] for r in env.store.assignments_open()] == [b]


def test_follow_up_reminder_message_and_interview_sheet(env):
    _profile(env)
    c = TestClient(env.web.app)
    jid = _job(env, "Operations Coordinator", description="We need planning and AWS. Kubernetes is a plus.")
    env.store.update_status(jid, "applied")
    assert env.store.awaiting_answer() == []                                # applied today
    env.store.update_fields(jid, {"applied_date": (datetime.date.today() - datetime.timedelta(days=12)).isoformat()})
    w = env.store.awaiting_answer()
    assert [x["id"] for x in w] == [jid] and w[0]["days_waiting"] == 12
    assert "time to follow up" in c.get("/jobs?status=applied").text
    page = c.get(f"/job/{jid}").text
    assert "Follow-up message" in page and "My application for Operations Coordinator" in page and "at Acme SA" in page
    assert c.post(f"/job/{jid}/followed-up", follow_redirects=False).status_code == 303
    assert env.store.awaiting_answer() == [] and env.store.get_job(jid)["followed_up_at"] == datetime.date.today().isoformat()
    for lang in ("fr", "de", "it"):
        text = env.compose.followup(PROFILE, env.store.get_job(jid), lang)
        assert "Operations Coordinator" in text and text.rstrip().endswith("Sam Test")
    pdf = c.get(f"/job/{jid}/prep.pdf")
    assert pdf.status_code == 200 and pdf.content[:4] == b"%PDF" and "Interview" in pdf.headers["content-disposition"]
    assert "Interview preparation sheet" in page
    assert c.get("/job/99999/prep.pdf").status_code == 404


def test_posting_conditions_are_flagged(env, monkeypatch):
    monkeypatch.setattr(env.config, "SCORE_KEYWORDS", ["french", "english", "aws"])
    r = env.requirements.flags
    kinds = lambda t: sorted(k for k, _ in r(t))
    assert kinds("Vous maîtrisez l'allemand (C1) et le français. Permis de conduire indispensable.") == ["driving", "language"]
    assert kinds("Deutschkenntnisse von Vorteil. Schweizer Bürger oder Arbeitsbewilligung. Strafregisterauszug.") == ["language", "permit", "record"]
    assert kinds("English and French required, AWS.") == [] and r("") == []
    assert [l for _, l in r("Bonnes connaissances d'italien")] == ["Italian (not in your skills)"]
    c = TestClient(env.web.app)
    jid = _job(env, description="Vous maîtrisez l'allemand. Extrait du casier judiciaire demandé.")
    page = c.get(f"/job/{jid}").text
    assert "German (not in your skills)" in page and "Criminal-record extract" in page and "salarium.bfs.admin.ch" in page


def test_travel_time_is_asked_once_per_town_and_far_jobs_greyed(env, net, monkeypatch):
    _profile(env)                                                        # home: Pully (from the CV address)
    monkeypatch.setattr(env.config, "COMMUTE_MAX", 30)
    asked = []

    def api(r):
        asked.append((r.url.params["from"], r.url.params["to"]))
        mins = {"Lausanne": "00d00:12:00", "Yverdon-les-Bains": "00d00:37:40"}.get(r.url.params["to"])
        return jresp({"connections": [{"duration": mins}, {"duration": "00d01:05:00"}] if mins else []})
    net["https://transport.opendata.ch/v1/connections"] = api
    assert env.commute.home() == "Pully" and env.commute.town("1400 Yverdon-les-Bains, VD") == "Yverdon-les-Bains"
    a, b, c_, d, e = (_job(env, "A", location="Lausanne, VD"), _job(env, "B", location="Lausanne"), _job(env, "C", location="Yverdon-les-Bains, VD"),
                      _job(env, "D", location="Atlantis"), _job(env, "E", location="Pully"))
    assert env.commute.fill() == 4
    got = {j: (env.store.get_job(j)["commute_min"], env.store.get_job(j)["dimmed"]) for j in (a, b, c_, d, e)}
    assert got == {a: (12, 0), b: (12, 0), c_: (38, 1), d: (None, 0), e: (0, 0)}                  # 38 > 30: greyed
    assert asked == [("Pully", "Lausanne"), ("Pully", "Yverdon-les-Bains"), ("Pully", "Atlantis")]
    env.commute.fill()
    assert len(asked) == 3                                              # remembered, also the unknown town
    page = TestClient(env.web.app).get("/jobs?status=new").text
    assert "🚆 12 min" in page and "🚆 38 min" in page
    assert "12 min</b> by public transport from Pully" in TestClient(env.web.app).get(f"/job/{a}").text
    # the timetable being down never breaks a scan or a page
    net["https://transport.opendata.ch/v1/connections"] = lambda r: httpx.Response(503)
    f = _job(env, "F", location="Morges")
    assert env.commute.fill() == 0 and TestClient(env.web.app).get(f"/job/{f}").status_code == 200


def test_postings_that_went_offline_are_noticed(env, net):
    old = (datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=9)).replace(tzinfo=None).isoformat(timespec="seconds")
    ids = {}
    for name, status, code in (("gone", "new", 404), ("gone-applied", "applied", 410), ("alive", "new", 200),
                               ("blocked", "new", 403), ("fresh", "new", 404)):
        ids[name] = _job(env, name.title(), status, url=f"https://jobs.test/{name}")
        net[f"https://jobs.test/{name}"] = (lambda code: lambda r: httpx.Response(code))(code)
        if name != "fresh":
            with env.store.conn() as c:
                c.execute("UPDATE jobs SET created_at=? WHERE id=?", (old, ids[name]))
    assert env.closed.check() == 2
    g = lambda n: env.store.get_job(ids[n])
    assert (g("gone")["status"], g("gone")["discard_reason"]) == ("discarded", "filled") and g("gone")["closed_at"]
    assert g("gone-applied")["status"] == "applied" and g("gone-applied")["closed_at"]          # kept, only noted
    assert all(g(n)["status"] == "new" and not g(n)["closed_at"] for n in ("alive", "blocked", "fresh"))
    assert not g("fresh")["url_checked_at"] and g("alive")["url_checked_at"]                    # young postings aren't asked
    assert env.closed.check() == 0                                       # asked this week already
    assert "no longer online" in TestClient(env.web.app).get(f"/job/{ids['gone-applied']}").text


def test_official_orp_form_lines_and_fallback(env, net):
    c = TestClient(env.web.app)
    a = _job(env, "Dessinatrice 80-100%", "applied", contact="Mme Dupont")
    b = _job(env, "Architecte", "applied")
    env.store.update_fields(a, {"applied_date": "2026-10-02", "contact": "Mme Dupont"})
    env.store.update_fields(b, {"applied_date": "2026-10-09", "apply_method": "phone", "orp_assigned": 1, "outcome_note": "Poste déjà pourvu"})
    env.store.update_status(b, "rejected")
    import importlib
    official = importlib.import_module("app.official")
    v = official.line_values(env.store.get_job(a), 1)
    assert v["jour-mois 1"] == "02  10" and v["Entreprise adresse_1"] == "Acme SA, Lausanne, VD\nMme Dupont"
    assert v["Description du poste_1"] == "Dessinatrice 80-100%" and (v["à temps partiel_1"], v["à plein temps_1"]) == ("/Ja", "/Off")
    assert (v["par lettre_1"], v["par téléphone_1"], v["en suspens_1"], v["négatif_1"], v["Assignation ORP_1"]) == ("/Ja", "/Off", "/Ja", "/Off", "/Off")
    v = official.line_values(env.store.get_job(b), 2)
    assert (v["par téléphone_2"], v["négatif_2"], v["Motif_2"], v["Assignation ORP_2"], v["à plein temps_2"]) == ("/Ja", "/Ja", "Poste déjà pourvu", "/Ja", "/Ja")
    assert official.month_label("2026-10") == "Octobre 2026"
    # the blank form can't be fetched (no network here): the app's own report is served instead
    net[official.URL] = lambda r: httpx.Response(503)
    r = c.get("/report.pdf?month=2026-10&official=1")
    assert r.status_code == 200 and r.content[:4] == b"%PDF" and "recherches-emploi-2026-10" in r.headers["content-disposition"]
    net[official.URL] = lambda r: httpx.Response(200, content=b"<html>not a pdf</html>")
    assert official.template() is None
    assert "Official ORP form" in c.get("/report?month=2026-10").text and "Official ORP form" not in c.get("/report?week=2026-W41").text
