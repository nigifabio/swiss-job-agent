"""The added sources: Job-Room, remote boards, keyed aggregators, alert emails, and the five
new company job systems. All network mocked (conftest.net)."""
import json
from pathlib import Path

import httpx

from conftest import jresp


def _ad(i, title, company, city="Lausanne", ext=None, lang="en", desc="Cloud architect role with AWS and Terraform in our team."):
    return {"jobAdvertisement": {"id": f"id{i}", "createdTime": "2026-09-24", "jobContent": {
        "jobDescriptions": [{"languageIsoCode": lang, "title": title, "description": desc}],
        "company": {"name": company}, "location": {"city": city, "cantonCode": "VD"},
        "externalUrl": ext}}}


def test_jobroom_skips_republished_and_maps_cantons(env, net, monkeypatch):
    env.scanlog.start()
    monkeypatch.setattr(env.config, "SEARCH_TERMS", ["architect"])
    monkeypatch.setattr(env.config, "WHERE", ["Vaud", "Genève"])
    assert env.providers.jobroom.cantons() == ["GE", "VD"]
    bodies = []

    def search(req):
        bodies.append(json.loads(req.content))
        return jresp([_ad(1, "Cloud <em>Architect</em>", "Nestlé SA"),
                      _ad(2, "Cloud Architect II", "Jobup", ext="https://www.jobup.ch/fr/emplois/detail/x/?utm=1"),
                      _ad(3, "Junior Cloud Architect", "Acme")])
    net["https://www.job-room.ch/jobadservice/api/jobAdvertisements/_search"] = search
    out = env.providers.jobroom.fetch()
    assert [j["title"] for j in out] == ["Cloud Architect"]            # republished + junior dropped
    assert out[0]["url"] == "https://www.job-room.ch/job-search/id1" and out[0]["location"] == "Lausanne, VD"
    assert bodies[0]["cantonCodes"] == ["GE", "VD"] and bodies[0]["displayRestricted"] is False
    net["https://www.job-room.ch/jobadservice/api/jobAdvertisements/_search"] = lambda r: jresp({"error": "x"})
    env.scanlog.start()
    env.providers.jobroom.fetch()
    assert "API may have changed" in env.scanlog.result()["job-room"]["errors"][0]


def test_remote_boards_filter_regions_repair_text_and_isolate_failures(env, net, monkeypatch):
    env.scanlog.start()
    monkeypatch.setattr(env.config, "SEARCH_TERMS", ["architect"])
    net["https://remotive.com/api/remote-jobs"] = lambda r: jresp({"jobs": [
        {"title": "Cloud Architect", "company_name": "A", "candidate_required_location": "Europe",
         "description": "<p>AWS team</p>", "url": "https://remotive.com/j/1"},
        {"title": "DevOps Engineer", "company_name": "B", "candidate_required_location": "USA only",
         "description": "x", "url": "https://remotive.com/j/2"}]})
    net["https://remoteok.com/api"] = lambda r: jresp([{"legal": "..."}, {
        "position": "Cloud Architect â\u0080\u0094 Platform", "company": "C", "location": "",
        "description": "AWS", "url": "https://remoteok.com/j/3"}])
    net["https://himalayas.app/jobs/api"] = lambda r: httpx.Response(500)
    out = env.providers.remote.fetch()
    assert {j["url"] for j in out} == {"https://remotive.com/j/1", "https://remoteok.com/j/3"}   # USA-only dropped
    ok = next(j for j in out if j["source"] == "remoteok")
    assert ok["title"] == "Cloud Architect — Platform" and ok["location"] == "Remote - Worldwide"
    rep = env.scanlog.result()
    assert rep["himalayas"]["errors"] and rep["remotive"]["count"] == 1   # one board down, others fine


