"""Application statistics and the ORP/RAV report ("Preuves des recherches personnelles
en vue de trouver un emploi"): one row per application in a week or a month, with the
columns the unemployment office asks for. Also the numbers for the Stats page."""
import csv
import io
import os
import datetime
import urllib.parse
from collections import Counter

from . import commute, config, filters, store

def target():
    """Applications per month the ORP / RAV asked for (Settings page, else ORP_MONTHLY_TARGET)."""
    from . import config
    return config.ORP_MONTHLY_TARGET


def month_progress(today=None):
    """Where the person stands against the monthly target, for the reminder on the home page:
    this month's count, days left, and (until the 5th) last month's report still to hand in."""
    today = today or datetime.date.today()
    first = today.replace(day=1)
    nxt = (first + datetime.timedelta(days=32)).replace(day=1)
    done = len(store.applications(first.isoformat(), (nxt - datetime.timedelta(days=1)).isoformat()))
    days_left = (nxt - today).days - 1
    goal = target()
    prev_last = first - datetime.timedelta(days=1)
    prev = {"key": prev_last.strftime("%Y-%m"), "label": prev_last.strftime("%m.%Y"),
            "n": len(store.applications(prev_last.replace(day=1).isoformat(), prev_last.isoformat()))} if today.day <= 5 else None
    return {"done": done, "target": goal, "missing": max(0, goal - done), "days_left": days_left,
            "urgent": done < goal and days_left <= 10, "month": today.strftime("%m.%Y"), "last_month": prev}
RESULT = {"applied": "En suspens", "shortlisted": "En suspens", "new": "En suspens",
          "interview": "En suspens – entretien", "offer": "Offre reçue", "rejected": "Refus",
          "discarded": "En suspens"}
COLUMNS = ["Date", "Entreprise, lieu", "Personne de contact", "Poste", "Taux", "Type de candidature",
           "Assign. ORP", "Résultat"]
LINK = "Lien de l'annonce"          # the posting applied to: extra column in the CSV, a link in the page and the PDF


def _http_url(u):
    u = (u or "").strip()
    return u if urllib.parse.urlsplit(u).scheme in ("http", "https") else ""


# ---- periods -------------------------------------------------------------
def month_bounds(ym):
    y, m = map(int, ym.split("-"))
    start = datetime.date(y, m, 1)
    end = (start.replace(day=28) + datetime.timedelta(days=4)).replace(day=1) - datetime.timedelta(days=1)
    return start, end


def week_bounds(yw):
    y, w = yw.split("-W")
    start = datetime.date.fromisocalendar(int(y), int(w), 1)
    return start, start + datetime.timedelta(days=6)


def period(month=None, week=None):
    """(kind, key, start, end, label) for ?month=YYYY-MM or ?week=YYYY-Www (default: this month)."""
    if week:
        s, e = week_bounds(week)
        return "week", week, s, e, f"semaine {week.split('-W')[1]} ({s:%d.%m} – {e:%d.%m.%Y})"
    ym = month or datetime.date.today().strftime("%Y-%m")
    s, e = month_bounds(ym)
    return "month", ym, s, e, f"{s:%m.%Y}"


def shift(kind, key, n):
    if kind == "week":
        s, _ = week_bounds(key)
        y, w, _ = (s + datetime.timedelta(weeks=n)).isocalendar()
        return f"{y}-W{w:02d}"
    s, _ = month_bounds(key)
    y, m = divmod(s.year * 12 + s.month - 1 + n, 12)
    return f"{y}-{m + 1:02d}"


# ---- ORP rows --------------------------------------------------------------
def rows(start, end):
    out = []
    for j in store.applications(start.isoformat(), end.isoformat()):
        result = RESULT.get(j["status"], "En suspens")
        if j["status"] == "rejected" and j.get("outcome_note"):
            result += f" ({j['outcome_note']})"
        out.append({
            "id": j["id"],
            "Date": datetime.date.fromisoformat(j["applied_date"]).strftime("%d.%m.%Y"),
            "Entreprise, lieu": ", ".join(x for x in (j.get("company"), j.get("location")) if x),
            "Personne de contact": j.get("contact") or "",
            "Poste": j.get("title") or "",
            LINK: _http_url(j.get("url")),
            "Taux": j.get("work_rate") or store.guess_work_rate(j.get("title")),
            "Type de candidature": store.APPLY_METHODS.get(j.get("apply_method") or "written"),
            "Assign. ORP": "Oui" if j.get("orp_assigned") else "Non",
            "Résultat": result,
        })
    return out


