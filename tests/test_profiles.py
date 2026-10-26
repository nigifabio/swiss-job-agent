"""Additional profiles ("roles"): views on the main profile, tags and scores, the union of what every
profile searches, the pages. No network."""
import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from test_features import _job

FULL = {"name": "Sam Test", "headline": "Draughtsperson", "summary": "Draughtsperson with ten years of practice. I like clear plans.",
        "contact": {"email": "sam@example.org", "location": "Pully, Vaud, Suisse"},
        "expertise": ["CAD", "BIM", "Planning", "Invoicing"], "education": ["CFC draughtsperson", "BIM course"],
        "extras_title": "LANGUAGES", "extras": ["French (C2)", "English (B2)"],
        "experience": [{"title": "Draughtsperson", "org": "Studio A", "loc": "Lausanne", "dates": "2020 – 2025",
                        "bullets": ["Drew floor plans in CAD.", "Prepared building permits.", "Trained two apprentices."]},
                       {"title": "Receptionist", "org": "Hotel B", "loc": "Geneva", "dates": "2015 – 2020",
                        "bullets": ["Welcomed guests.", "Handled invoicing and payments."]},
                       {"title": "Sales assistant", "org": "Shop C", "loc": "Vevey", "dates": "2012 – 2015", "bullets": ["Served customers."]}]}


def _setup(env, profile=FULL):
    Path(env.config.PROFILE_PATH).write_text(json.dumps(profile))
    return profile


def _titles(cv):
    return [e["title"] for e in cv["experience"]]


# ---- the view ---------------------------------------------------------------------------------
def test_a_new_profile_shows_everything_and_the_main_profile_is_untouched(env):
    p = _setup(env)
    pid = env.profiles.create("Interior designer", p)
    view = env.profiles.apply_view(p, pid)
    assert view["name"] == p["name"] and view["contact"] == p["contact"]
    assert view["headline"] == "Draughtsperson" and view["summary"] == p["summary"]            # prefilled from the main profile
    assert view["expertise"] == p["expertise"] and _titles(view) == _titles(p) and view["extras"] == p["extras"]
    assert env.profiles.apply_view(p, 0) is p and env.profiles.apply_view(p, 99) is p           # main profile, unknown id: as is
    assert env.profiles.apply_view(None, pid) is None


def test_a_view_chooses_and_orders_but_never_invents(env):
    p = _setup(env)
    pid = env.profiles.create("Reception", p)
    sel = {"expertise": [2, 0], "education": None, "extras": [1],
           "experience": [{"i": 1, "b": [1, 0]}, {"i": 0, "b": [2]}]}
    env.profiles.update(pid, headline="Receptionist", summary="Welcoming and organised.", sel=sel)
    v = env.profiles.apply_view(p, pid)
    assert v["headline"] == "Receptionist" and v["summary"] == "Welcoming and organised."
    assert v["expertise"] == ["Planning", "CAD"] and v["education"] == p["education"] and v["extras"] == ["English (B2)"]
    assert _titles(v) == ["Receptionist", "Draughtsperson"]
    assert v["experience"][0]["bullets"] == ["Handled invoicing and payments.", "Welcomed guests."]
    assert v["experience"][1]["bullets"] == ["Trained two apprentices."]
    assert v["experience"][0]["org"] == "Hotel B" and v["experience"][0]["dates"] == "2015 – 2020"      # the facts are the main profile's
    assert all(b in sum((e["bullets"] for e in p["experience"]), []) for e in v["experience"] for b in e["bullets"])
    assert p["experience"][0]["bullets"][0] == "Drew floor plans in CAD." and len(p["experience"]) == 3     # main profile not modified


def test_indexes_that_no_longer_exist_are_dropped_and_new_items_wait_unless_all(env):
    p = _setup(env)
    pid = env.profiles.create("Reception", p)
    env.profiles.update(pid, sel={"expertise": [0, 7, 3], "education": None, "extras": [],
                                  "experience": [{"i": 5, "b": None}, {"i": 1, "b": [0, 9]}]})
    shorter = dict(p, expertise=["CAD", "BIM"], experience=p["experience"][:2], extras=["French (C2)"])
    v = env.profiles.apply_view(shorter, pid)
    assert v["expertise"] == ["CAD"] and v["extras"] == [] and _titles(v) == ["Receptionist"]
    assert v["experience"][0]["bullets"] == ["Welcomed guests."]
    longer = dict(p, expertise=p["expertise"] + ["Rendering"], education=p["education"] + ["Master"], experience=p["experience"] + [{"title": "New job", "bullets": ["x"]}])
    v = env.profiles.apply_view(longer, pid)
    assert v["expertise"] == ["CAD", "Invoicing"]                    # chosen list: the new item is not shown until chosen
    assert v["education"] == longer["education"]                     # "all": it shows the new line too
    assert _titles(v) == ["Receptionist"]
    env.profiles.update(pid, sel={"expertise": None, "education": None, "extras": None, "experience": None})
    assert env.profiles.apply_view(longer, pid)["expertise"][-1] == "Rendering" and _titles(env.profiles.apply_view(longer, pid))[-1] == "New job"


def test_a_corrupt_selection_is_harmless(env):
    p = _setup(env)
    pid = env.profiles.create("Reception", p)
    env.profiles.update(pid, sel={"expertise": "oops", "education": [True, -1, "a", 1], "extras": None, "experience": [{"i": "x"}, 3, {"i": 0, "b": "no"}]})
    v = env.profiles.apply_view(p, pid)
    assert v["expertise"] == [] and v["education"] == ["BIM course"] and _titles(v) == ["Draughtsperson"]
    env.store.set_meta(profiles="not json")
    env.profiles.invalidate()
    assert env.profiles.extras() == [] and env.profiles.ids() == [0]


