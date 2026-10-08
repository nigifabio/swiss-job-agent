import hashlib


def content_hash(*parts):
    """Stable short hash used to de-dupe postings across fetches."""
    s = "|".join(" ".join((p or "").split()).lower() for p in parts)
    return hashlib.sha256(s.encode("utf-8")).hexdigest()[:32]


import re as _re
import unicodedata as _ud

_GENDER = _re.compile(r"\((?:[fmdhwx]\s*/\s*)+[fmdhwx]\)|\b[fmdhw]\s*/\s*[fmdhw](?:\s*/\s*[fmdhwx])?\b", _re.I)
_RATE = _re.compile(r"\d{2,3}\s*%?\s*(?:-|–|a|à|to|bis)?\s*\d{0,3}\s*%")
_CO_NOISE = {"ag", "sa", "gmbh", "sarl", "sàrl", "ltd", "inc", "llc", "schweiz", "suisse", "svizzera",
             "switzerland", "group", "groupe", "holding", "services", "international"}


def _plain(s):
    s = _re.sub(r"<[^>]+>", " ", s or "")
    s = _ud.normalize("NFKD", s).encode("ascii", "ignore").decode().lower()
    return " ".join(_re.sub(r"[^a-z0-9 ]", " ", s).split())


def loose_key(title, company, location):
    """Looser fingerprint for the same job written differently across sources: ignores
    gender markers (H/F, m/w/d), work rates (80-100%), accents, punctuation, company
    suffixes (AG, SA, Sàrl, Schweiz...) and everything after the first word of the location."""
    t = _plain(_RATE.sub(" ", _GENDER.sub(" ", title or "")))
    c = " ".join(w for w in _plain(company).split() if w not in _CO_NOISE)
    loc = _plain(location).split()
    return content_hash(t, c, loc[0] if loc else "")


def title_key(title, location):
    """The job without its company: the same position advertised by the employer and by agencies
    shares it (see twins.py, which also compares the texts before calling two postings one job)."""
    t = _plain(_RATE.sub(" ", _GENDER.sub(" ", title or "")))
    loc = _plain(location).split()
    return f"{t}|{loc[0] if loc else ''}"
