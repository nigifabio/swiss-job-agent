"""jobs.ch / jobup.ch crawler (JobCloud platform) — GRAY AREA, opt-in.

Uses the public search backend the sites' own frontends call: no official API,
against their ToS, may change without notice. Enable by adding 'jobup' to PROVIDERS.

API shape (verified 2026): GET https://www.<site>/api/v1/public/search
  ?query=&location=&rows=&page=   rows is capped at 20 (40 -> 422);
  location is a plain string ("Vaud"). Documents: title, company_name, place,
  preview, publication_date, _links.detail_{fr,en,de}.href
"""
import os

from .. import config, filters, scanlog
from ..http import Http
from ..normalize import content_hash

SITES = [s.strip() for s in os.environ.get("JOBCLOUD_SITES", "jobs.ch,jobup.ch").split(",") if s.strip()]
ROWS = min(int(os.environ.get("JOBCLOUD_ROWS", "20")), 20)
PAGES = int(os.environ.get("JOBCLOUD_PAGES", "2"))
GAP = float(os.environ.get("JOBCLOUD_GAP", "0.7"))   # seconds between requests to one site

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/124.0 Safari/537.36",
    "Accept": "application/json",
}


def _url(site, d):
    links = d.get("_links") or {}
    for k in ("detail_fr", "detail_en", "detail_de"):
        href = (links.get(k) or {}).get("href")
        if href:
            return href
    sid = d.get("slug") or d.get("job_id")
    return f"https://www.{site}/fr/offres-emplois/detail/{sid}/" if sid else f"https://www.{site}/"


def fetch():
    out, seen = [], set()
    terms = config.SEARCH_TERMS or [""]
    with Http(timeout=20, headers=HEADERS, min_gap=GAP) as client:
        for site in SITES:
            base = f"https://www.{site}/api/v1/public/search"
            got = 0
            for term in terms:
                for where in config.WHERE:
                    for page in range(1, PAGES + 1):
                        params = {"query": term, "location": where, "rows": ROWS, "page": page}
                        try:
                            data = client.json(base, params=params)
                        except Exception as e:  # noqa: BLE001
                            scanlog.error(site, f"'{term}' {where} p{page}: {type(e).__name__}: {str(e)[:120]}")
                            break
                        if not isinstance(data, dict) or "documents" not in data:
                            # the site changed its API: say so instead of silently finding nothing
                            scanlog.error(site, "unexpected response shape (no 'documents'); the API may have changed")
                            break
                        docs = data["documents"] or []
                        for d in docs:
                            title = filters.strip_html(d.get("title", ""))
                            company = d.get("company_name", "")
                            place = d.get("place", "") or where
                            preview = filters.strip_html(d.get("preview", ""))
                            ch = content_hash(title, company, place)
                            if ch in seen or not filters.title_ok(title):
                                continue
                            if not filters.language_ok(title, preview):
                                continue
                            seen.add(ch)
                            got += 1
                            out.append({
                                "source": site, "title": title, "company": company,
                                "location": place, "description": preview, "url": _url(site, d),
                                "salary": "", "posted_at": d.get("publication_date", ""),
                                "content_hash": ch,
                            })
                        if len(docs) < ROWS:
                            break
            scanlog.count(site, got)
            print(f"[jobup] {site}: {got} postings")
    return out