def test_translated_profiles_take_the_same_choice(env):
    p = _setup(env)
    fr = {"name": "IGNORED", "contact": {"email": "x@example.org"}, "headline": "Dessinatrice", "summary": "Dessinatrice avec dix ans de pratique. Elle aime les plans clairs.",
          "expertise": ["DAO", "BIM", "Planification", "Facturation"], "education": ["CFC dessinatrice", "Cours BIM"],
          "extras_title": "LANGUES", "extras": ["Français (C2)", "Anglais (B2)"],
          "experience": [{"title": "Dessinatrice", "org": "Studio A", "loc": "Lausanne", "dates": "2020 – 2025",
                          "bullets": ["Plans d'étage en DAO.", "Dossiers de permis.", "Formation de deux apprentis."]},
                         {"title": "Réceptionniste", "org": "Hôtel B", "loc": "Genève", "dates": "2015 – 2020", "bullets": ["Accueil des clients.", "Facturation et paiements."]},
                         {"title": "Vendeuse", "org": "Magasin C", "loc": "Vevey", "dates": "2012 – 2015", "bullets": ["Service aux clients."]}]}
    Path(env.tailor.translated_path("fr")).write_text(json.dumps(fr))
    pid = env.profiles.create("Reception", p)
    env.profiles.update(pid, headline="Réceptionniste", summary="Accueillante et organisée.",
                        sel={"expertise": [3], "experience": [{"i": 1, "b": [1]}]})
    job = {"title": "Réceptionniste H/F", "company": "Hôtel X", "location": "Lausanne", "description": "Accueil des clients. Poste à Lausanne, " * 4, "profile": pid}
    cv, lang = env.tailor.localized(p, job)
    assert lang == "fr" and cv["expertise"] == ["Facturation"] and _titles(cv) == ["Réceptionniste"]
    assert cv["experience"][0]["bullets"] == ["Facturation et paiements."]
    assert cv["headline"] == "Réceptionniste" and cv["summary"] == "Accueillante et organisée."      # the profile's own text, as written
    assert cv["name"] == "Sam Test" and cv["contact"] == p["contact"]
    cv, lang = env.tailor.localized(p, dict(job, profile=0))
    assert len(cv["experience"]) == 3 and cv["headline"] == "Dessinatrice"                          # the main profile's French version


# ---- limits and names ---------------------------------------------------------------------------
def test_at_most_four_profiles_in_all_and_names_are_unique(env):
    p = _setup(env)
    ids = [env.profiles.create(n, p) for n in ("A", "B", "C")]
    assert ids == [1, 2, 3] and env.profiles.ids() == [0, 1, 2, 3] and not env.profiles.can_add()
    with pytest.raises(env.profiles.ProfileError) as e:
        env.profiles.create("D", p)
    assert e.value.code == "limit"
    env.profiles.delete(2)
    assert env.profiles.can_add()
    with pytest.raises(env.profiles.ProfileError) as e:
        env.profiles.create("a", p)
    assert e.value.code == "exists"
    with pytest.raises(env.profiles.ProfileError) as e:
        env.profiles.create("   ", p)
    assert e.value.code == "name"
    assert env.profiles.create("D", p) == 4                      # ids are never reused


def test_creating_a_profile_copies_the_main_skills(env):
    p = _setup(env)
    env.prefs.apply("have", "autocad")
    env.prefs.apply("avoid", "german")
    pid = env.profiles.create("Designer", p)
    got = env.profiles.get(pid)
    assert got["skills"] == env.prefs.skills() and "autocad" in got["skills"] and got["avoid"] == ["german"]
    env.prefs.apply("have", "revit")
    assert "revit" not in env.profiles.get(pid)["skills"]        # a copy: later clicks on the main profile don't change it
    assert env.profiles.skills_of(pid) == got["skills"] and env.profiles.skills_of(0) == env.prefs.skills()


# ---- what every profile searches ------------------------------------------------------------------
def test_title_ok_and_search_terms_are_the_union_of_the_profiles(env, monkeypatch):
    p = _setup(env)
    monkeypatch.setattr(env.config, "SEARCH_TERMS", ["cloud architect"])
    f = env.filters
    assert not f.title_ok("Interior Designer") and f.title_ok("Cloud Architect")
    assert env.profiles.search_terms() == ["cloud architect"] and env.profiles.extra_title_words() == []
    pid = env.profiles.create("Designer", p)
    assert not f.title_ok("Interior Designer")                           # a profile without title words adds nothing
    env.profiles.update(pid, titles=["designer", "Dessinat*"], terms=["interior designer", "Cloud Architect", "cad drafter"])
    assert f.title_ok("Interior Designer") and f.title_ok("Dessinatrice DAO") and f.title_ok("Cloud Architect")
    assert not f.title_ok("Receptionist")
    assert env.profiles.search_terms() == ["cloud architect", "interior designer", "cad drafter"]    # no repeat, case apart
    monkeypatch.setattr(env.config, "TITLE_EXCLUDE", ["junior"])
    assert not f.title_ok("Junior Interior Designer")                    # the exclusions stay global
    env.profiles.delete(pid)
    assert not f.title_ok("Interior Designer") and env.profiles.search_terms() == ["cloud architect"]


