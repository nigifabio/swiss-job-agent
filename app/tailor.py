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
    if profile.get("_fixed_expertise"):
        return list(profile.get("expertise", []))          # the profile put its skills in the order it wants
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
    """(profile, lang) for a job, as the profile the job is tagged with shows it (see profiles.py; the
    main profile shows everything). The translated profile has the same shape, so the choice applies to it too."""
    from . import profiles
    cv, lang = _translated(profile, job)
    return profiles.apply_view(cv, job.get("profile")), lang


def _translated(profile, job):
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


# ---- the CV of a job as text the person can edit before the PDF is made ------------------------
# "## " starts a section, "### " a job (its next line: the dates), "- " a point. Name, title and
# contact details are not in the text: they come from the profile.
MAX_CV_TEXT = 20000
PHOTO = os.path.join(os.path.dirname(config.DB_PATH) or ".", "photo.jpg")


def draft_text(job, profile):
    """The CV for one job, written out: same choices as build() (posting's language when a translated
    profile exists, summary for the posting, skills and points the posting asks for first)."""
    cv, lang = localized(profile, job)
    H, hits = HEADINGS.get(lang, HEADINGS["en"]), filters.matched(job)
    out = ["## " + H[0], compose.summary(cv, job, lang), ""]
    if cv.get("expertise"):
        out += ["## " + H[1]] + ["- " + e for e in _ordered_expertise(cv, hits)] + [""]
    out.append("## " + H[3])
    for e in cv.get("experience", []):
        where = ", ".join(x for x in (e.get("org", ""), e.get("loc", "")) if x)
        out += ["### " + e.get("title", "") + (f" — {where}" if where else ""), e.get("dates", "")]
        out += ["- " + b for b in _by_relevance(e.get("bullets", []), job, e.get("_fixed"))] + [""]
    if cv.get("education"):
        out += ["## " + H[4]] + ["- " + x for x in cv["education"]] + [""]
    if cv.get("extras"):
        out += ["## " + (cv.get("extras_title") or "ADDITIONAL")] + ["- " + x for x in cv["extras"]] + [""]
    return "\n".join(out).strip() + "\n"


def profile_text(profile):
    """The profile written out as a CV text, in its own order: the start of a named version."""
    lang = _profile_lang(profile)
    H = HEADINGS.get(lang, HEADINGS["en"])
    out = ["## " + H[0], profile.get("summary", ""), ""]
    if profile.get("expertise"):
        out += ["## " + H[1]] + ["- " + e for e in profile["expertise"]] + [""]
    out.append("## " + H[3])
    for e in profile.get("experience", []):
        where = ", ".join(x for x in (e.get("org", ""), e.get("loc", "")) if x)
        out += ["### " + e.get("title", "") + (f" — {where}" if where else ""), e.get("dates", "")]
        out += ["- " + b for b in e.get("bullets", [])] + [""]
    if profile.get("education"):
        out += ["## " + H[4]] + ["- " + x for x in profile["education"]] + [""]
    if profile.get("extras"):
        out += ["## " + (profile.get("extras_title") or "ADDITIONAL")] + ["- " + x for x in profile["extras"]] + [""]
    return "\n".join(out).strip() + "\n"


def version_path(vid):
    return os.path.join(CV_DIR, f"version-{int(vid)}.pdf")


def build_version(profile, version):
    return render(profile, [], version_path(version["id"]), sections=parse_text(version["text"]))


def parse_text(text):
    """[{"title", "items"}] where an item is ("p", text), ("li", text) or a job
    {"role", "dates", "bullets"}. Anything before the first section title is a paragraph of an untitled one."""
    sections, cur, role = [], None, None
    for raw in (text or "")[:MAX_CV_TEXT].replace("\r", "").split("\n"):
        line = " ".join(raw.split())
        if not line:
            continue
        if line.startswith("## "):
            cur, role = {"title": line[3:].strip(), "items": []}, None
            sections.append(cur)
            continue
        if cur is None:
            cur = {"title": "", "items": []}
            sections.append(cur)
        if line.startswith("### "):
            role = {"role": line[4:].strip(), "dates": None, "bullets": []}
            cur["items"].append(role)
        elif line[:2] in ("- ", "• ", "* "):
            (role["bullets"].append(line[2:].strip()) if role else cur["items"].append(("li", line[2:].strip())))
        elif role is not None and role["dates"] is None and not role["bullets"]:
            role["dates"] = line
        else:
            (role["bullets"].append(line) if role else cur["items"].append(("p", line)))
    return sections


