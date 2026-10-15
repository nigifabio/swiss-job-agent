"""Add a job posting: reading a link or pasted text, the guard on fetched addresses, the review and save
flow, what the search is missing for a posting and the one-click fixes. No network."""
import json

import httpx
import pytest
from fastapi.testclient import TestClient

LD = {"@context": "https://schema.org", "@type": "JobPosting", "title": "Cloud Architect (m/w/d) 80-100%",
      "hiringOrganization": {"@type": "Organization", "name": "Acme SA"},
      "jobLocation": {"@type": "Place", "address": {"@type": "PostalAddress", "addressLocality": "Lausanne", "addressRegion": "VD"}},
      "description": "<p>You design <b>AWS</b> landscapes with Terraform &amp; Kubernetes.</p><ul><li>Python</li></ul>"}


def ld_page(data=LD):
    return f'<html><head><title>x</title><script type="application/ld+json">{json.dumps(data).replace("</", "<\\/")}</script></head><body>Hi</body></html>'


PLAIN = ('<html><head><title>Senior DevOps | Site</title><meta property="og:title" content="DevOps Engineer - Beta AG">'
         '<meta content="Beta Jobs" property="og:site_name"><script>var x=1</script></head><body><nav>menu menu</nav>'
         '<main><h1>DevOps Engineer</h1><p>' + "We build pipelines with Docker and Terraform every day. " * 5 + '</p></main><footer>legal</footer></body></html>')


def public(monkeypatch, env, table=None):
    """Names resolve to the given addresses (default: a public one)."""
    table = table or {}
    monkeypatch.setattr(env.posting, "_getaddrinfo",
                        lambda host, port: [(2, 1, 6, "", (table.get(host, "93.184.216.34"), port))])


# ---- reading ------------------------------------------------------------------------------------
def test_reads_schema_org_job_posting(env):
    job = env.posting.read_page(ld_page())
    assert job["title"] == "Cloud Architect (m/w/d) 80-100%" and job["company"] == "Acme SA" and job["location"] == "Lausanne"
    assert "AWS" in job["description"] and "<" not in job["description"] and "& Kubernetes" in job["description"]


def test_reads_json_ld_inside_a_graph_and_remote_postings(env):
    data = {"@graph": [{"@type": "WebSite"}, {**LD, "jobLocation": None, "jobLocationType": "TELECOMMUTE", "hiringOrganization": "Solo GmbH"}]}
    job = env.posting.read_page(ld_page(data))
    assert job["company"] == "Solo GmbH" and job["location"] == "Remote"


def test_reads_a_plain_page_from_its_title_tags_and_text(env):
    job = env.posting.read_page(PLAIN)
    assert job["title"] == "DevOps Engineer - Beta AG" and job["company"] == "Beta Jobs"
    assert "Docker and Terraform" in job["description"] and "menu" not in job["description"] and "legal" not in job["description"]
    assert "var x" not in job["description"]


def test_a_login_wall_or_empty_page_yields_nothing(env):
    job = env.posting.read_page("<html><head><title>Sign Up | LinkedIn</title></head><body>Join now</body></html>")
    assert job["title"] == "" and job["description"] == ""


def test_pasted_text_first_line_is_the_title(env):
    job = env.posting.read_text("\n\n  Coordinateur logistique 80%  \nAcme SA\nVous planifiez les tournées.\n")
    assert job["title"] == "Coordinateur logistique 80%" and job["description"] == "Acme SA\nVous planifiez les tournées."
    assert env.posting.read_text("  \n ")["title"] == ""
    assert env.posting.as_link(" https://x.ch/job/1 ") == "https://x.ch/job/1" and env.posting.as_link("www.x.ch/a") == "https://www.x.ch/a"
    assert env.posting.as_link("see https://x.ch/job/1") == "" and env.posting.as_link("Title\nhttps://x.ch") == ""


def test_fields_are_clamped(env):
    job = env.posting.clamp({"title": "t" * 500, "company": " c ", "location": None, "description": "d" * 40000})
    assert len(job["title"]) == 200 and job["company"] == "c" and job["location"] == "" and len(job["description"]) == 30000