def test_the_providers_search_every_profiles_terms(env, net, monkeypatch):
    p = _setup(env)
    from conftest import jresp
    monkeypatch.setattr(env.config, "SEARCH_TERMS", ["cloud architect"])
    pid = env.profiles.create("Designer", p)
    env.profiles.update(pid, terms=["interior designer"], titles=["designer"])
    asked = []

    def search(request):
        asked.append(json.loads(request.content)["keywords"])
        return jresp([])
    net["https://www.job-room.ch/jobadservice/api/jobAdvertisements/_search"] = search
    monkeypatch.setattr(env.config, "PROVIDERS", ["jobroom"])
    env.fetch._run()
    assert {tuple(k) for k in asked} == {("cloud architect",), ("interior designer",)}
    env.profiles.delete(pid)
    asked.clear()
    env.fetch._run()
    assert {tuple(k) for k in asked} == {("cloud architect",)}


def test_the_shared_collector_is_asked_for_the_union_and_restarts_when_a_profile_changes(env, monkeypatch):
    p = _setup(env)
    monkeypatch.setattr(env.config, "SEARCH_TERMS", ["cloud architect"])
    pool = env.providers.pool
    sent = []
    monkeypatch.setattr(pool, "URL", "http://pool")
    monkeypatch.setattr(pool, "TOKEN", "t")
    monkeypatch.setattr(pool, "_post", lambda payload: (sent.append(payload), {"ready": True, "jobs": [], "covers": [], "now": "2026-01-01T00:00:00"})[1])

    def pull():
        mark = pool.pull()[2]
        env.store.set_meta(**mark)              # what a scan keeps once the postings are stored
        return sent[-1]
    first = pull()
    assert first["spec"]["terms"] == ["cloud architect"] and first["since"] == ""
    assert pull()["since"] == "2026-01-01T00:00:00"                      # nothing changed: only what is new
    pid = env.profiles.create("Designer", p)
    assert pull()["since"] == "2026-01-01T00:00:00"                      # a profile with no words of its own changes nothing
    env.profiles.update(pid, terms=["interior designer"])
    got = pull()
    assert got["spec"]["terms"] == ["cloud architect", "interior designer"] and got["since"] == ""      # new terms: the whole pool again
    assert pull()["since"] == "2026-01-01T00:00:00"
    env.profiles.update(pid, titles=["designer"])
    assert pull()["since"] == ""                                         # new title words too (they filter what comes back)
    env.profiles.update(pid, skills=["cad"], avoid=["x"], headline="new")
    assert pull()["since"] == "2026-01-01T00:00:00"                      # what a profile shows or scores is local: no new pull


def test_the_pool_postings_are_kept_by_any_profiles_title_words(env, monkeypatch):
    p = _setup(env)
    pool = env.providers.pool
    pid = env.profiles.create("Designer", p)
    jobs = [{"content_hash": "a", "title": "Interior Designer", "location": "Lausanne", "description": "We look for a designer to plan the rooms of our homes in Lausanne. " * 3},
            {"content_hash": "b", "title": "Cloud Architect", "location": "Lausanne", "description": "We look for an architect to build the cloud of our company in Lausanne. " * 3}]
    monkeypatch.setattr(pool, "URL", "http://pool")
    monkeypatch.setattr(pool, "TOKEN", "t")
    monkeypatch.setattr(pool, "_post", lambda payload: {"ready": True, "jobs": jobs, "covers": ["jobroom"], "now": "x"})
    monkeypatch.setattr(env.config, "LANGUAGES", ["en"])
    assert [j["content_hash"] for j in pool.pull()[0]] == ["b"]
    env.profiles.update(pid, titles=["designer"])
    assert [j["content_hash"] for j in pool.pull()[0]] == ["a", "b"]


# ---- tags and scores --------------------------------------------------------------------------------
def _two_profiles(env, monkeypatch):
    p = _setup(env)
    monkeypatch.setattr(env.config, "SEARCH_TERMS", ["cloud architect"])
    pid = env.profiles.create("Designer", p)
    env.profiles.update(pid, titles=["designer", "architect"], terms=["interior designer"], skills=["cad", "plans", "bim"], avoid=["night shift"])
    return p, pid


def test_a_job_is_tagged_with_every_matching_profile_and_the_best_score_is_its_main_tag(env, monkeypatch):
    p, pid = _two_profiles(env, monkeypatch)
    tag = env.fetch.tag_job
    cad = {"title": "Interior Designer", "description": "CAD, plans and BIM for homes."}
    t = tag(cad)
    assert t["profile"] == pid and t["profiles"] == str(pid) and t["score"] > 0 and t["locked"] == 0       # the main profile's title words don't match
    both = {"title": "Cloud Architect", "description": "AWS and Terraform on Azure with an API. CAD plans."}
    t = tag(both)
    assert t["profile"] == 0 and t["profiles"] == f"0,{pid}"                    # main scores higher: main tag first
    assert t["score"] == env.fetch.score_job(both)[0] and "matches: aws" in t["why"]
    both2 = {"title": "Cloud Architect", "description": "CAD plans for BIM models."}
    t = tag(both2)
    assert t["profile"] == pid and t["profiles"] == f"{pid},0"                  # the profile of the role scores higher: it leads
    assert t["score"] == env.fetch.score_job(both2, ["cad", "plans", "bim"], ["night shift"])[0]
    none = tag({"title": "Receptionist", "description": "CAD"})
    assert none["profile"] == 0 and none["profiles"] == "0"                     # nothing matches: the main profile
    tie = tag({"title": "Cloud Architect", "description": "nothing here"})
    assert tie["profile"] == 0                                                  # a tie goes to the oldest profile


