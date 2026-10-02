"""Job-Room (work.swiss), the national job portal run by SECO: public search, no key.

Uses the search backend of www.job-room.ch (same as the site). Only publicly visible ads:
jobs under the reporting obligation (visible to RAV-registered job seekers first) need the
person's own Job-Room login and stay manual. Ads Job-Room republishes from jobs.ch/jobup.ch
(externalUrl on those sites, company shown as "Jobup") are skipped: the jobup provider
brings them with the real employer. Job-Room adds what employers and the RAV post directly.

Verified 2026-09-24: POST /jobadservice/api/jobAdvertisements/_search?page=&size=&sort=date_desc
body {keywords[], cantonCodes[], onlineSince, displayRestricted, ...} ->
[{jobAdvertisement: {id, status, jobContent: {jobDescriptions[{languageIsoCode,title,description}],
  company{name,city}, location{city,cantonCode}, employment{workloadPercentageMin/Max}, externalUrl}}}]
"""
import os

from .. import config, enrich, filters, scanlog
from ..http import Http
from ..normalize import content_hash

URL = "https://www.job-room.ch/jobadservice/api/jobAdvertisements/_search"
PAGE = 50
PAGES = int(os.environ.get("JOBROOM_PAGES", "2"))
DAYS = int(os.environ.get("JOBROOM_DAYS", "30"))          # ads online in the last N days
CANTONS = {"vaud": "VD", "geneve": "GE", "genève": "GE", "geneva": "GE", "valais": "VS", "fribourg": "FR",
           "neuchatel": "NE", "neuchâtel": "NE", "jura": "JU", "bern": "BE", "berne": "BE", "zurich": "ZH",
           "zürich": "ZH", "basel": "BS", "ticino": "TI", "tessin": "TI", "lucerne": "LU", "luzern": "LU",
           "zug": "ZG", "st. gallen": "SG", "aargau": "AG", "argovie": "AG", "solothurn": "SO"}
REPUBLISHED = ("jobup.ch", "jobs.ch", "topjobs.ch", "jobscout24.ch")
HEADERS = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
                         "(KHTML, like Gecko) Chrome/124.0 Safari/537.36",
           "Accept": "application/json", "Content-Type": "application/json"}


def cantons():
    """JOBROOM_CANTONS (e.g. "VD,GE"), else derived from WHERE ("Vaud;Genève" -> VD, GE)."""
    if config.JOBROOM_CANTONS:
        return [c.strip().upper() for c in config.JOBROOM_CANTONS if c.strip()]
    return sorted({CANTONS[w.strip().lower()] for w in config.WHERE if w.strip().lower() in CANTONS})


def _pick(descs):
    """The ad's text in an accepted language, else the first one."""
    for d in descs:
        if (d.get("languageIsoCode") or "").lower() in config.LANGUAGES:
            return d
    return descs[0] if descs else {}


def fetch():
    out, seen = [], set()
    codes = cantons()
    terms = config.SEARCH_TERMS or [""]
    with Http(timeout=25, headers=HEADERS, min_gap=0.7) as client:
        for term in terms:
            for page in range(PAGES):
                body = {"workloadPercentageMin": 0, "workloadPercentageMax": 100, "permanent": None,
                        "companyName": None, "onlineSince": DAYS, "displayRestricted": False,
                        "professionCodes": [], "keywords": [term] if term else [],
                        "communalCodes": [], "cantonCodes": codes}
                try:
                    data = client.json(URL, method="POST", params={"page": page, "size": PAGE, "sort": "date_desc"}, json=body)
                except Exception as e:  # noqa: BLE001
                    scanlog.error("job-room", f"'{term}' p{page}: {type(e).__name__}: {str(e)[:120]}")
                    break
                if not isinstance(data, list):
                    scanlog.error("job-room", "unexpected response shape (not a list); the API may have changed")
                    break
                for item in data:
                    ad = (item or {}).get("jobAdvertisement") or {}
                    c = ad.get("jobContent") or {}
                    ext = (c.get("externalUrl") or "").lower()
                    if any(f"{d}/" in ext or ext.endswith(d) for d in REPUBLISHED):
                        continue          # republished from JobCloud: the jobup provider has the original
                    d = _pick(c.get("jobDescriptions") or [])
                    title = filters.strip_html(d.get("title", ""))
                    company = ((c.get("company") or {}).get("name") or "").strip()
                    loc = c.get("location") or {}
                    place = ", ".join(x for x in (loc.get("city"), loc.get("cantonCode")) if x)
                    desc = enrich.html_to_text(d.get("description", ""))
                    h = content_hash(title, company, place)
                    if not ad.get("id") or h in seen or not filters.title_ok(title):
                        continue
                    if not filters.language_ok(title, desc):
                        continue
                    seen.add(h)
                    out.append({"source": "job-room", "title": title, "company": company, "location": place,
                                "description": desc, "url": f"https://www.job-room.ch/job-search/{ad['id']}",
                                "salary": "", "posted_at": ad.get("createdTime", ""), "content_hash": h})
                if len(data) < PAGE:
                    break
    scanlog.count("job-room", len(out))
    return out