def to_csv(rs):
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=COLUMNS + [LINK], extrasaction="ignore", delimiter=";")
    w.writeheader()
    w.writerows(rs)
    return "﻿" + buf.getvalue()   # BOM so Excel opens accents correctly


def to_pdf(rs, label, name, out):
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import mm
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
    from xml.sax.saxutils import escape as esc, quoteattr

    ss = getSampleStyleSheet()
    cell = ParagraphStyle("c", parent=ss["Normal"], fontSize=8, leading=10)
    head = [Paragraph(f"<b>{esc(c)}</b>", cell) for c in COLUMNS]
    def text(r, c):          # the posting's address under the job title, clickable
        t = esc(str(r[c]))
        if c == "Poste" and r.get(LINK):
            shown = esc(r[LINK].split("://", 1)[-1])          # readable on paper too
            t += f'<br/><link href={quoteattr(r[LINK])} color="#1F4E78"><font size="6">{shown}</font></link>'
        return t
    data = [head] + [[Paragraph(text(r, c), cell) for c in COLUMNS] for r in rs]
    widths = [22 * mm, 55 * mm, 38 * mm, 54 * mm, 18 * mm, 32 * mm, 24 * mm, 34 * mm]
    t = Table(data, colWidths=widths, repeatRows=1)
    t.setStyle(TableStyle([("GRID", (0, 0), (-1, -1), 0.4, colors.grey),
                           ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e8eef5")),
                           ("VALIGN", (0, 0), (-1, -1), "TOP")]))
    flow = [Paragraph("Preuves des recherches personnelles en vue de trouver un emploi", ss["Title"]),
            Paragraph(f"Nom, prénom : <b>{esc(name)}</b> &nbsp;&nbsp; N° AVS : ______________ "
                      f"&nbsp;&nbsp; Période : <b>{esc(label)}</b> &nbsp;&nbsp; Recherches : <b>{len(rs)}</b>",
                      ss["Normal"]), Spacer(1, 5 * mm), t, Spacer(1, 8 * mm),
            Paragraph("Relevé établi à partir du suivi de candidatures. À reporter dans Job-Room "
                      "(work.swiss) ou à joindre au formulaire officiel selon les consignes de votre ORP, "
                      "au plus tard le 5 du mois suivant.", cell),
            Spacer(1, 10 * mm), Paragraph("Date : ____________________ &nbsp;&nbsp;&nbsp;&nbsp; "
                                          "Signature : ______________________________", ss["Normal"])]
    os.makedirs(os.path.dirname(out), exist_ok=True)
    SimpleDocTemplate(out, pagesize=landscape(A4), leftMargin=10 * mm, rightMargin=10 * mm,
                      topMargin=10 * mm, bottomMargin=10 * mm,
                      title=f"Recherches d'emploi {label} — {name}", author=name).build(flow)
    return out


# ---- why jobs were discarded -----------------------------------------------
# What each reason suggests changing in Settings.
HINTS = {
    "wrong_role": "Skip titles with a word these jobs share (one click below), or tighten \"Keep titles containing\".",
    "too_senior": "Add words like senior, lead, head, responsable to \"Skip titles containing\".",
    "too_junior": "Add words like junior, stage, stagiaire, apprenti* to \"Skip titles containing\".",
    "location": "Stop searching the towns below with one click, or set a maximum travel time in Settings.",
    "language": "Remove that language from the posting languages.",
    "workload": "Add words like temporaire, 20%, stage to \"Skip titles containing\".",
    "company": "Never show a company or an agency again with one click below.",
    "duplicate": "The same job came from two sites with different wording: tell the administrator which ones.",
}


def _title_words(titles, limit=10):
    from .compose import _tokens
    c = Counter(w for t in titles for w in set(_tokens(t)) if len(w) > 3 and not w.isdigit())
    return [(w, n) for w, n in c.most_common(limit) if n > 1]