def test_each_profile_scores_with_its_own_skills_and_avoided_words(env, monkeypatch):
    p, pid = _two_profiles(env, monkeypatch)
    job = {"title": "Interior Designer", "description": "CAD plans. Night shift work."}
    sc, why = env.fetch.score_job(job, env.profiles.skills_of(pid), env.profiles.avoid_of(pid))
    base, _ = env.fetch.score_job(job, env.profiles.skills_of(pid), [])
    assert sc == base - env.fetch.AVOID_PENALTY and "avoid: night shift" in why and "matches: cad, plans" in why
    assert env.fetch.score_job(job) == env.fetch.score_job(job, env.prefs.skills(), env.prefs.avoided())     # main: as before
    assert env.filters.matched(dict(job, profile=pid)) == ["cad", "plans"] and env.filters.matched(job) == []
    assert env.filters.avoided_hits(dict(job, profile=pid)) == ["night shift"] and env.filters.avoided_hits(job) == []


def test_scans_tag_what_they_store(env, monkeypatch):
    p, pid = _two_profiles(env, monkeypatch)
    monkeypatch.setattr(env.config, "PROVIDERS", ["jobup"])
    row = lambda h, t, d: {"source": "x", "title": t, "company": "Acme", "location": "Lausanne", "description": d, "url": "u" + h, "salary": "", "posted_at": "", "content_hash": h}  # noqa: E731
    monkeypatch.setattr(env.fetch, "MODULES", {"jobup": type("M", (), {"fetch": staticmethod(lambda: [
        row("1", "Interior Designer", "CAD plans BIM"), row("2", "Cloud Architect", "AWS Terraform Azure api")])})})
    assert env.fetch._run() == 2
    jobs = {j["title"]: j for j in env.store.list_jobs("new")}
    assert jobs["Interior Designer"]["profile"] == pid and jobs["Cloud Architect"]["profile"] == 0
    assert jobs["Cloud Architect"]["profiles"] == f"0,{pid}" and jobs["Cloud Architect"]["score"] == env.fetch.score_job(jobs["Cloud Architect"])[0]


def test_jobs_are_tagged_again_when_profiles_change_and_when_one_is_deleted(env, monkeypatch):
    p, pid = _two_profiles(env, monkeypatch)
    a = _job(env, "Interior Designer", description="CAD plans BIM")
    b = _job(env, "Cloud Architect", description="CAD plans BIM and AWS")
    old = _job(env, "Cloud Architect two", "discarded", description="CAD plans")
    c = TestClient(env.web.app)
    env.fetch.rescore_all()
    assert env.store.get_job(a)["profile"] == pid and env.store.get_job(b)["profile"] == pid and env.store.get_job(old)["profile"] == 0
    # the person edits the skills of the profile: scores and tags follow at once
    c.post(f"/cv/profiles/{pid}", data={"name": "Designer", "headline": "x", "summary": "y", "titles": "designer\narchitect", "terms": "interior designer", "skills": "aws\nazure", "avoid": ""})
    assert env.store.get_job(a)["profile"] == 0 or env.store.get_job(a)["score"] == 0       # CAD no longer scores for the profile
    assert env.store.get_job(b)["profile"] == 0
    # delete the profile: its jobs go back to the main profile
    env.store.set_tag(a, 50, "x", pid, f"{pid},0", 0)
    r = c.post(f"/cv/profiles/{pid}/delete", follow_redirects=False)
    assert r.status_code == 303 and env.profiles.ids() == [0]
    for jid in (a, b):
        j = env.store.get_job(jid)
        assert j["status"] in ("new", "discarded") and (j["profile"] or 0) == 0 and "," not in (j["profiles"] or "")
    assert env.profiles.tags({"profile": pid, "profiles": f"{pid},0"}) == [0]               # a closed job with a stale tag shows the main one


def test_the_main_tag_can_be_chosen_by_hand_and_kept(env, monkeypatch):
    p, pid = _two_profiles(env, monkeypatch)
    jid = _job(env, "Cloud Architect", description="CAD plans BIM")
    c = TestClient(env.web.app)
    env.fetch.rescore_all()
    j = env.store.get_job(jid)
    assert j["profile"] == pid
    page = c.get(f"/job/{jid}").text
    assert 'action="/job/%d/profile"' % jid in page and "Change the main tag" in page and "Back to automatic" not in page
    r = c.post(f"/job/{jid}/profile", data={"profile": "0"}, follow_redirects=False)
    assert r.status_code == 303
    j = env.store.get_job(jid)
    assert j["profile"] == 0 and j["profile_locked"] == 1 and j["profiles"].split(",")[0] == "0" and str(pid) in j["profiles"]
    assert j["score"] == env.fetch.score_job(j)[0]                                          # the score is the chosen profile's
    env.fetch.rescore_all()                                                                 # a change elsewhere keeps the choice
    assert env.store.get_job(jid)["profile"] == 0
    assert "Back to automatic" in c.get(f"/job/{jid}").text
    c.post(f"/job/{jid}/profile", data={"auto": "1", "profile": "0"})
    j = env.store.get_job(jid)
    assert j["profile"] == pid and j["profile_locked"] == 0
    c.post(f"/job/{jid}/profile", data={"profile": "9"})                                    # an unknown profile is ignored
    assert env.store.get_job(jid)["profile"] == pid
    c.post(f"/job/{jid}/profile", data={"profile": str(pid)})
    env.profiles.delete(pid)
    env.fetch.rescore_all()
    j = env.store.get_job(jid)
    assert j["profile"] == 0 and j["profile_locked"] == 0                                   # the chosen profile is gone


