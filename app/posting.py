"""Add a job posting the person found: read it from its link (or from pasted text), then say what their
search is missing to find postings like it.

The link is fetched by the server, so the address is checked first (see check_url): only http(s) on the
usual ports, and never a loopback, private, link-local or otherwise non-public address, also after each
redirect. The connection goes to the address that was checked, so a name can't change its answer between
the check and the request."""
import ipaddress
import json
import re
import socket
from html import unescape
from urllib.parse import urljoin, urlsplit

import httpx

from . import config, enrich, filters, lang, normalize, places, profiles, roles, skills
from .commute import town

TRANSPORT = None                # tests: httpx.MockTransport(handler)
MAX_BYTES = 3_000_000           # a posting page is far smaller; the rest is cut off
MAX_REDIRECTS = 4
TIMEOUT = 10
PORTS = (80, 443)
LIMITS = {"title": 200, "company": 120, "location": 120, "description": 30000}
TEXT_TYPES = ("text/", "application/xhtml+xml", "application/ld+json", "application/json")


class PostingError(Exception):
    """code: "blocked" (the address is not allowed), "fetch" (could not be fetched), "empty" (nothing to read)."""

    def __init__(self, code):
        super().__init__(code)
        self.code = code


def _getaddrinfo(host, port):
    return socket.getaddrinfo(host, port, type=socket.SOCK_STREAM)


def _public(ip):
    ip = ipaddress.ip_address(ip)
    if isinstance(ip, ipaddress.IPv6Address) and ip.ipv4_mapped:         # ::ffff:127.0.0.1 is 127.0.0.1
        ip = ip.ipv4_mapped
    bad = (ip.is_loopback, ip.is_private, ip.is_link_local, ip.is_multicast, ip.is_reserved, ip.is_unspecified, not ip.is_global)
    return not any(bad)


def check_url(url):
    """(host, port, address) the link may be fetched from; PostingError("blocked") when it may not."""
    try:
        parts = urlsplit((url or "").strip())
        host, port = parts.hostname, parts.port
    except ValueError:
        raise PostingError("blocked")
    if parts.scheme not in ("http", "https") or not host or parts.username is not None or parts.password is not None:
        raise PostingError("blocked")
    port = port or (443 if parts.scheme == "https" else 80)
    if port not in PORTS:
        raise PostingError("blocked")
    try:
        ipaddress.ip_address(host)
        found = [host]
    except ValueError:
        try:
            found = [a[4][0].split("%")[0] for a in _getaddrinfo(host, port)]
        except OSError:
            raise PostingError("fetch")
    if not found or not all(_public(a) for a in found):               # one private answer is enough to refuse
        raise PostingError("blocked")
    return host, port, found[0]


def fetch_page(url):
    """(html text, final address) of one page. Follows a few redirects, checking each target; text only,
    at most MAX_BYTES, TIMEOUT seconds per request. Raises PostingError."""
    with httpx.Client(transport=TRANSPORT, timeout=TIMEOUT, follow_redirects=False, headers=enrich.HEADERS) as client:
        for _ in range(MAX_REDIRECTS + 1):
            host, port, ip = check_url(url)
            parts = urlsplit(url)
            netloc = f"[{ip}]" if ":" in ip else ip
            netloc += f":{port}" if parts.port else ""
            pinned = parts._replace(netloc=netloc).geturl()
            hosthdr = host if not parts.port else f"{host}:{parts.port}"
            try:
                with client.stream("GET", pinned, headers={"Host": hosthdr}, extensions={"sni_hostname": host}) as r:
                    if r.status_code in (301, 302, 303, 307, 308) and r.headers.get("location"):
                        url = urljoin(url, r.headers["location"])
                        continue
                    if r.status_code >= 400:
                        raise PostingError("fetch")
                    ctype = r.headers.get("content-type", "text/html").lower()
                    if not ctype.startswith(TEXT_TYPES):
                        raise PostingError("fetch")
                    body = bytearray()
                    for chunk in r.iter_bytes():
                        body += chunk
                        if len(body) >= MAX_BYTES:
                            break
            except httpx.HTTPError:
                raise PostingError("fetch")
            m = re.search(r"charset=([\w-]+)", ctype)
            try:
                return bytes(body[:MAX_BYTES]).decode(m.group(1) if m else "utf-8", "replace"), url
            except LookupError:
                return bytes(body[:MAX_BYTES]).decode("utf-8", "replace"), url
    raise PostingError("fetch")                                       # too many redirects


