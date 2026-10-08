"""Generic ATS provider — pulls public job boards for a watchlist of companies. No API key.
Supported: Greenhouse, Lever, Ashby, SmartRecruiters, Workday, Personio, Recruitee,
Teamtailor, Workable (all verified against live boards, 2026-09-24), and the systems of large
Swiss employers and administrations: SAP SuccessFactors career sites (RSS), Prospective
(JSON) and Oracle Recruiting Cloud (JSON), verified 2026-10-08.

Boards crawled = the person's watchlist + app/watchlists/public.json (public-sector and other
large Swiss employers everybody gets; PUBLIC_BOARDS=0 turns that off).

Filters each posting by:
  - title keywords  (config.TITLE_KEYWORDS, seniority by default)
  - location        (config.LOCATION_KEYWORDS, or remote/EU if ALLOW_REMOTE)
  - language        (config.LANGUAGES, default English + Italian)

The watchlist (app/watchlist.json) is produced by app/discover.py, which
probes each company against all four ATSs and records the ones that resolve.
"""
import os
import re
import json
import xml.etree.ElementTree as ET

from .. import config, enrich, filters, scanlog, store
from ..http import Http
from ..normalize import content_hash

_seen = set()          # hashes emitted in the current scan (boards repeat postings)
SR_PAGE = 100          # SmartRecruiters page size (API max)
SR_MAX_PAGES = 10

_strip = filters.strip_html


def _emit(out, source, company, title, location, desc, url, posted=""):
    if not filters.title_ok(title):
        return
    if not filters.location_ok(location, desc):
        return
    if not filters.language_ok(title, desc):
        return
    h = content_hash(title, company, location)
    if h in _seen:
        return
    _seen.add(h)
    out.append({
        "source": source, "title": title, "company": company,
        "location": location, "description": (desc or "")[:20000], "url": url,
        "salary": "", "posted_at": str(posted or ""),
        "content_hash": content_hash(title, company, location),
    })


def _greenhouse(client, slug, company, out):
    for j in client.json(f"https://boards-api.greenhouse.io/v1/boards/{slug}/jobs", params={"content": "true"}).get("jobs", []):
        _emit(out, f"gh:{slug}", company, j.get("title", ""),
              (j.get("location") or {}).get("name", ""), enrich.html_to_text(j.get("content", "")),
              j.get("absolute_url", ""), j.get("updated_at", ""))


def _lever(client, slug, company, out):
    for j in client.json(f"https://api.lever.co/v0/postings/{slug}", params={"mode": "json"}):
        cat = j.get("categories") or {}
        _emit(out, f"lever:{slug}", company, j.get("text", ""), cat.get("location", ""),
              j.get("descriptionPlain", ""), j.get("hostedUrl", ""), j.get("createdAt", ""))


def _ashby(client, slug, company, out):
    data = client.json(f"https://api.ashbyhq.com/posting-api/job-board/{slug}", params={"includeCompensation": "true"})
    for j in data.get("jobs", []):
        _emit(out, f"ashby:{slug}", company, j.get("title", ""), j.get("location", ""),
              enrich.html_to_text(j.get("descriptionHtml", "") or j.get("descriptionPlain", "")),
              j.get("jobUrl", "") or j.get("applyUrl", ""), j.get("publishedAt", ""))


def _sr_description(client, slug, jid):
    """The list endpoint has no text; fetch the ad only for postings that passed the filters."""
    try:
        ad = client.json(f"https://api.smartrecruiters.com/v1/companies/{slug}/postings/{jid}")
        sections = (ad.get("jobAd") or {}).get("sections") or {}
        parts = (enrich.html_to_text((sections.get(k) or {}).get("text", ""))
                 for k in ("companyDescription", "jobDescription", "qualifications", "additionalInformation"))
        return "\n\n".join(p for p in parts if p)
    except Exception:  # noqa: BLE001
        return ""