def test_existing_databases_get_the_new_columns(env):
    jid = _job(env, "Old job")
    with env.store.conn() as c:                        # a database from before profiles
        for col in ("profile", "profiles", "profile_locked"):
            c.execute(f"ALTER TABLE jobs DROP COLUMN {col}")
    env.store.init_db()
    j = env.store.list_jobs("new")[0]
    assert j["profile"] == 0 and j["profiles"] is None and j["profile_locked"] == 0
    assert env.profiles.tags(j) == [0]


# ---- tune.apply ---------------------------------------------------------------------------------------
def test_tune_apply_follows_the_profiles(env, monkeypatch):
    p = _setup(env)
    monkeypatch.setattr(env.config, "LOCATION_KEYWORDS", ["lausanne"])
    arch = _job(env, "Cloud Architect")
    design = _job(env, "Interior Designer")
    both = _job(env, "Designer Architect")
    shortlisted = _job(env, "Another Designer", "shortlisted")
    hand = env.store.add_manual({"title": "Receptionist", "company": "X", "location": "Lausanne"})
    env.store.update_status(hand, "new")
    # adding a profile (and its title words) never removes a job
    pid = env.profiles.create("Designer", p)
    env.profiles.update(pid, titles=["designer"])
    assert env.tune.apply() == 0 and env.store.get_job(design)["status"] == "new"
    # removing it removes only the new jobs no profile still wants
    env.profiles.delete(pid)
    assert env.tune.apply() == 1
    assert env.store.get_job(design)["status"] == "discarded" and env.store.get_job(design)["discard_reason"] == "filtered"
    assert env.store.get_job(arch)["status"] == "new" and env.store.get_job(both)["status"] == "new"      # the main profile still wants them
    assert env.store.get_job(shortlisted)["status"] == "shortlisted"                                     # only "new" jobs are looked at
    assert env.store.get_job(hand)["status"] == "new"                                                    # typed in by hand: never touched


def test_saving_a_profile_removes_what_it_alone_wanted_and_starts_a_scan_for_new_words(env, monkeypatch):
    p = _setup(env)
    runs = []
    monkeypatch.setattr(env.web, "_start_background", lambda fn: (runs.append(1), env.store.set_meta(scan_started_at=env.store.now())))
    monkeypatch.setattr(env.config, "LOCATION_KEYWORDS", ["lausanne"])
    c = TestClient(env.web.app)
    pid = env.profiles.create("Designer", p)
    form = {"name": "Designer", "headline": "h", "summary": "s", "terms": "", "titles": "designer", "skills": "cad", "avoid": ""}
    r = c.post(f"/cv/profiles/{pid}", data=form, follow_redirects=False)
    assert "saved=1" in r.headers["location"] and "scan=1" in r.headers["location"] and len(runs) == 1      # new title words: look for jobs now
    d = _job(env, "Interior Designer")
    env.fetch.rescore_all()
    r = c.post(f"/cv/profiles/{pid}", data=dict(form, titles=""), follow_redirects=False)
    assert "removed=1" in r.headers["location"] and env.store.get_job(d)["status"] == "discarded"
    r = c.post(f"/cv/profiles/{pid}", data=dict(form, titles="designer", terms="interior"), follow_redirects=False)
    assert "scan=0" in r.headers["location"] and len(runs) == 1                                         # saves in a row: one scan
    assert "Saved." in c.get(r.headers["location"]).text


# ---- the CV and the letter follow the tag --------------------------------------------------------------------
def test_cv_and_letter_are_written_with_the_profile_of_the_main_tag(env, monkeypatch):
    p = _setup(env)
    monkeypatch.setattr(env.config, "SEARCH_TERMS", [])
    pid = env.profiles.create("Reception", p)
    env.profiles.update(pid, titles=["receptionist"], headline="Receptionist", summary="Welcoming, calm and exact, with years of guests and desks behind me.",
                        skills=["welcome"], sel={"expertise": [3, 2], "education": [], "extras": None,
                                                 "experience": [{"i": 1, "b": [1, 0]}]})
    jid = _job(env, "Receptionist", description="Welcome guests, invoicing and payments at our hotel.")
    env.fetch.rescore_all()
    job = env.store.get_job(jid)
    assert job["profile"] == pid
    text = env.tailor.draft_text(job, p)
    assert "Welcoming, calm and exact, with years of guests and desks behind me." in text and "Draughtsperson with ten years" not in text
    assert text.index("- Invoicing") < text.index("- Planning") and "- CAD" not in text            # the profile's skills, in its order
    assert "### Receptionist — Hotel B, Geneva" in text and "Draughtsperson — Studio A" not in text
    assert text.index("- Handled invoicing and payments.") < text.index("- Welcomed guests.")      # its order, not the posting's relevance
    assert "CFC draughtsperson" not in text and "French (C2)" in text
    assert env.tailor.build(job, p).endswith(f"{jid}.pdf") and Path(env.tailor.cv_path(jid)).read_bytes()[:4] == b"%PDF"
    letter, _ = env.letter.write(p, job)
    assert "Welcoming, calm and exact, with years of guests and desks behind me." in letter and "Hotel B" in letter and "Studio A" not in letter and "Planned" not in letter
    # the same job tagged with the main profile gives the full CV
    env.store.set_tag(jid, 10, "x", 0, "0", 1)
    full = env.tailor.draft_text(env.store.get_job(jid), p)
    assert "Draughtsperson — Studio A" in full and "Welcoming, calm" not in full
    # through the pages
    c = TestClient(env.web.app)
    env.store.set_tag(jid, 10, "x", pid, f"{pid},0", 0)
    c.post(f"/job/{jid}/cv")
    assert "Welcoming, calm and exact, with years of guests and desks behind me." in env.store.get_job(jid)["cv_text"]
    c.post(f"/job/{jid}/letter")
    assert "Hotel B" in env.store.get_job(jid)["letter"]
    page = c.get(f"/job/{jid}").text
    assert "Written with the profile “Reception”." in page