# ---- the guard on fetched addresses --------------------------------------------------------------
@pytest.mark.parametrize("url", [
    "ftp://example.com/x", "file:///etc/passwd", "javascript:alert(1)", "gopher://example.com", "//example.com/x", "example.com/x", "",
    "http://127.0.0.1/", "http://127.1.2.3/admin", "http://localhost:80/", "http://10.20.30.40/", "http://192.168.0.0/", "http://172.16.0.1/",
    "http://169.254.169.254/latest/meta-data/", "http://0.0.0.0/", "http://224.0.0.1/", "http://100.64.0.1/", "http://240.0.0.1/",
    "http://[::1]/", "http://[fc00::1]/", "http://[fe80::1]/", "http://[::]/", "http://[::ffff:127.0.0.1]/", "http://[::ffff:10.2.3.4]/",
    "https://example.com:8080/", "https://example.com:22/", "http://user:pw@example.com/", "https://example.com:99999/",
])
def test_refuses_addresses_that_are_not_public_web_pages(env, monkeypatch, url):
    public(monkeypatch, env, {"localhost": "127.0.0.1"})
    with pytest.raises(env.posting.PostingError) as e:
        env.posting.check_url(url)
    assert e.value.code == "blocked"


def test_a_name_resolving_to_a_private_address_is_refused_even_among_public_ones(env, monkeypatch):
    monkeypatch.setattr(env.posting, "_getaddrinfo", lambda host, port: [(2, 1, 6, "", ("93.184.216.34", port)), (2, 1, 6, "", ("10.1.2.3", port))])
    with pytest.raises(env.posting.PostingError) as e:
        env.posting.check_url("https://rebind.example/job")
    assert e.value.code == "blocked"
    monkeypatch.setattr(env.posting, "_getaddrinfo", lambda host, port: (_ for _ in ()).throw(OSError("no such host")))
    with pytest.raises(env.posting.PostingError) as e:
        env.posting.check_url("https://nowhere.example/job")
    assert e.value.code == "fetch"


def test_accepts_public_addresses_on_the_usual_ports(env, monkeypatch):
    public(monkeypatch, env)
    assert env.posting.check_url("https://jobs.example.ch/p/1") == ("jobs.example.ch", 443, "93.184.216.34")
    assert env.posting.check_url("http://jobs.example.ch:80/p/1")[1] == 80
    assert env.posting.check_url("https://[2606:4700::1111]/")[2] == "2606:4700::1111"
    assert env.posting.check_url("http://93.184.216.34/")[2] == "93.184.216.34"


def _serve(env, monkeypatch, routes, seen=None):
    public(monkeypatch, env)

    def handler(request):
        if seen is not None:
            seen.append(request)
        return routes[request.url.path](request)
    env.posting.TRANSPORT = httpx.MockTransport(handler)


def test_fetch_connects_to_the_checked_address_and_keeps_the_name(env, monkeypatch):
    seen = []
    _serve(env, monkeypatch, {"/job": lambda r: httpx.Response(200, text=ld_page(), headers={"content-type": "text/html; charset=utf-8"})}, seen)
    page, final = env.posting.fetch_page("https://jobs.example.ch/job")
    assert "JobPosting" in page and final == "https://jobs.example.ch/job"
    assert seen[0].url.host == "93.184.216.34" and seen[0].headers["host"] == "jobs.example.ch"
    assert seen[0].extensions["sni_hostname"] == "jobs.example.ch"


def test_fetch_follows_redirects_and_checks_each_target(env, monkeypatch):
    seen = []
    _serve(env, monkeypatch, {"/short": lambda r: httpx.Response(302, headers={"location": "/job"}),
                              "/job": lambda r: httpx.Response(200, text=ld_page(), headers={"content-type": "text/html"})}, seen)
    page, final = env.posting.fetch_page("https://jobs.example.ch/short")
    assert final == "https://jobs.example.ch/job" and len(seen) == 2


