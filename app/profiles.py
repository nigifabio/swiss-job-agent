"""Additional profiles ("roles"): the same person, a different CV and a wider search.

A person keeps the main profile (profile.json, id 0) and can add up to MAX_PROFILES - 1 more, each with
a role name. An additional profile is a VIEW on the main one, not a copy: name, contact details, photo and
every fact (jobs, dates, the wording of each point...) always come from the main profile. The view only
chooses and orders which skills, jobs, points of each job, education and extras lines are shown, and has
its own headline and summary. It stores positions in the main profile's lists, so nothing can be invented
and a change of the main profile can't break it: a position that no longer exists is dropped, and a list
chosen as "all" (None) keeps showing everything, new items included.

A profile also widens the search: its own search terms, title words, skills that score and words to avoid.
Place, languages, work rate, exclusions, sources... stay shared and global. Stored in the instance DB
(meta table), like the skill preferences."""
import json

from . import config, i18n, prefs, store

MAX_PROFILES = 4            # in all, the main profile included
MAIN = 0
LISTS = ("expertise", "education", "extras")         # lists of text lines the view can pick from
MAX_TERMS = 40
_cache = None


class ProfileError(Exception):
    """code: limit (already MAX_PROFILES), name (empty), exists (name taken), unknown."""
    def __init__(self, code):
        super().__init__(code)
        self.code = code


def _words(items, lower=False, limit=MAX_TERMS):
    """Clean list of short entries, in order, without repeats (case apart)."""
    out, seen = [], set()
    for x in items or []:
        x = " ".join(str(x).split())[:60]
        x = x.lower() if lower else x
        if x and x.lower() not in seen and len(out) < limit:
            seen.add(x.lower())
            out.append(x)
    return out


def _indexes(raw):
    """A list of distinct non-negative ints, or None (None = everything, in the main profile's order)."""
    if raw is None:
        return None
    out = []
    for i in raw if isinstance(raw, list) else []:
        if isinstance(i, int) and not isinstance(i, bool) and i >= 0 and i not in out:
            out.append(i)
    return out


def _sel(raw):
    """The stored choice of what a profile shows, checked."""
    raw = raw if isinstance(raw, dict) else {}
    sel = {k: _indexes(raw.get(k)) for k in LISTS}
    exp = raw.get("experience")
    if isinstance(exp, list):
        sel["experience"], seen = [], set()
        for e in exp:
            i = e.get("i") if isinstance(e, dict) else None
            if isinstance(i, int) and not isinstance(i, bool) and i >= 0 and i not in seen:
                seen.add(i)
                sel["experience"].append({"i": i, "b": _indexes(e.get("b"))})
    else:
        sel["experience"] = None
    return sel


def _clean(p):
    sel = _sel(p.get("sel"))
    return {"id": int(p["id"]), "name": " ".join(str(p.get("name") or "").split())[:40],
            "headline": " ".join(str(p.get("headline") or "").split())[:140],
            "summary": str(p.get("summary") or "").strip()[:3000], "sel": sel,
            "terms": _words(p.get("terms")), "titles": _words(p.get("titles"), lower=True),
            "skills": _words(p.get("skills"), lower=True), "avoid": _words(p.get("avoid"), lower=True)}


def load():
    global _cache
    try:
        raw = json.loads(store.get_meta().get("profiles") or "{}")
    except ValueError:
        raw = {}
    items = []
    for p in raw.get("items") or [] if isinstance(raw, dict) else []:
        try:
            items.append(_clean(p))
        except (KeyError, TypeError, ValueError, AttributeError):
            continue
    nxt = max([raw.get("next", 1) if isinstance(raw, dict) and isinstance(raw.get("next"), int) else 1]
              + [p["id"] + 1 for p in items])
    _cache = {"next": nxt, "items": items[:MAX_PROFILES - 1]}
    return _cache


def invalidate():
    global _cache
    _cache = None


def _get():
    return _cache if _cache is not None else load()


def _save(data):
    store.set_meta(profiles=json.dumps({"next": data["next"], "items": data["items"]}, ensure_ascii=False))
    invalidate()


def extras():
    """The additional profiles, oldest first."""
    return [dict(p) for p in _get()["items"]]


def get(pid):
    """An additional profile by id (None for the main profile or an unknown id)."""
    return next((dict(p) for p in _get()["items"] if p["id"] == pid), None)


def exists(pid):
    return pid == MAIN or get(pid) is not None


def ids():
    return [MAIN] + [p["id"] for p in _get()["items"]]


def multiple():
    return bool(_get()["items"])


def can_add():
    return len(_get()["items"]) + 1 < MAX_PROFILES


