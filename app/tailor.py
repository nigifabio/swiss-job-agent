"""On-demand CV tailoring: builds a PDF CV for one job from the candidate's factual
profile (PROFILE_PATH, JSON), re-ordering expertise and leading with the skills the
posting mentions. Never invents experience. No language model: translated profiles
(profile.<lang>.json, reviewed by the candidate) give the CV in the posting's language.

Profile JSON keys: name, contact{email,phone,linkedin,location}, headline, summary,
expertise[], experience[{title,org,loc,dates,bullets[]}], education[], extras_title, extras[]
"""
import os
import re
import json

from . import compose, config, filters
from .lang import detect_language

CV_DIR = os.path.join(os.path.dirname(config.DB_PATH) or ".", "cv")


def load_profile():
    try:
        with open(config.PROFILE_PATH) as f:
            return json.load(f)
    except (OSError, ValueError):
        return None


def cv_path(jid):
    return os.path.join(CV_DIR, f"{int(jid)}.pdf")


CUSTOM_CV = os.path.join(CV_DIR, "custom.pdf")


def _profile_text(profile):
    parts = [profile.get("headline", ""), profile.get("summary", "")] + profile.get("expertise", [])
    for e in profile.get("experience", []):
        parts += [e.get("title", "")] + e.get("bullets", [])
    parts += profile.get("education", []) + profile.get("extras", [])
    return " ".join(parts).lower()


def split_keywords(profile, keywords):
    """(supported, unsupported): a keyword is supported only if the profile already mentions it."""
    text, sup, unsup = _profile_text(profile), [], []
    for k in keywords:
        term = k.strip().lower().rstrip("*")
        if not term:
            continue
        hit = re.search(r"(?<!\w)" + re.escape(term) + ("" if k.strip().endswith("*") else r"(?!\w)"), text)
        (sup if hit else unsup).append(k.strip())
    return sup, unsup


def download_name(profile, job):
    who = re.sub(r"[^A-Za-z0-9]+", "_", profile.get("name", "CV")).strip("_")
    org = re.sub(r"[^A-Za-z0-9]+", "_", job.get("company") or "role").strip("_")[:40]
    return f"{who}_CV_{org}.pdf"


def _ordered_expertise(profile, hits):
    words = set(" ".join(hits).split())
    return sorted(profile.get("expertise", []),
                  key=lambda e: 0 if words & set(e.lower().replace("&", " ").split()) else 1)


HEADINGS = {
    "en": ("PROFILE", "AREAS OF EXPERTISE", "KEY SKILLS", "PROFESSIONAL EXPERIENCE", "EDUCATION"),
    "fr": ("PROFIL", "DOMAINES D'EXPERTISE", "COMPÉTENCES CLÉS", "EXPÉRIENCE PROFESSIONNELLE", "FORMATION"),
    "it": ("PROFILO", "AREE DI COMPETENZA", "COMPETENZE CHIAVE", "ESPERIENZA PROFESSIONALE", "FORMAZIONE"),
    "de": ("PROFIL", "KOMPETENZEN", "SCHLÜSSELKOMPETENZEN", "BERUFSERFAHRUNG", "AUSBILDUNG"),
}
def _profile_lang(profile):
    return detect_language(" ".join([profile.get("summary", "")] + [
        b for e in profile.get("experience", []) for b in e.get("bullets", [])]))


def _fields(profile):
    return {"expertise": profile.get("expertise", []), "education": profile.get("education", []),
            "extras": profile.get("extras", []),
            "experience": [e.get("bullets", []) for e in profile.get("experience", [])]}


def _same_shape(a, b):
    fa, fb = _fields(a), _fields(b)
    return (all(len(fa[k]) == len(fb[k]) for k in ("expertise", "education", "extras", "experience"))
            and all(len(x) == len(y) for x, y in zip(fa["experience"], fb["experience"])))


def translated_path(lang):
    base, ext = os.path.splitext(config.PROFILE_PATH)
    return f"{base}.{lang}{ext}"


