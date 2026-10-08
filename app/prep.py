"""One-page interview preparation sheet (PDF) for a job: what the posting asks for against the
person's skills, their most relevant experience, usual questions, questions to ask, practical details.
Rule-based like the CV and the letter; in the posting's language when the profile exists in it."""
import os

from . import compose, skills, tailor


def path(jid):
    return os.path.join(tailor.CV_DIR, f"prep-{int(jid)}.pdf")


def build(job, profile):
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import mm
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, ListFlowable, ListItem
    from xml.sax.saxutils import escape as esc

    cv, lang = tailor.localized(profile, job)
    w = compose.PREP.get(lang) or compose.PREP["en"]
    _, have, missing, _ = skills.analyse(job.get("description") or "")
    bullets = [b for e in cv.get("experience", []) for b in e.get("bullets", [])] or list(cv.get("expertise", []))
    top = tailor._by_relevance(bullets, job)[:4]

    ss = getSampleStyleSheet()
    blue = colors.HexColor("#1F4E78")
    h1 = ParagraphStyle("h1", parent=ss["Title"], fontSize=16, leading=19, alignment=0, textColor=blue, spaceAfter=2)
    sub = ParagraphStyle("sub", parent=ss["Normal"], fontSize=10, leading=13, textColor=colors.HexColor("#555555"))
    h2 = ParagraphStyle("h2", parent=ss["Normal"], fontSize=11, leading=14, textColor=blue, spaceBefore=8, spaceAfter=3)
    body = ParagraphStyle("b", parent=ss["Normal"], fontSize=9.5, leading=12.5)

    def lst(items):
        return ListFlowable([ListItem(Paragraph(esc(i), body), leftIndent=8) for i in items],
                            bulletType="bullet", start="•", leftIndent=10)

    flow = [Paragraph(esc(w["title"]), h1),
            Paragraph(esc(" — ".join(x for x in ((job.get("title") or "").strip(), job.get("company") or "", job.get("location") or "") if x)), sub)]
    if have or missing:
        flow.append(Paragraph(esc(w["asks"]), h2))
        if have:
            flow.append(Paragraph(f"<b>{esc(w['have'])} :</b> " + esc(", ".join(have[:14])), body))
        if missing:
            flow.append(Paragraph(f"<b>{esc(w['gap'])} :</b> " + esc(", ".join(missing[:10])), body))
    if top:
        flow += [Paragraph(esc(w["yours"]), h2), lst(top)]
    flow += [Paragraph(esc(w["q"]), h2), lst(w["questions"]), Paragraph(esc(w["ask"]), h2), lst(w["theirs"])]
    facts = []
    if job.get("applied_date"):
        facts.append(f"{w['applied']} {job['applied_date']}")
    if job.get("contact"):
        facts.append(f"{w['contact']} : {job['contact']}")
    if job.get("commute_min") is not None:
        facts.append(f"{w['travel']} : {job['commute_min']} {w['min']}")
    if job.get("url"):
        facts.append(str(job["url"])[:110])
    if facts:
        flow += [Paragraph(esc(w["practical"]), h2), lst(facts)]
    flow.append(Spacer(1, 2 * mm))
    out = path(job["id"])
    os.makedirs(os.path.dirname(out), exist_ok=True)
    SimpleDocTemplate(out, pagesize=A4, leftMargin=18 * mm, rightMargin=18 * mm, topMargin=15 * mm, bottomMargin=14 * mm,
                      title=f"{w['title']} — {job.get('company') or ''}", author=profile.get("name", "")).build(flow)
    return out
