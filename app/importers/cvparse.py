"""CV text -> draft profile. Heuristic and multilingual (EN/FR/DE/IT); the user reviews it.

Draft keys: the profile.json keys (name, headline, contact{email,phone,linkedin,location},
summary, expertise[], experience[{title,org,loc,dates,bullets[]}], education[], extras_title,
extras[]) plus skills[] (lowercase keywords for scoring) and languages[{name, level}].

    draft = parse(text)             # a CV
    draft = parse_linkedin_pdf(text)  # the PDF from LinkedIn's "Save to PDF" (More... menu)
"""
import re
import unicodedata

from .. import roles, skills as skill_lexicon

BULLET = re.compile(r"^\s*(?:[•●▪◦·‣∙○■□➢➤►▶✓✔\-–—*]|||•|\d+[.)])\s*")
EMAIL = re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+")
PHONE = re.compile(r"(?:\+|00)\d{2}[\s\d./-]{7,16}\d|\b0\d{2}[\s./-]?\d{3}[\s./-]?\d{2}[\s./-]?\d{2}\b")
LINKEDIN = re.compile(r"(?:https?://)?(?:[a-z]{2,3}\.)?linkedin\.com/in/[\w%-]+/?", re.I)
URL = re.compile(r"https?://\S+|www\.\S+", re.I)

MONTHS = ("jan|feb|mar|apr|may|jun|jul|aug|sep|sept|oct|nov|dec|janv|févr|fevr|mars|avr|mai|juin|juil|août|aout|"
          "déc|dez|mär|märz|okt|gen|mag|giu|lug|ago|set|ott|dic|january|february|march|april|june|july|august|"
          "september|october|november|december|janvier|février|avril|juillet|septembre|octobre|novembre|décembre|"
          "januar|februar|juni|juli|oktober|dezember|gennaio|febbraio|marzo|aprile|maggio|giugno|luglio|agosto|"
          "settembre|ottobre|dicembre")
_D = rf"(?:(?:{MONTHS})\.?\s+)?(?:\d{{1,2}}[./])?(?:19|20)\d{{2}}"
NOW = r"(?:present|current|now|today|ongoing|aujourd'hui|aujourd’hui|actuel(?:lement)?|en cours|heute|jetzt|oggi|attuale|in corso|presente)"
DATE_RANGE = re.compile(rf"({_D})\s*(?:[-–—~]|to|à|au|bis|a|al)\s*({_D}|{NOW})", re.I)
SINGLE_YEAR = re.compile(rf"(?:since|depuis|seit|dal|dal)\s+{_D}|^\s*{_D}\s*$", re.I)

SECTIONS = {
    "summary": ["profile", "professional profile", "summary", "professional summary", "about", "about me", "objective",
                "profil", "profil professionnel", "résumé", "à propos", "zusammenfassung", "profil beruflich", "über mich",
                "kurzprofil", "profilo", "profilo professionale", "sommario", "chi sono", "career summary"],
    "skills": ["skills", "core competencies", "competencies", "key skills", "technical skills", "expertise",
               "areas of expertise", "compétences", "compétences clés", "domaines de compétence", "savoir-faire",
               "kompetenzen", "fähigkeiten", "kenntnisse", "fachkenntnisse", "competenze", "competenze chiave",
               "top skills", "tools", "outils", "it skills", "informatique", "technologies", "strengths", "atouts"],
    "experience": ["experience", "professional experience", "work experience", "employment", "employment history",
                   "career", "expérience", "expériences", "expérience professionnelle", "parcours professionnel",
                   "berufserfahrung", "erfahrung", "werdegang", "beruflicher werdegang", "esperienza",
                   "esperienze", "esperienza professionale", "esperienze lavorative"],
    "education": ["education", "training", "academic background", "qualifications", "formation", "formations",
                  "études", "diplômes", "ausbildung", "bildung", "weiterbildung", "formazione", "istruzione", "studi"],
    "languages": ["languages", "language skills", "langues", "sprachen", "sprachkenntnisse", "lingue",
                  "conoscenze linguistiche"],
    "certifications": ["certifications", "certificates", "licenses & certifications", "licenses and certifications",
                       "certificats", "zertifikate", "zertifizierungen", "certificazioni"],
    "other": ["interests", "hobbies", "centres d'intérêt", "loisirs", "interessen", "hobby", "interessi",
              "references", "références", "referenzen", "referenze", "publications", "honors-awards", "awards",
              "volunteering", "bénévolat", "projects", "projets", "personal", "informations personnelles",
              "personal details", "persönliche angaben", "dati personali", "contact", "coordonnées", "kontakt"],
}

