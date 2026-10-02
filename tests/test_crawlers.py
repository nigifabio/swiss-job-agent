"""Crawler robustness: HTTP retry/pacing, each provider's parsing and failure isolation,
scan-health reporting, scheduler timing. All network is mocked (see conftest.net)."""
import datetime
import json
from pathlib import Path

import httpx
import pytest

from conftest import jresp


# ---- HTTP helper -------------------------------------------------------------------
def test_http_retries_transient_then_succeeds(env, net):
    calls, sleeps = [], []
    env.http.SLEEP = sleeps.append

    def flaky(req):
        calls.append(1)
        if len(calls) == 1:
            return httpx.Response(503)
        if len(calls) == 2:
            return httpx.Response(429, headers={"retry-after": "7"})
        return jresp({"ok": True})
    net["https://x.test/"] = flaky
    with env.http.Http() as h:
        assert h.json("https://x.test/a") == {"ok": True}
    assert len(calls) == 3 and 7.0 in sleeps          # Retry-After honoured


def test_http_gives_up_and_does_not_retry_4xx(env, net):
    calls = []
    net["https://x.test/"] = lambda r: (calls.append(1), httpx.Response(404))[1]
    with env.http.Http() as h, pytest.raises(httpx.HTTPStatusError):
        h.get("https://x.test/missing")
    assert len(calls) == 1

    def down(req):
        raise httpx.ConnectError("refused", request=req)
    net["https://down.test/"] = down
    with env.http.Http(tries=3) as h, pytest.raises(httpx.ConnectError):
        h.get("https://down.test/")


def test_http_paces_requests_to_same_host(env, net):
    sleeps = []
    env.http.SLEEP = sleeps.append
    net["https://x.test/"] = lambda r: jresp({})
    with env.http.Http(min_gap=5) as h:
        h.get("https://x.test/1")
        h.get("https://x.test/2")
    assert sleeps and sleeps[0] > 4


# ---- ATS boards --------------------------------------------------------------------
def _watchlist(env, boards):
    Path(env.config.WATCHLIST_PATH).write_text(json.dumps(boards))


def test_ats_parses_every_board_type_and_isolates_failures(env, net):
    env.scanlog.start()
    _watchlist(env, [
        {"company": "GH", "ats": "greenhouse", "slug": "gh"},
        {"company": "Broken", "ats": "lever", "slug": "broken"},
        {"company": "LV", "ats": "lever", "slug": "lv"},
        {"company": "AB", "ats": "ashby", "slug": "ab"},
    ])
    net["https://boards-api.greenhouse.io/v1/boards/gh/"] = lambda r: jresp({"jobs": [
        {"title": "Cloud Architect", "location": {"name": "Geneva"},
         "content": "&lt;p&gt;We use &lt;b&gt;AWS&lt;/b&gt;&lt;/p&gt;", "absolute_url": "https://gh/1"},
        {"title": "Junior Cloud Architect", "location": {"name": "Geneva"}, "content": "", "absolute_url": "https://gh/2"},
        {"title": "Cloud Architect", "location": {"name": "Zurich"}, "content": "", "absolute_url": "https://gh/3"},
    ]})
    net["https://api.lever.co/v0/postings/broken"] = lambda r: httpx.Response(500)
    net["https://api.lever.co/v0/postings/lv"] = lambda r: jresp([
        {"text": "DevOps Engineer", "categories": {"location": "Lausanne"},
         "descriptionPlain": "Terraform and Kubernetes on our platform team", "hostedUrl": "https://lv/1"}])
    net["https://api.ashbyhq.com/posting-api/job-board/ab"] = lambda r: jresp({"jobs": [
        {"title": "Solutions Architect", "location": "Remote - EMEA",
         "descriptionHtml": "<p>Customer facing</p>", "jobUrl": "https://ab/1"}]})
    jobs = env.providers.ats.fetch()
    by = {j["url"]: j for j in jobs}
    assert set(by) == {"https://gh/1", "https://lv/1", "https://ab/1"}   # junior + Zurich filtered
    assert by["https://gh/1"]["description"] == "We use AWS"              # escaped HTML decoded
    rep = env.scanlog.result()["ats"]
    assert rep["count"] == 3 and any("broken" in e for e in rep["errors"])  # failure isolated + reported


