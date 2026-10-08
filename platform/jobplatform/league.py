"""The league: people of the platform who chose to compare their job-search points.

What is shown to the others is a nickname the person picked, points, a streak and badges: numbers
worked out inside each workspace (app/game.py). No e-mail, no name, no job, no company, no date.
Joining is each person's own choice, and leaving removes them from the board at once."""
import datetime
import json
import random

from . import db

LEVELS = ["Warming up", "On the move", "In the race", "Front runner", "Unstoppable"]
BADGES = {"first": ("🚀", "Lift-off"), "five": ("🖐", "High five"), "target": ("🎯", "Bullseye"), "streak3": ("🔥", "On fire"),
          "follow3": ("📣", "Persistent"), "sharp": ("🧐", "Sharp eye"), "tailor": ("✂️", "Made to measure"),
          "interview": ("🎤", "On stage"), "skin": ("🛡", "Thick skin"), "profile": ("💎", "Polished"), "offer": ("🏆", "Jackpot")}
NAMES = ["Marmotte", "Bouquetin", "Chamois", "Lynx", "Edelweiss", "Cervin", "Gypaète", "Saint-Bernard", "Raclette", "Rösti",
         "Fondue", "Toblerone", "Funiculaire", "Alphorn", "Léman", "Gothard"]


def suggestion(taken=()):
    free = [n for n in NAMES if n.lower() not in {t.lower() for t in taken}]
    return random.choice(free) if free else f"{random.choice(NAMES)} {random.randint(2, 99)}"


def board(members, summary, me=""):
    """Rows for the page, best of the week first. summary(slug) -> a workspace's totals ({} when it can't answer)."""
    rows = []
    for t in members:
        g = (summary(t["slug"]) or {}).get("game") or {}
        rows.append({"name": t["league_name"], "me": t["slug"] == me, "week": int(g.get("week") or 0), "month": int(g.get("month") or 0),
                     "total": int(g.get("total") or 0), "streak": int(g.get("streak") or 0),
                     "level": LEVELS[min(len(LEVELS) - 1, max(0, int(g.get("level") or 0)))],
                     "badges": [BADGES[k] for k in g.get("badges") or [] if k in BADGES], "slug": t["slug"]})
    rows.sort(key=lambda r: (-r["week"], -r["month"], -r["total"], r["name"].lower()))
    top = rows[0]["week"] if rows else 0
    for i, r in enumerate(rows):
        r["rank"], r["lead"], r["bar"] = i + 1, top > 0 and r["week"] == top, round(100 * r["week"] / top) if top else 0
    return rows


def champion(rows, today=None):
    """Last week's winner (nickname, points), remembered when a new week starts. None when nobody scored."""
    week = "%d-W%02d" % (today or datetime.date.today()).isocalendar()[:2]
    if db.get_kv("league_week") != week:                      # a new week: last view's standings were last week's
        try:
            old = json.loads(db.get_kv("league_scores") or "{}")
        except ValueError:
            old = {}
        best = max(old.items(), key=lambda kv: kv[1], default=None)
        db.set_kv("league_champion", json.dumps(best if best and best[1] > 0 else None))
        db.set_kv("league_week", week)
    db.set_kv("league_scores", json.dumps({r["name"]: r["week"] for r in rows}))
    try:
        return json.loads(db.get_kv("league_champion") or "null")
    except ValueError:
        return None
