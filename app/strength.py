"""Profile check: what a Swiss recruiter looks for in a CV, checked against the person's profile.
Plain rules on the profile's own text; it says what is missing and why it matters, it changes nothing."""
import re

from . import config, tailor

LEVEL = re.compile(r"\b(?:[abc][12])\b|native|maternelle|muttersprache|madrelingua|courant|fluent|fliessend|fluente|bilingue|"
                   r"bilingual|notions|grundkenntnisse|basic|intermediate|avanc|advanced|professional", re.I)
LANG_NAMES = {"fr": "French", "de": "German", "it": "Italian", "en": "English"}


def _bullets(profile, first=None):
    return [b for e in profile.get("experience", [])[:first] for b in e.get("bullets", [])]


def checks(profile):
    """[{ok, label, hint, link}] in the order a reader meets them on the CV."""
    c = profile.get("contact") or {}
    exp = profile.get("experience") or []
    words = len((profile.get("summary") or "").split())
    bullets = _bullets(profile)
    numbers = [b for b in bullets if re.search(r"\d", b)]
    extras = " ".join((profile.get("extras") or []) + (profile.get("expertise") or []))
    out = [
        (bool(c.get("email") and c.get("phone") and c.get("location")), "Contact details complete",
         "E-mail, phone number and town: recruiters call, and they check how far you live."),
        (bool((profile.get("headline") or "").strip()), "A job title under your name",
         "The title you are looking for, in the words job ads use."),
        (25 <= words <= 110, "A summary of 3 to 5 lines",
         "Who you are, how many years in what, your strongest result. Shorter than 25 words says too little, longer than 110 isn't read."),
        (len(profile.get("expertise") or []) >= 6, "At least 6 skills listed",
         "Skills are what the match score and recruiters' searches look for."),
        (bool(exp) and all((e.get("dates") or "").strip() for e in exp), "Dates on every job",
         "Month or year for each job; a job without dates raises questions."),
        (bool(exp) and all(len(e.get("bullets") or []) >= 2 for e in exp[:3]), "Your last jobs say what you did",
         "At least two points for each of your three most recent jobs."),
        (len(numbers) >= 3, "Results with numbers",
         "At least three points with a figure: how many people, clients, francs, percent, days. Numbers are what a reader remembers."),
        (bool(profile.get("education")), "Education and training listed",
         "Diplomas, CFC, certificates, with the year. Foreign diplomas: add the Swiss equivalent if you have it."),
        (bool(LEVEL.search(extras)), "Languages with their level",
         "For example French (native), English (C1), German (A2). Almost every Swiss ad asks."),
    ]
    rows = [{"ok": ok, "label": label, "hint": hint, "link": ""} for ok, label, hint in out]
    versions = tailor.profile_versions()
    own = next((k for k, v in versions.items() if "original" in v), "")
    for lang in config.LANGUAGES:
        if lang in tailor.HEADINGS and lang != own:
            rows.append({"ok": versions.get(lang, "").startswith("ok"), "label": f"CV ready in {LANG_NAMES[lang]}",
                         "hint": "You search postings in this language: with a translated profile, the CV and letter for those jobs are written in it.",
                         "link": f"/profile/translate/{lang}"})
    return rows


def report(profile):
    rows = checks(profile)
    return {"rows": rows, "done": sum(1 for r in rows if r["ok"]), "total": len(rows)}


# ---- translated profile, written side by side with the original -------------------------------
def fields(profile):
    """[(form name, label, original text, multiline)] in the order of the CV."""
    out = [("headline", "Job title", profile.get("headline", ""), False), ("summary", "Summary", profile.get("summary", ""), True)]
    out += [(f"expertise_{i}", "Skill", v, False) for i, v in enumerate(profile.get("expertise") or [])]
    for i, e in enumerate(profile.get("experience") or []):
        out.append((f"exp_{i}_title", "Job", e.get("title", ""), False))
        out.append((f"exp_{i}_dates", "Dates", e.get("dates", ""), False))
        out += [(f"exp_{i}_b_{k}", "Point", b, True) for k, b in enumerate(e.get("bullets") or [])]
    out += [(f"education_{i}", "Education", v, False) for i, v in enumerate(profile.get("education") or [])]
    if profile.get("extras"):
        out.append(("extras_title", "Heading of the last section", profile.get("extras_title", ""), False))
    out += [(f"extras_{i}", "Line", v, False) for i, v in enumerate(profile.get("extras") or [])]
    return [f for f in out if (f[2] or "").strip()]


def translation(profile, lang):
    """{form name: translated text} from the saved translated profile ({} when none or out of step)."""
    import json
    import os
    path = tailor.translated_path(lang)
    if not os.path.exists(path):
        return {}
    try:
        with open(path) as f:
            tr = json.load(f)
    except (OSError, ValueError):
        return {}
    if not isinstance(tr, dict) or not tailor._same_shape(tr, profile):
        return {}
    mine, theirs = dict((n, v) for n, _, v, _ in fields(profile)), dict((n, v) for n, _, v, _ in fields(tr))
    return {n: v for n, v in theirs.items() if n in mine and v != mine[n]}


def save_translation(profile, lang, form):
    """Write profile.<lang>.json with the same items as the profile; a field left empty keeps the original."""
    import copy
    import json
    import os

    def get(name, original):
        v = " ".join(str(form.get(name) or "").split())[:2000]
        return v or original
    tr = copy.deepcopy({k: profile.get(k) for k in ("headline", "summary", "expertise", "experience", "education",
                                                     "extras_title", "extras") if k in profile})
    for k in ("headline", "summary", "extras_title"):
        if k in tr:
            tr[k] = get(k, tr[k] or "")
    for k in ("expertise", "education", "extras"):
        tr[k] = [get(f"{k}_{i}", v) for i, v in enumerate(tr.get(k) or [])]
    for i, e in enumerate(tr.get("experience") or []):
        e["title"], e["dates"] = get(f"exp_{i}_title", e.get("title", "")), get(f"exp_{i}_dates", e.get("dates", ""))
        e["bullets"] = [get(f"exp_{i}_b_{k}", b) for k, b in enumerate(e.get("bullets") or [])]
    path = tailor.translated_path(lang)
    tmp = path + ".tmp"
    with open(tmp, "w") as f:
        json.dump(tr, f, indent=2, ensure_ascii=False)
    os.replace(tmp, path)
    return sum(1 for n, _, v, _ in fields(profile) if " ".join(str(form.get(n) or "").split()) not in ("", v))