def test_keyed_aggregators_silent_without_key_and_safe_with_it(env, net, monkeypatch):
    assert env.providers.careerjet.fetch() == [] and env.providers.jooble.fetch() == []   # no key: no request
    monkeypatch.setattr(env.config, "SEARCH_TERMS", ["architect"])
    monkeypatch.setattr(env.config, "WHERE", ["Genève"])
    monkeypatch.setenv("CAREERJET_API_KEY", "CJKEY")
    seen_auth = []
    net["https://search.api.careerjet.net/v4/query"] = lambda r: (seen_auth.append(r.headers.get("authorization")), jresp(
        {"jobs": [{"title": "Cloud Architect", "company": "Acme", "locations": "Genève",
                   "description": "AWS", "url": "https://cj/1", "date": "2026-09-24"}]}))[1]
    env.scanlog.start()
    [job] = env.providers.careerjet.fetch()
    assert job["url"] == "https://cj/1" and seen_auth[0].startswith("Basic ")
    monkeypatch.setenv("JOOBLE_API_KEY", "JKEY")
    calls = []
    net["https://jooble.org/api/"] = lambda r: (calls.append(1), httpx.Response(403))[1]
    env.scanlog.start()
    assert env.providers.jooble.fetch() == [] and len(calls) == 1          # bad key: stop at once
    errs = " ".join(env.scanlog.result()["jooble"]["errors"])
    assert "403" in errs and "JKEY" not in errs                             # key never shown
    net["https://jooble.org/api/"] = lambda r: jresp({"unexpected": True})
    env.scanlog.start()
    env.providers.jooble.fetch()
    assert "unexpected response shape" in env.scanlog.result()["jooble"]["errors"][0]


LINKEDIN_ALERT = """<table><tr><td><a href="https://www.linkedin.com/comm/jobs/view/4012345678/?trackingId=abc">
Cloud Architect</a></td></tr><tr><td>Acme SA</td></tr><tr><td>Geneva, Switzerland</td></tr>
<tr><td><a href="https://www.linkedin.com/comm/jobs/view/4012345678/?x=1">View job</a></td></tr></table>
<p><a href="https://ch.indeed.com/rc/clk?jk=0a1b2c3d4e5f6a7b&from=ja">DevOps Engineer</a></p><p>Beta AG</p><p>Lausanne</p>
<p><a href="https://www.linkedin.com/jobs/search/?keywords=x">See all jobs</a></p>"""


def test_alert_email_links_are_extracted(env):
    found = env.providers.mailalerts.jobs_from_html(LINKEDIN_ALERT)
    assert found == [
        ("linkedin", "https://www.linkedin.com/jobs/view/4012345678/", "Cloud Architect", "Acme SA", "Geneva, Switzerland"),
        ("indeed", "https://ch.indeed.com/viewjob?jk=0a1b2c3d4e5f6a7b", "DevOps Engineer", "Beta AG", "Lausanne")]
    assert env.providers.mailalerts.fetch() == []                          # no IMAP_HOST: silent


