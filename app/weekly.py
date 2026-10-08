"""The week in one page: what came in, the best of it, where the applications stand against the
ORP target, and what is waiting for the person. Also the Monday entry of the calendar feed, and,
on a personal installation, an optional weekly message to a chat webhook (SUMMARY_WEBHOOK)."""
import datetime
import os

from . import report, store


def summary(today=None):
    today = today or datetime.date.today()
    monday = today - datetime.timedelta(days=today.weekday())
    since = (datetime.datetime.combine(today, datetime.time()) - datetime.timedelta(days=7)).isoformat(timespec="seconds")
    fresh = [j for j in store.created_since(since) if j["status"] in ("new", "shortlisted")]
    applied = store.applications(monday.isoformat(), today.isoformat())
    soon = (today + datetime.timedelta(days=7)).isoformat()
    interviews = [j for j in store.interviews() if today.isoformat() <= j["interview_at"][:10] <= soon]
    return {"week": monday.isocalendar()[1], "monday": monday.isoformat(), "new": len(fresh), "best": fresh[:5],
            "applied": applied, "orp": report.month_progress(today), "waiting": store.awaiting_answer(),
            "assigned": store.assignments_open(), "followups": store.followups_due(7), "interviews": interviews}


def text(s=None):
    """A few plain lines (calendar entry, chat message)."""
    from .i18n import tr
    s = s or summary()
    o = s["orp"]
    lines = [tr("{n} new jobs this week").format(n=s["new"]),
             tr("Applications this month: {done} of {target}").format(done=o["done"], target=o["target"])]
    if s["assigned"]:
        lines.append(tr("Assigned by the ORP, to apply: {n}").format(n=len(s["assigned"])))
    if s["interviews"]:
        lines.append(tr("Interviews in the next 7 days: {n}").format(n=len(s["interviews"])))
    if s["waiting"]:
        lines.append(tr("Without an answer, to follow up: {n}").format(n=len(s["waiting"])))
    for j in s["best"][:3]:
        lines.append(f"• {j['title']} — {j['company']}" + (f" ({j['score']})" if j.get("score") is not None else ""))
    return "\n".join(lines)


def send_if_due(today=None):
    """Once a week, from the first scan of the week: post the summary to SUMMARY_WEBHOOK ({"msg": ...})."""
    url = os.environ.get("SUMMARY_WEBHOOK", "")
    today = today or datetime.date.today()
    week = "%d-W%02d" % today.isocalendar()[:2]
    if not url or store.get_meta().get("weekly_sent") == week:
        return False
    import httpx
    httpx.post(url, json={"msg": "🇨🇭 " + text(summary(today))}, timeout=10).raise_for_status()
    store.set_meta(weekly_sent=week)
    return True
