"""Careerjet (aggregator), official API, needs a free key: CAREERJET_API_KEY (register at
careerjet.com partners). Silent until the key is set.

Verified 2026-09-24 only up to authentication: GET https://search.api.careerjet.net/v4/query
with the key as HTTP Basic username (empty password); without it -> 401. The results shape
below follows Careerjet's documentation (jobs[{title, company, locations, description, url,
date, salary}]) and is UNVERIFIED until a real key is used: an unexpected shape is reported
on the dashboard instead of silently finding nothing.
"""
import os

import httpx

from .. import config, enrich, filters, scanlog
from ..http import Http
from ..normalize import content_hash

URL = "https://search.api.careerjet.net/v4/query"
LOCALE = os.environ.get("CAREERJET_LOCALE", "fr_CH")


def fetch():
    key = os.environ.get("CAREERJET_API_KEY", "")
    if not key:
        return []
    out, seen = [], set()
    with Http(timeout=30, min_gap=0.5) as client:
        client.client.auth = httpx.BasicAuth(key, "")
        for term in config.SEARCH_TERMS or [""]:
            for where in config.WHERE:
                try:
                    data = client.json(URL, params={"locale_code": LOCALE, "keywords": term, "location": where,
                                                    "page_size": 50, "page": 1})
                except httpx.HTTPStatusError as e:
                    scanlog.error("careerjet", f"HTTP {e.response.status_code} for '{term}' in '{where}'")
                    if e.response.status_code in (401, 403):
                        return out
                    continue
                except Exception as e:  # noqa: BLE001
                    scanlog.error("careerjet", f"{type(e).__name__} for '{term}' in '{where}'")
                    continue
                if not isinstance(data, dict) or not isinstance(data.get("jobs"), list):
                    scanlog.error("careerjet", "unexpected response shape (no 'jobs' list); check the API")
                    return out
                for j in data["jobs"]:
                    title = filters.strip_html(j.get("title", ""))
                    company, loc = j.get("company", ""), j.get("locations", "") or where
                    desc = enrich.html_to_text(j.get("description", ""))
                    h = content_hash(title, company, loc)
                    if h in seen or not filters.title_ok(title) or not filters.language_ok(title, desc):
                        continue
                    seen.add(h)
                    out.append({"source": "careerjet", "title": title, "company": company, "location": loc,
                                "description": desc, "url": j.get("url", ""), "salary": j.get("salary", ""),
                                "posted_at": j.get("date", ""), "content_hash": h})
    scanlog.count("careerjet", len(out))
    return out