def test_new_company_job_systems_parse(env, net):
    env.scanlog.start()
    Path(env.config.WATCHLIST_PATH).write_text(json.dumps([
        {"company": "WD", "ats": "workday", "slug": "wd/wd3/External"},
        {"company": "PS", "ats": "personio", "slug": "ps"},
        {"company": "RC", "ats": "recruitee", "slug": "rc"},
        {"company": "TT", "ats": "teamtailor", "slug": "tt.teamtailor.com"},
        {"company": "WK", "ats": "workable", "slug": "wk"}]))
    net["https://wd.wd3.myworkdayjobs.com/wday/cxs/wd/External/jobs"] = lambda r: jresp(
        {"total": 1, "jobPostings": [{"title": "Cloud Architect", "externalPath": "/job/Geneva/Cloud-Architect_1",
                                      "locationsText": "Geneva"}]})
    net["https://wd.wd3.myworkdayjobs.com/wday/cxs/wd/External/job/"] = lambda r: jresp(
        {"jobPostingInfo": {"jobDescription": "<p>AWS</p>", "externalUrl": "https://wd/job/1", "location": "Geneva"}})
    net["https://ps.jobs.personio.de/xml"] = lambda r: httpx.Response(200, content=(
        "<workzag-jobs><position><id>7</id><subcompany>PS AG</subcompany><office>Lausanne</office>"
        "<name>DevOps Engineer</name><jobDescriptions><jobDescription><name>Tasks</name>"
        "<value><![CDATA[<p>You will build our cloud platform with Terraform and automate everything.</p>]]></value></jobDescription></jobDescriptions></position></workzag-jobs>").encode())
    net["https://rc.recruitee.com/api/offers/"] = lambda r: jresp({"offers": [
        {"title": "Solutions Architect", "city": "Geneva", "country": "Switzerland", "description": "<p>x</p>",
         "careers_url": "https://rc/o/1", "company_name": "RC"}]})
    net["https://tt.teamtailor.com/jobs.rss"] = lambda r: httpx.Response(200, content=(
        '<rss xmlns:tt="https://teamtailor.com/locations"><channel><item><title>Cloud Architect Lead</title>'
        "<description>&lt;p&gt;AWS&lt;/p&gt;</description><link>https://tt/jobs/1</link>"
        "<tt:locations><tt:location><tt:city>Lausanne</tt:city><tt:country>Switzerland</tt:country>"
        "</tt:location></tt:locations></item></channel></rss>").encode())
    net["https://apply.workable.com/api/v3/accounts/wk/jobs"] = lambda r: jresp({"total": 1, "results": [
        {"title": "DevOps Architect", "shortcode": "AB12", "location": {"city": "Geneva", "country": "Switzerland"}}]})
    net["https://apply.workable.com/api/v2/accounts/wk/jobs/AB12"] = lambda r: jresp({"description": "<p>Azure</p>"})
    out = {j["source"].split(":")[0]: j for j in env.providers.ats.fetch()}
    assert set(out) == {"workday", "personio", "recruitee", "teamtailor", "workable"}, env.scanlog.result()
    assert out["workday"]["url"] == "https://wd/job/1" and out["workday"]["description"] == "AWS"
    assert out["personio"]["company"] == "PS AG" and "Terraform" in out["personio"]["description"]
    assert out["personio"]["url"] == "https://ps.jobs.personio.de/job/7"
    assert out["teamtailor"]["location"] == "Lausanne, Switzerland" and out["teamtailor"]["description"] == "AWS"
    assert out["workable"]["url"] == "https://apply.workable.com/wk/j/AB12/" and out["workable"]["description"] == "Azure"
    assert not env.scanlog.result()["ats"]["errors"]


def test_mailbox_is_opened_read_only_and_never_marks_mail(env, monkeypatch):
    from email.mime.text import MIMEText
    calls = []
    msg = MIMEText(LINKEDIN_ALERT, "html")
    msg["Date"] = "Wed, 24 Sep 2026 08:00:00 +0200"

    class FakeIMAP:
        def __init__(self, host, timeout=None):
            calls.append(("connect", host))

        def login(self, user, pw):
            calls.append(("login", user))

        def select(self, folder, readonly=False):
            calls.append(("select", folder, readonly))

        def search(self, charset, *criteria):
            calls.append(("search",) + criteria[:1])
            return "OK", [b"1"]

        def fetch(self, num, what):
            calls.append(("fetch", what))
            return "OK", [(b"1", msg.as_bytes())]

        def logout(self):
            calls.append(("logout",))
    monkeypatch.setattr(env.providers.mailalerts.imaplib, "IMAP4_SSL", FakeIMAP)
    monkeypatch.setenv("IMAP_HOST", "imap.example.com")
    monkeypatch.setenv("IMAP_USER", "alerts@example.com")
    monkeypatch.setenv("IMAP_PASSWORD", "secret-pw")
    env.scanlog.start()
    out = env.providers.mailalerts.fetch()
    assert ("select", "INBOX", True) in calls                               # read-only
    assert all(c[1] == "(BODY.PEEK[])" for c in calls if c[0] == "fetch")    # PEEK: never sets \Seen
    assert [j["source"] for j in out] == ["email:linkedin", "email:indeed"]
    assert out[0]["company"] == "Acme SA"

    class Broken(FakeIMAP):
        def login(self, user, pw):
            raise env.providers.mailalerts.imaplib.IMAP4.error("AUTHENTICATIONFAILED")
    monkeypatch.setattr(env.providers.mailalerts.imaplib, "IMAP4_SSL", Broken)
    env.scanlog.start()
    assert env.providers.mailalerts.fetch() == []
    errs = " ".join(env.scanlog.result()["email alerts"]["errors"])
    assert "AUTHENTICATIONFAILED" in errs and "secret-pw" not in errs
