"""Public-transport time from home to each job, from the Swiss timetable (transport.opendata.ch,
the open API over the official timetable data; no key). One request per (home, town), remembered:
a scan asks about a few new towns only.

Verified 2026-10-08: GET /v1/connections?from=Pully&to=Yverdon-les-Bains&limit=3
  -> {"connections": [{"duration": "00d00:37:00", "transfers": 1}, ...]}
"""
import os
import re

from . import config, store
from .http import Http

API = "https://transport.opendata.ch/v1/connections"
PER_SCAN = int(os.environ.get("COMMUTE_PER_SCAN", "20"))        # new towns looked up per scan
_DUR = re.compile(r"(\d+)d(\d+):(\d+):(\d+)")


def town(location):
    """The town of a posting's location: "Renens VD, Ouest Lausannois, Suisse" -> "Renens VD"."""
    t = re.split(r"[,;/|(]", location or "")[0]
    t = re.sub(r"\b\d{4}\b", " ", t)                               # postcode
    t = " ".join(t.split())
    return "" if not t or t.lower() in ("ch", "suisse", "schweiz", "switzerland", "svizzera", "remote") else t[:60]


def _lookup(client, home, place):
    data = client.json(API, params=[("from", home), ("to", place), ("limit", "3"),
                                    ("fields[]", "connections/duration")])
    mins = []
    for c in data.get("connections") or []:
        m = _DUR.match(c.get("duration") or "")
        if m:
            d, h, mi, s = (int(x) for x in m.groups())
            mins.append(d * 1440 + h * 60 + mi + (1 if s >= 30 else 0))
    return min(mins) if mins else None


def minutes(home, place, client=None):
    """Minutes door to door between two towns, None when unknown. Remembered, also when unknown."""
    home, place = " ".join((home or "").split()), " ".join((place or "").split())
    if not home or not place:
        return None
    if home.lower() == place.lower():
        return 0
    with store.conn() as c:
        row = c.execute("SELECT minutes FROM commutes WHERE home=? AND place=?", (home.lower(), place.lower())).fetchone()
    if row:
        return row["minutes"]
    if client is None:
        with Http(timeout=15, min_gap=0.5, tries=2) as cl:
            m = _lookup(cl, home, place)
    else:
        m = _lookup(client, home, place)
    with store.conn() as c:
        c.execute("INSERT OR REPLACE INTO commutes (home, place, minutes, checked_at) VALUES (?,?,?,?)",
                  (home.lower(), place.lower(), m, store.now()))
    return m


def home():
    """The person's home town: the setting, else the town of the address on their CV."""
    if config.HOME_TOWN:
        return config.HOME_TOWN
    from . import tailor
    p = tailor.load_profile() or {}
    return town((p.get("contact") or {}).get("location", ""))


def fill(limit=None):
    """Give every open job its travel time; asks the timetable about at most `limit` new towns.
    Jobs further than COMMUTE_MAX minutes are greyed out in the list."""
    home_ = home()
    if not home_:
        return 0
    limit = PER_SCAN if limit is None else limit
    with store.conn() as c:
        jobs = [dict(r) for r in c.execute(
            "SELECT id, location, commute_min, dimmed FROM jobs WHERE status IN ('new','shortlisted') AND commute_min IS NULL").fetchall()]
        known = {r["place"]: r["minutes"] for r in c.execute("SELECT place, minutes FROM commutes WHERE home=?", (home_.lower(),))}
    asked = done = 0
    with Http(timeout=15, min_gap=0.5, tries=2) as client:
        for j in jobs:
            place = town(j["location"])
            if not place:
                continue
            if place.lower() not in known and place.lower() != home_.lower():
                if asked >= limit:
                    continue
                asked += 1
                try:
                    known[place.lower()] = minutes(home_, place, client)
                except Exception:  # noqa: BLE001  (timetable down: try again at the next scan)
                    break
            m = 0 if place.lower() == home_.lower() else known.get(place.lower())
            if m is None:
                continue
            with store.conn() as c:
                c.execute("UPDATE jobs SET commute_min=? WHERE id=?", (m, j["id"]))
                if config.COMMUTE_MAX and m > config.COMMUTE_MAX:
                    c.execute("UPDATE jobs SET dimmed=1 WHERE id=? AND status='new'", (j["id"],))
            done += 1
    return done


def reset():
    """Home town changed: forget the times stored on the jobs (the town-to-town memory stays)."""
    with store.conn() as c:
        c.execute("UPDATE jobs SET commute_min=NULL")