@pytest.mark.parametrize("target", ["http://127.0.0.1/admin", "http://169.254.169.254/latest/meta-data/", "http://10.2.3.4/", "http://[::1]/",
                                    "file:///etc/passwd", "https://jobs.example.ch:8443/x"])
def test_a_redirect_to_a_private_address_is_refused_before_it_is_requested(env, monkeypatch, target):
    seen = []
    _serve(env, monkeypatch, {"/go": lambda r: httpx.Response(302, headers={"location": target})}, seen)
    with pytest.raises(env.posting.PostingError) as e:
        env.posting.fetch_page("https://jobs.example.ch/go")
    assert e.value.code == "blocked" and len(seen) == 1


def test_fetch_gives_up_on_redirect_loops_errors_and_non_text(env, monkeypatch):
    _serve(env, monkeypatch, {"/loop": lambda r: httpx.Response(302, headers={"location": "/loop"}),
                              "/gone": lambda r: httpx.Response(404, text="no"),
                              "/pdf": lambda r: httpx.Response(200, content=b"%PDF", headers={"content-type": "application/pdf"}),
                              "/boom": lambda r: (_ for _ in ()).throw(httpx.ConnectTimeout("slow"))})
    for path in ("loop", "gone", "pdf", "boom"):
        with pytest.raises(env.posting.PostingError) as e:
            env.posting.fetch_page(f"https://jobs.example.ch/{path}")
        assert e.value.code == "fetch", path


def test_fetch_cuts_the_body_at_the_cap(env, monkeypatch):
    monkeypatch.setattr(env.posting, "MAX_BYTES", 1000)
    _serve(env, monkeypatch, {"/big": lambda r: httpx.Response(200, content=b"a" * 50000, headers={"content-type": "text/html"})})
    page, _ = env.posting.fetch_page("https://jobs.example.ch/big")
    assert len(page) == 1000


# ---- adding a posting ---------------------------------------------------------------------------------
def client(env, monkeypatch, page=None, error=None):
    def fake(url):
        if error:
            raise env.posting.PostingError(error)
        return page, url
    monkeypatch.setattr(env.posting, "fetch_page", fake)
    return TestClient(env.web.app)


def test_the_add_page_and_the_header_offer_it(env):
    c = TestClient(env.web.app)
    html = c.get("/add").text
    assert 'action="/add/posting"' in html and "+ Add a job posting" in html
    assert 'href="/add#posting"' in c.get("/jobs").text


def test_a_link_is_read_and_shown_for_review(env, monkeypatch):
    c = client(env, monkeypatch, ld_page())
    r = c.post("/add/posting", data={"posting": "https://jobs.example.ch/p/1"})
    assert r.status_code == 200
    for want in ('value="Cloud Architect (m/w/d) 80-100%"', 'value="Acme SA"', 'value="Lausanne"', 'value="https://jobs.example.ch/p/1"',
                 'action="/add/posting/save"', "Terraform"):
        assert want in r.text, want
    assert env.store.list_jobs() == []                                  # nothing saved before the review


def test_pasted_text_is_read_without_any_fetch(env, monkeypatch):
    c = client(env, monkeypatch, error="fetch")                          # (a fetch would fail the test)
    r = c.post("/add/posting", data={"posting": "DevOps Engineer\nWe use Terraform."})
    assert 'value="DevOps Engineer"' in r.text and "We use Terraform." in r.text


@pytest.mark.parametrize("error,text", [("blocked", "can't be opened from here"), ("fetch", "LinkedIn"), ("empty", "No posting was found")])
def test_a_link_that_cannot_be_read_asks_for_the_text_instead(env, monkeypatch, error, text):
    c = client(env, monkeypatch, error=error)
    r = c.post("/add/posting", data={"posting": "https://www.linkedin.com/jobs/view/1"})
    assert text in r.text and "Paste the text of the posting instead" in r.text
    assert "https://www.linkedin.com/jobs/view/1" in r.text and 'action="/add/posting/save"' not in r.text