def test_smartrecruiters_pages_and_skips_known_details(env, net):
    env.scanlog.start()
    _watchlist(env, [{"company": "SR", "ats": "smartrecruiters", "slug": "sr"}])

    offsets = []

    def listing(req):
        off = int(req.url.params["offset"])
        offsets.append(off)
        n = 100 if off == 0 else 20
        return jresp({"totalFound": 120, "content": [
            {"id": f"j{off + i}", "name": "Cloud Architect" if i == 0 else f"Accountant {off + i}",
             "location": {"city": "Geneva", "country": "ch"}} for i in range(n)]})
    details = []
    net["https://api.smartrecruiters.com/v1/companies/sr/postings?"] = listing
    net["https://api.smartrecruiters.com/v1/companies/sr/postings/"] = lambda r: (
        details.append(str(r.url)), jresp({"jobAd": {"sections": {"jobDescription": {"text": "<p>Azure</p>"}}}}))[1]
    jobs = env.providers.ats.fetch()
    assert offsets == [0, 100]                  # second page requested, then stopped (120 total)
    # identical title/company/place on both pages -> kept once, and only one detail request
    assert len(jobs) == 1 and jobs[0]["description"] == "Azure" and len(details) == 1
    env.store.upsert_jobs(jobs)
    details.clear()
    env.providers.ats.fetch()
    assert details == []                       # already stored -> no detail requests


# ---- jobs.ch / jobup.ch --------------------------------------------------------------
def test_jobcloud_paging_dedupe_filters_and_shape_change(env, net, monkeypatch):
    env.scanlog.start()
    monkeypatch.setattr(env.config, "SEARCH_TERMS", ["architect"])
    monkeypatch.setattr(env.config, "WHERE", ["Genève"])
    pages = []

    def jobs_ch(req):
        page = int(req.url.params["page"])
        pages.append(page)
        docs = [{"title": f"Cloud Architect {page}-{i}", "company_name": "Acme", "place": "Genève",
                 "preview": "Cloud architecture role in Geneva with AWS and Terraform for our team",
                 "_links": {"detail_en": {"href": f"https://www.jobs.ch/en/job/{page}-{i}"}}}
                for i in range(20 if page == 1 else 3)]
        docs.append({"title": "Architecte cloud", "company_name": "Acme", "place": "Genève",
                     "preview": "Nous cherchons un architecte cloud expérimenté pour notre équipe à Genève",
                     "slug": "fr-only"})
        return jresp({"documents": docs})
    net["https://www.jobs.ch/api/v1/public/search"] = jobs_ch
    net["https://www.jobup.ch/api/v1/public/search"] = lambda r: jresp({"results": []})  # API changed
    out = env.providers.jobup.fetch()
    assert pages == [1, 2]                                    # stopped when a page came back short
    assert all("Architecte" not in j["title"] for j in out)  # LANGUAGES=en drops the French ad
    assert len(out) == 23 and len({j["content_hash"] for j in out}) == 23
    assert out[0]["url"].startswith("https://www.jobs.ch/en/job/")
    rep = env.scanlog.result()
    assert rep["jobs.ch"]["count"] == 23
    assert "API may have changed" in rep["jobup.ch"]["errors"][0]


# ---- Adzuna ----------------------------------------------------------------------------
def test_adzuna_parses_and_never_leaks_key(env, net, monkeypatch):
    env.scanlog.start()
    monkeypatch.setattr(env.config, "ADZUNA_APP_ID", "id123")
    monkeypatch.setattr(env.config, "ADZUNA_APP_KEY", "SECRETKEY")
    monkeypatch.setattr(env.config, "SEARCH_TERMS", ["architect", "devops"])
    monkeypatch.setattr(env.config, "WHERE", ["Genève"])
    net["https://api.adzuna.com/"] = lambda r: jresp({"results": [
        {"title": "<strong>Cloud</strong> Architect", "company": {"display_name": "Acme"},
         "location": {"display_name": "Genève"}, "description": "AWS team",
         "redirect_url": "https://adz/1", "salary_min": 120000, "salary_max": None}]})
    [job] = [j for j in env.providers.adzuna.fetch() if j["url"] == "https://adz/1"][:1]
    assert job["title"] == "Cloud Architect" and job["salary"] == "120'000-120'000"

    calls = []
    net["https://api.adzuna.com/"] = lambda r: (calls.append(1), httpx.Response(401))[1]
    env.scanlog.start()
    assert env.providers.adzuna.fetch() == []
    errs = env.scanlog.result()["adzuna"]["errors"]
    assert len(calls) == 1                                     # stops after a bad key
    assert "401" in errs[0] and "SECRETKEY" not in " ".join(errs)