# ---- the pages ----------------------------------------------------------------------------------------
def test_the_profiles_pages_create_edit_rename_and_delete(env):
    p = _setup(env)
    c = TestClient(env.web.app)
    page = c.get("/cv/profiles").text
    assert "My profiles" in page and "Main profile" in page and "New profile" in page
    assert "My profiles" in c.get("/cv").text and "My profiles" in c.get("/cv/versions").text
    r = c.post("/cv/profiles", data={"name": "Interior designer"}, follow_redirects=False)
    assert r.headers["location"] == "/cv/profiles/1?new=1"
    edit = c.get("/cv/profiles/1?new=1").text
    assert "Profile created" in edit and 'name="headline" value="Draughtsperson"' in edit and edit.count('name="expertise"') == 4
    assert edit.count('name="experience"') == 3 and edit.count('name="b0"') == 3 and "Planning" in edit
    r = c.post("/cv/profiles", data={"name": "interior DESIGNER"}, follow_redirects=False)
    assert r.headers["location"] == "/cv/profiles?err=exists" and "exists already" in c.get(r.headers["location"]).text
    assert "Give the profile a name" in c.get(c.post("/cv/profiles", data={"name": " "}, follow_redirects=False).headers["location"]).text
    c.post("/cv/profiles/1/rename", data={"name": "Designer"})
    assert env.profiles.get(1)["name"] == "Designer"
    c.post("/cv/profiles/1/rename", data={"name": ""})
    assert env.profiles.get(1)["name"] == "Designer"
    c.post("/cv/profiles", data={"name": "Reception"})
    c.post("/cv/profiles", data={"name": "Sales"})
    r = c.post("/cv/profiles", data={"name": "One too many"}, follow_redirects=False)
    assert r.headers["location"] == "/cv/profiles?err=limit"
    page = c.get(r.headers["location"]).text
    assert "4 profiles in all" in page and "New profile" not in page and "the most there can be" in page
    assert c.get("/cv/profiles/9", follow_redirects=False).status_code == 303 and c.get("/cv/profiles/0", follow_redirects=False).status_code == 303
    assert c.get("/cv/profiles/1.pdf").content[:4] == b"%PDF" and c.get("/cv/profiles/9.pdf").status_code == 404
    c.post("/cv/profiles/2/delete")
    assert env.profiles.ids() == [0, 1, 3] and "New profile" in c.get("/cv/profiles").text
    assert c.post("/cv/profiles/2/delete", follow_redirects=False).status_code == 303


