"""List management (scan after a change of settings, best new, bulk actions, duplicates), skill
suggestions, profile check, translated profile, document checklist, week page, calendar feed and
the totals for the operator. No network."""
import datetime
import json
from pathlib import Path

from fastapi.testclient import TestClient

from test_features import PROFILE, _job

TEXT = ("Nous cherchons une personne pour coordonner la logistique du dépôt de Lausanne. Vous planifiez les tournées, "
        "suivez les stocks, gérez les fournisseurs et encadrez une équipe de douze chauffeurs. Expérience de trois ans "
        "dans la logistique, maîtrise de SAP et de kubernetes, permis de conduire, excellent français et bon anglais. "
        "Merci d'envoyer votre dossier complet avec certificats de travail, diplômes et extrait du casier judiciaire.")


def _form(env, **over):
    f = {k: (",".join(map(str, v)) if isinstance(v, list) else str(int(v) if isinstance(v, (bool, float)) else v))
         for k, v in ((k, getattr(env.config, k)) for k in env.config.EDITABLE)}
    f.update(over)
    return f


def test_a_change_of_what_is_searched_starts_a_scan_once(env, monkeypatch):
    c, runs = TestClient(env.web.app), []
    monkeypatch.setattr(env.web, "_start_background", lambda fn: (runs.append(1), env.store.set_meta(scan_started_at=env.store.now())))
    r = c.post("/settings", data=_form(env, UI_LANG="fr"), follow_redirects=False)
    assert r.headers["location"] == "/settings?saved=1" and not runs                    # nothing searched changed
    r = c.post("/settings", data=_form(env, TITLE_KEYWORDS="architect,devops,cloud"), follow_redirects=False)
    assert r.headers["location"] == "/settings?saved=1&scan=1" and len(runs) == 1
    assert "Une nouvelle recherche a démarré" in c.get(r.headers["location"]).text          # (the site is in French now)
    r = c.post("/settings", data=_form(env, TITLE_KEYWORDS="architect,devops,cloud,sre"), follow_redirects=False)
    assert r.headers["location"] == "/settings?saved=1" and len(runs) == 1              # one scan for several saves in a row
    env.store.set_meta(scan_started_at="2020-01-01T00:00:00")
    c.post("/settings", data=_form(env, SCORE_KEYWORDS="aws"))                          # skills only re-rank: no scan
    assert len(runs) == 1
    c.post("/settings", data=_form(env, TITLE_EXCLUDE="junior"))
    assert len(runs) == 2


def test_best_new_shows_what_arrived_since_the_last_visit(env):
    c = TestClient(env.web.app)
    old = [_job(env, f"Old Architect {i}") for i in range(3)]
    with env.store.conn() as k:
        k.execute("UPDATE jobs SET created_at='2020-01-01T00:00:00', score=90")
    assert "Best new" not in c.get("/jobs").text                                     # first visit: nothing older than 48 h is "new"
    env.store.set_meta(visit_at="2021-01-01T00:00:00")                                # ... the person comes back days later
    fresh = [_job(env, f"Fresh Architect {i}") for i in range(12)]
    with env.store.conn() as k:
        for n, jid in enumerate(fresh):
            k.execute("UPDATE jobs SET score=? WHERE id=?", (n, jid))
    page = c.get("/jobs").text
    assert "★ Best new (10)" in page and page.count('class="fresh"') == 12
    best = c.get("/jobs?status=new&view=best").text
    assert best.count('<div class="card') == 10 and "Fresh Architect 11" in best and "Fresh Architect 1<" not in best
    assert "Old Architect" not in best and 'id="bulk"' not in best
    assert c.get("/jobs").text.count('class="fresh"') == 12                           # same visit: still marked
    assert old