# ---- reading a page ---------------------------------------------------------------------------
_META = re.compile(r"<meta\s[^>]*>", re.I)
_ATTR = re.compile(r'([\w:-]+)\s*=\s*(?:"([^"]*)"|\'([^\']*)\')')
_TITLE = re.compile(r"<title[^>]*>(.*?)</title>", re.I | re.S)
_H1 = re.compile(r"<h1[^>]*>(.*?)</h1>", re.I | re.S)
_NOISE = re.compile(r"<(script|style|noscript|svg|nav|header|footer|form|template)\b[^>]*>.*?</\1\s*>", re.I | re.S)
_MAIN = re.compile(r"<(main|article)\b[^>]*>(.*)</\1\s*>", re.I | re.S)


def _metas(page):
    out = {}
    for tag in _META.findall(page):
        a = {k.lower(): unescape(v1 or v2) for k, v1, v2 in _ATTR.findall(tag)}
        key = (a.get("property") or a.get("name") or "").lower()
        if key and a.get("content"):
            out.setdefault(key, a["content"])
    return out


def _plain(s):
    return " ".join(unescape(re.sub(r"<[^>]+>", " ", s or "")).split())


def _name(x):
    if isinstance(x, dict):
        x = x.get("name")
    return x.strip() if isinstance(x, str) else ""


def _place(x):
    """The town of a JobPosting's jobLocation (an object, a list of them, or text)."""
    if isinstance(x, list):
        x = x[0] if x else {}
    if isinstance(x, dict):
        x = x.get("address", x)
    if isinstance(x, dict):
        x = x.get("addressLocality") or x.get("addressRegion")
    return x.strip() if isinstance(x, str) else ""


def clamp(job):
    return {k: (job.get(k) or "").strip()[:n] for k, n in LIMITS.items()}


def read_page(page):
    """title, company, location, description of a page: its schema.org JobPosting when it has one,
    else the title tags and the text of the page. Empty strings for what isn't there."""
    for m in enrich._LD.finditer(page):
        try:
            data = json.loads(m.group(1))
        except ValueError:
            continue
        for p in enrich._postings(data):
            title = _plain(p.get("title") if isinstance(p.get("title"), str) else "")
            if not title:
                continue
            loc = _place(p.get("jobLocation"))
            if not loc and str(p.get("jobLocationType", "")).upper() == "TELECOMMUTE":
                loc = "Remote"
            return clamp({"title": title, "company": _name(p.get("hiringOrganization")), "location": loc,
                          "description": enrich.html_to_text(p.get("description") if isinstance(p.get("description"), str) else "")})
    meta = _metas(page)
    h1, ttl = _H1.search(page), _TITLE.search(page)
    title = _plain(meta.get("og:title") or (h1.group(1) if h1 else "") or (ttl.group(1) if ttl else ""))
    body = _NOISE.sub(" ", page)
    main = _MAIN.search(body)
    text = enrich.html_to_text(main.group(2) if main else body)
    if len(text) < 120:                          # a login wall or an empty shell, not a posting
        return {"title": "", "company": "", "location": "", "description": ""}
    return clamp({"title": title, "company": _plain(meta.get("og:site_name", "")), "location": "", "description": text})


def read_text(text):
    """Pasted text: the first non-empty line is the title, the rest the description."""
    lines = [x.strip() for x in (text or "").replace("\r", "").split("\n")]
    while lines and not lines[0]:
        lines.pop(0)
    if not lines:
        return {"title": "", "company": "", "location": "", "description": ""}
    return clamp({"title": lines[0], "company": "", "location": "", "description": "\n".join(lines[1:]).strip()})


def as_link(raw):
    """The link when the pasted input is only a link, else ""."""
    raw = (raw or "").strip()
    if re.fullmatch(r"https?://\S+", raw, re.I):
        return raw
    if re.fullmatch(r"www\.\S+", raw, re.I):
        return "https://" + raw
    return ""


def read(raw):
    """What the person pasted (a link or the text of the posting) -> ({title, company, location,
    description}, link). Raises PostingError."""
    link = as_link(raw)
    if link:
        page, final = fetch_page(link)
        job = read_page(page)
        link = final
    else:
        job = read_text(raw)
    if not job["title"]:
        raise PostingError("empty")
    return job, link


# ---- what the search is missing -----------------------------------------------------------------
_STOP = {"with", "from", "that", "this", "your", "have", "pour", "avec", "dans", "chez", "und", "der", "die", "das", "für", "fur", "mit",
         "bei", "des", "les", "une", "the", "and", "per", "con", "von", "zum", "zur", "sur", "mixed", "full", "time", "part", "temps", "plein",
         "partiel", "vollzeit", "teilzeit", "stage", "junior", "senior", "intern", "internship"}