LANG_NAMES = {   # canonical English name -> (spellings, ISO code)
    "English": (["english", "anglais", "englisch", "inglese"], "en"),
    "French": (["french", "français", "francais", "französisch", "francese"], "fr"),
    "German": (["german", "allemand", "deutsch", "tedesco"], "de"),
    "Swiss German": (["swiss german", "suisse allemand", "schweizerdeutsch"], "de"),
    "Italian": (["italian", "italien", "italienisch", "italiano"], "it"),
    "Spanish": (["spanish", "espagnol", "spanisch", "spagnolo", "español"], "es"),
    "Portuguese": (["portuguese", "portugais", "portugiesisch", "portoghese", "português"], "pt"),
    "Arabic": (["arabic", "arabe", "arabisch", "arabo"], "ar"),
    "Russian": (["russian", "russe", "russisch", "russo"], "ru"),
    "Chinese": (["chinese", "mandarin", "chinois", "chinesisch", "cinese"], "zh"),
    "Dutch": (["dutch", "néerlandais", "niederländisch", "olandese"], "nl"),
    "Polish": (["polish", "polonais", "polnisch", "polacco"], "pl"),
    "Turkish": (["turkish", "turc", "türkisch", "turco"], "tr"),
    "Romanian": (["romanian", "roumain", "rumänisch", "rumeno"], "ro"),
    "Albanian": (["albanian", "albanais", "albanisch", "albanese"], "sq"),
    "Serbian": (["serbian", "serbe", "serbisch", "serbo", "croatian", "croate", "kroatisch", "bosnian"], "sr"),
    "Czech": (["czech", "tchèque", "tschechisch", "ceco"], "cs"),
}
LEVELS = [   # (level, words) most specific first
    ("native", ["native", "mother tongue", "bilingual", "langue maternelle", "maternelle", "muttersprache",
                "madrelingua", "lingua madre", "bilingue", "zweisprachig", "c2"]),
    ("fluent", ["fluent", "full professional", "courant", "couramment", "fliessend", "fließend", "verhandlungssicher",
                "fluente", "ottimo", "excellent", "c1"]),
    ("professional", ["professional working", "professional", "professionnel", "professionnelle", "très bon",
                      "sehr gut", "buono", "good", "bon", "gut", "b2"]),
    ("intermediate", ["intermediate", "intermédiaire", "limited working", "mittel", "intermedio", "b1"]),
    ("basic", ["basic", "elementary", "notions", "débutant", "scolaire", "grundkenntnisse", "base", "a2", "a1",
               "beginner", "learning", "en cours d'apprentissage"]),
]
LEVEL_RANK = {"native": 5, "fluent": 4, "professional": 3, "intermediate": 2, "basic": 1, "": 3}


def _fold(s):
    return unicodedata.normalize("NFKD", s or "").encode("ascii", "ignore").decode().lower()


def _unspace(line):
    """Designed CVs letter-space their headings and the name ("C O N T A C T", "E X PÉ R I E N C ES"):
    a line of very short upper-case fragments is one word (two spaces or more separate words)."""
    toks = line.split()
    if len(toks) < 4 or line != line.upper() or sum(len(t) for t in toks) / len(toks) > 2 \
            or not all(t.isalpha() for t in toks):
        return line
    return " ".join("".join(w.split()) for w in re.split(r"\s{2,}", line.strip()))