def test_bulk_discard_shortlist_and_below_a_score(env):
    c = TestClient(env.web.app)
    ids = [_job(env, f"Architect {i}") for i in range(6)]
    with env.store.conn() as k:
        for n, jid in enumerate(ids):
            k.execute("UPDATE jobs SET score=? WHERE id=?", (n * 10, jid))
        k.execute("UPDATE jobs SET orp_assigned=1 WHERE id=?", (ids[0],))
    page = c.get("/jobs").text
    assert 'id="bulk"' in page and page.count('class="pick"') == 6 and "Discard the selected" in page
    r = c.post("/jobs/bulk", data={"status": "new", "action": "discard", "reason": "location", "ids": [str(ids[5]), str(ids[4]), "999"]},
               follow_redirects=False)
    assert r.headers["location"] == "/jobs?status=new&done=2" and "2 jobs moved." in c.get(r.headers["location"]).text
    assert env.store.get_job(ids[5])["status"] == "discarded" and env.store.get_job(ids[5])["discard_reason"] == "location"
    c.post("/jobs/bulk", data={"status": "new", "action": "shortlist", "ids": [str(ids[3])]})
    assert env.store.get_job(ids[3])["status"] == "shortlisted"
    c.post("/jobs/bulk", data={"status": "new", "action": "below", "below": "20"})
    # under 20: scores 0 and 10, but the one the ORP assigned is never swept away
    assert [env.store.get_job(i)["status"] for i in ids[:3]] == ["new", "discarded", "new"]
    assert c.post("/jobs/bulk", data={"status": "new", "action": "below", "below": "abc"}, follow_redirects=False).headers["location"].endswith("done=0")
    assert c.post("/jobs/bulk", data={"status": "applied", "action": "discard", "ids": [str(ids[2])]}).status_code == 200


def test_the_same_job_from_an_agency_is_one_card(env):
    c = TestClient(env.web.app)
    a = _job(env, "Coordinateur logistique (H/F) 80-100%", company="Transports Dupont SA", description=TEXT)
    b = _job(env, "Coordinateur Logistique 100%", company="Adecco Ressources Humaines", source="jobup.ch",
             description="Notre client, une entreprise de transport, cherche: " + TEXT[40:330])
    other = _job(env, "Coordinateur logistique", company="Migros Vaud",
                 description="Vous rejoignez notre centrale de distribution à Ecublens pour organiser les flux de marchandises, la réception "
                             "des camions et la préparation des commandes des magasins de la région avec une équipe motivée et soudée chaque jour.")
    short = _job(env, "Coordinateur logistique", company="Petit SA", description="Poste à Lausanne.")
    rows = env.twins.group(env.store.list_jobs("new"))
    lead = next(j for j in rows if j["twins"])
    assert {lead["id"], lead["twins"][0]["id"]} == {a, b} and len(rows) == 3          # same title elsewhere, other text: separate
    page = c.get("/jobs").text
    assert "Same job also posted by:" in page and page.count('<div class="card') == 3
    twin = lead["twins"][0]["id"]
    assert f'name="twins" value="{twin}"' in page
    # what is done to the card is done to its copy
    c.post(f"/job/{lead['id']}/dismiss", data={"twins": str(twin)})
    assert env.store.get_job(twin)["dimmed"] == 1
    c.post(f"/job/{lead['id']}/keep", data={"twins": str(twin)})
    assert env.store.get_job(twin)["dimmed"] == 0
    c.post(f"/job/{lead['id']}/status", data={"status": "applied", "twins": str(twin)})
    assert env.store.get_job(lead["id"])["status"] == "applied"
    assert env.store.get_job(twin)["status"] == "discarded" and env.store.get_job(twin)["discard_reason"] == "duplicate"
    assert env.twins.expand([other], env.store.list_jobs("new")) == [other] and short


def test_skills_often_asked_are_offered_once(env):
    Path(env.config.PROFILE_PATH).write_text(json.dumps(PROFILE))
    c = TestClient(env.web.app)
    for i in range(3):
        _job(env, f"Architect {i}", description="Kubernetes and docker every day. AWS.")
    _job(env, "Architect x", description="Ansible once.")
    asked, total = env.suggest.missing_skills()
    assert dict(asked).get("kubernetes") == 3 and "ansible" not in dict(asked) and "aws" not in dict(asked) and total == 4
    page = c.get("/cv").text
    assert "Often asked in your jobs" in page and "kubernetes" in page and "3 jobs" in page
    c.post("/skills", data={"action": "have", "term": "kubernetes", "next": "/cv#asked"})
    c.post("/skills", data={"action": "ignore", "term": "docker", "next": "/cv#asked"})
    asked, _ = env.suggest.missing_skills()
    assert "kubernetes" not in dict(asked) and "docker" not in dict(asked) and "kubernetes" in env.prefs.skills()


