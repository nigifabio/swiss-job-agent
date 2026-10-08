"""Cover letter for one job, Swiss business-letter layout, rule-based (no language model):
the body comes from compose.letter_body, i.e. the candidate's own profile ranked against
the posting, in the posting's language when a translated profile exists. The user edits it
before sending.
"""
import io
import os
import re
import datetime

from . import compose
from .lang import detect_language


MONTHS = {
    "fr": ["janvier", "février", "mars", "avril", "mai", "juin", "juillet", "août",
           "septembre", "octobre", "novembre", "décembre"],
    "it": ["gennaio", "febbraio", "marzo", "aprile", "maggio", "giugno", "luglio", "agosto",
           "settembre", "ottobre", "novembre", "dicembre"],
    "de": ["Januar", "Februar", "März", "April", "Mai", "Juni", "Juli", "August",
           "September", "Oktober", "November", "Dezember"],
}
WORDS = {
    "fr": {"subject": "Objet : Candidature au poste de", "hello": "Madame, Monsieur,",
           "bye": "Je vous prie d'agréer, Madame, Monsieur, mes salutations distinguées.",
           "annex": "Annexe : CV", "date": "{place}, le {d} {m} {y}"},
    "it": {"subject": "Oggetto: Candidatura per la posizione di", "hello": "Gentili Signore e Signori,",
           "bye": "Distinti saluti.", "annex": "Allegato: CV", "date": "{place}, {d} {m} {y}"},
    "de": {"subject": "Bewerbung als", "hello": "Sehr geehrte Damen und Herren",
           "bye": "Freundliche Grüsse", "annex": "Beilage: Lebenslauf", "date": "{place}, {d}. {m} {y}"},
    "en": {"subject": "Application for the position of", "hello": "Dear Hiring Manager,",
           "bye": "Kind regards,", "annex": "Enclosure: CV", "date": "{place}, {d} {m} {y}"},
}
LANG_NAMES = {"fr": "French", "it": "Italian", "de": "German", "en": "English"}


def language(job):
    lang = detect_language(f"{job.get('title', '')}. {job.get('description') or ''}")
    return lang if lang in WORDS else "en"


def _date(lang, place):
    t = datetime.date.today()
    m = MONTHS.get(lang, [datetime.date(2000, i, 1).strftime("%B") for i in range(1, 13)])[t.month - 1]
    return WORDS[lang]["date"].format(place=place, d=t.day, m=m, y=t.year)


CITY = {  # Swiss city names in the letter's language
    "geneva": {"en": "Geneva", "fr": "Genève", "it": "Ginevra", "de": "Genf"},
    "genève": {"en": "Geneva", "fr": "Genève", "it": "Ginevra", "de": "Genf"},
    "zurich": {"en": "Zurich", "fr": "Zurich", "it": "Zurigo", "de": "Zürich"},
    "basel": {"en": "Basel", "fr": "Bâle", "it": "Basilea", "de": "Basel"},
    "bern": {"en": "Bern", "fr": "Berne", "it": "Berna", "de": "Bern"},
    "lucerne": {"en": "Lucerne", "fr": "Lucerne", "it": "Lucerna", "de": "Luzern"},
}


def _city(place, lang):
    return CITY.get(place.strip().lower(), {}).get(lang, place.strip())


def _frame(profile, job, lang, body):
    """Wrap a body (salutation excluded) in the sender/recipient/subject/closing layout."""
    w, c = WORDS[lang], profile.get("contact", {})
    place = _city((c.get("location") or "").split(",")[0], lang) or "Suisse"
    sender = [profile["name"]] + [v for v in (c.get("location"), c.get("phone"), c.get("email")) if v]
    recipient = [job.get("company") or "", job.get("location") or ""]
    # in the text the date sits above the signature; on the page (see pdf) the signature is at the
    # foot on the left and the place and date at the foot on the right, the recipient top right
    parts = ["\n".join(sender), "\n".join(x for x in recipient if x),
             f"{w['subject']} {(job.get('title') or '').strip()}", w["hello"], body.strip(), w["bye"],
             _date(lang, place), profile["name"], w["annex"]]
    return "\n\n".join(p for p in parts if p)


def write(profile, job):
    """Return (letter_text, how). Rule-based: the posting's language when the candidate has a
    profile version in it (else the profile's language, so the letter never mixes languages),
    paragraphs from the profile ranked against the posting (see compose.py)."""
    from . import tailor
    cv, lang = tailor.localized(profile, job)
    lang = lang if lang in WORDS else "en"
    return _frame(profile, job, lang, compose.letter_body(cv, job, lang)), "rules"


# ---- a letter kept under a name, for other jobs ------------------------------------------------
# What changes from one job to the next is written as {company}, {title}, {location} and {date}.
_DATE_LINE = re.compile(r"^[^\n]{0,40}\b\d{1,2}\.? [^\W\d]+ \d{4}$", re.M)


def to_template(text, job):
    """A job's letter with that job's company, title, place and the date turned into placeholders."""
    out = text or ""
    for key in ("title", "company", "location"):
        value = " ".join((job.get(key) or "").split())
        if len(value) >= 3:
            out = out.replace(value, "{" + key + "}")
    return _DATE_LINE.sub("{date}", out, count=1) if "{date}" not in out else out


def from_template(text, profile, job):
    """A kept letter for this job: the placeholders become this job's company, title, place and today's date."""
    lang = detect_language(text)
    lang = lang if lang in WORDS else "en"
    place = _city(((profile.get("contact") or {}).get("location") or "").split(",")[0], lang) or "Suisse"
    out = text or ""
    for key, value in (("title", (job.get("title") or "").strip()), ("company", job.get("company") or ""),
                       ("location", job.get("location") or ""), ("date", _date(lang, place))):
        out = out.replace("{" + key + "}", value)
    return out