def _clean_lines(text):
    lines = []
    for raw in (text or "").replace("\r", "\n").split("\n"):
        line = raw.replace("\t", " | ").replace("\xa0", " ")
        line = re.sub(r"[​﻿]", "", line)
        line = re.sub(r"\s{2,}", "  ", _unspace(line)).strip()
        if re.fullmatch(r"(?:page\s*)?\d+\s*(?:/|of|de|von|di)\s*\d+|page \d+", line, re.I):
            continue
        lines.append(line)
    counts = {}
    for ln in lines:
        if len(ln) > 15:
            counts[ln] = counts.get(ln, 0) + 1
    repeated = {ln for ln, n in counts.items() if n >= 2 and not BULLET.match(ln) and
                re.search(r"\||\b(cv|curriculum|resume|résumé|lebenslauf|page|seite)\b", ln, re.I)}
    seen = set()
    out = []
    for ln in lines:            # keep the first copy (it may be the real name line)
        if ln in repeated:
            if ln in seen:
                continue
            seen.add(ln)
        out.append(ln)
    return out


def _heading_of(line):
    """The section a line starts, or None. Headings are short, and may be SHOUTED or end with ':'."""
    if re.search(r"[.,;()]\s*$", line) or line.lstrip("•●-–* ")[:1].islower():
        return None
    t = _fold(re.sub(r"[^\w\s&'’-]", " ", line)).strip()
    t = re.sub(r"\s+", " ", t)
    if not t or len(t) > 45:
        return None
    for sec, names in SECTIONS.items():
        for n in names:
            if t == _fold(n):
                return sec
    # "Compétences clés & outils", "Outils de conception & langues": starts with a heading word
    words = t.split()
    if len(words) <= 5:
        for sec, names in SECTIONS.items():
            for n in names:
                fn = _fold(n)
                if t.startswith(fn + " ") and len(fn) >= 5:
                    return sec
    return None


def _split_parts(line):
    parts = re.split(r"\s*(?:\||•|·|—|–(?=\s)|\s-\s|,\s(?=[A-ZÀ-Ü]))\s*", line)
    return [p.strip(" ,;") for p in parts if p and p.strip(" ,;")]


def _contact(lines):
    text = "\n".join(lines[:25])
    c = {}
    m = EMAIL.search(text)
    if m:
        c["email"] = m.group(0)
    m = LINKEDIN.search("\n".join(lines))
    if m:
        c["linkedin"] = re.sub(r"^https?://(?:[a-z]{2,3}\.)?", "", m.group(0).rstrip("/"))
        if not c["linkedin"].startswith("linkedin"):
            c["linkedin"] = "linkedin.com/in/" + c["linkedin"].split("/in/")[-1]
    m = PHONE.search(text)
    if m:
        c["phone"] = " ".join(m.group(0).split())
    from .. import places
    for line in lines[:15]:
        for part in re.split(r"\s*[|•·]\s*", re.sub(r"[📞✉☎📍🏠]", " ", line)):
            part = part.strip()
            if EMAIL.search(part) or PHONE.search(part) or "linkedin" in part.lower():
                continue
            if len(part) < 40 and places.find(part.split(",")[0]):
                c["location"] = part.strip()
                return c
    return c


def _looks_like_name(s):
    words = s.split()
    return (2 <= len(words) <= 5 and all(re.fullmatch(r"[A-Za-zÀ-ÿ'’.-]+", w) for w in words)
            and not re.search(r"\b(cv|curriculum|resume|résumé|lebenslauf|vitae)\b", s, re.I))


def _name(lines):
    for line in lines[:6]:
        for part in _split_parts(line)[:1]:
            if _looks_like_name(part):
                return part.title() if part.isupper() else part
    return ""


