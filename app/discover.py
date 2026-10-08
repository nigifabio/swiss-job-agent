"""ATS discovery: find which job-board system each company uses, and add it to the watchlist.

Run on a box with open internet:

    python -m app.discover                              # app/companies.seed.txt
    python -m app.discover app/companies.romandie.txt   # any seed file(s)

Seed file: one company per line; or "Company = https://careers-url" to give the board directly
(recognised: Greenhouse, Lever, Ashby, SmartRecruiters, Workday, Personio, Recruitee,
Workable, Teamtailor). Results are MERGED into the watchlist (existing boards are kept).
A found board is kept only if its declared company name matches (or, where the system
declares none, if the address is the full company name): short-name collisions like
"Four Seasons Garage Doors" or demo boards are rejected. `python -m app.discover --verify`
re-checks an existing watchlist. Workday addresses can't be derived from a name, so only
common patterns are tried; paste the careers URL when you know it.
"""
import os
import re
import sys
import json
import unicodedata
import xml.etree.ElementTree as ET

import httpx

from . import config

UA = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
                    "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"}
WORKDAY_HOSTS = ("wd3", "wd5", "wd1", "wd103")


def slug_candidates(name):
    # transliterate accents: Zürich -> zurich, Genève -> geneve
    name = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode()
    base = re.sub(r"&", " and ", name.strip().lower())
    base = re.sub(r"\b(ag|sa|holding|group|inc|ltd|gmbh|llc|sarl)\b", " ", base)
    base = re.sub(r"[^a-z0-9]+", " ", base).strip()
    words = [w for w in base.split() if w]
    out = []
    if words:
        for c in ("".join(words), "-".join(words), words[0]):
            if c and c not in out:
                out.append(c)
    return out


def _get_json(client, url, **kw):
    r = client.get(url, **kw)
    return r.json() if r.status_code == 200 else None


def _post_json(client, url, body):
    r = client.post(url, json=body)
    return r.json() if r.status_code == 200 else None


def _xml_count(client, url, tag):
    r = client.get(url)
    if r.status_code != 200 or b"<" not in r.content[:200]:
        return None
    try:
        return sum(1 for _ in ET.fromstring(r.content).iter(tag))
    except ET.ParseError:
        return None


PROBES = {
    "greenhouse": lambda c, s: len((_get_json(c, f"https://boards-api.greenhouse.io/v1/boards/{s}/jobs") or {}).get("jobs", [])),
    "lever": lambda c, s: len(_get_json(c, f"https://api.lever.co/v0/postings/{s}", params={"mode": "json"}) or []),
    "ashby": lambda c, s: len((_get_json(c, f"https://api.ashbyhq.com/posting-api/job-board/{s}") or {}).get("jobs") or []),
    "smartrecruiters": lambda c, s: ((_get_json(c, f"https://api.smartrecruiters.com/v1/companies/{s}/postings") or {}).get("totalFound") or 0),
    "personio": lambda c, s: _xml_count(c, f"https://{s}.jobs.personio.de/xml", "position") or 0,
    "recruitee": lambda c, s: len((_get_json(c, f"https://{s}.recruitee.com/api/offers/") or {}).get("offers", [])),
    "workable": lambda c, s: ((_post_json(c, f"https://apply.workable.com/api/v3/accounts/{s}/jobs", {"query": ""}) or {}).get("total") or 0),
    "teamtailor": lambda c, s: _xml_count(c, f"https://{s}.teamtailor.com/jobs.rss", "item") or 0,
}


def _probe_workday(client, slug):
    sites = ["External", slug.capitalize(), f"{slug.capitalize()}_Careers", "Careers", "External_Careers"]
    for wd in WORKDAY_HOSTS:
        for site in sites:
            try:
                d = _post_json(client, f"https://{slug}.{wd}.myworkdayjobs.com/wday/cxs/{slug}/{site}/jobs",
                               {"appliedFacets": {}, "limit": 1, "offset": 0, "searchText": ""})
            except Exception:  # noqa: BLE001
                continue
            if d and d.get("total"):
                return f"{slug}/{wd}/{site}", d["total"]
    return None


URL_PATTERNS = [
    ("greenhouse", r"(?:job-)?boards(?:-api)?\.greenhouse\.io/(?:v1/boards/)?([\w-]+)"),
    ("lever", r"jobs\.lever\.co/([\w.-]+)"),
    ("ashby", r"jobs\.ashbyhq\.com/([\w.-]+)"),
    ("smartrecruiters", r"(?:jobs|careers)\.smartrecruiters\.com/([\w-]+)"),
    ("personio", r"([\w-]+)\.jobs\.personio\.(?:de|com)"),
    ("recruitee", r"([\w-]+)\.recruitee\.com"),
    ("workable", r"apply\.workable\.com/([\w-]+)"),
    ("teamtailor", r"([\w-]+\.teamtailor\.com)"),
]


def from_url(url):
    """(ats, slug) for a careers URL of a supported system, else None."""
    m = re.search(r"https?://([\w-]+)\.(wd\d+)\.myworkdayjobs\.com/(?:[a-z]{2}-[A-Z]{2}/)?([\w-]+)", url)
    if m:
        return "workday", f"{m.group(1)}/{m.group(2)}/{m.group(3)}"
    m = re.search(r"https?://([\w.-]+\.oraclecloud\.com)/hcmUI/CandidateExperience/[\w-]+/sites/([\w-]+)", url)
    if m:
        return "oracle", f"{m.group(1)}/{m.group(2)}"
    m = re.search(r"prospective\.ch/public/v1/(?:medium|careercenter)/(\d+)|/careercenter/(\d+)", url)
    if m:
        return "prospective", m.group(1) or m.group(2)
    m = re.search(r"https?://([\w.-]+)/services/rss/job", url)          # a SuccessFactors career site's feed address
    if m:
        return "successfactors", m.group(1)
    for ats, pat in URL_PATTERNS:
        m = re.search(pat, url)
        if m:
            return ats, m.group(1)
    return None