def _smartrecruiters(client, slug, company, out, known=frozenset()):
    """Paged list (100 per page); the ad text is fetched only for new postings that pass the filters."""
    for page in range(SR_MAX_PAGES):
        data = client.json(f"https://api.smartrecruiters.com/v1/companies/{slug}/postings",
                           params={"limit": SR_PAGE, "offset": page * SR_PAGE})
        content = data.get("content", [])
        for j in content:
            loc = j.get("location") or {}
            locstr = ", ".join(x for x in [loc.get("city"), loc.get("country")] if x)
            if loc.get("remote"):
                locstr = (locstr + " (remote)").strip()
            title = j.get("name", "")
            if not (filters.title_ok(title) and filters.location_ok(locstr)):
                continue
            h = content_hash(title, company, locstr)
            if h in known or h in _seen:
                continue          # already stored or already seen this scan: skip the detail request
            _emit(out, f"sr:{slug}", company, title, locstr, _sr_description(client, slug, j.get("id", "")),
                  f"https://jobs.smartrecruiters.com/{slug}/{j.get('id', '')}", j.get("releasedDate", ""))
        if len(content) < SR_PAGE or (page + 1) * SR_PAGE >= (data.get("totalFound") or 0):
            break


def _recruitee(client, slug, company, out, known=frozenset()):
    for j in client.json(f"https://{slug}.recruitee.com/api/offers/").get("offers", []):
        loc = ", ".join(x for x in (j.get("city") or j.get("location"), j.get("country")) if x)
        if j.get("remote"):
            loc = (loc + " (remote)").strip()
        _emit(out, f"recruitee:{slug}", j.get("company_name") or company, j.get("title", ""), loc,
              enrich.html_to_text(j.get("description", "")), j.get("careers_url", ""), j.get("published_at", ""))


def _personio(client, slug, company, out, known=frozenset()):
    """XML feed; host .de and .com serve the same data."""
    root = ET.fromstring(client.get(f"https://{slug}.jobs.personio.de/xml").content)
    for pos in root.iter("position"):
        offices = [pos.findtext("office") or ""] + [o.text or "" for o in pos.iterfind("additionalOffices/office")]
        desc = "\n\n".join(enrich.html_to_text((d.findtext("name") or "") + "\n" + (d.findtext("value") or ""))
                           for d in pos.iter("jobDescription"))
        _emit(out, f"personio:{slug}", pos.findtext("subcompany") or company, pos.findtext("name") or "",
              ", ".join(o for o in offices if o), desc,
              f"https://{slug}.jobs.personio.de/job/{pos.findtext('id')}", pos.findtext("createdAt") or "")


TT = "{https://teamtailor.com/locations}"


def _teamtailor(client, slug, company, out, known=frozenset()):
    """RSS feed of the career site; slug is the host ("acme.teamtailor.com" or "careers.acme.ch")."""
    host = slug if "." in slug else f"{slug}.teamtailor.com"
    root = ET.fromstring(client.get(f"https://{host}/jobs.rss").content)
    for item in root.iter("item"):
        locs = [", ".join(x for x in (l.findtext(f"{TT}city"), l.findtext(f"{TT}country")) if x)
                for l in item.iter(f"{TT}location")]
        loc = "; ".join(l for l in locs if l)
        if (item.findtext("remoteStatus") or "").lower() in ("fully", "remote"):
            loc = (loc + " (remote)").strip()
        _emit(out, f"teamtailor:{host}", company, item.findtext("title") or "", loc,
              enrich.html_to_text(item.findtext("description") or ""), item.findtext("link") or "",
              item.findtext("pubDate") or "")