def _headline(lines, name):
    """The line(s) right under the name that aren't contact details or a section heading."""
    seen = False
    for line in lines[:8]:
        if not line:
            continue
        if not seen:
            if name and _fold(name) in _fold(line):
                seen = True
            continue
        if _fold(name) in _fold(line):
            continue
        if _heading_of(line) or EMAIL.search(line) or PHONE.search(line) or "linkedin" in line.lower():
            break
        if 3 < len(line) < 140:
            return _untitle(line) if line.isupper() else line
    return ""


KEEP_UPPER = {"IT", "ICT", "HR", "RH", "AI", "IA", "UX", "UI", "BI", "CRM", "ERP", "SAP", "AWS", "GCP", "SRE",
              "CEO", "CTO", "CIO", "CISO", "CFO", "PMO", "B2B", "B2C", "KYC", "AML", "QA", "R&D", "SEO", "CAD"}


def _untitle(s):
    return " ".join(w if w in KEEP_UPPER else w.capitalize() if w.isalpha() else w.title() for w in s.split(" "))


def _sections(lines):
    """{section: [lines]} plus "head" for everything before the first heading."""
    out, cur = {"head": []}, "head"
    for line in lines:
        sec = _heading_of(line)
        if sec:
            cur = sec
            out.setdefault(cur, [])
            rest = line.split(":", 1)[1].strip() if ":" in line else ""
            if rest:
                out[cur].append(rest)
            continue
        out.setdefault(cur, []).append(line)
    return out


def _paragraphs(lines):
    """Join wrapped lines back into sentences/bullets."""
    items = []
    for line in lines:
        if not line:
            continue
        is_bullet = bool(BULLET.match(line)) and not DATE_RANGE.match(line)
        body = BULLET.sub("", line).strip() if is_bullet else line
        if not body:
            continue
        if items and not is_bullet and (body[:1].islower() or not re.search(r"[.!?:;]$", items[-1])) \
                and not DATE_RANGE.search(body) and len(items[-1]) < 600:
            items[-1] = f"{items[-1]} {body}"
        else:
            items.append(body)
    return items


def _dates(line):
    m = DATE_RANGE.search(line)
    if m:
        return m.group(0).strip(), line[:m.start()] + " " + line[m.end():]
    m = re.search(rf"(?:since|depuis|seit|dal)\s+{_D}", line, re.I)
    if m:
        return m.group(0).strip(), line[:m.start()] + " " + line[m.end():]
    return None, line


TOOL_LINE = re.compile(r"^(environment|environnement|umgebung|ambiente|tools|outils|technologies|tech stack|stack)\s*:", re.I)