def test_a_page_with_nothing_in_it_is_reported_empty(env, monkeypatch):
    c = client(env, monkeypatch, "<html><title>Sign Up | LinkedIn</title><body>Join</body></html>")
    assert "No posting was found" in c.post("/add/posting", data={"posting": "https://www.linkedin.com/jobs/view/1"}).text


def test_page_content_is_escaped_and_unsafe_links_dropped(env, monkeypatch):
    evil = {**LD, "title": "Architect <script>alert(1)</script>", "description": "<p>Hello &lt;img src=x onerror=alert(2)&gt;</p>"}
    c = client(env, monkeypatch, ld_page(evil))
    html = c.post("/add/posting", data={"posting": "https://jobs.example.ch/p/1"}).text
    assert "<script>alert" not in html and "<img src=x" not in html
    page = TestClient(env.web.app).post("/add/posting", data={"posting": "Title\n<img src=x onerror=alert(3)>"}).text           # pasted text keeps its markup as text
    assert "<img src=x" not in page and "&lt;img src=x onerror=alert(3)&gt;" in page
    r = c.post("/add/posting/save", data={"title": "Architect", "url": "javascript:alert(1)", "description": "<script>x</script>"}, follow_redirects=False)
    jid = int(r.headers["location"].split("/")[2])
    assert env.store.get_job(jid)["url"] == ""
    assert "<script>x</script>" not in c.get(f"/job/{jid}/search").text and "<script>x</script>" not in c.get(f"/job/{jid}").text


def test_saving_adds_a_scored_job_and_shows_what_is_missing(env, monkeypatch):
    c = TestClient(env.web.app)
    r = c.post("/add/posting/save", data={"title": "Cloud Architect", "company": "Acme SA", "location": "Lausanne", "url": "https://jobs.example.ch/p/1",
                                          "description": "AWS and Terraform with API design.", "status": "new", "source": "jobs.example.ch"},
               follow_redirects=False)
    jid = int(r.headers["location"].split("/")[2])
    assert r.headers["location"] == f"/job/{jid}/search"
    job = env.store.get_job(jid)
    assert job["status"] == "new" and job["source"] == "jobs.example.ch" and job["origin"] == "manual" and job["url"] == "https://jobs.example.ch/p/1"
    assert job["score"] == env.fetch.score_job(job)[0] and job["score"] > 0 and "matches" in job["score_rationale"]
    assert job["loose_key"] and [h["status"] for h in job["history"]] == ["new"]
    page = c.get(r.headers["location"]).text
    assert "would find a posting like this one" in page and "Open the job" not in page
    assert c.post("/add/posting/save", data={"title": "Cloud Architect", "status": "applied"}, follow_redirects=False).headers["location"].startswith("/job/")
    assert env.store.get_job(jid + 1)["status"] == "shortlisted"            # only new or shortlisted, shortlisted by default


def test_a_posting_already_in_the_list_is_not_added_twice(env, monkeypatch):
    c = TestClient(env.web.app)
    first = c.post("/add/posting/save", data={"title": "Cloud Architect", "company": "Acme SA", "location": "Lausanne"}, follow_redirects=False).headers["location"]
    again = c.post("/add/posting/save", data={"title": "Cloud Architect (m/w/d) 80-100%", "company": "Acme", "location": "Lausanne VD"}, follow_redirects=False)
    assert again.headers["location"] == first and len(env.store.list_jobs()) == 1
    assert c.post("/add/posting/save", data={"title": "  "}, follow_redirects=False).headers["location"] == "/add"


def test_a_saved_posting_is_not_removed_by_a_change_of_settings(env):
    c = TestClient(env.web.app)
    jid = int(c.post("/add/posting/save", data={"title": "Gardener", "location": "Zurich", "status": "new"}, follow_redirects=False).headers["location"].split("/")[2])
    c.post("/tune", data={"action": "add", "name": "TITLE_EXCLUDE", "value": "junior"})
    assert env.store.get_job(jid)["status"] == "new"


