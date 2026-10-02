"""Application statistics and the ORP/RAV report ("Preuves des recherches personnelles
en vue de trouver un emploi"): one row per application in a week or a month, with the
columns the unemployment office asks for. Also the numbers for the Stats page."""
import csv
import io
import os
import datetime
from collections import Counter

from . import store

TARGET = int(os.environ.get("ORP_MONTHLY_TARGET", "10"))   # searches/month the ORP asked for
RESULT = {"applied": "En suspens", "shortlisted": "En suspens", "new": "En suspens",
          "interview": "En suspens – entretien", "offer": "Offre reçue", "rejected": "Refus",
          "discarded": "En suspens"}
COLUMNS = ["Date", "Entreprise, lieu", "Personne de contact", "Poste", "Taux", "Type de candidature",
           "Assign. ORP", "Résultat"]


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
            "Taux": j.get("work_rate") or store.guess_work_rate(j.get("title")),
            "Type de candidature": store.APPLY_METHODS.get(j.get("apply_method") or "written"),
            "Assign. ORP": "Oui" if j.get("orp_assigned") else "Non",
            "Résultat": result,
        })
    return out


def to_csv(rs):
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=COLUMNS, extrasaction="ignore", delimiter=";")
    w.writeheader()
    w.writerows(rs)
    return "﻿" + buf.getvalue()   # BOM so Excel opens accents correctly


def to_pdf(rs, label, name, out):
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import mm
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
    from xml.sax.saxutils import escape as esc

    ss = getSampleStyleSheet()
    cell = ParagraphStyle("c", parent=ss["Normal"], fontSize=8, leading=10)
    head = [Paragraph(f"<b>{esc(c)}</b>", cell) for c in COLUMNS]
    data = [head] + [[Paragraph(esc(str(r[c])), cell) for c in COLUMNS] for r in rs]
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
        "this_month": this_month, "target": TARGET, "this_week_key": this_week_key,
        "this_week": sum(1 for j in applied
                         if "{}-W{:02d}".format(*datetime.date.fromisoformat(j["applied_date"]).isocalendar()[:2])
                         == this_week_key),
        "weeks": bucket(lambda d: "{}-W{:02d}".format(*d.isocalendar()[:2]), weeks),
        "months": bucket(lambda d: d.strftime("%Y-%m"), months),
        "funnel": [("Applied", n), ("Interview", interviews), ("Offer", offers)],
        "by_source": Counter(j.get("source") or "manual" for j in applied).most_common(8),
        "by_method": Counter(store.APPLY_METHODS.get(j.get("apply_method") or "written") for j in applied).most_common(),
    }