def _workable(client, slug, company, out, known=frozenset()):
    data = client.json(f"https://apply.workable.com/api/v3/accounts/{slug}/jobs", method="POST",
                       json={"query": "", "location": [], "department": [], "worktype": [], "remote": []})
    for j in data.get("results", []):
        loc = j.get("location") or {}
        locstr = ", ".join(x for x in (loc.get("city"), loc.get("country")) if x)
        if j.get("remote"):
            locstr = (locstr + " (remote)").strip()
        title = j.get("title", "")
        if not (filters.title_ok(title) and filters.location_ok(locstr)):
            continue
        h = content_hash(title, company, locstr)
        if h in known or h in _seen:
            continue
        try:
            d = client.json(f"https://apply.workable.com/api/v2/accounts/{slug}/jobs/{j['shortcode']}")
            desc = "\n\n".join(enrich.html_to_text(d.get(k) or "") for k in ("description", "requirements") if d.get(k))
        except Exception:  # noqa: BLE001
            desc = ""
        _emit(out, f"workable:{slug}", company, title, locstr, desc,
              f"https://apply.workable.com/{slug}/j/{j['shortcode']}/", j.get("published", ""))


WORKDAY_PAGE = 20
WORKDAY_MAX_PAGES = int(os.environ.get("WORKDAY_MAX_PAGES", "15"))


def _workday(client, slug, company, out, known=frozenset()):
    """slug = "tenant/wdN/Site" (from the career URL https://tenant.wdN.myworkdayjobs.com/Site)."""
    tenant, wd, site = slug.split("/")
    base = f"https://{tenant}.{wd}.myworkdayjobs.com"
    api = f"{base}/wday/cxs/{tenant}/{site}"
    for page in range(WORKDAY_MAX_PAGES):
        data = client.json(f"{api}/jobs", method="POST",
                           json={"appliedFacets": {}, "limit": WORKDAY_PAGE, "offset": page * WORKDAY_PAGE, "searchText": ""})
        posts = data.get("jobPostings") or []
        for j in posts:
            title, loc = j.get("title", ""), j.get("locationsText", "")
            if not (filters.title_ok(title) and filters.location_ok(loc)):
                continue
            h = content_hash(title, company, loc)
            if h in known or h in _seen:
                continue
            try:
                info = client.json(f"{api}{j['externalPath']}").get("jobPostingInfo") or {}
            except Exception:  # noqa: BLE001
                info = {}
            _emit(out, f"workday:{tenant}", company, title, info.get("location") or loc,
                  enrich.html_to_text(info.get("jobDescription") or ""),
                  info.get("externalUrl") or f"{base}/{site}{j['externalPath']}", info.get("postedOn", ""))
        if len(posts) < WORKDAY_PAGE or (page + 1) * WORKDAY_PAGE >= (data.get("total") or 0):
            break


# ---- systems of large Swiss employers and administrations ------------------------------------
SF_LOCALES = {"fr": "fr_FR", "de": "de_DE", "it": "it_IT", "en": "en_US"}
SF_TERMS = 12                  # search terms tried on a SuccessFactors site (20 newest results each)
PAGES_MAX = 12


def _successfactors(client, slug, company, out, known=frozenset()):
    """SAP SuccessFactors career site; slug is its host ("careers.epfl.ch"). The site's RSS feed
    gives the 20 newest jobs, and 20 per keyword search: one feed per region and search term of the person.
    Verified 2026-10-08: GET https://{host}/services/rss/job/?locale=fr_FR[&keywords=(term)] ->
    <item><title>Title (Town, CC)</title><description>html</description><pubDate/><link/></item>"""
    locale = next((SF_LOCALES[l] for l in config.LANGUAGES if l in SF_LOCALES), "en_US")
    links = set()
    # the keyword search also matches the place ("Vaud"): the person's regions bring the local jobs of
    # employers with thousands of postings
    terms = [t for t in list(config.WHERE) + list(config.SEARCH_TERMS) if t.strip()][:SF_TERMS]
    for n, kw in enumerate([""] + terms):
        params = {"locale": locale}
        if kw:
            params["keywords"] = f"({kw})"
        try:
            root = ET.fromstring(client.get(f"https://{slug}/services/rss/job/", params=params).content)
        except Exception:  # noqa: BLE001
            if n == 0:                 # the site itself is unreachable or changed: report it
                raise
            continue                   # one search term the site doesn't like is not a failure
        for item in root.iter("item"):
            link = (item.findtext("link") or "").split("?")[0]
            if not link or link in links:
                continue
            links.add(link)
            title, loc = (item.findtext("title") or "").strip(), ""
            m = re.match(r"^(.*\S)\s*\(([^()]*)\)$", title)       # "Title (Lausanne, CH)"
            if m:
                title, loc = m.group(1), m.group(2)
            _emit(out, f"sf:{slug}", company, title, loc, enrich.html_to_text(item.findtext("description") or ""),
                  link, item.findtext("pubDate") or "")


