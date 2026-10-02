"""Jooble (aggregator), official API, needs a free key: JOOBLE_API_KEY (jooble.org/api/about).
Silent until the key is set.

POST https://jooble.org/api/<key> {"keywords", "location", "page"} -> {"totalCount",
"jobs": [{"title","location","snippet","salary","source","type","link","company","updated","id"}]}
per Jooble's documentation; UNVERIFIED until a real key is used (without one the endpoint sits
behind a bot check). An unexpected shape is reported on the dashboard.
"""
import os

import httpx

from .. import config, enrich, filters, scanlog
from ..http import Http
from ..normalize import content_hash


def fetch():
    key = os.environ.get("JOOBLE_API_KEY", "")
    if not key:
        return []
    out, seen = [], set()
    with Http(timeout=30, min_gap=0.5) as client:
        for term in config.SEARCH_TERMS or [""]:
            for where in config.WHERE:
                try:
                    data = client.json(f"https://jooble.org/api/{key}", method="POST",
                                       json={"keywords": term, "location": where, "page": 1})
                except httpx.HTTPStatusError as e:
                    # never log e itself: the URL carries the key
                    scanlog.error("jooble", f"HTTP {e.response.status_code} for '{term}' in '{where}'")
                    if e.response.status_code in (401, 403):
                        return out
                    continue
                except Exception as e:  # noqa: BLE001
                    scanlog.error("jooble", f"{type(e).__name__} for '{term}' in '{where}'")
                    continue
                if not isinstance(data, dict) or not isinstance(data.get("jobs"), list):
                    scanlog.error("jooble", "unexpected response shape (no 'jobs' list); check the API")
                    return out
                for j in data["jobs"]:
                    title = filters.strip_html(j.get("title", ""))
                    company, loc = j.get("company", ""), j.get("location", "") or where
                    desc = enrich.html_to_text(j.get("snippet", ""))
                    h = content_hash(title, company, loc)
                    if h in seen or not filters.title_ok(title) or not filters.language_ok(title, desc):
                        continue
                    seen.add(h)
                    out.append({"source": "jooble", "title": title, "company": company, "location": loc,
                                "description": desc, "url": j.get("link", ""), "salary": j.get("salary", ""),
                                "posted_at": j.get("updated", ""), "content_hash": h})
    scanlog.count("jooble", len(out))
    return out