# ---- what the search is missing -----------------------------------------------------------------------
def kinds(env, **job):
    base = {"title": "Cloud Architect", "company": "Acme SA", "location": "Lausanne", "description": "A long enough description in English for the detector " * 3}
    a = env.posting.advice({**base, **job})
    return {p["kind"]: p for p in a["problems"]}, a


def test_a_posting_the_search_finds_has_no_problems(env):
    probs, a = kinds(env)
    assert probs == {} and a["found"]


def test_title_without_any_title_word_offers_words_that_match_it(env):
    probs, a = kinds(env, title="Consultant Cloud Infrastructure (m/w/d) 80%")
    fixes = [f[2] for f in probs["title_word"]["fixes"]]
    assert fixes and all(f[:2] == ("add", "TITLE_KEYWORDS") for f in probs["title_word"]["fixes"])
    assert "consultant" in fixes and "cloud" in fixes and "m/w/d" not in " ".join(fixes) and not any(ch.isdigit() for f in fixes for ch in f)
    assert all(env.filters._hit(f, "consultant cloud infrastructure (m/w/d) 80%") for f in fixes) and len(fixes) <= 5 and not a["found"]


def test_title_with_an_excluded_word_offers_to_stop_skipping_it(env):
    probs, _ = kinds(env, title="Junior Cloud Architect")
    assert probs["title_exclude"]["words"] == ["junior"] and probs["title_exclude"]["fixes"] == [("remove", "TITLE_EXCLUDE", "junior")]
    assert "title_word" not in probs


def test_an_excluded_company_offers_to_show_it_again(env, monkeypatch):
    monkeypatch.setattr(env.config, "COMPANY_EXCLUDE", ["adecco"])
    probs, _ = kinds(env, company="Adecco SA")
    assert probs["company"]["fixes"] == [("remove", "COMPANY_EXCLUDE", "adecco")]


def test_a_title_none_of_the_search_terms_occur_in_offers_the_cleaned_title(env, monkeypatch):
    monkeypatch.setattr(env.config, "SEARCH_TERMS", ["devops engineer"])
    probs, _ = kinds(env, title="Cloud Architect (m/w/d) 80-100%")
    assert probs["search_term"]["fixes"] == [("add", "SEARCH_TERMS", "cloud architect")]
    probs, _ = kinds(env, title="Senior DevOps Engineer (f/m/d)")
    assert "search_term" not in probs
    monkeypatch.setattr(env.config, "SEARCH_TERMS", [])                    # no terms: the sources are not narrowed by terms
    assert "search_term" not in kinds(env)[0]


def test_a_place_outside_the_towns_offers_the_town_and_its_canton(env, monkeypatch):
    probs, _ = kinds(env, location="Zürich, ZH, Schweiz")
    assert probs["location"]["town"] == "Zürich" and probs["location"]["canton"] == "ZH"
    assert probs["location"]["fixes"] == [("add", "LOCATION_KEYWORDS", "zürich"), ("add", "JOBROOM_CANTONS", "ZH")]
    probs, _ = kinds(env, location="Renens VD")
    assert probs["location"]["fixes"][0] == ("add", "LOCATION_KEYWORDS", "renens") and probs["location"]["canton"] == "VD"
    assert len(probs["location"]["fixes"]) == 1                              # VD is already searched (derived from WHERE)
    probs, _ = kinds(env, location="Nowhereville")
    assert probs["location"]["fixes"] == [("add", "LOCATION_KEYWORDS", "nowhereville")]
    probs, _ = kinds(env, location="", description="Our office in Bern. " * 20)
    assert probs["location"]["fixes"] == []


def test_a_language_outside_the_search_offers_to_add_it(env):
    probs, _ = kinds(env, title="Architecte cloud", description="Nous cherchons un architecte cloud pour concevoir des plateformes et accompagner les équipes de développement. " * 3)
    assert probs["language"]["code"] == "fr" and probs["language"]["fixes"] == [("add", "LANGUAGES", "fr")]