def profile_versions():
    """{lang: "ok" | "ignored: reason"} for the translated profiles next to profile.json."""
    base = load_profile()
    out = {}
    if not base:
        return out
    out[_profile_lang(base)] = "ok (original)"
    for lang in HEADINGS:
        path = translated_path(lang)
        if not os.path.exists(path):
            continue
        try:
            with open(path) as f:
                tr = json.load(f)
        except (OSError, ValueError) as e:
            out[lang] = f"ignored: unreadable ({type(e).__name__})"
            continue
        out[lang] = "ok" if _same_shape(tr, base) else "ignored: jobs or bullet points differ from profile.json"
    return out


def localized(profile, job):
    """(profile, lang) for a job: the translated profile in the posting's language when one exists
    and matches profile.json item for item (name/contact always from profile.json); otherwise
    the profile as is, in its own language."""
    from .letter import language           # posting language, same rule as cover letters
    lang, own = language(job), _profile_lang(profile)
    if lang != own and lang in HEADINGS and os.path.exists(translated_path(lang)):
        try:
            with open(translated_path(lang)) as f:
                tr = json.load(f)
        except (OSError, ValueError):
            tr = None
        if isinstance(tr, dict) and _same_shape(tr, profile):
            merged = dict(profile)
            merged.update({k: v for k, v in tr.items() if k not in ("name", "contact")})
            merged["experience"] = [dict(e, **{k: t.get(k, e.get(k)) for k in ("title", "loc", "dates", "bullets")})
                                    for e, t in zip(profile.get("experience", []), tr.get("experience", []))]
            return merged, lang
    return profile, own if own in HEADINGS else "en"


def build(job, profile):
    """CV for one job: in the posting's language when a translated profile exists, summary and
    bullet order chosen for the posting (rule-based, see compose.py)."""
    cv, lang = localized(profile, job)
    return render(cv, filters.matched(job), cv_path(job["id"]), company=job.get("company") or "", lang=lang,
                  summary=compose.summary(cv, job, lang), job=job)


def build_custom(profile, keywords):
    """CV around a user-typed keyword list. Returns (path, supported, unsupported)."""
    sup, unsup = split_keywords(profile, keywords)
    summary = profile.get("summary", "")
    lang = _profile_lang(profile)
    return render(profile, [k.lower() for k in sup], CUSTOM_CV, key_skills=sup, summary=summary,
                  lang=lang if lang in HEADINGS else "en"), sup, unsup


def _by_relevance(bullets, job):
    terms, skills = compose.posting_terms(job), filters.matched(job)
    return [b for _, b in sorted(enumerate(bullets), key=lambda ib: (-compose._score(ib[1], terms, skills), ib[0]))]


def _bullet_first(bullets, hits):
    return sorted(bullets, key=lambda b: 0 if any(h in b.lower() for h in hits) else 1)