GENERIC_WORDS = {"careers", "career", "jobs", "job", "ag", "sa", "sarl", "gmbh", "inc", "ltd", "llc", "group",
                 "holding", "the", "company", "co", "switzerland", "suisse", "schweiz", "international"}


def _words(s):
    s = unicodedata.normalize("NFKD", s or "").encode("ascii", "ignore").decode().lower()
    return [w for w in re.sub(r"[^a-z0-9]+", " ", s).split() if w not in GENERIC_WORDS]


def name_matches(searched, board):
    """The board's own company name must be the company we searched for (generic words like
    'Careers', 'SA', 'Group' ignored): 'Four Seasons' != 'Four Seasons Garage Doors'."""
    return bool(_words(searched)) and _words(searched) == _words(board)


def board_name(client, ats, slug):
    """The company name the board itself declares, or None when the system doesn't expose one."""
    try:
        if ats == "greenhouse":
            return (_get_json(client, f"https://boards-api.greenhouse.io/v1/boards/{slug}") or {}).get("name")
        if ats == "smartrecruiters":
            c = (_get_json(client, f"https://api.smartrecruiters.com/v1/companies/{slug}/postings", params={"limit": 1}) or {}).get("content") or []
            return c[0]["company"]["name"] if c else None
        if ats == "recruitee":
            o = (_get_json(client, f"https://{slug}.recruitee.com/api/offers/") or {}).get("offers") or []
            if any("(sample)" in (x.get("title") or "").lower() for x in o):
                return "__demo board__"
            return o[0].get("company_name") if o else None
        if ats == "personio":
            r = client.get(f"https://{slug}.jobs.personio.de/xml")
            return ET.fromstring(r.content).findtext("position/subcompany") if r.status_code == 200 else None
        if ats == "teamtailor":
            r = client.get(f"https://{slug}.teamtailor.com/jobs.rss")
            return ET.fromstring(r.content).findtext("channel/title") if r.status_code == 200 else None
    except Exception:  # noqa: BLE001
        return None
    return None       # lever, ashby, workable, workday: no declared name


def accept(client, name, ats, slug):
    """A hit counts only if the board's declared name matches; for systems without one, only
    if the slug is the full company name (never a first-word guess like 'tag' for TAG Heuer)."""
    declared = board_name(client, ats, slug)
    if declared is not None:
        return name_matches(name, declared)
    full = slug_candidates(name)[:2]            # "tagheuer", "tag-heuer"
    return slug.split("/")[0] in full


def probe(client, name):
    """(ats, slug, n_jobs) for a company name, or None. Hits that belong to another company
    with the same short name are rejected (see accept)."""
    for slug in slug_candidates(name):
        for ats, fn in PROBES.items():
            try:
                n = fn(client, slug)
            except Exception:  # noqa: BLE001
                continue
            if n and accept(client, name, ats, slug):
                return ats, slug, n
    first = (slug_candidates(name) or [None])[0]
    if first:
        hit = _probe_workday(client, first)
        if hit:
            return "workday", hit[0], hit[1]
    return None


def load_watchlist():
    try:
        with open(config.WATCHLIST_PATH) as f:
            return json.load(f)
    except (OSError, ValueError):
        return []


def verify():
    """Re-check every watchlist entry; drop the ones that belong to another company."""
    wl, kept = load_watchlist(), []
    with httpx.Client(timeout=15, headers=UA, follow_redirects=True, trust_env=False) as client:
        for e in wl:
            ok = e.get("verified_url") or accept(client, e["company"], e["ats"], e["slug"])
            print(f"{'ok ' if ok else 'DROP'} {e['company']:34s} {e['ats']:16s} {e['slug']}")
            if ok:
                kept.append(e)
    with open(config.WATCHLIST_PATH, "w") as f:
        json.dump(kept, f, indent=2, ensure_ascii=False)
    print(f"\n{len(wl) - len(kept)} dropped, {len(kept)} kept")


def main(paths):
    wl = load_watchlist()
    have = {(e["ats"], e["slug"]) for e in wl}
    added = 0
    with httpx.Client(timeout=15, headers=UA, follow_redirects=True, trust_env=False) as client:
        for path in paths:
            with open(path) as f:
                lines = f.read().splitlines()
            for line in lines:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                name, _, url = (x.strip() for x in line.partition("="))
                hit = None
                if url:
                    parsed = from_url(url)          # given by a person: trusted as is
                    hit = (*parsed, "?") if parsed else None
                else:
                    hit = probe(client, name)
                if not hit:
                    print(f"--  {name:34s} no supported board{' (unrecognised URL)' if url else ''}")
                    continue
                ats, slug, n = hit
                if (ats, slug) in have:
                    print(f"=   {name:34s} {ats:16s} {slug} (already in watchlist)")
                    continue
                wl.append({"company": name, "ats": ats, "slug": slug, **({"verified_url": True} if url else {})})
                have.add((ats, slug))
                added += 1
                print(f"OK  {name:34s} {ats:16s} {slug} ({n} jobs)")
    with open(config.WATCHLIST_PATH, "w") as f:
        json.dump(wl, f, indent=2, ensure_ascii=False)
    print(f"\n{added} boards added, {len(wl)} in {config.WATCHLIST_PATH}")


if __name__ == "__main__":
    if sys.argv[1:] == ["--verify"]:
        verify()
    else:
        main(sys.argv[1:] or [os.path.join(os.path.dirname(__file__), "companies.seed.txt")])
