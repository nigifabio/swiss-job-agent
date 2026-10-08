"""The job search as a game: points for what moves a search forward (applying, following up, sorting
the list, getting interviews), a level, badges and a streak. Worked out from what the person already
recorded; nothing new is stored. On a platform the totals (numbers and badge names only, never a job,
a company or a date) can feed a league the person chose to join."""
import datetime

from . import report, store

POINTS = {"applied": 10, "interview": 30, "offer": 100, "followup": 5, "sorted": 1, "cv": 3, "letter": 3,
          "refusal": 2, "target": 25}
SORT_CAP = 20                      # points a week for sorting the list: sorting is good, applying is the point
LEVELS = [(0, "Warming up"), (50, "On the move"), (150, "In the race"), (400, "Front runner"), (1000, "Unstoppable")]
BADGES = [   # key, emoji, name, how to get it
    ("first", "🚀", "Lift-off", "Send your first application"),
    ("five", "🖐", "High five", "5 applications in one week"),
    ("target", "🎯", "Bullseye", "Reach the monthly target"),
    ("streak3", "🔥", "On fire", "Apply 3 weeks in a row"),
    ("follow3", "📣", "Persistent", "Follow up 3 applications"),
    ("sharp", "🧐", "Sharp eye", "Sort 20 jobs and say why"),
    ("tailor", "✂️", "Made to measure", "Write a CV and a letter for the same job"),
    ("interview", "🎤", "On stage", "Get an interview"),
    ("skin", "🛡", "Thick skin", "5 refusals and still going"),
    ("profile", "💎", "Polished", "Complete the profile check"),
    ("offer", "🏆", "Jackpot", "Get an offer"),
]


def _week(d):
    return d - datetime.timedelta(days=d.weekday())


def stats(today=None, profile=None):
    today = today or datetime.date.today()
    monday, first = _week(today), today.replace(day=1)
    jobs, hist = store.list_jobs(), store.history_all()
    by_id = {j["id"]: j for j in jobs}

    def day(ts):
        try:
            return datetime.date.fromisoformat((ts or "")[:10])
        except ValueError:
            return None
    applied = [(day(j.get("applied_date")), j) for j in jobs if day(j.get("applied_date"))]
    reached = {}                                      # (job, status) -> first day it got there
    for h in hist:
        d = day(h["changed_at"])
        if d and h["status"] in ("interview", "offer", "rejected", "shortlisted", "discarded"):
            reached.setdefault((h["job_id"], h["status"]), d)
    sorted_days = [d for (jid, st), d in reached.items()
                   if st == "shortlisted" or (st == "discarded" and (by_id.get(jid) or {}).get("discard_reason") not in (None, "", "filtered"))]
    follow = [day(j.get("followed_up_at")) for j in jobs if day(j.get("followed_up_at"))]
    months = {}
    for d, _ in applied:
        months[(d.year, d.month)] = months.get((d.year, d.month), 0) + 1
    goal = report.target()

    def points(since):
        ok = lambda d: d is not None and d >= since                       # noqa: E731
        mine = [j for d, j in applied if ok(d)]
        n = {"applied": len(mine), "followup": sum(1 for d in follow if ok(d)),
             "interview": sum(1 for (_, st), d in reached.items() if st == "interview" and ok(d)),
             "offer": sum(1 for (_, st), d in reached.items() if st == "offer" and ok(d)),
             "refusal": sum(1 for (jid, st), d in reached.items() if st == "rejected" and ok(d) and (by_id.get(jid) or {}).get("applied_date")),
             "cv": sum(1 for j in mine if j.get("cv_text")), "letter": sum(1 for j in mine if j.get("letter")),
             "target": sum(1 for (y, m), c in months.items() if c >= goal and datetime.date(y, m, 1) >= since.replace(day=1))}
        weeks = {}
        for d in sorted_days:
            if ok(d):
                weeks[_week(d)] = weeks.get(_week(d), 0) + 1
        n["sorted"] = sum(min(SORT_CAP, c) for c in weeks.values())
        return sum(POINTS[k] * v for k, v in n.items()), n
    week, wn = points(monday)
    month, _ = points(first)
    total, tn = points(datetime.date(2000, 1, 1))
    weeks_applied = {_week(d) for d, _ in applied}
    streak, w = 0, monday if monday in weeks_applied else monday - datetime.timedelta(days=7)
    while w in weeks_applied:
        streak, w = streak + 1, w - datetime.timedelta(days=7)
    per_week = {}
    for d, _ in applied:
        per_week[_week(d)] = per_week.get(_week(d), 0) + 1
    check = None
    if profile:
        from . import strength
        check = strength.report(profile)
    sorted_why = sum(1 for (jid, st), _ in reached.items() if st == "discarded"
                     and (by_id.get(jid) or {}).get("discard_reason") not in (None, "", "filtered"))
    have = {"first": bool(applied), "five": any(c >= 5 for c in per_week.values()), "target": tn["target"] > 0,
            "streak3": streak >= 3 or _longest(weeks_applied) >= 3, "follow3": len(follow) >= 3, "sharp": sorted_why >= 20,
            "tailor": any(j.get("cv_text") and j.get("letter") for j in jobs), "interview": tn["interview"] > 0,
            "skin": tn["refusal"] >= 5, "profile": bool(check and check["done"] == check["total"]), "offer": tn["offer"] > 0}
    level = max(i for i, (need, _) in enumerate(LEVELS) if total >= need)
    nxt = LEVELS[level + 1][0] if level + 1 < len(LEVELS) else None
    return {"week": week, "month": month, "total": total, "streak": streak, "level": level, "level_name": LEVELS[level][1],
            "next_level": nxt, "to_next": (nxt - total) if nxt else 0, "this_week": wn,
            "badges": [k for k, *_ in BADGES if have[k]],
            "next_badges": [(e, name, how) for k, e, name, how in BADGES if not have[k]][:3]}


def _longest(weeks):
    best = 0
    for w in weeks:
        if w - datetime.timedelta(days=7) not in weeks:
            n = 1
            while w + datetime.timedelta(days=7 * n) in weeks:
                n += 1
            best = max(best, n)
    return best


def public(s):
    """What may leave the workspace for a league: numbers and badge keys only."""
    return {k: s[k] for k in ("week", "month", "total", "streak", "level", "badges")}