def _prospective(client, slug, company, out, known=frozenset()):
    """Prospective career centre (many Swiss administrations and companies); slug is the "medium" id,
    the number in the career page's address or scripts ("/careercenter/1000625/").
    Verified 2026-10-08: GET https://ohws.prospective.ch/public/v1/medium/{id}/jobs?lang=&limit=&offset=
    -> {total, jobs: [{title, start_date, links{directlink}, attributes{arbeitsort[]}, szas{sza_tasks, ...}}]}"""
    lang = next((l for l in config.LANGUAGES if l in SF_LOCALES), "fr")
    offset = 0
    for _ in range(PAGES_MAX):
        d = client.json(f"https://ohws.prospective.ch/public/v1/medium/{slug}/jobs",
                        params={"lang": lang, "limit": 100, "offset": offset})
        jobs = d.get("jobs") or []
        for j in jobs:
            sz, at = j.get("szas") or {}, j.get("attributes") or {}
            loc = sz.get("sza_location.city") or ", ".join(at.get("arbeitsort") or [])
            desc = "\n\n".join(enrich.html_to_text(sz[k]) for k in
                               ("sza_tasks", "sza_requirements", "sza_company_profil", "sza_benefits") if sz.get(k))
            units = sorted((k, v) for k, v in at.items() if k.startswith("verwaltungseinheit") and v)
            unit = units[-1][1][0] if units else ""              # the most specific one: the office, not the department
            _emit(out, f"prospective:{slug}", f"{company} ({unit})" if unit else company, j.get("title", ""), loc, desc,
                  (j.get("links") or {}).get("directlink") or sz.get("sza_apply_link", ""), j.get("start_date", ""))
        offset += len(jobs)
        if not jobs or offset >= int(d.get("total") or 0):
            break