def test_profile_check_says_what_is_missing(env):
    Path(env.config.PROFILE_PATH).write_text(json.dumps(PROFILE))
    rep = env.strength.report(PROFILE)
    state = {r["label"]: r["ok"] for r in rep["rows"]}
    assert state["A job title under your name"] and state["Dates on every job"] and state["Your last jobs say what you did"]
    assert not state["Contact details complete"] and not state["A summary of 3 to 5 lines"] and not state["Languages with their level"]
    assert not state["Results with numbers"] and not state["Education and training listed"]
    full = dict(PROFILE, contact={"email": "a@b.ch", "phone": "+41 79 000 00 00", "location": "Pully"}, education=["CFC, 2010"],
                extras=["Français (langue maternelle)", "Anglais (C1)"], expertise=list("abcdef"), summary=" ".join(["mot"] * 40))
    full["experience"] = [dict(PROFILE["experience"][0], bullets=["Planned 12 drivers.", "Cut delays by 30%.", "Trained 5 colleagues."])]
    assert all(r["ok"] for r in env.strength.checks(full) if not r["link"])
    page = TestClient(env.web.app).get("/cv").text
    assert "Profile check" in page and f"{rep['done']} / {rep['total']}" in page and "Results with numbers" in page


def test_profile_translated_side_by_side(env, monkeypatch):
    profile = dict(PROFILE, summary="Coordinateur des opérations avec huit ans d'expérience dans la logistique et le service à la clientèle en Suisse romande.",
                   experience=[dict(PROFILE["experience"][0], bullets=["Planification des tournées de douze chauffeurs dans le canton.",
                                                                       "Formation de cinq nouveaux collègues sur le système."])])
    Path(env.config.PROFILE_PATH).write_text(json.dumps(profile))
    monkeypatch.setattr(env.config, "LANGUAGES", ["fr", "de"])
    c = TestClient(env.web.app)
    assert c.get("/profile/translate/fr", follow_redirects=False).status_code == 303          # its own language
    assert c.get("/profile/translate/xx", follow_redirects=False).status_code == 303
    need = next(r for r in env.strength.checks(profile) if r["link"])
    assert need["label"] == "CV ready in German" and not need["ok"] and "/profile/translate/de" in c.get("/cv").text
    page = c.get("/profile/translate/de").text
    assert "My profile in German" in page and "Planification des tournées" in page and 'name="exp_0_b_1"' in page
    r = c.post("/profile/translate/de", data={"headline": "Koordinator", "summary": "Koordinator mit acht Jahren Erfahrung.",
                                              "exp_0_b_0": "Tourenplanung für zwölf Fahrer."}, follow_redirects=False)
    assert r.headers["location"] == "/profile/translate/de?saved=3"
    saved = json.loads(Path(env.tailor.translated_path("de")).read_text())
    assert saved["headline"] == "Koordinator" and saved["experience"][0]["bullets"] == ["Tourenplanung für zwölf Fahrer.", profile["experience"][0]["bullets"][1]]
    assert "name" not in saved and "contact" not in saved
    assert env.tailor.profile_versions()["de"] == "ok"
    page = c.get("/profile/translate/de?saved=3").text
    assert "Tourenplanung für zwölf Fahrer." in page and "Saved: 3 of" in page
    assert next(r for r in env.strength.checks(profile) if r["link"])["ok"]


def test_documents_checklist_follows_the_posting(env):
    c = TestClient(env.web.app)
    jid = _job(env, "Coordinateur", description=TEXT)
    rows = {r["key"]: r for r in env.docs.checklist(env.store.get_job(jid))}
    assert rows["certificates"]["asked"] and rows["diplomas"]["asked"] and rows["record"]["asked"] and rows["cv"]["asked"]
    assert not rows["photo"]["asked"] and not rows["debt"]["asked"] and not any(r["done"] for r in rows.values())
    page = c.get(f"/job/{jid}").text
    assert "Documents to send" in page and page.count("asked in the posting") == 3
    c.post(f"/job/{jid}/docs", data={"docs": ["cv", "certificates", "bogus"]})
    assert env.docs.done(env.store.get_job(jid)) == ["cv", "certificates"]
    assert "2 ready" in c.get(f"/job/{jid}").text


