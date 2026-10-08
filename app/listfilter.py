"""Search and filters on top of a job list: keyword, role, when the job was found, distance from
home, and the order. Everything is worked out from the list already loaded; nothing is stored."""
import datetime
import functools
import unicodedata

from . import commute, places, roles, store

DAYS = (1, 3, 7, 30)
KM = (5, 10, 20, 30, 50)
SORTS = ("best", "newest", "nearest")


def _fold(s):
    return unicodedata.normalize("NFKD", s or "").encode("ascii", "ignore").decode().lower()


@functools.lru_cache(maxsize=4096)
def _roles(title):
    return tuple(roles.match_title(title or "")[:2])        # a title can be two roles at most ("sales assistant")


@functools.lru_cache(maxsize=2048)
def _place(town):
    return places.find(town) if town else None


def distance(job, home_place):
    """Straight-line km from home to the job's town (None: no home set, remote job or a town not in the table)."""
    p = _place(commute.town(job.get("location"))) if home_place else None
    return round(places._km(home_place, p)) if p else None


def apply(rows, q="", role="", days=0, km=0, sort="best", lang="en"):
    """(rows to show, what the filter bar needs). Each row gets "km"."""
    home = _place(commute.home())
    for j in rows:
        j["km"] = distance(j, home)
    count = {}
    for j in rows:
        for rid in _roles(j.get("title")):
            count[rid] = count.get(rid, 0) + 1
    role = role if roles.get(role) else ""
    days = days if days in DAYS else 0
    km = km if km in KM and home else 0
    sort = sort if sort in SORTS and (sort != "nearest" or home) else "best"
    words = _fold(" ".join((q or "").split())[:80]).split()
    out = rows
    if words:
        def text(j):
            return _fold(" ".join(str(j.get(k) or "") for k in ("title", "company", "location", "description", "source")))
        out = [j for j in out if all(w in t for t in [text(j)] for w in words)]
    if role:
        out = [j for j in out if role in _roles(j.get("title"))]
    if days:
        cut = (datetime.datetime.fromisoformat(store.now()) - datetime.timedelta(days=days)).isoformat()
        out = [j for j in out if (j.get("created_at") or "") >= cut]
    if km:
        out = [j for j in out if j["km"] is not None and j["km"] <= km]
    if sort == "newest":
        out = sorted(out, key=lambda j: j.get("created_at") or "", reverse=True)
    elif sort == "nearest":
        out = sorted(out, key=lambda j: (j["km"] is None, j["km"] or 0))
    options = sorted(((roles.label(roles.get(rid), lang), rid, n) for rid, n in count.items()), key=lambda r: (-r[2], r[0]))
    on = bool(words or role or days or km)
    return out, {"q": " ".join((q or "").split())[:80], "role": role, "days": days, "km": km, "sort": sort, "roles": options,
                 "home": bool(home), "on": on, "total": len(rows), "show": on or sort != "best" or len(rows) > 3}