def test_the_edit_page_saves_choices_in_the_order_of_the_page_and_arrows_move_one_item(env):
    p = _setup(env)
    c = TestClient(env.web.app)
    c.post("/cv/profiles", data={"name": "Designer"})
    base = {"name": "Designer", "headline": "Interior designer", "summary": "Plans for homes.", "terms": "interior designer\ncad drafter", "titles": "designer; dessinat*",
            "skills": "cad\nBIM", "avoid": "night shift"}
    # tick two skills, in the order the page lists them (Planning before CAD), leave the rest
    r = c.post("/cv/profiles/1", data=dict(base, expertise=["2", "0"], experience=["1", "0"], b1=["1"], b0=["2", "0", "1"], education=["0", "1"], extras=["0"]), follow_redirects=False)
    assert r.headers["location"].startswith("/cv/profiles/1?saved=1")
    got = env.profiles.get(1)
    assert got["headline"] == "Interior designer" and got["summary"] == "Plans for homes." and got["terms"] == ["interior designer", "cad drafter"]
    assert got["titles"] == ["designer", "dessinat*"] and got["skills"] == ["cad", "bim"] and got["avoid"] == ["night shift"]
    assert got["sel"] == {"expertise": [2, 0], "education": None, "extras": [0],
                          "experience": [{"i": 1, "b": [1]}, {"i": 0, "b": [2, 0, 1]}]}
    assert env.profiles.apply_view(p, 1)["expertise"] == ["Planning", "CAD"]
    page = c.get("/cv/profiles/1").text
    assert page.index('value="2" id="expertise2"') < page.index('value="0" id="expertise0"') < page.index('value="1" id="expertise1"')      # chosen first, in order
    assert page.index('id="experience1"') < page.index('id="experience0"') < page.index('id="experience2"')
    assert 'id="experience2" ' in page and 'id="experience2" checked' not in page
    # an arrow saves the form too and moves one shown item
    c.post("/cv/profiles/1", data=dict(base, expertise=["2", "0"], experience=["1", "0"], b1=["1"], b0=["2", "0", "1"], education=["0", "1"], extras=["0"], move="expertise:0:up"))
    assert env.profiles.get(1)["sel"]["expertise"] == [0, 2]
    c.post("/cv/profiles/1", data=dict(base, expertise=["0", "2"], experience=["1", "0"], b1=["1"], b0=["2", "0", "1"], education=["0", "1"], extras=["0"], move="expertise:2:down"))
    assert env.profiles.get(1)["sel"]["expertise"] == [0, 2]                           # the last one can't go further down
    c.post("/cv/profiles/1", data=dict(base, expertise=["0", "2"], experience=["1", "0"], b1=["1"], b0=["2", "0", "1"], education=["0", "1"], extras=["0"], move="experience:1:down"))
    assert [e["i"] for e in env.profiles.get(1)["sel"]["experience"]] == [0, 1]
    c.post("/cv/profiles/1", data=dict(base, expertise=["0", "2"], experience=["0", "1"], b1=["1"], b0=["2", "0", "1"], education=["0", "1"], extras=["0"], move="b:0:0:up"))
    assert env.profiles.get(1)["sel"]["experience"][0]["b"] == [0, 2, 1]
    c.post("/cv/profiles/1", data=dict(base, expertise=["0", "2"], experience=["0", "1"], b1=["1"], b0=["2", "0", "1"], education=["0", "1"], extras=["0"], move="b:0:0:down"))
    assert env.profiles.get(1)["sel"]["experience"][0]["b"] == [2, 1, 0]
    # everything ticked, in the main profile's order, is stored as "all": new items of the main profile will show
    c.post("/cv/profiles/1", data=dict(base, expertise=["0", "1", "2", "3"], experience=["0", "1", "2"], b0=["0", "1", "2"], b1=["0", "1"], b2=["0"], education=["0", "1"], extras=["0", "1"]))
    assert env.profiles.get(1)["sel"] == {"expertise": None, "education": None, "extras": None, "experience": None}
    # nothing ticked is a real choice too: the profile shows no skills
    c.post("/cv/profiles/1", data=dict(base))
    assert env.profiles.get(1)["sel"]["expertise"] == [] and env.profiles.get(1)["sel"]["experience"] == []
    assert env.profiles.apply_view(p, 1)["experience"] == []


def test_profile_chips_filter_the_list_by_any_tag(env, monkeypatch):
    p = _setup(env)
    monkeypatch.setattr(env.config, "SEARCH_TERMS", [])
    c = TestClient(env.web.app)
    solo = _job(env, "Cloud Architect", description="AWS")
    page = c.get("/jobs?status=new").text
    assert 'class="pchip ' not in page and 'class="ptag' not in page                      # only the main profile: nothing shown
    pid = env.profiles.create("Designer", p)
    env.profiles.update(pid, titles=["designer", "architect"], skills=["cad", "plans"])
    only = _job(env, "Interior Designer", description="CAD plans")
    other = _job(env, "Receptionist", description="Welcome")
    both = _job(env, "Architect Designer", description="CAD plans and AWS")
    env.fetch.rescore_all()
    page = c.get("/jobs?status=new").text
    assert page.count('class="pchip ') == 3 and "All</a>" in page and "Main profile (" in page and "Designer (" in page
    assert page.count('class="ptag main"') == 4 and 'class="ptag"' in page            # every card: its main tag, and its other tags
    ids = lambda t: sorted(int(i) for i in __import__("re").findall(r'id="job-(\d+)"', t))  # noqa: E731
    assert ids(page) == sorted([solo, only, other, both])
    page = c.get(f"/jobs?status=new&profile={pid}").text
    assert ids(page) == sorted([solo, only, both])                                     # any tag: "Architect Designer" and "Cloud Architect" match both
    assert 'pchip active" href="/jobs?status=new&amp;profile=%d"' % pid in page
    assert 'name="profile" value="%d"' % pid in page and "3 of 4" in page
    page = c.get("/jobs?status=new&profile=0").text
    assert ids(page) == sorted([solo, other, both] if env.store.get_job(both)["profile"] == 0 else [solo, other, both])
    page = c.get(f"/jobs?status=new&profile={pid}&q=cad&sort=newest").text              # together with the other filters
    assert ids(page) == sorted([only, both]) and "profile=%d" % pid in page
    assert "q=cad" in page and "sort=newest" in page                                   # the chips keep the other filters
    assert ids(c.get("/jobs?status=new&profile=7").text) == sorted([solo, only, other, both])   # an unknown profile: ignored
    assert ids(c.get("/jobs?status=new&profile=abc").text) == sorted([solo, only, other, both])
    assert 'class="pchip ' not in c.get("/jobs?status=new&view=best").text
    assert ids(c.get("/jobs?status=new").text) == sorted([solo, only, other, both])
    detail = c.get(f"/job/{only}").text
    assert 'class="ptag main"' in detail and "Designer" in detail and "score" in detail.lower()