def test_a_work_rate_outside_the_wanted_range_is_reported(env, monkeypatch):
    monkeypatch.setattr(env.config, "WORK_RATE_MIN", 80)
    probs, _ = kinds(env, title="Cloud Architect 20-40%")
    assert (probs["rate"]["low"], probs["rate"]["high"], probs["rate"]["wanted_low"]) == (20, 40, 80) and probs["rate"]["fixes"] == []
    assert "rate" not in kinds(env, title="Cloud Architect 80-100%")[0]


def test_skills_the_posting_asks_that_are_not_the_persons_are_listed(env):
    _, a = kinds(env, description="You know Kubernetes, AWS and Terraform. " * 5)
    assert "kubernetes" in a["skills"] and "aws" not in a["skills"]       # SCORE_KEYWORDS has aws and terraform


def test_the_advice_page_shows_buttons_for_each_fix_and_skill_chips(env, monkeypatch):
    monkeypatch.setattr(env.config, "SEARCH_TERMS", ["devops engineer"])
    c = TestClient(env.web.app)
    jid = env.store.add_manual({"title": "Junior Consultant Kubernetes", "company": "Acme SA", "location": "Zürich",
                                "description": "Kubernetes everywhere. " * 20, "status": "new"})
    html = c.get(f"/job/{jid}/search").text
    for want in ("Does my search find postings like this one?", "Stop skipping “junior”", "+ consultant", "+ Search in zürich",
                 "+ Also search the canton ZH", "Search for it too:", 'action="/skills"', "+ I have it", f'name="next" value="/job/{jid}/search"'):
        assert want in html, want
    assert c.get("/job/9999/search", follow_redirects=False).status_code in (302, 303, 307)


def test_a_fix_changes_that_one_setting_and_starts_a_scan(env, monkeypatch):
    runs = []
    monkeypatch.setattr(env.web, "_start_background", lambda fn: (runs.append(1), env.store.set_meta(scan_started_at=env.store.now())))
    c = TestClient(env.web.app)
    r = c.post("/tune", data={"action": "add", "name": "TITLE_KEYWORDS", "value": "Consultant", "next": "/job/3/search"}, follow_redirects=False)
    assert r.headers["location"] == "/job/3/search" and env.config.TITLE_KEYWORDS == ["architect", "devops", "consultant"] and len(runs) == 1
    assert env.config.TITLE_EXCLUDE == ["junior", "intern"]                    # nothing else moved
    env.store.set_meta(scan_started_at="2020-01-01T00:00:00")
    c.post("/tune", data={"action": "add", "name": "SEARCH_TERMS", "value": "Cloud Architect"})
    c.post("/tune", data={"action": "add", "name": "LANGUAGES", "value": "FR"})
    c.post("/tune", data={"action": "add", "name": "JOBROOM_CANTONS", "value": "zh"})
    assert env.config.SEARCH_TERMS == ["cloud architect"] and env.config.LANGUAGES == ["en", "fr"]
    assert env.config.JOBROOM_CANTONS == ["VD", "ZH"]                          # the cantons derived from WHERE are kept
    env.store.set_meta(scan_started_at="2020-01-01T00:00:00")
    n = len(runs)
    c.post("/tune", data={"action": "remove", "name": "TITLE_EXCLUDE", "value": "junior"})
    assert env.config.TITLE_EXCLUDE == ["intern"] and len(runs) == n + 1
    env.store.set_meta(scan_started_at="2020-01-01T00:00:00")
    c.post("/tune", data={"action": "add", "name": "TITLE_EXCLUDE", "value": "stagiaire"})            # narrowing: no scan
    assert len(runs) == n + 1