# ---- scan health, scheduler, enrichment -----------------------------------------------
def test_scan_report_flags_errors_and_sources_that_drop_to_zero(env, monkeypatch):
    from fastapi.testclient import TestClient

    def ok():
        env.scanlog.count("jobs.ch", 5)
        return []
    monkeypatch.setattr(env.config, "PROVIDERS", ["jobup"])
    monkeypatch.setattr(env.providers.jobup, "fetch", ok)
    monkeypatch.setitem(env.fetch.MODULES, "jobup", env.providers.jobup)
    env.fetch.run()
    assert json.loads(env.store.get_meta()["last_scan_warnings"]) == []

    def crash():
        env.scanlog.count("jobs.ch", 0)
        raise RuntimeError("boom")
    monkeypatch.setattr(env.providers.jobup, "fetch", crash)
    env.fetch.run()
    warnings = json.loads(env.store.get_meta()["last_scan_warnings"])
    assert any("returned 0 postings (had 5" in w for w in warnings)
    assert any("jobup: 1 error" in w for w in warnings)
    page = TestClient(env.web.app).get("/jobs?status=new").text
    assert "Last scan had problems" in page and "had 5 last scan" in page


def test_scheduler_does_not_rescan_after_restart(env):
    now = datetime.datetime(2026, 9, 24, 12, 0)
    due = env.scheduler.seconds_until_due
    assert due(3600, {}, now) == 0
    assert due(12 * 3600, {"last_scan_at": "2026-09-24T11:00:00"}, now) == 11 * 3600
    assert due(3600, {"last_scan_at": "2026-09-24T09:00:00"}, now) == 0


def test_full_text_fetch_retried_only_after_network_failure(env, monkeypatch):
    from fastapi.testclient import TestClient
    env.store.upsert_jobs([{"content_hash": "e1", "title": "Cloud Architect", "url": "https://job/1",
                            "description": "short", "source": "t"}])
    [job] = env.store.list_jobs("new")
    c = TestClient(env.web.app)
    monkeypatch.setattr(env.enrich, "full_description", lambda url: None)      # network error
    c.get(f"/job/{job['id']}")
    assert env.store.get_job(job["id"])["enriched_at"] is None                 # will retry
    monkeypatch.setattr(env.enrich, "full_description", lambda url: "Full posting text with AWS " * 3)
    assert "Full posting text" in c.get(f"/job/{job['id']}").text
    assert env.store.get_job(job["id"])["enriched_at"]                          # done, cached


def test_discover_urls_and_merge(env, tmp_path, monkeypatch):
    import app.discover as d
    assert d.from_url("https://pmi.wd3.myworkdayjobs.com/en-US/PMI_Careers") == ("workday", "pmi/wd3/PMI_Careers")
    assert d.from_url("https://boards.greenhouse.io/proton") == ("greenhouse", "proton")
    assert d.from_url("https://acme.jobs.personio.de/job/123") == ("personio", "acme")
    assert d.from_url("https://apply.workable.com/huggingface/") == ("workable", "huggingface")
    assert d.from_url("https://acme.teamtailor.com/jobs") == ("teamtailor", "acme.teamtailor.com")
    assert d.from_url("https://example.com/careers") is None
    Path(env.config.WATCHLIST_PATH).write_text(json.dumps([{"company": "Old", "ats": "lever", "slug": "old"}]))
    seed = tmp_path / "seed.txt"
    seed.write_text("# comment\nPMI = https://pmi.wd3.myworkdayjobs.com/PMI_Careers\nOld = https://jobs.lever.co/old\n")
    monkeypatch.setattr(d, "config", env.config)
    d.main([str(seed)])
    wl = json.loads(Path(env.config.WATCHLIST_PATH).read_text())
    assert [(e["ats"], e["slug"]) for e in wl] == [("lever", "old"), ("workday", "pmi/wd3/PMI_Careers")]   # merged, no dupes


def test_discovery_rejects_other_companies_with_the_same_short_name(env):
    import app.discover as d
    assert d.name_matches("Four Seasons", "Four Seasons Hotels Careers") is False   # extra words = other company
    assert d.name_matches("Four Seasons", "Four Seasons Careers")
    assert not d.name_matches("International Organization for Migration", "UpWork International")
    assert d.name_matches("Audemars Piguet", "Audemars Piguet SA")
    assert d.name_matches("International Committee of the Red Cross", "International Committee of the Red Cross")
    assert not d.name_matches("Sunrise", "Sunrise Management")
    assert d.accept(None, "TAG Heuer", "lever", "tagheuer") and not d.accept(None, "TAG Heuer", "lever", "tag")
    assert d.accept(None, "Logitech", "workday", "logitech/wd5/Logitech")