def build_from_text(job, profile, text):
    """The PDF of a job's CV from its (edited) text, exactly as written: nothing is re-ordered."""
    return render(profile, [], cv_path(job["id"]), company=job.get("company") or "", sections=parse_text(text))


def save_photo(data):
    """Keep the person's portrait for their CVs: any common image, turned into a small JPEG.
    Returns False when the file isn't an image."""
    import io
    from PIL import Image, ImageOps
    Image.MAX_IMAGE_PIXELS = 40_000_000
    try:
        im = Image.open(io.BytesIO(data))
        if im.format not in ("JPEG", "PNG", "WEBP", "MPO"):
            return False
        im = ImageOps.exif_transpose(im).convert("RGB")
        im.thumbnail((600, 800))
    except Exception:  # noqa: BLE001  (not an image, or a broken one)
        return False
    os.makedirs(os.path.dirname(PHOTO) or ".", exist_ok=True)
    im.save(PHOTO + ".tmp", "JPEG", quality=88)
    os.replace(PHOTO + ".tmp", PHOTO)
    return True


def remove_photo():
    if os.path.exists(PHOTO):
        os.remove(PHOTO)


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


def build_profile_view(profile, pid):
    """The CV of an additional profile as it starts out: its headline, summary and choices, nothing tailored to a posting."""
    from . import profiles
    cv, lang = profiles.apply_view(profile, pid), _profile_lang(profile)
    return render(cv, [], os.path.join(CV_DIR, f"profile-{int(pid)}.pdf"), summary=cv.get("summary", ""), lang=lang if lang in HEADINGS else "en")


def _by_relevance(bullets, job, fixed=False):
    if fixed:
        return list(bullets)                               # the profile chose the order of these points
    terms, skills = compose.posting_terms(job), filters.matched(job)
    return [b for _, b in sorted(enumerate(bullets), key=lambda ib: (-compose._score(ib[1], terms, skills), ib[0]))]


def _bullet_first(bullets, hits):
    return sorted(bullets, key=lambda b: 0 if any(h in b.lower() for h in hits) else 1)


CONTACT_LABELS = {   # e-mail, phone, where the person lives, LinkedIn
    "en": ("E-mail", "Phone", "Location", "LinkedIn"), "fr": ("E-mail", "Téléphone", "Domicile", "LinkedIn"),
    "de": ("E-Mail", "Telefon", "Wohnort", "LinkedIn"), "it": ("E-mail", "Telefono", "Domicilio", "LinkedIn"),
}


def _sections_lang(sections, fallback):
    """The language of a written-out CV, from its section titles (they are the standard headings unless renamed)."""
    titles = {(s.get("title") or "").strip().upper() for s in sections or []}
    best = max(HEADINGS, key=lambda l: len(titles & set(HEADINGS[l])))
    return best if titles & set(HEADINGS[best]) else fallback


