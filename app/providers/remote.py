"""Remote-job boards: Remotive, Remote OK, Himalayas, Jobicy. Public APIs, no key.

Terms of use (checked 2026-09-24): link back to the posting on their site and name them as
the source. Every card shows its source ("remotive", "remoteok", "himalayas", "jobicy") and "Open & apply"
goes to their posting URL. A role counts only if it's open to Switzerland/Europe/worldwide
(filters.location_ok on "Remote - <regions>"); "USA only" and similar are dropped.

Verified fields 2026-09-24:
  remotive  GET remotive.com/api/remote-jobs?search=  -> jobs[{title, company_name,
            candidate_required_location, description, url, publication_date}]
  remoteok  GET remoteok.com/api -> [legal, {position, company, location, description, url, date}...]
  himalayas GET himalayas.app/jobs/api?limit=&cursor= -> {jobs[{title, companyName,
            locationRestrictions[], description, guid, applicationLink, pubDate}], nextCursor}
  jobicy    GET jobicy.com/api/v2/remote-jobs?count=50&geo=switzerland (verified 2026-10-08; they ask to be
            credited with a link to the posting) -> {jobs[{jobTitle, companyName, jobGeo, jobDescription, url, pubDate}]}
"""
import os

from .. import config, enrich, filters, scanlog
from ..http import Http
from ..normalize import content_hash

HIMALAYAS_PAGES = int(os.environ.get("HIMALAYAS_PAGES", "5"))
UA = {"User-Agent": "swiss-job-agent (personal job search; links back to postings)"}


def fix_mojibake(s):
    """Remote OK double-encodes UTF-8 ("â\x80\x94" for "—"); repair it when that's what it is."""
    if not s or not any(m in s for m in ("â", "Ã", "Â")):
        return s
    try:
        return s.encode("latin-1").decode("utf-8")
    except (UnicodeEncodeError, UnicodeDecodeError):
        return s


def _job(out, seen, source, title, company, regions, desc_html, url, posted):
    title, company = filters.strip_html(fix_mojibake(title)), fix_mojibake(company or "")
    desc_html = fix_mojibake(desc_html)
    regions = "" if (regions or "").strip().lower() in ("", "remote", "anywhere") else regions
    loc = f"Remote - {regions or 'Worldwide'}"
    h = content_hash(title, company, loc)
    if h in seen or not url or not filters.title_ok(title) or not filters.location_ok(loc):
        return
    desc = enrich.html_to_text(desc_html or "")
    if not filters.language_ok(title, desc):
        return
    seen.add(h)
    out.append({"source": source, "title": title, "company": company or "", "location": loc,
                "description": desc[:20000], "url": url, "salary": "", "posted_at": str(posted or ""),
                "content_hash": h})


def _remotive(client, out, seen):
    n0 = len(out)
    for term in config.SEARCH_TERMS or [""]:
        data = client.json("https://remotive.com/api/remote-jobs", params={"search": term, "limit": 50})
        if "jobs" not in data:
            raise ValueError("unexpected response shape (no 'jobs'); the API may have changed")
        for j in data["jobs"]:
            _job(out, seen, "remotive", j.get("title", ""), j.get("company_name", ""),
                 j.get("candidate_required_location", ""), j.get("description", ""), j.get("url", ""),
                 j.get("publication_date", ""))
    return len(out) - n0


def _remoteok(client, out, seen):
    n0 = len(out)
    data = client.json("https://remoteok.com/api")
    if not isinstance(data, list):
        raise ValueError("unexpected response shape (not a list); the API may have changed")
    for j in data[1:]:                      # first item is the legal notice
        _job(out, seen, "remoteok", j.get("position", ""), j.get("company", ""), j.get("location", ""),
             j.get("description", ""), j.get("url", ""), j.get("date", ""))
    return len(out) - n0


def _himalayas(client, out, seen):
    n0, cursor = len(out), None
    for _ in range(HIMALAYAS_PAGES):
        params = {"limit": 20, **({"cursor": cursor} if cursor else {})}
        data = client.json("https://himalayas.app/jobs/api", params=params)
        if "jobs" not in data:
            raise ValueError("unexpected response shape (no 'jobs'); the API may have changed")
        for j in data["jobs"]:
            url = j.get("guid") if str(j.get("guid", "")).startswith("http") else j.get("applicationLink", "")
            _job(out, seen, "himalayas", j.get("title", ""), j.get("companyName", ""),
                 ", ".join(j.get("locationRestrictions") or []), j.get("description", ""), url, j.get("pubDate", ""))
        cursor = data.get("nextCursor")
        if not cursor:
            break
    return len(out) - n0


def _jobicy(client, out, seen):
    n0 = len(out)
    for geo in ("switzerland", "europe"):               # roles open to people in Switzerland, then all of Europe
        data = client.json("https://jobicy.com/api/v2/remote-jobs", params={"count": 50, "geo": geo})
        if "jobs" not in data:
            raise ValueError("unexpected response shape (no 'jobs'); the API may have changed")
        for j in data["jobs"]:
            _job(out, seen, "jobicy", j.get("jobTitle", ""), j.get("companyName", ""), j.get("jobGeo", ""),
                 j.get("jobDescription", ""), j.get("url", ""), j.get("pubDate", ""))
    return len(out) - n0


BOARDS = {"remotive": _remotive, "remoteok": _remoteok, "himalayas": _himalayas, "jobicy": _jobicy}


def fetch():
    out, seen = [], set()
    with Http(timeout=30, headers=UA, min_gap=1.0) as client:
        for name, fn in BOARDS.items():
            try:
                scanlog.count(name, fn(client, out, seen))
            except Exception as e:  # noqa: BLE001  (one board failing never stops the others)
                scanlog.error(name, f"{type(e).__name__}: {str(e)[:150]}")
    return out
