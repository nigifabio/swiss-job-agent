"""Calendar feed (iCalendar): interviews, ORP deadlines, follow-up dates, the monthly hand-in of the
proofs of job search and the week's summary, for the person's own calendar app (phone, Google, Outlook).

A calendar app can't sign in, so the feed has its own address with a long random key in it: whoever
has the address can read these dates, and "new address" on the Settings page makes the old one stop
working. The feed is read-only and holds dates, job titles and company names, nothing else."""
import datetime
import hmac
import os
import secrets
import socket

from . import store, weekly
from .i18n import tr


def key(create=True):
    k = store.get_meta().get("feed_key", "")
    if not k and create:
        k = secrets.token_urlsafe(24)
        store.set_meta(feed_key=k)
    return k


def reset():
    store.set_meta(feed_key=secrets.token_urlsafe(24))


def valid(candidate):
    k = key(create=False)
    return bool(k) and hmac.compare_digest(k.encode(), (candidate or "").encode())


def address(base):
    """Where the feed is, seen from outside: behind the platform gateway it is one of the public pages."""
    slug = os.environ.get("TENANT_SLUG", "")
    if not slug and os.environ.get("PLATFORM_TENANT") == "1":          # containers are named jat-<slug>-web
        host = socket.gethostname()
        slug = host[4:-4] if host.startswith("jat-") and host.endswith("-web") else ""
    if slug:                                   # the platform is https only, whatever the proxy chain reports
        return "https://" + base.split("://", 1)[-1].rstrip("/") + f"/welcome/cal/{slug}/{key()}.ics"
    return base.rstrip("/") + f"/calendar/{key()}.ics"


def _esc(s):
    s = str(s or "").replace("\\", "\\\\").replace(";", "\\;").replace(",", "\\,")
    return s.replace("\r", "").replace("\n", "\\n")


def _fold(line):
    """Lines of at most 75 bytes, continued with a leading space (RFC 5545)."""
    out, cur = [], b""
    for ch in line:
        b = ch.encode()
        if len(cur) + len(b) > (74 if out else 75):
            out.append(cur)
            cur = b""
        cur += b
    out.append(cur)
    return "\r\n ".join(p.decode() for p in out)


def _day(d):
    return datetime.date.fromisoformat(d[:10])


def events(today=None, base=""):
    """[{uid, start, end?, title, text}]: start is a date (all day) or a datetime (local time)."""
    today = today or datetime.date.today()
    out = []

    def link(j):
        return f"{base}/job/{j['id']}" if base else ""
    for j in store.interviews():
        try:
            start = datetime.datetime.fromisoformat(j["interview_at"])
        except ValueError:
            continue
        out.append({"uid": f"interview-{j['id']}", "start": start, "end": start + datetime.timedelta(hours=1),
                    "title": tr("Interview: {title} — {company}").format(title=j["title"], company=j["company"] or ""),
                    "text": "\n".join(x for x in (j.get("location"), j.get("contact"), link(j)) if x)})
    for j in store.assignments_open():
        if j.get("orp_deadline"):
            out.append({"uid": f"orp-{j['id']}", "start": _day(j["orp_deadline"]),
                        "title": tr("ORP deadline: apply to {title} — {company}").format(title=j["title"], company=j["company"] or ""),
                        "text": link(j)})
    for j in store.followups_due(365):
        try:
            out.append({"uid": f"followup-{j['id']}", "start": _day(j["followup_date"]),
                        "title": tr("Follow up: {title} — {company}").format(title=j["title"], company=j["company"] or ""),
                        "text": link(j)})
        except ValueError:
            continue
    first = today.replace(day=1)
    for month_start in (first, (first + datetime.timedelta(days=32)).replace(day=1)):
        prev = month_start - datetime.timedelta(days=1)
        out.append({"uid": f"proofs-{prev:%Y-%m}", "start": month_start.replace(day=5),
                    "title": tr("Hand in the proofs of job search for {month}").format(month=prev.strftime("%m.%Y")),
                    "text": f"{base}/report?month={prev:%Y-%m}" if base else ""})
    s = weekly.summary(today)
    out.append({"uid": f"week-{s['monday']}", "start": _day(s["monday"]),
                "title": tr("Job search, week {week}: {n} new jobs").format(week=s["week"], n=s["new"]),
                "text": weekly.text(s) + (f"\n{base}/week" if base else "")})
    return out


def ics(today=None, base=""):
    stamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    lines = ["BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:-//Swiss Job Agent//EN", "CALSCALE:GREGORIAN", "METHOD:PUBLISH",
             "X-WR-CALNAME:" + _esc(tr("Job search")), "REFRESH-INTERVAL;VALUE=DURATION:PT6H", "X-PUBLISHED-TTL:PT6H"]
    for e in events(today, base):
        lines += ["BEGIN:VEVENT", f"UID:{e['uid']}@swiss-job-agent", f"DTSTAMP:{stamp}"]
        if isinstance(e["start"], datetime.datetime):
            lines += [f"DTSTART:{e['start']:%Y%m%dT%H%M%S}", f"DTEND:{e['end']:%Y%m%dT%H%M%S}"]
        else:
            lines += [f"DTSTART;VALUE=DATE:{e['start']:%Y%m%d}",
                      f"DTEND;VALUE=DATE:{e['start'] + datetime.timedelta(days=1):%Y%m%d}"]
        lines.append("SUMMARY:" + _esc(e["title"]))
        if e.get("text"):
            lines.append("DESCRIPTION:" + _esc(e["text"]))
        lines.append("END:VEVENT")
    lines.append("END:VCALENDAR")
    return "\r\n".join(_fold(x) for x in lines) + "\r\n"