def main_label():
    return i18n.tr("Main profile")


def label(pid):
    p = get(pid)
    return p["name"] if p else main_label()


def names():
    """{id: name} of every profile, the main one first."""
    return {MAIN: main_label(), **{p["id"]: p["name"] for p in _get()["items"]}}


def parse_ids(raw):
    """"0,2" -> [0, 2] (what is stored on a job)."""
    return [int(x) for x in str(raw or "").split(",") if x.strip().isdigit()]


def tags(job):
    """The profile ids a job is tagged with, its main tag first; only profiles that still exist."""
    main = job.get("profile") or MAIN
    out = [main] + [i for i in parse_ids(job.get("profiles")) if i != main]
    out = [i for i in out if exists(i)]
    return out or [MAIN]


# ---- creating, changing, deleting ---------------------------------------------------------------
def create(name, main_profile=None):
    """A new profile, showing everything of the main profile, with its headline and summary to start from
    and the main profile's skills and avoided words as its own. Returns its id."""
    data = _get()
    if len(data["items"]) + 1 >= MAX_PROFILES:
        raise ProfileError("limit")
    name = " ".join((name or "").split())[:40]
    if not name:
        raise ProfileError("name")
    if name.lower() in {p["name"].lower() for p in data["items"]}:
        raise ProfileError("exists")
    main_profile = main_profile or {}
    p = _clean({"id": data["next"], "name": name, "headline": main_profile.get("headline"), "summary": main_profile.get("summary"),
                "skills": prefs.skills(), "avoid": prefs.avoided()})
    _save({"next": data["next"] + 1, "items": data["items"] + [p]})
    return p["id"]


def update(pid, **fields):
    """Change what a profile shows or searches. Only the fields given change; unknown ones are ignored."""
    data = _get()
    items = [dict(p) for p in data["items"]]
    p = next((x for x in items if x["id"] == pid), None)
    if not p:
        raise ProfileError("unknown")
    if "name" in fields:
        name = " ".join((fields["name"] or "").split())[:40]
        if not name:
            raise ProfileError("name")
        if name.lower() in {x["name"].lower() for x in items if x["id"] != pid}:
            raise ProfileError("exists")
        p["name"] = name
    for k in ("headline", "summary", "sel", "terms", "titles", "skills", "avoid"):
        if k in fields:
            p[k] = fields[k]
    items = [_clean(p) if x["id"] == pid else x for x in items]
    _save({"next": data["next"], "items": items})


def delete(pid):
    data = _get()
    items = [p for p in data["items"] if p["id"] != pid]
    if len(items) == len(data["items"]):
        return False
    _save({"next": data["next"], "items": items})
    return True


def skill_action(pid, action, term):
    """The "I have it" / "remove" / "avoid" clicks, for an additional profile's own lists."""
    p = get(pid)
    term = prefs._norm(term)
    if not p or not term or action not in ("have", "remove", "avoid", "unavoid"):
        return False
    skills, avoid = p["skills"], p["avoid"]
    drop = lambda lst: [x for x in lst if x.rstrip("*") != term.rstrip("*")]  # noqa: E731
    if action == "have":
        skills, avoid = skills + [term], drop(avoid)
    elif action == "remove":
        skills = drop(skills)
    elif action == "avoid":
        skills, avoid = drop(skills), avoid + [term]
    else:
        avoid = drop(avoid)
    update(pid, skills=skills, avoid=avoid)
    return True


# ---- what each profile searches and scores --------------------------------------------------------
def skills_of(pid):
    p = get(pid) if pid else None
    return list(p["skills"]) if p else prefs.skills()


def avoid_of(pid):
    p = get(pid) if pid else None
    return list(p["avoid"]) if p else prefs.avoided()


def search_terms():
    """What the scan searches: the main profile's terms (Settings) and every additional profile's.
    The providers read their terms here, so none of them needs to know about profiles."""
    more = [x for p in _get()["items"] for x in p["terms"]]
    return _words(list(config.SEARCH_TERMS) + more, limit=10 ** 6) if more else list(config.SEARCH_TERMS)


def extra_title_words():
    """Title words the additional profiles accept (the main profile's are TITLE_KEYWORDS)."""
    return _words([w for p in _get()["items"] for w in p["titles"]], lower=True, limit=10 ** 6)


def matching(title):
    """Ids of the profiles a posting's title belongs to: one of its title words occurs in the title, or one
    of its search terms does. The main profile's words are the global settings."""
    from . import filters
    t = (title or "").lower()
    out = []
    if (not config.TITLE_KEYWORDS or any(filters._hit(k, t) for k in config.TITLE_KEYWORDS)
            or any(filters._hit(k.lower(), t) for k in config.SEARCH_TERMS)):
        out.append(MAIN)
    for p in _get()["items"]:
        if any(filters._hit(k, t) for k in p["titles"]) or any(filters._hit(k.lower(), t) for k in p["terms"]):
            out.append(p["id"])
    return out