def _experience(lines):
    """Roles from the experience section. A line with a date range marks a role; title, employer
    and place are on that line ("Title | Org | Place | Jan 2020 - Present") or on the line just
    above it ("Title • Org" then "2022 - 2025 | Turin"). An employer line with dates followed by
    roles without an employer ("PwC  2016 - 2018", "Senior Engineer (2017 - 2018)") is a group."""
    roles_, cur, prev = [], None, None
    for line in lines:
        if not line:
            continue
        is_bullet = bool(BULLET.match(line))
        dates, rest = (None, line) if is_bullet else _dates(line)
        if dates:
            parts = _split_parts(rest.strip(" |,()"))
            if len(parts) <= 1 and prev and not TOOL_LINE.match(prev):
                if cur and cur["bullets"] and cur["bullets"][-1] == prev:
                    cur["bullets"].pop()
                parts = _split_parts(prev) + parts
            cur = {"title": "", "org": "", "loc": "", "dates": dates, "bullets": []}
            for key, val in zip(("title", "org", "loc"), parts):
                cur[key] = val
            roles_.append(cur)
            prev = None
            continue
        if cur is None:
            prev = None if is_bullet else line
            continue
        body = BULLET.sub("", line).strip() if is_bullet else line
        if is_bullet or not cur["bullets"] or TOOL_LINE.match(body):
            cur["bullets"].append(body)
        elif body[:1].islower() or not re.search(r"[.!?:;)]$", cur["bullets"][-1]) and not TOOL_LINE.match(cur["bullets"][-1]):
            cur["bullets"][-1] += " " + body
        else:
            cur["bullets"].append(body)
        # a plain line (not a bullet, not a tool list, no final period) may head the next role
        prev = None if is_bullet or TOOL_LINE.match(body) or re.search(r"[.!?]$", body) else line
    out, group = [], None
    for r in roles_:
        r["bullets"] = [b for b in (" ".join(x.split()) for x in r["bullets"]) if len(b) > 2][:12]
        if r["title"] and not r["org"]:       # "Title at Org" / "Title chez Org"
            m = re.match(r"(.+?)\s+(?:at|chez|bei|presso|@)\s+(.+)", r["title"])
            if m:
                r["title"], r["org"] = m.group(1), m.group(2)
        if not r["bullets"] and not r["loc"] and (not r["org"] or group is None):
            group = r                            # possibly an employer heading its roles
            out.append(r)
            continue
        if group is not None and not r["org"] and out and (out[-1] is group or out[-1].get("_grouped") is group):
            if out[-1] is group and not group["bullets"]:
                out.pop()
            r["org"], r["loc"] = group["title"], r["loc"] or group["org"]
            r["_grouped"] = group
        else:
            group = None
        out.append(r)
    for r in out:
        r.pop("_grouped", None)
    return out


def _languages(text):
    out = []
    folded = _fold(text)
    for name, (spellings, code) in LANG_NAMES.items():
        for sp in spellings:
            m = re.search(r"(?<!\w)" + re.escape(_fold(sp)) + r"(?!\w)", folded)
            if not m:
                continue
            if name == "German" and any(x["name"] == "Swiss German" for x in out) and "swiss german" in folded \
                    and folded.count("german") + folded.count("allemand") + folded.count("deutsch") <= 1:
                break
            window = folded[m.end():m.end() + 45]
            window = re.split(r"[|,;\n•·]| {2}", window)[0] if not window.lstrip().startswith("(") \
                else window.split(")")[0]
            level = ""
            for lv, words in LEVELS:
                if any(re.search(r"(?<!\w)" + re.escape(_fold(w)) + r"(?!\w)", window) for w in words):
                    level = lv
                    break
            if name not in [x["name"] for x in out]:
                out.append({"name": name, "code": code, "level": level})
            break
    return out


def _aliases():
    """canonical skill -> every spelling: the lexicon's synonym groups (languages excluded, they
    are read separately), the role catalog's skills and their FR/DE/IT spellings."""
    lang_words = {w for sp, _ in LANG_NAMES.values() for w in sp}
    out = {}
    for g in skill_lexicon.GROUPS:
        if g[0] in lang_words:
            continue
        canon = next((x for x in g if x in roles.SKILL_I18N), g[0])
        out[canon] = list(dict.fromkeys(list(g) + roles.spellings(canon)))
    for s in roles.vocabulary() + list(roles.SKILL_I18N):
        if s in lang_words:
            continue
        if s in out or any(s in v for v in out.values()):
            continue
        out[s] = roles.spellings(s)
    return out


ALIASES = _aliases()


def vocabulary():
    """Known skills (canonical names, lowercase)."""
    return list(ALIASES)


def find_skills(text, limit=60):
    """Skills from the vocabulary that the text mentions, in order of first appearance."""
    low = (text or "").lower()
    hits = []
    for s, spellings in ALIASES.items():
        pos = [m.start() for sp in spellings
               for m in [re.search(r"(?<!\w)" + re.escape(sp.rstrip("*")) + ("" if sp.endswith("*") else r"(?!\w)"), low)]
               if m]
        if pos:
            hits.append((min(pos), s))
    return [s for _, s in sorted(hits)][:limit]