def test_improve_shows_what_each_profile_is_missing(env, monkeypatch):
    p = _setup(env)
    monkeypatch.setattr(env.config, "SEARCH_TERMS", [])
    c = TestClient(env.web.app)
    pid = env.profiles.create("Cloud", p)
    env.profiles.update(pid, titles=["engineer"], skills=["docker", "kubernetes"])
    for i in range(3):
        _job(env, f"DevOps Architect {i}", description="Terraform and Kubernetes and Docker and Ansible.")
        _job(env, f"Platform Engineer {i}", description="Terraform and Kubernetes and Docker and Ansible and Python.")
    env.fetch.rescore_all()
    page = c.get("/improve").text
    assert "All profiles (your main profile's skills)" in page
    main = env.improve.analyse(profile=0)
    cloud = env.improve.analyse(profile=pid)
    assert main["total"] == 3 and cloud["total"] == 3 and env.improve.analyse()["total"] == 6
    miss = lambda a: {m["skill"] for m in a["missing"]}  # noqa: E731
    assert "kubernetes" in miss(main) and "kubernetes" not in miss(cloud) and "docker" not in miss(cloud) and "ansible" in miss(cloud)
    assert {s["skill"] for s in cloud["strengths"]} >= {"kubernetes", "docker"}
    page = c.get(f"/improve?profile={pid}").text
    assert "ansible" in page and 'name="profile" value="%d"' % pid in page and "profile=%d" % pid in page
    # "I have it" on a profile's page changes that profile's skills, not the main one's
    c.post("/skills", data={"action": "have", "term": "python", "next": f"/improve?profile={pid}", "profile": str(pid)})
    assert "python" in env.profiles.get(pid)["skills"] and "python" not in env.prefs.skills()
    assert "python" not in miss(env.improve.analyse(profile=pid))
    c.post("/skills", data={"action": "have", "term": "ansible", "next": "/improve"})
    assert "ansible" in env.prefs.skills() and "ansible" not in env.profiles.get(pid)["skills"]
    assert c.get("/improve?profile=99").status_code == 200


def test_a_person_with_only_the_main_profile_sees_no_profile_marks(env):
    _setup(env)
    c = TestClient(env.web.app)
    jid = _job(env, "Cloud Architect", description="AWS Terraform")
    env.fetch.rescore_all()
    for url in ("/jobs?status=new", f"/job/{jid}", "/improve", "/cv"):
        page = c.get(url).text
        assert "ptag" not in page.replace(".ptag", "") and 'class="pchip ' not in page and "Change the main tag" not in page and "Written with the profile" not in page
    assert env.store.get_job(jid)["profile"] == 0


def test_settings_save_and_skill_clicks_tag_again(env):
    p = _setup(env)
    c = TestClient(env.web.app)
    pid = env.profiles.create("Designer", p)
    env.profiles.update(pid, titles=["designer"], skills=["cad"])
    jid = _job(env, "Interior Designer", description="CAD plans and AWS")
    env.fetch.rescore_all()
    assert env.store.get_job(jid)["profile"] == pid
    c.post("/skills", data={"action": "have", "term": "plans", "next": "/cv", "profile": str(pid)})
    assert env.profiles.get(pid)["skills"] == ["cad", "plans"] and env.store.get_job(jid)["score"] == env.fetch.score_job(env.store.get_job(jid), ["cad", "plans"], [])[0]
    c.post("/skills", data={"action": "avoid", "term": "aws", "next": "/cv", "profile": str(pid)})
    assert env.profiles.get(pid)["avoid"] == ["aws"] and "avoid: aws" in env.store.get_job(jid)["score_rationale"]
    c.post("/skills", data={"action": "remove", "term": "plans", "next": "/cv", "profile": str(pid)})
    assert env.profiles.get(pid)["skills"] == ["cad"]
    c.post("/skills", data={"action": "unavoid", "term": "aws", "next": "/cv", "profile": str(pid)})
    assert env.profiles.get(pid)["avoid"] == []
    assert not env.profiles.skill_action(pid, "bogus", "x") and not env.profiles.skill_action(99, "have", "x")


def test_a_manual_posting_is_tagged_when_it_is_saved(env, monkeypatch):
    p = _setup(env)
    monkeypatch.setattr(env.config, "SEARCH_TERMS", [])
    c = TestClient(env.web.app)
    pid = env.profiles.create("Designer", p)
    env.profiles.update(pid, titles=["designer"], skills=["cad"])
    r = c.post("/add/posting/save", data={"title": "Interior Designer", "company": "Studio", "location": "Lausanne", "description": "CAD plans", "status": "shortlisted"},
               follow_redirects=False)
    jid = int(r.headers["location"].split("/")[2])
    j = env.store.get_job(jid)
    assert j["profile"] == pid and j["origin"] == "manual" and j["score"] == env.fetch.score_job(j, ["cad"], [])[0]
    r = c.post("/add/posting/save", data={"title": "Gardener", "company": "Green", "location": "Lausanne", "description": "", "status": "shortlisted"}, follow_redirects=False)
    assert env.store.get_job(int(r.headers["location"].split("/")[2]))["profile"] == 0       # nothing matches: the main profile


def test_pages_render_in_every_language_with_profiles(env):
    p = _setup(env)
    pid = env.profiles.create("Designer", p)
    env.profiles.update(pid, titles=["designer"])
    jid = _job(env, "Interior Designer", description="CAD")
    env.fetch.rescore_all()
    for lang, word in (("fr", "Mes profils"), ("de", "Meine Profile"), ("it", "I miei profili")):
        c = TestClient(env.web.app, headers={"accept-language": lang})
        for url in ("/cv/profiles", f"/cv/profiles/{pid}", "/jobs?status=new", f"/job/{jid}", "/improve", "/cv/profiles?err=limit", f"/cv/profiles/{pid}?saved=1&removed=2&scan=1"):
            assert c.get(url).status_code == 200
        assert word in c.get("/cv/profiles").text
        assert "Main profile" not in c.get("/jobs?status=new").text