def render(profile, hits, out, company="", key_skills=None, summary=None, lang="en", job=None, sections=None):
    """The CV as a PDF. sections (from parse_text): the body exactly as the person wrote it, instead of
    the profile's. The page is balanced: the type and the spacing grow until the last page is full, and
    a CV that would spill a few lines onto a new page is tightened to end on the page before."""
    import io
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import mm
    from reportlab.platypus import (SimpleDocTemplate, Paragraph, HRFlowable, Spacer,
                                    ListFlowable, ListItem, Image, Table, TableStyle)
    from xml.sax.saxutils import escape as esc

    if sections is not None:
        lang = _sections_lang(sections, _profile_lang(profile))
    H = HEADINGS.get(lang, HEADINGS["en"])
    labels = CONTACT_LABELS.get(lang, CONTACT_LABELS["en"])
    blue, grey, soft, band = colors.HexColor("#1F4E78"), colors.HexColor("#555555"), colors.HexColor("#C9D6E3"), colors.HexColor("#EEF3F8")
    base = getSampleStyleSheet()["Normal"]
    width = A4[0] - 32 * mm - 12                     # the text column (the frame pads 6 pt each side)

    def flow_for(f, g):
        """Everything on the page for a type scale f and a spacing scale g."""
        st = {
            "name": ParagraphStyle("name", parent=base, fontName="Helvetica-Bold", fontSize=23 * f, leading=27 * f, textColor=blue),
            "headline": ParagraphStyle("hl", parent=base, fontSize=12 * f, leading=16 * f, textColor=grey),
            "label": ParagraphStyle("lb", parent=base, fontSize=6.6 * f, leading=9 * f, textColor=grey),
            "value": ParagraphStyle("vl", parent=base, fontSize=9 * f, leading=11.5 * f),
            "head": ParagraphStyle("hd", parent=base, fontName="Helvetica-Bold", fontSize=10.5 * f, leading=13 * f, textColor=blue,
                                   spaceBefore=9 * g, spaceAfter=1.5),
            "role": ParagraphStyle("rl", parent=base, fontSize=10.5 * f, leading=13.5 * f, spaceBefore=2.5 * g),
            "sub": ParagraphStyle("sb", parent=base, fontSize=8.6 * f, leading=11 * f, textColor=grey, spaceAfter=2 * g),
            "body": ParagraphStyle("bd", parent=base, fontSize=9.4 * f, leading=13.2 * f, spaceAfter=2.2 * g),
            "bullet": ParagraphStyle("bl", parent=base, fontSize=9.1 * f, leading=12.4 * f, spaceAfter=0.8 * g),
        }
        tight = [("LEFTPADDING", (0, 0), (-1, -1), 0), ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                 ("TOPPADDING", (0, 0), (-1, -1), 0), ("BOTTOMPADDING", (0, 0), (-1, -1), 0), ("VALIGN", (0, 0), (-1, -1), "TOP")]
        # ---- the head of the page: name and title, the portrait on the right, then the contact details in a band
        who = [Paragraph(esc(profile["name"]), st["name"])]
        if profile.get("headline"):
            who.append(Paragraph(esc(profile["headline"]), st["headline"]))
        flow = who
        if os.path.exists(PHOTO):                    # portrait at the top right, as Swiss CVs have it
            try:
                from reportlab.lib.utils import ImageReader
                w, h = ImageReader(PHOTO).getSize()
                pw = 27 * mm
                flow = [Table([[who, Image(PHOTO, width=pw, height=pw * h / w)]], colWidths=[width - pw - 3 * mm, pw + 3 * mm],
                              style=TableStyle(tight + [("ALIGN", (1, 0), (1, 0), "RIGHT"), ("VALIGN", (0, 0), (0, 0), "MIDDLE")]))]
            except Exception:  # noqa: BLE001  (unreadable picture: the CV is made without it)
                flow = who
        c = profile.get("contact", {})
        cells = [[Paragraph(esc(lab.upper()), st["label"]), Paragraph(esc(val), st["value"])]
                 for lab, val in zip(labels, (c.get("email"), c.get("phone"), c.get("location"), c.get("linkedin"))) if val]
        flow.append(Spacer(1, 5 * g))
        if cells:
            flow.append(Table([cells], colWidths=[width / len(cells)] * len(cells),
                              style=TableStyle([("BACKGROUND", (0, 0), (-1, -1), band), ("ROUNDEDCORNERS", [5, 5, 5, 5]),
                                                ("LEFTPADDING", (0, 0), (-1, -1), 8), ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                                                ("TOPPADDING", (0, 0), (-1, -1), 5), ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                                                ("VALIGN", (0, 0), (-1, -1), "TOP")])))
        flow.append(Spacer(1, 3 * g))

        def heading(title):
            return [Paragraph(esc(title), st["head"]), HRFlowable(width="100%", thickness=0.7, color=soft, spaceAfter=3.5 * g)]

        def bullets_of(items):
            return ListFlowable([ListItem(Paragraph(esc(b), st["bullet"]), leftIndent=8) for b in items],
                                bulletType="bullet", start="•", leftIndent=10, spaceAfter=4 * g)
        if sections is not None:
            for sec in sections:
                if sec["title"]:
                    flow += heading(sec["title"])
                pending = []

                def flush():
                    if pending:        # a list of short words reads as one line (skills); longer lines stay lines
                        short = len(pending) >= 4 and sum(map(len, pending)) / len(pending) <= 35
                        flow.extend([Paragraph(" &nbsp;•&nbsp; ".join(esc(x) for x in pending), st["body"])] if short
                                    else [Paragraph(esc(x), st["body"]) for x in pending])
                        pending.clear()
                for it in sec["items"]:
                    if isinstance(it, dict):
                        flush()
                        flow.append(Paragraph(f'<b>{esc(it["role"])}</b>', st["role"]))
                        if it["dates"]:
                            flow.append(Paragraph(esc(it["dates"]), st["sub"]))
                        if it["bullets"]:
                            flow.append(bullets_of(it["bullets"]))
                    elif it[0] == "li":
                        pending.append(it[1])
                    else:
                        flush()
                        flow.append(Paragraph(esc(it[1]), st["body"]))
                flush()
            return flow
        flow += heading(H[0]) + [Paragraph(esc(summary if summary is not None else profile.get("summary", "")), st["body"])]
        if profile.get("expertise"):
            flow += heading(H[1]) + [Paragraph(" &nbsp;•&nbsp; ".join(esc(e) for e in _ordered_expertise(profile, hits)), st["body"])]
        if key_skills:
            flow += heading(H[2]) + [Paragraph(" &nbsp;•&nbsp; ".join(esc(k) for k in key_skills), st["body"])]
        flow += heading(H[3])
        for e in profile.get("experience", []):
            where = ", ".join(x for x in (e.get("org", ""), e.get("loc", "")) if x)      # either may be missing
            flow.append(Paragraph(f'<b>{esc(e["title"])}</b>' + (f" — {esc(where)}" if where else ""), st["role"]))
            flow.append(Paragraph(esc(e.get("dates", "")), st["sub"]))
            bullets = (_by_relevance(e.get("bullets", []), job, e.get("_fixed")) if job else _bullet_first(e.get("bullets", []), hits))
            if bullets:                                    # a job listed without details: no (empty) list
                flow.append(bullets_of(bullets))
        if profile.get("education"):
            flow += heading(H[4]) + [Paragraph(esc(ed), st["body"]) for ed in profile["education"]]
        if profile.get("extras"):
            flow += heading(profile.get("extras_title", "ADDITIONAL")) + [Paragraph(esc(x), st["body"]) for x in profile["extras"]]
        return flow

    def build(f, g, target):
        doc = SimpleDocTemplate(target, pagesize=A4, leftMargin=16 * mm, rightMargin=16 * mm, topMargin=15 * mm, bottomMargin=15 * mm,
                                title=f"{profile['name']} — CV" + (f" — {company}" if company else ""), author=profile["name"])
        doc.build(flow_for(f, g))
        return doc.page

    def pages(f, g):
        return build(f, g, io.BytesIO())
    f, g, goal = 1.0, 1.0, pages(1.0, 1.0)
    if goal > 1:                                     # a few lines alone on a last page: tighten to end on the page before
        for smaller in (0.96, 0.92, 0.88):
            if pages(smaller, 0.85) == goal - 1:
                f, g, goal = smaller, 0.85, goal - 1
                break
    if f == 1.0:                                     # room left on the last page: larger type first ...
        for larger in (1.06, 1.12, 1.18, 1.24, 1.3):
            if pages(larger, g) != goal:
                break
            f = larger
    while g < 6.5 and pages(f, g * 1.1) == goal:     # ... then more air between the blocks, down to the foot of the page
        g *= 1.1
    os.makedirs(CV_DIR, exist_ok=True)
    build(f, g, out)
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