def _items(lines):
    """Skill/expertise items from a skills section: split on | • · ; , and double spaces."""
    out = []
    for line in lines:
        line = BULLET.sub("", line)
        head, _, tail = line.partition(":")
        if tail and len(head) < 30 and re.search(r"[|,•·;]", tail):
            line = tail
        for part in re.split(r"\s*(?:\||•|·|;|,(?![^()]*\))| {2,})\s*", line):
            part = part.strip(" .-–")
            if 1 < len(part) <= 90 and part.lower() not in (x.lower() for x in out):
                out.append(part)
    return out


def _education(lines):
    out = []
    for line in lines:
        if not line or len(_languages(line)) >= 2:
            continue
        body = BULLET.sub("", line).strip()
        if out and (body[:1].islower() or body.startswith("(")):
            out[-1] += " " + body
        else:
            out.append(body)
    return out[:8]


def parse(text):
    lines = _clean_lines(text)
    secs = _sections(lines)
    name = _name(lines)
    draft = {
        "name": name,
        "headline": _headline(lines, name),
        "contact": _contact(lines),
        "summary": " ".join(_paragraphs(secs.get("summary", []))),
        "expertise": [],
        "experience": _experience(secs.get("experience", [])),
        "education": _education(secs.get("education", [])),
        "extras_title": "",
        "extras": [],
    }
    items = _items(secs.get("skills", []))
    draft["expertise"] = [i for i in items if not (_languages(i) and len(i) < 40)][:16]
    lang_text = "\n".join(secs.get("languages", [])) or "\n".join(
        ln for ln in lines if len(_languages(ln)) >= 2)
    draft["languages"] = _languages(lang_text)
    certs = _paragraphs(secs.get("certifications", []))
    if certs:
        draft["extras_title"], draft["extras"] = "CERTIFICATIONS", certs[:10]
    if not draft["summary"]:          # no heading: the paragraph under the header block
        head = _paragraphs(secs.get("head", []))
        long = [p for p in head if len(p) > 120 and not EMAIL.search(p)]
        draft["summary"] = long[0] if long else ""
    draft["skills"] = find_skills(text)
    return draft


# ---- LinkedIn "Save to PDF" ------------------------------------------------------------
LI_DURATION = re.compile(r"^\(?\s*\d+\s+(?:years?|yrs?|ans?|jahre?n?|anni|mois|months?|mos?|monate?|mesi)"
                         r"(?:\s+\d+\s+(?:months?|mos?|mois|monate?|mesi))?\s*\)?$", re.I)


def is_linkedin_pdf(text):
    t = text or ""
    return ("(LinkedIn)" in t or "linkedin.com/in/" in t) and bool(re.search(
        r"^(Top Skills|Principales compétences|Top-Kenntnisse|Competenze principali)\s*$", t, re.M))


