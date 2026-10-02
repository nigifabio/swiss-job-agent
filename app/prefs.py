"""Skill preferences the user refines from job pages ("I have it", "Remove", "Avoid").

Effective CV skills = SCORE_KEYWORDS from the profile .env, minus removed, plus added.
Avoided words (e.g. "german") push postings that mention them down the list.
Stored in the instance DB (meta table), so every scan and rescore uses them.
"""
import json

from . import config, store

KEYS = ("skills_added", "skills_removed", "skills_avoided")
_cache = None


def _norm(term):
    return " ".join((term or "").split()).lower()[:60]


def load():
    global _cache
    meta = store.get_meta()
    out = {}
    for k in KEYS:
        try:
            out[k] = [t for t in json.loads(meta.get(k) or "[]") if isinstance(t, str)]
        except ValueError:
            out[k] = []
    _cache = out
    return out


def invalidate():
    global _cache
    _cache = None


def _get():
    return _cache if _cache is not None else load()


def skills():
    p = _get()
    removed = set(p["skills_removed"])
    base = [k for k in config.SCORE_KEYWORDS if k.rstrip("*") not in removed]
    return base + [k for k in p["skills_added"] if k not in base]


def avoided():
    return list(_get()["skills_avoided"])


def summary():
    p = _get()
    return {"skills": skills(), "added": p["skills_added"], "removed": p["skills_removed"],
            "avoided": p["skills_avoided"]}


def apply(action, term):
    """action: have | remove | avoid | unavoid | restore. Returns False for an invalid request."""
    term = _norm(term)
    if not term or action not in ("have", "remove", "avoid", "unavoid", "restore"):
        return False
    p = {k: list(v) for k, v in _get().items()}
    add, rem, avo = p["skills_added"], p["skills_removed"], p["skills_avoided"]

    def drop(lst):
        while term in lst:
            lst.remove(term)
    if action == "have":
        drop(rem), drop(avo)
        if term not in [k.rstrip("*") for k in config.SCORE_KEYWORDS] and term not in add:
            add.append(term)
    elif action == "remove":
        drop(add)
        if term in [k.rstrip("*") for k in config.SCORE_KEYWORDS] and term not in rem:
            rem.append(term)
    elif action == "restore":
        drop(rem)
    elif action == "avoid":
        drop(add)
        if term not in avo:
            avo.append(term)
    elif action == "unavoid":
        drop(avo)
    store.set_meta(**{k: json.dumps(v) for k, v in p.items()})
    invalidate()
    return True