def render(profile, hits, out, company="", key_skills=None, summary=None, lang="en", job=None):
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import mm
    from reportlab.platypus import (SimpleDocTemplate, Paragraph, HRFlowable,
                                    ListFlowable, ListItem)
    from xml.sax.saxutils import escape as esc

    H = HEADINGS.get(lang, HEADINGS["en"])
    blue, grey = colors.HexColor("#1F4E78"), colors.HexColor("#555555")
    base = getSampleStyleSheet()["Normal"]
    st = {
        "name": ParagraphStyle("name", parent=base, fontSize=20, leading=24, textColor=blue),
        "headline": ParagraphStyle("hl", parent=base, fontSize=11, leading=14, textColor=blue),
        "contact": ParagraphStyle("ct", parent=base, fontSize=8.5, textColor=grey, spaceAfter=6),
        "head": ParagraphStyle("hd", parent=base, fontSize=11, leading=14, textColor=blue,
                               spaceBefore=8, spaceAfter=3),
        "role": ParagraphStyle("rl", parent=base, fontSize=10.5, leading=13),
        "sub": ParagraphStyle("sb", parent=base, fontSize=8.5, textColor=grey, spaceAfter=2),
        "body": ParagraphStyle("bd", parent=base, fontSize=9, leading=12.5, spaceAfter=2),
        "bullet": ParagraphStyle("bl", parent=base, fontSize=8.7, leading=11.5),
    }
    c = profile.get("contact", {})
    contact = " &nbsp;|&nbsp; ".join(esc(v) for v in
                                     (c.get("email"), c.get("phone"), c.get("linkedin"), c.get("location")) if v)
    flow = [Paragraph(esc(profile["name"]), st["name"])]
    if profile.get("headline"):
        flow.append(Paragraph(esc(profile["headline"]), st["headline"]))
    flow += [Paragraph(contact, st["contact"]),
             HRFlowable(width="100%", thickness=1, color=blue, spaceAfter=6),
             Paragraph(H[0], st["head"]),
             Paragraph(esc(summary if summary is not None else profile.get("summary", "")), st["body"])]
    if profile.get("expertise"):
        flow += [Paragraph(H[1], st["head"]),
                 Paragraph(" &nbsp;•&nbsp; ".join(esc(e) for e in _ordered_expertise(profile, hits)), st["body"])]
    if key_skills:
        flow += [Paragraph(H[2], st["head"]),
                 Paragraph(" &nbsp;•&nbsp; ".join(esc(k) for k in key_skills), st["body"])]
    flow.append(Paragraph(H[3], st["head"]))
    for e in profile.get("experience", []):
        where = ", ".join(x for x in (e.get("org", ""), e.get("loc", "")) if x)      # either may be missing
        flow.append(Paragraph(f'<b>{esc(e["title"])}</b>' + (f" — {esc(where)}" if where else ""), st["role"]))
        flow.append(Paragraph(esc(e.get("dates", "")), st["sub"]))
        bullets = (_by_relevance(e.get("bullets", []), job) if job else _bullet_first(e.get("bullets", []), hits))
        if bullets:                                    # a job listed without details: no (empty) list
            flow.append(ListFlowable([ListItem(Paragraph(esc(b), st["bullet"]), leftIndent=8) for b in bullets],
                                     bulletType="bullet", start="•", leftIndent=10, spaceAfter=4))
    if profile.get("education"):
        flow.append(Paragraph(H[4], st["head"]))
        flow += [Paragraph(esc(ed), st["body"]) for ed in profile["education"]]
    if profile.get("extras"):
        flow.append(Paragraph(esc(profile.get("extras_title", "ADDITIONAL")), st["head"]))
        flow += [Paragraph(esc(x), st["body"]) for x in profile["extras"]]

    os.makedirs(CV_DIR, exist_ok=True)
    SimpleDocTemplate(out, pagesize=A4, leftMargin=16 * mm, rightMargin=16 * mm,
                      topMargin=14 * mm, bottomMargin=14 * mm,
                      title=f"{profile['name']} — CV" + (f" — {company}" if company else ""),
                      author=profile["name"]).build(flow)
    return out


def cv_note():
    """End-user description of the job CV, shown next to the button."""
    langs = [k for k, v in profile_versions().items() if v.startswith("ok")]
    where = f" ({', '.join(langs)})" if len(langs) > 1 else ""
    from . import i18n
    a, b = {"fr": ("Dans la langue de l'annonce quand votre profil existe dans cette langue",
                   " ; résumé et ordre des points choisis pour cette offre, à partir de votre propre profil."),
            "de": ("In der Sprache des Inserats, wenn Ihr Profil in dieser Sprache vorliegt",
                   "; Kurzprofil und Reihenfolge der Punkte für diese Stelle gewählt, aus Ihrem eigenen Profil."),
            "it": ("Nella lingua dell'annuncio quando il tuo profilo esiste in quella lingua",
                   "; riassunto e ordine dei punti scelti per questa offerta, a partire dal tuo profilo.")}.get(
        i18n.current(), ("In the posting's language when your profile has a version in it",
                         "; summary and bullet order chosen for this job, from your own profile."))
    return a + where + b