def parse_linkedin_pdf(text):
    """LinkedIn's profile PDF: a sidebar (Contact, Top Skills, Languages, Certifications) and the
    main column (name, headline, location, Summary, Experience, Education)."""
    lines = [ln for ln in _clean_lines(text) if ln and not re.fullmatch(r"Page \d+ of \d+", ln)]
    li_heads = {"contact": ["contact", "coordonnées", "kontakt", "contatto", "contatti"],
                "skills": ["top skills", "principales compétences", "top-kenntnisse", "competenze principali"],
                "languages": ["languages", "langues", "sprachen", "lingue"],
                "certifications": ["certifications", "zertifizierungen", "certificazioni"],
                "honors": ["honors-awards", "distinctions", "auszeichnungen", "riconoscimenti", "publications"],
                "summary": ["summary", "résumé", "zusammenfassung", "riepilogo", "info"],
                "experience": ["experience", "expérience", "berufserfahrung", "esperienza"],
                "education": ["education", "formation", "ausbildung", "formazione"]}
    secs, cur = {"head": []}, "head"
    for ln in lines:
        key = next((k for k, v in li_heads.items() if _fold(ln).strip() in [_fold(x) for x in v]), None)
        if key:
            cur = key
            secs.setdefault(cur, [])
            continue
        secs.setdefault(cur, []).append(ln)
    draft = {"name": "", "headline": "", "contact": _contact(lines), "summary": "", "expertise": [],
             "experience": [], "education": [], "extras_title": "", "extras": []}
    # the name/headline/location block sits at the end of the sidebar sections (before Summary)
    side_tail = []
    for k in ("certifications", "honors", "languages", "skills", "contact", "head"):
        if secs.get(k):
            side_tail = secs[k]
            break
    for i, ln in enumerate(side_tail):
        if _looks_like_name(ln) and i + 1 < len(side_tail):
            draft["name"] = ln
            draft["headline"] = side_tail[i + 1]
            if i + 2 < len(side_tail):
                draft["contact"].setdefault("location", side_tail[i + 2])
            secs[k] = side_tail[:i]
            break
    draft["expertise"] = [s for s in secs.get("skills", []) if len(s) <= 60][:16]
    draft["languages"] = _languages("\n".join(secs.get("languages", [])))
    certs = [c for c in secs.get("certifications", []) if len(c) <= 120]
    if certs:
        draft["extras_title"], draft["extras"] = "CERTIFICATIONS", certs[:10]
    draft["summary"] = " ".join(_paragraphs(secs.get("summary", [])))
    draft["experience"] = _li_experience(secs.get("experience", []))
    edu = []
    for ln in secs.get("education", []):
        if edu and (ln.startswith(("·", "(")) or re.search(r"\(\s*\d{4}", ln) or ln[:1].islower()):
            edu[-1] += " " + ln
        else:
            edu.append(ln)
    draft["education"] = [" ".join(e.replace("·", ",").split()) for e in edu]
    draft["skills"] = find_skills(text)
    return draft


def _li_date_line(ln):
    d, rest = _dates(ln)
    return bool(d) and (not rest.strip(" ()") or bool(LI_DURATION.match(rest.strip())))


def _li_place(ln):
    from .. import places
    return (len(ln) <= 60 and not ln.endswith(".") and
            ("," in ln or places.find(ln.split(",")[0]) is not None or
             re.search(r"\b(area|region|remote|switzerland|suisse|schweiz|svizzera)\b", ln, re.I) is not None))


def _li_experience(xl):
    """LinkedIn's layout: [Company, (total duration)], Title, Dates (duration), [Place], description.
    A company line with a duration line under it heads several roles."""
    idx = [k for k, ln in enumerate(xl) if _li_date_line(ln)]
    out, org = [], ""
    for n, k in enumerate(idx):
        title = xl[k - 1] if k >= 1 else ""
        before = xl[k - 2] if k >= 2 else ""
        if before and LI_DURATION.match(before):
            org = xl[k - 3] if k >= 3 else org
        elif k >= 2 and (n == 0 or k - 2 > idx[n - 1] + 1) and len(before) <= 60 and not before.endswith("."):
            org = before                 # a single-role company: Company, Title, Dates
        start = k + 1
        loc = ""
        if start < len(xl) and start + 1 not in idx and _li_place(xl[start]):
            loc, start = xl[start], start + 1
        end = idx[n + 1] - 1 if n + 1 < len(idx) else len(xl)     # the next title
        if n + 1 < len(idx):
            nb = xl[end - 1] if end - 1 >= start else ""
            if nb and LI_DURATION.match(nb):
                end -= 2                  # next company + its duration
            elif nb and end - 1 >= start and len(nb) <= 60 and not nb.endswith("."):
                end -= 1                  # next company (single role)
        out.append({"title": title, "org": org, "loc": loc, "dates": _dates(xl[k])[0],
                    "bullets": _paragraphs(xl[start:end])[:12]})
    return out


def parse_any(text):
    return parse_linkedin_pdf(text) if is_linkedin_pdf(text) else parse(text)
