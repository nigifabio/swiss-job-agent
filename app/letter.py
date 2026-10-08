"""Cover letter for one job, Swiss business-letter layout, rule-based (no language model):
the body comes from compose.letter_body, i.e. the candidate's own profile ranked against
the posting, in the posting's language when a translated profile exists. The user edits it
before sending.
"""
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
    parts = ["\n".join(sender), "\n".join(x for x in recipient if x), _date(lang, place),
             f"{w['subject']} {(job.get('title') or '').strip()}", w["hello"], body.strip(), w["bye"],
             profile["name"], w["annex"]]
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


def pdf(profile, job, text, out):
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import mm
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
    from xml.sax.saxutils import escape as esc

    base = getSampleStyleSheet()["Normal"]
    body = ParagraphStyle("b", parent=base, fontSize=10.5, leading=15)
    flow = []
    for block in text.split("\n\n"):
        flow += [Paragraph(esc(block).replace("\n", "<br/>"), body), Spacer(1, 4 * mm)]
    os.makedirs(os.path.dirname(out), exist_ok=True)
    SimpleDocTemplate(out, pagesize=A4, leftMargin=25 * mm, rightMargin=20 * mm, topMargin=20 * mm,
                      bottomMargin=20 * mm, title=f"{profile['name']} — {job.get('company') or ''}",
                      author=profile["name"]).build(flow)
    return out


def config_note():
    """What the user sees under "Cover letter"."""
    return ("A draft built from your profile for this posting and company: review and personalise it "
            "before sending.")