def test_the_fix_routes_refuse_unknown_names_actions_and_values(env, monkeypatch):
    monkeypatch.setattr(env.web, "_start_background", lambda fn: pytest.fail("no scan for a refused change"))
    c = TestClient(env.web.app)
    before = {k: getattr(env.config, k) for k in env.config.EDITABLE}
    bad = [("add", "PROVIDERS", "adzuna"), ("add", "SCORE_KEYWORDS", "x"), ("add", "WHERE", "Bern"), ("add", "NOPE", "x"), ("add", "HOME_TOWN", "x"),
           ("remove", "SEARCH_TERMS", "devops"), ("remove", "TITLE_KEYWORDS", "architect"), ("remove", "LANGUAGES", "en"), ("remove", "JOBROOM_CANTONS", "VD"),
           ("replace", "TITLE_KEYWORDS", "x"), ("", "TITLE_KEYWORDS", "x"), ("add", "LANGUAGES", "xx"), ("add", "LANGUAGES", "klingon"),
           ("add", "JOBROOM_CANTONS", "ZHH"), ("add", "JOBROOM_CANTONS", "1A"), ("add", "JOBROOM_CANTONS", "Z"), ("add", "SEARCH_TERMS", "x" * 61),
           ("add", "SEARCH_TERMS", "a;b"), ("add", "SEARCH_TERMS", "a,b"), ("add", "TITLE_KEYWORDS", "<script>"), ("add", "SEARCH_TERMS", "  "),
           ("add", "TITLE_KEYWORDS", "a\x00b")]
    for action, name, value in bad:
        c.post("/tune", data={"action": action, "name": name, "value": value})
        assert {k: getattr(env.config, k) for k in env.config.EDITABLE} == before, (action, name, value)
        assert env.tune.change(action, name, value) is None, (action, name, value)


def test_fix_buttons_do_not_duplicate_and_keep_other_cantons(env):
    env.tune.change("add", "TITLE_KEYWORDS", "SRE")
    env.tune.change("add", "TITLE_KEYWORDS", "sre")
    assert env.config.TITLE_KEYWORDS.count("sre") == 1
    env.tune.change("add", "JOBROOM_CANTONS", "GE")
    env.tune.change("add", "JOBROOM_CANTONS", "ge")
    assert env.config.JOBROOM_CANTONS == ["VD", "GE"]


def test_the_job_page_links_to_the_check(env):
    c = TestClient(env.web.app)
    jid = env.store.add_manual({"title": "Cloud Architect", "company": "Acme SA", "location": "Lausanne", "status": "new"})
    assert f'href="/job/{jid}/search"' in c.get(f"/job/{jid}").text


# ---- languages ----------------------------------------------------------------------------------------
@pytest.mark.parametrize("lang,words", [
    ("fr", ["Ajouter une offre d'emploi", "Lire l'annonce", "Lien ou texte de l'annonce"]),
    ("de", ["Stelleninserat hinzufügen", "Inserat lesen", "Link oder Text des Inserats"]),
    ("it", ["Aggiungi un annuncio di lavoro", "Leggi l'annuncio", "Link o testo dell'annuncio"]),
])
def test_the_pages_render_in_french_german_and_italian(env, monkeypatch, lang, words):
    monkeypatch.setattr(env.config, "SEARCH_TERMS", ["devops engineer"])
    c = client(env, monkeypatch, ld_page(), None)
    c.headers["accept-language"] = f"{lang},en;q=0.5"
    add = c.get("/add").text
    for w in words:
        assert w in add, w
    assert "Read the posting" not in add and "Link or text of the posting" not in add
    review = c.post("/add/posting", data={"posting": "https://jobs.example.ch/p/1"}).text
    assert "Check the posting" not in review and "Add this job and check my search" not in review and 'action="/add/posting/save"' in review
    err = client(env, monkeypatch, error="fetch")
    err.headers["accept-language"] = lang
    assert "Paste the text of the posting instead" not in err.post("/add/posting", data={"posting": "https://x.ch/1"}).text
    jid = env.store.add_manual({"title": "Junior Consultant Kubernetes", "company": "Acme SA", "location": "Zürich",
                                "description": "Kubernetes everywhere. " * 20, "status": "new"})
    page = c.get(f"/job/{jid}/search").text
    for english in ("Does my search find postings like this one?", "Stop skipping", "Search for it too:", "+ Search in", "Skills this posting asks for",
                    "A change that widens your search", "None of your title words", "This place is not in your towns"):
        assert english not in page, english
    assert f'<html lang="{lang}">' in page