def _title_words(title, limit=4):
    out = []
    for w in re.findall(r"[^\W\d_]{4,}", normalize.clean_title(title).lower()):
        if w not in _STOP and w not in out:
            out.append(w)
    return out[:limit]


def title_candidates(title):
    """Words to add to TITLE_KEYWORDS so that the title passes: role names and role title words from the
    catalog that occur in it, then its own significant words. Only those that really match it."""
    low = (title or "").lower()
    cands = []
    for rid in roles.match_title(title)[:2]:
        r = roles.get(rid)
        words = [n for ns in r["names"].values() for n in ns] + list(r["titles"])
        cands += [w.lower() for w in words]
    cands += _title_words(title)
    out = []
    for c in cands:
        c = c.strip()
        if c and c not in [v for v, _ in out] and len(c) <= 60 and filters._hit(c, low) and tuneable(c):
            out.append((c, _as_written(c, title)))
    return out[:5]


def _as_written(word, text):
    """The word as the posting writes it ("Dessinatrice", not "dessinatrice"): what the button shows;
    the setting itself stores words in small letters."""
    m = re.search(r"(?<![\w])" + re.escape(word.rstrip("*")) + r"(?![\w])", text or "", re.IGNORECASE)
    return m.group(0) if m else word


def tuneable(value):
    from . import tune
    return tune.clean("TITLE_KEYWORDS", value) is not None


def search_term(title):
    """The title as a search term, within the length a setting takes."""
    t = normalize.clean_title(title)
    if len(t) > 60:
        t = t[:60].rsplit(" ", 1)[0]
    return t if tuneable(t) else ""


def advice(job):
    """What the current settings would do with this posting. {"problems": [...], "skills": [missing skills],
    "found": True when nothing stops the search from finding it}. Each problem has a "kind" and what the
    page needs to word it and to offer the fix(es) ("fixes": [(action, setting, value)])."""
    title, company = job.get("title") or "", job.get("company") or ""
    desc, location = job.get("description") or "", job.get("location") or ""
    low = title.lower()
    problems = []
    gone = [k for k in config.TITLE_EXCLUDE if filters._hit(k, low)]
    if gone:
        problems.append({"kind": "title_exclude", "words": gone, "fixes": [("remove", "TITLE_EXCLUDE", k, k) for k in gone]})
    if config.TITLE_KEYWORDS and not any(filters._hit(k, low) for k in list(config.TITLE_KEYWORDS) + profiles.extra_title_words()):
        problems.append({"kind": "title_word", "fixes": [("add", "TITLE_KEYWORDS", c, label) for c, label in title_candidates(title)]})
    blocked = [k for k in config.COMPANY_EXCLUDE if filters._hit(k, company.lower())]
    if blocked:
        problems.append({"kind": "company", "words": blocked, "fixes": [("remove", "COMPANY_EXCLUDE", k, k) for k in blocked]})
    clean = normalize.clean_title(title)
    if config.SEARCH_TERMS and clean and not any(filters._hit(t.lower(), clean.lower()) for t in profiles.search_terms()):
        term = search_term(title)
        problems.append({"kind": "search_term", "term": term, "fixes": [("add", "SEARCH_TERMS", term, term)] if term else []})
    if not filters.location_ok(location, desc):
        name = re.sub(r"\s+[A-Z]{2}$", "", town(location)).strip()
        fixes, canton = [], ""
        if name:
            fixes.append(("add", "LOCATION_KEYWORDS", name.lower(), name))
            place = places.find(name)
            if place:
                from .providers import jobroom
                canton = place[3]
                effective = jobroom.cantons()          # (empty: all of Switzerland, which a single canton would narrow)
                if effective and canton not in effective:
                    fixes.append(("add", "JOBROOM_CANTONS", canton, canton))
        problems.append({"kind": "location", "town": name, "canton": canton, "fixes": fixes})
    if not filters.language_ok(title, desc):
        code = lang.detect_language(f"{title}. {desc}"[:600])
        problems.append({"kind": "language", "code": code,
                         "fixes": [("add", "LANGUAGES", code, code.upper())] if code in ("fr", "de", "it", "en") else []})
    if not filters.rate_ok(title):
        lo, hi = filters.stated_rate(title)
        problems.append({"kind": "rate", "low": lo, "high": hi, "wanted_low": config.WORK_RATE_MIN, "wanted_high": config.WORK_RATE_MAX,
                         "fixes": []})
    missing = skills.analyse(desc)[2]
    return {"problems": problems, "skills": missing, "found": not problems}