def discard_stats():
    """Reasons given when discarding, most frequent first, with where those postings came from and
    (for "not my kind of job") the title words they share: what to change in the search."""
    jobs = store.discarded()
    by = {}
    for j in jobs:
        by.setdefault(j["discard_reason"] or "", []).append(j)
    rows = []
    for key, js in sorted(by.items(), key=lambda kv: (-len(kv[1]), kv[0])):
        rows.append({
            "key": key, "label": store.DISCARD_REASONS.get(key, "No reason given"), "n": len(js),
            "sources": Counter(j["source"] or "?" for j in js).most_common(4),
            "words": [(w, n) for w, n in _title_words([j["title"] or "" for j in js]) if not any(filters._hit(k, w) for k in config.TITLE_EXCLUDE)]
            if key in ("wrong_role", "too_senior", "too_junior", "workload") else [],
            # one-click fixes: towns still searched, companies not blocked yet
            "towns": [(t, n) for t, n in Counter(commute.town(j["location"]).lower() for j in js).most_common(6)
                      if t and t in config.LOCATION_KEYWORDS] if key == "location" else [],
            "companies": [(c, n) for c, n in Counter((j["company"] or "").strip() for j in js).most_common(6)
                          if c and filters.company_ok(c)] if key == "company" else [],
            "hint": HINTS.get(key, ""),
        })
    return {"total": len(jobs), "with_reason": sum(1 for j in jobs if j["discard_reason"]), "rows": rows}


def discarded_csv():
    buf = io.StringIO()
    w = csv.writer(buf, delimiter=";")
    w.writerow(["Discarded on", "Reason", "Title", "Company", "Location", "Source", "Score"])
    for j in store.discarded():
        w.writerow([(j["discarded_at"] or "")[:10], store.DISCARD_REASONS.get(j["discard_reason"] or "", ""),
                    j["title"] or "", j["company"] or "", j["location"] or "", j["source"] or "", j["score"] if j["score"] is not None else ""])
    return "\ufeff" + buf.getvalue()


# ---- stats -----------------------------------------------------------------
def _reached(history):
    """job_id -> {status: first date it was reached}"""
    out = {}
    for h in history:
        out.setdefault(h["job_id"], {}).setdefault(h["status"], h["changed_at"][:10])
    return out


def stats(today=None):
    today = today or datetime.date.today()
    applied = store.all_applied()
    reached = _reached(store.history_all())
    for j in applied:
        # jobs moved straight to interview/offer/rejected also count as "reached" those steps
        reached.setdefault(j["id"], {}).setdefault(j["status"], j["applied_date"])
    n = len(applied)
    got = lambda st: sum(1 for j in applied if st in reached.get(j["id"], {}) or j["status"] == st)  # noqa: E731
    interviews, offers, rejected = got("interview"), got("offer"), got("rejected")
    answered = sum(1 for j in applied if {"interview", "offer", "rejected"} & set(reached.get(j["id"], {}))
                   or j["status"] in ("interview", "offer", "rejected"))
    waits = []
    for j in applied:
        r = reached.get(j["id"], {})
        firsts = [r[s] for s in ("interview", "offer", "rejected") if s in r]
        if firsts:
            waits.append((datetime.date.fromisoformat(min(firsts)) - datetime.date.fromisoformat(j["applied_date"])).days)

    def bucket(key_fn, keys):
        c = Counter(key_fn(datetime.date.fromisoformat(j["applied_date"])) for j in applied)
        return [(k, c.get(k, 0)) for k in keys]

    weeks = []
    for i in range(11, -1, -1):
        y, w, _ = (today - datetime.timedelta(weeks=i)).isocalendar()
        weeks.append(f"{y}-W{w:02d}")
    months = [shift("month", today.strftime("%Y-%m"), -i) for i in range(11, -1, -1)]
    this_month = sum(1 for j in applied if j["applied_date"][:7] == today.strftime("%Y-%m"))
    this_week_key = "{}-W{:02d}".format(*today.isocalendar()[:2])
    return {
        "applied": n, "interviews": interviews, "offers": offers, "rejected": rejected,
        "pending": n - answered,
        "response_rate": round(100 * answered / n) if n else None,
        "interview_rate": round(100 * interviews / n) if n else None,
        "avg_wait": round(sum(waits) / len(waits)) if waits else None,
        "this_month": this_month, "target": target(), "this_week_key": this_week_key,
        "this_week": sum(1 for j in applied
                         if "{}-W{:02d}".format(*datetime.date.fromisoformat(j["applied_date"]).isocalendar()[:2])
                         == this_week_key),
        "weeks": bucket(lambda d: "{}-W{:02d}".format(*d.isocalendar()[:2]), weeks),
        "months": bucket(lambda d: d.strftime("%Y-%m"), months),
        "funnel": [("Applied", n), ("Interview", interviews), ("Offer", offers)],
        "by_source": Counter(j.get("source") or "manual" for j in applied).most_common(8),
        "by_method": Counter(store.APPLY_METHODS.get(j.get("apply_method") or "written") for j in applied).most_common(),
    }