def test_week_page_and_calendar_feed(env):
    c = TestClient(env.web.app)
    today = datetime.date.today()
    a = _job(env, "Cloud Architect; senior, AWS", "applied")
    env.store.update_fields(a, {"interview_at": (today + datetime.timedelta(days=2)).isoformat() + "T14:30"})
    assert env.store.get_job(a)["status"] == "interview"                               # an interview date moves the job
    b = _job(env, "Assigned job")
    env.store.update_fields(b, {"orp_assigned": 1, "orp_deadline": (today + datetime.timedelta(days=3)).isoformat()})
    f = _job(env, "Follow me", "applied")
    env.store.update_fields(f, {"followup_date": (today + datetime.timedelta(days=5)).isoformat()})
    _job(env, "Fresh DevOps")
    page = c.get("/week").text
    for w in ("My week", "Interviews in the next 7 days", "Assigned by the ORP, to apply", "The best new jobs of the week", "Fresh DevOps"):
        assert w in page, w
    settings = c.get("/settings").text
    key = env.agenda.key()
    assert f"http://testserver/calendar/{key}.ics" in settings and f"webcal://testserver/calendar/{key}.ics" in settings
    r = c.get(f"/calendar/{key}.ics")
    assert r.status_code == 200 and r.headers["content-type"].startswith("text/calendar")
    cal = r.text.replace("\r\n ", "")
    assert cal.startswith("BEGIN:VCALENDAR") and cal.count("BEGIN:VEVENT") == cal.count("END:VEVENT") == 6
    assert "SUMMARY:Interview: Cloud Architect\\; senior\\, AWS — Acme SA" in cal
    assert f"DTSTART:{today + datetime.timedelta(days=2):%Y%m%d}T143000" in cal
    assert "SUMMARY:ORP deadline: apply to Assigned job" in cal and "SUMMARY:Follow up: Follow me" in cal
    assert "Hand in the proofs of job search for" in cal and "SUMMARY:Job search\\, week" in cal
    assert all(len(line.encode()) <= 75 for line in r.text.split("\r\n"))
    assert c.get("/calendar/wrong.ics").status_code == 404 and c.get(f"/calendar/{key}").status_code == 404
    c.post("/settings/calendar")
    assert c.get(f"/calendar/{key}.ics").status_code == 404 and c.get(f"/calendar/{env.agenda.key()}.ics").status_code == 200
    import os
    os.environ["TENANT_SLUG"] = "marie"                                               # behind the platform: a public, https address
    try:
        assert env.agenda.address("http://jobs.example.org") == f"https://jobs.example.org/welcome/cal/marie/{env.agenda.key()}.ics"
    finally:
        del os.environ["TENANT_SLUG"]
    c.post(f"/job/{a}/fields", data={"interview_at": "tomorrow"})
    assert env.store.get_job(a)["interview_at"] == ""


def test_calendar_and_totals_need_their_own_key_even_behind_the_login(env, monkeypatch):
    monkeypatch.setattr(env.auth, "ENABLED", True)                     # every other page wants a Cloudflare Access login
    c = TestClient(env.web.app)
    assert c.get("/jobs").status_code == 403
    assert c.get("/calendar/x.ics").status_code == 404 and c.get(f"/calendar/{env.agenda.key()}.ics").status_code == 200
    assert c.get("/ops/summary").status_code == 404                    # no token configured: the address doesn't exist
    monkeypatch.setenv("OPS_TOKEN", "s3cret-token")
    assert c.get("/ops/summary").status_code == 404
    assert c.get("/ops/summary", headers={"authorization": "Bearer wrong"}).status_code == 404
    _job(env, "Secret Title", company="Secret Company")
    env.store.set_meta(last_scan_at="2026-10-08T06:00:00", last_scan_new=4, last_scan_report=json.dumps(
        {"jobup": {"count": 12, "errors": []}, "ats": {"count": 0, "errors": ["GET https://x.example/search?q=secret words -> HTTP 403"]}}))
    r = c.get("/ops/summary", headers={"authorization": "Bearer s3cret-token"})
    data = r.json()
    assert data["jobs"] == {"new": 1} and data["last_scan_at"] == "2026-10-08T06:00:00"
    assert data["sources"] == {"jobup": {"count": 12, "errors": 0, "kind": ""}, "ats": {"count": 0, "errors": 1, "kind": "HTTP 403"}}
    assert "Secret" not in r.text and "secret words" not in r.text and "example" not in r.text      # totals only