def _oracle(client, slug, company, out, known=frozenset()):
    """Oracle Recruiting Cloud candidate site; slug = "host/site" from the career address
    https://{host}/hcmUI/CandidateExperience/fr/sites/{site}. The list has no ad text: the ad is
    fetched only for new postings that pass the filters.
    Verified 2026-10-08: GET https://{host}/hcmRestApi/resources/latest/recruitingCEJobRequisitions
      ?onlyData=true&finder=findReqs;siteNumber={site},limit=25,offset=0,sortBy=POSTING_DATES_DESC
    -> {items: [{TotalJobsCount, requisitionList: [{Id, Title, PostedDate, PrimaryLocation, ShortDescriptionStr}]}]}
    detail: .../recruitingCEJobRequisitionDetails?onlyData=true&expand=all&finder=ById;Id="{id}",siteNumber={site}"""
    host, _, site = slug.partition("/")
    base = f"https://{host}/hcmRestApi/resources/latest"
    lang = next((l for l in config.LANGUAGES if l in SF_LOCALES), "fr")
    offset = 0
    for _ in range(PAGES_MAX):
        d = client.json(f"{base}/recruitingCEJobRequisitions", params={
            "onlyData": "true", "expand": "requisitionList.secondaryLocations",       # no list without the expand
            "finder": f"findReqs;siteNumber={site},limit=25,offset={offset},sortBy=POSTING_DATES_DESC"})
        page = (d.get("items") or [{}])[0]
        reqs = page.get("requisitionList") or []
        for r in reqs:
            title, loc, desc = r.get("Title", ""), r.get("PrimaryLocation", ""), r.get("ShortDescriptionStr") or ""
            if (filters.title_ok(title) and filters.location_ok(loc, desc)
                    and content_hash(title, company, loc) not in known):
                try:
                    det = (client.json(f"{base}/recruitingCEJobRequisitionDetails", params={
                        "onlyData": "true", "expand": "all",
                        "finder": f'ById;Id="{r.get("Id")}",siteNumber={site}'}).get("items") or [{}])[0]
                    desc = "\n\n".join(enrich.html_to_text(det[k]) for k in (
                        "ExternalDescriptionStr", "ExternalResponsibilitiesStr", "ExternalQualificationsStr",
                        "OrganizationDescriptionStr") if det.get(k)) or desc
                except Exception:  # noqa: BLE001  (keep the posting with its short text)
                    pass
            _emit(out, f"oracle:{host.split('.')[0]}", company, title, loc, desc,
                  f"https://{host}/hcmUI/CandidateExperience/{lang}/sites/{site}/job/{r.get('Id')}", r.get("PostedDate", ""))
        offset += len(reqs)
        if not reqs or offset >= int(page.get("TotalJobsCount") or 0):
            break


DISPATCH = {
    "successfactors": _successfactors, "prospective": _prospective, "oracle": _oracle,
    "greenhouse": _greenhouse, "lever": _lever,
    "ashby": _ashby, "smartrecruiters": _smartrecruiters,
    "workday": _workday, "personio": _personio, "recruitee": _recruitee,
    "teamtailor": _teamtailor, "workable": _workable,
}
NEEDS_KNOWN = {_smartrecruiters, _workday, _workable, _personio, _recruitee, _teamtailor,
               _successfactors, _prospective, _oracle}
PUBLIC_BOARDS = os.path.join(os.path.dirname(os.path.dirname(__file__)), "watchlists", "public.json")


def _public_boards():
    """Large Swiss employers and administrations everybody gets, on top of their own watchlist."""
    if os.environ.get("PUBLIC_BOARDS", "1") == "0":
        return []
    try:
        with open(PUBLIC_BOARDS) as f:
            return json.load(f)
    except (OSError, ValueError):
        return []


def _load_watchlist():
    path = config.WATCHLIST_PATH
    if not os.path.exists(path):
        return []
    try:
        with open(path) as f:
            return json.load(f)
    except Exception as e:  # noqa: BLE001
        print(f"[ats] bad watchlist {path}: {e}")
        return []


def fetch():
    wl = _load_watchlist()
    have = {(e.get("ats"), e.get("slug")) for e in wl}
    wl = wl + [e for e in _public_boards() if (e.get("ats"), e.get("slug")) not in have]
    if not wl:
        scanlog.error("ats", "watchlist empty; run: docker compose run --rm scheduler python -m app.discover")
        return []
    out, known = [], store.known_hashes()
    _seen.clear()
    with Http(timeout=20, min_gap=0.2) as client:
        for e in wl:
            fn = DISPATCH.get(e.get("ats"))
            if not fn:
                continue
            try:
                if fn in NEEDS_KNOWN:
                    fn(client, e["slug"], e.get("company", e["slug"]), out, known)
                else:
                    fn(client, e["slug"], e.get("company", e["slug"]), out)
            except Exception as ex:  # noqa: BLE001  (one bad board never stops the others)
                scanlog.error("ats", f"{e.get('ats')}:{e.get('slug')}: {ex}")
    scanlog.count("ats", len(out))
    print(f"[ats] {len(out)} matching postings from {len(wl)} boards")
    return out
