"""Shared posting filters + CV-keyword scoring, used by every provider."""
import re
import html

from . import config
from .lang import keep_language

_TAG = re.compile(r"<[^>]+>")

REMOTE_KW = ["remote", "télétravail", "teletravail", "home office", "anywhere", "distributed", "fully remote"]


def strip_html(h):
    """One-line plain text: tags removed, entities decoded, whitespace collapsed."""
    return " ".join(html.unescape(_TAG.sub(" ", h)).split()) if h else ""


def _has(text, kws):
    t = (text or "").lower()
    return any(k in t for k in kws)


def title_ok(title):
    t = (title or "").lower()
    if not t:
        return False
    if any(_hit(k, t) for k in config.TITLE_EXCLUDE):
        return False
    return not config.TITLE_KEYWORDS or any(_hit(k, t) for k in config.TITLE_KEYWORDS)


def location_ok(location, desc=""):
    """Judge by the location field; the description is only a fallback when it's empty
    (descriptions mention 'remote' and city names far too loosely)."""
    t = (location or "").lower().strip() or (desc or "")[:300].lower()
    if any(_hit(k, t) for k in config.LOCATION_KEYWORDS):
        return True
    if config.ALLOW_REMOTE and _has(t, REMOTE_KW):
        # remote counts only when scoped to CH/Europe/EMEA, or when it's bare "Remote"
        if any(_hit(k, t) for k in config.REMOTE_REGIONS):
            return True
        rest = t
        for k in REMOTE_KW + ["(", ")", "-", ",", ";", "/"]:
            rest = rest.replace(k, " ")
        return not rest.strip()
    return False


_RATE_RANGE = re.compile(r"(\d{2,3})\s*%?\s*(?:-|–|—|/|à|a|bis|to)\s*(\d{2,3})\s*%")
_RATE_ONE = re.compile(r"(?<![\d.,])(\d{2,3})\s*%")


def stated_rate(title):
    """(min, max) work rate a title states ("Coordinator 60-80%" -> (60, 80)), or None."""
    t = title or ""
    m = _RATE_RANGE.search(t)
    pair = (int(m.group(1)), int(m.group(2))) if m else None
    if not pair:
        m = _RATE_ONE.search(t)
        pair = (int(m.group(1)), int(m.group(1))) if m else None
    if not pair or not all(10 <= x <= 100 for x in pair):
        return None
    return min(pair), max(pair)


def rate_ok(title):
    """False only when the title states a work rate outside what the person wants; a posting that
    states none (usually full time) is kept."""
    r = stated_rate(title)
    return not r or (r[1] >= config.WORK_RATE_MIN and r[0] <= config.WORK_RATE_MAX)


def company_ok(company):
    c = (company or "").lower()
    return not any(_hit(k, c) for k in config.COMPANY_EXCLUDE)


def language_ok(title, desc):
    return keep_language(f"{title}. {desc or ''}"[:600], config.LANGUAGES)


_kw_re = {}


def _hit(kw, text):
    """Whole-word match so 'aws' doesn't hit 'laws' or 'api' hit 'rapid'.
    A trailing '*' makes it a prefix: 'coordinat*' hits coordinateur/coordinatrice."""
    if kw not in _kw_re:
        end = "" if kw.endswith("*") else r"(?![\w])"
        _kw_re[kw] = re.compile(r"(?<![\w])" + re.escape(kw.rstrip("*")) + end)
    return bool(_kw_re[kw].search(text))


def _hit_skill(kw, text):
    """A skill matches in any of its spellings for the posting languages searched ("sales" also
    matches "vente" and "Verkauf"); keywords outside the catalog match as written."""
    from . import roles
    return any(_hit(sp, text) for sp in roles.spellings_for(kw, config.LANGUAGES))


def _skills():
    from . import prefs          # runtime-refined list (profile keywords +/- user clicks)
    return prefs.skills()


def matched(job, kws=None):
    kws = _skills() if kws is None else kws
    text = f"{job.get('title') or ''} {job.get('description') or ''}".lower()
    return [k.rstrip("*") for k in kws if _hit_skill(k, text)]


def avoided_hits(job):
    from . import prefs
    text = f"{job.get('title') or ''} {job.get('description') or ''}".lower()
    return [k.rstrip("*") for k in prefs.avoided() if _hit_skill(k, text)]


def score(job):
    """0-100 keyword match of a posting against the CV skills (prefs.skills()).
    Title hits weigh triple. Returns None when no keywords are configured."""
    kws = _skills()
    if not kws:
        return None
    title = (job.get("title") or "").lower()
    text = f"{title} {job.get('description') or ''}".lower()
    pts = sum(3 if _hit_skill(k, title) else 1 for k in kws if _hit_skill(k, text))
    return min(100, round(100 * pts / max(6, len(kws) // 2)))