# ---- the view ------------------------------------------------------------------------------------
def _pick(items, idx):
    return list(items) if idx is None else [items[i] for i in idx if i < len(items)]


def apply_view(profile, pid):
    """`profile` (the main one, or a translated one of the same shape) as profile pid shows it. The main
    profile, an unknown id or no profile: unchanged. Lists whose order the profile chose are marked
    ("_fixed"), so a CV written for a posting doesn't re-order them."""
    p = get(pid) if pid else None
    if not p or not profile:
        return profile
    out, sel = dict(profile), p["sel"]
    out["headline"], out["summary"] = p["headline"], p["summary"]
    for k in LISTS:
        out[k] = _pick(profile.get(k) or [], sel[k])
    out["_fixed_expertise"] = sel["expertise"] is not None
    exp = profile.get("experience") or []
    if sel["experience"] is None:
        out["experience"] = [dict(e) for e in exp]
    else:
        out["experience"] = []
        for e in sel["experience"]:
            if e["i"] < len(exp):
                src = exp[e["i"]]
                out["experience"].append(dict(src, bullets=_pick(src.get("bullets") or [], e["b"]), _fixed=e["b"] is not None))
    return out


def choices(profile, pid):
    """What the edit page shows: for every list of the main profile, its items with whether the profile
    shows them, those shown first in the profile's order, then the others in the main profile's order.
    {"expertise": [(index, text, picked)], ..., "experience": [{"i", "title", "picked", "bullets": [...]}]}"""
    p = get(pid)
    sel = p["sel"] if p else _sel({})

    def listed(items, idx):
        shown = list(range(len(items))) if idx is None else [i for i in idx if i < len(items)]
        return [(i, items[i], True) for i in shown] + [(i, items[i], False) for i in range(len(items)) if i not in shown]
    out = {k: listed(profile.get(k) or [], sel[k]) for k in LISTS}
    exp = profile.get("experience") or []
    chosen = ([{"i": i, "b": None} for i in range(len(exp))] if sel["experience"] is None
              else [e for e in sel["experience"] if e["i"] < len(exp)])
    rows = []
    for e in chosen:
        rows.append({"i": e["i"], "picked": True, "bullets": listed(exp[e["i"]].get("bullets") or [], e["b"])})
    for i in range(len(exp)):
        if all(r["i"] != i for r in rows):
            rows.append({"i": i, "picked": False, "bullets": listed(exp[i].get("bullets") or [], None)})
    for r in rows:
        e = exp[r["i"]]
        r["title"] = e.get("title", "")
        r["where"] = ", ".join(x for x in (e.get("org", ""), e.get("loc", "")) if x)
        r["dates"] = e.get("dates", "")
    out["experience"] = rows
    return out


def selection_from_form(profile, form):
    """The choice made on the edit page, from the submitted form (checkbox values in page order, so the
    order on the page is the order chosen). `move` = "list:index:up" (or down, and "b:job:index:up") moves
    one shown item. A list picked in full and in the main profile's order is stored as "all"."""
    def picks(name, n):
        return _indexes([int(v) for v in form.getlist(name) if str(v).isdigit() and int(v) < n])

    move = str(form.get("move") or "").split(":")

    def moved(idx, which):
        if move[:len(which)] == which and len(move) == len(which) + 2 and move[-2].isdigit() and move[-1] in ("up", "down"):
            item, at = int(move[-2]), None
            if item in idx:
                at = idx.index(item)
                to = at - 1 if move[-1] == "up" else at + 1
                if 0 <= to < len(idx):
                    idx[at], idx[to] = idx[to], idx[at]
        return idx

    def whole(idx, n):
        return None if idx == list(range(n)) else idx
    sel = {}
    for k in LISTS:
        n = len(profile.get(k) or [])
        sel[k] = whole(moved(picks(k, n), [k]), n)
    exp = profile.get("experience") or []
    chosen = moved(picks("experience", len(exp)), ["experience"])
    entries, all_default = [], True
    for i in chosen:
        nb = len((exp[i].get("bullets") or []))
        b = whole(moved(picks(f"b{i}", nb), ["b", str(i)]), nb)
        all_default = all_default and b is None
        entries.append({"i": i, "b": b})
    sel["experience"] = None if all_default and chosen == list(range(len(exp))) else entries
    return sel