def test_weekly_message_goes_out_once_a_week_when_a_webhook_is_set(env, monkeypatch):
    sent = []

    class R:
        def raise_for_status(self):
            pass
    import httpx
    monkeypatch.setattr(httpx, "post", lambda url, **kw: (sent.append((url, kw["json"]["msg"])), R())[1])
    assert env.weekly.send_if_due() is False and not sent              # no webhook: nothing leaves
    monkeypatch.setenv("SUMMARY_WEBHOOK", "http://bridge.example/alert")
    _job(env, "Fresh DevOps")
    assert env.weekly.send_if_due() is True and env.weekly.send_if_due() is False
    assert len(sent) == 1 and "1 new jobs this week" in sent[0][1] and "Fresh DevOps" in sent[0][1]


def test_search_and_filters_on_top_of_the_list(env, monkeypatch):
    monkeypatch.setattr(env.config, "HOME_TOWN", "Lausanne")
    c = TestClient(env.web.app)
    a = _job(env, "Cloud Architect", company="Acme SA", location="Lausanne, VD", description="Kubernetes à Lausanne.")
    b = _job(env, "DevOps Engineer", company="Globex", location="Morges", description="Terraform et pipelines, équipe à Genève.")
    d = _job(env, "Cloud Architect senior", company="Initech", location="Zürich", description="Azure.")
    e = _job(env, "DevOps Engineer", company="Hooli", location="Remote", description="Anywhere.")
    with env.store.conn() as k:
        k.execute("UPDATE jobs SET created_at='2020-01-01T00:00:00' WHERE id=?", (d,))
        for jid, sc in ((a, 50), (b, 90), (d, 70), (e, 10)):
            k.execute("UPDATE jobs SET score=? WHERE id=?", (sc, jid))

    def titles(query):
        page = c.get("/jobs?status=new&" + query).text
        return [x.split("</strong>")[0] for x in page.split("<strong>")[1:] if "</a>" in x.split("</strong>")[1][:6]], page
    got, page = titles("")
    assert 'class="filterbar"' in page and len(got) == 4 and "Within 20 km of home" in page and " · 0 km" in page
    assert titles("q=terraform")[0] == ["DevOps Engineer"]
    assert titles("q=GENEVE")[0] == ["DevOps Engineer"]                                # accents and case ignored, any field
    assert titles("q=cloud+initech")[0] == ["Cloud Architect senior"]                  # every word must be there
    got, page = titles("q=nothinglikethis")
    assert got == [] and "No job matches this search." in page
    role = next(rid for _, rid, _ in env.listfilter.apply(env.store.list_jobs("new"))[1]["roles"] if "devops" in rid.lower())
    got, page = titles(f"role={role}")
    assert got == ["DevOps Engineer", "DevOps Engineer"] and "2 of 4" in page
    # the person's own title words are choices too: "architect" (their setting) next to the catalogue's roles
    got, page = titles("role=kw:architect")
    assert got == ["Cloud Architect senior", "Cloud Architect"] and ">architect (2)<" in page and ">devops (2)<" in page
    assert len(titles("days=7")[0]) == 3 and "Cloud Architect senior" not in titles("days=7")[0]
    assert titles("km=5")[0] == ["Cloud Architect"]                                    # Morges is about 10 km away, remote has no distance
    assert set(titles("km=20")[0]) == {"Cloud Architect", "DevOps Engineer"}
    assert titles("sort=nearest")[0][:2] == ["Cloud Architect", "DevOps Engineer"]
    assert titles("sort=newest")[0][-1] == "Cloud Architect senior" and titles("")[0][0] == "DevOps Engineer"
    assert len(titles("days=abc&km=7&sort=bogus&role=nope")[0]) == 4                   # nonsense is ignored
    monkeypatch.setattr(env.config, "HOME_TOWN", "")                                   # no home: no distance menu
    assert "Any distance" not in c.get("/jobs").text
    for lang, word in (("fr", "Tous les types de poste"), ("de", "Alle Stellenarten"), ("it", "Tutti i tipi di posto")):
        assert word in c.get("/jobs", headers={"accept-language": lang}).text