def blank(profile):
    """A letter from the profile for no job in particular: the start of a named version."""
    text, _ = write(profile, {"title": "{title}", "company": "{company}", "location": "{location}", "description": ""})
    return to_template(text, {})


ANNEX = re.compile(r"^(annexes?|annex|enclosures?|beilagen?|allegat[oi])\b", re.I)
SUBJECT = re.compile(r"^(objet|oggetto|betreff|subject|bewerbung als|application for|concerne|re)\b", re.I)


def layout(text, name=""):
    """The letter's blocks by what they are: {"sender", "recipient", "subject", "body": [...], "date",
    "signature", "annex"}. Found by what a block looks like, not by its place, so an edited letter
    (a paragraph added, the date moved) still lays out."""
    blocks = [b.strip() for b in re.split(r"\n\s*\n", (text or "").replace("\r", "")) if b.strip()]
    out = {"sender": "", "recipient": "", "subject": "", "body": [], "date": "", "signature": "", "annex": ""}

    def short(b):
        return len(b) <= 160 and b.count("\n") <= 4 and not re.search(r"[.!?]\s*$", b)
    if blocks and short(blocks[0]) and not SUBJECT.match(blocks[0]):
        out["sender"] = blocks.pop(0)
    if blocks and ANNEX.match(blocks[-1]):
        out["annex"] = blocks.pop()
    for b in list(blocks):
        if not out["date"] and "\n" not in b and (_DATE_LINE.match(b) or b == "{date}"):
            out["date"] = b
            blocks.remove(b)
    if blocks and name and blocks[-1].strip().lower() == name.strip().lower():
        out["signature"] = blocks.pop()
    for b in list(blocks[:2]):                         # what stands between the sender and the subject is the recipient
        if SUBJECT.match(b):
            break
        if short(b) and not out["recipient"]:
            out["recipient"] = b
            blocks.remove(b)
            break
    if blocks and SUBJECT.match(blocks[0]):
        out["subject"] = blocks.pop(0)
    out["body"] = blocks
    return out


def pdf(profile, job, text, out):
    """Swiss letter page: sender top left, recipient below it on the right, subject, text, and at the
    foot the signature on the left with the place and date on the right. The type grows for a short
    letter so the page isn't left half empty."""
    from reportlab.lib.enums import TA_JUSTIFY, TA_RIGHT
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import mm
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
    from xml.sax.saxutils import escape as esc

    lay = layout(text, profile.get("name", ""))
    base = getSampleStyleSheet()["Normal"]
    width = A4[0] - 45 * mm - 12          # the text column (the frame pads 6 pt each side)

    def build(size, lead, gap, target):
        plain = ParagraphStyle("p", parent=base, fontSize=size, leading=lead)
        body = ParagraphStyle("b", parent=plain, alignment=TA_JUSTIFY)
        right = ParagraphStyle("r", parent=plain, alignment=TA_RIGHT)
        para = lambda b, st: Paragraph(esc(b).replace("\n", "<br/>"), st)       # noqa: E731
        tight = TableStyle([("LEFTPADDING", (0, 0), (-1, -1), 0), ("RIGHTPADDING", (0, 0), (-1, -1), 0), ("VALIGN", (0, 0), (-1, -1), "BOTTOM")])
        flow = []
        if lay["sender"]:
            flow += [para(lay["sender"], plain), Spacer(1, 2 * gap * mm)]
        if lay["recipient"]:                               # under the sender, on the right half
            flow += [Table([["", para(lay["recipient"], plain)]], colWidths=[width * 0.56, width * 0.44], style=tight), Spacer(1, 3 * gap * mm)]
        if lay["subject"]:
            flow += [Paragraph(f"<b>{esc(lay['subject'])}</b>", plain), Spacer(1, 1.6 * gap * mm)]
        for b in lay["body"]:
            flow += [para(b, body), Spacer(1, gap * mm)]
        if lay["signature"] or lay["date"]:                # foot of the letter: signature left, place and date right
            flow += [Spacer(1, 2.5 * gap * mm),
                     Table([[para(lay["signature"], plain), para(lay["date"], right)]], colWidths=[width * 0.5, width * 0.5], style=tight)]
        if lay["annex"]:
            flow += [Spacer(1, 2 * gap * mm), para(lay["annex"], ParagraphStyle("a", parent=plain, fontSize=size - 1.5))]
        doc = SimpleDocTemplate(target, pagesize=A4, leftMargin=25 * mm, rightMargin=20 * mm, topMargin=22 * mm,
                                bottomMargin=20 * mm, title=f"{profile['name']} — {job.get('company') or ''}", author=profile["name"])
        doc.build(flow)
        return doc.page
    # the largest type that keeps the letter on one page: a short letter fills its page, a long one still fits
    choices = [(12.5, 19, 6), (12, 18, 5.5), (11.5, 17, 5), (11, 16, 4.5), (10.5, 15, 4), (10, 14, 3.4), (9.5, 13, 2.8)]
    best = next((c for c in choices if build(*c, io.BytesIO()) == 1), choices[-1])
    size, lead, gap = best                             # then open up the spacing while it still fits: the foot goes down the page
    for wider in (gap * f for f in (1.25, 1.5, 1.8, 2.2, 2.7)):
        if build(size, lead, wider, io.BytesIO()) != 1:
            break
        best = (size, lead, wider)
    os.makedirs(os.path.dirname(out), exist_ok=True)
    build(*best, out)
    return out


def config_note():
    """What the user sees under "Cover letter"."""
    return ("A draft built from your profile for this posting and company: review and personalise it "
            "before sending.")
