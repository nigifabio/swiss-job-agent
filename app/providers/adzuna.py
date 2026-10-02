import httpx

from .. import config, filters, scanlog
from ..http import Http
from ..normalize import content_hash

BASE = "https://api.adzuna.com/v1/api/jobs/{country}/search/1"


def fetch():
    """Pull postings from the official Adzuna Switzerland API."""
    if not (config.ADZUNA_APP_ID and config.ADZUNA_APP_KEY):
        print("[adzuna] no API key set; skipping")
        return []

    out = []
    terms = config.SEARCH_TERMS or [""]
    url = BASE.format(country=config.ADZUNA_COUNTRY)

    with Http(timeout=30, min_gap=0.5) as client:
        for term, where in [(t, w) for t in terms for w in config.WHERE]:
            params = {
                "app_id": config.ADZUNA_APP_ID,
                "app_key": config.ADZUNA_APP_KEY,
                "results_per_page": config.RESULTS_PER_PAGE,
                "what": term,
                "where": where,
                "content-type": "application/json",
            }
            try:
                data = client.json(url, params=params)
            except httpx.HTTPStatusError as e:
                # never log e itself: the request URL carries app_key
                scanlog.error("adzuna", f"HTTP {e.response.status_code} for '{term}' in '{where}'")
                if e.response.status_code in (401, 403):
                    break         # bad key: every other query would fail the same way
                continue
            except Exception as e:  # noqa: BLE001
                scanlog.error("adzuna", f"{type(e).__name__} for '{term}' in '{where}'")
                continue

            for j in data.get("results", []):
                title = filters.strip_html(j.get("title", ""))
                desc = filters.strip_html(j.get("description", ""))
                if not (filters.title_ok(title) and filters.language_ok(title, desc)):
                    continue
                company = (j.get("company") or {}).get("display_name", "")
                location = (j.get("location") or {}).get("display_name", "")
                salary = ""
                if j.get("salary_min"):
                    lo = int(j["salary_min"])
                    hi = int(j.get("salary_max") or lo)
                    salary = f"{lo:,}-{hi:,}".replace(",", "'")
                out.append({
                    "source": "adzuna",
                    "title": title,
                    "company": company,
                    "location": location,
                    "description": desc,
                    "url": j.get("redirect_url", ""),
                    "salary": salary,
                    "posted_at": j.get("created", ""),
                    "content_hash": content_hash(title, company, location),
                })
    scanlog.count("adzuna", len(out))
    print(f"[adzuna] kept {len(out)} postings across {len(terms)} term(s) x {len(config.WHERE)} region(s)")
    return out
