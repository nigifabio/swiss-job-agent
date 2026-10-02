"""Onboarding: imported drafts -> reviewed profile -> target -> search settings + role CV.

State lives in the tenant DB (meta "onboarding"): {"step", "draft", "targets"} so the wizard
survives a reload. Everything here is rule-based and every generated value stays editable
(Settings page).
"""
import json
import os
import re
from collections import Counter

from . import config, filters, places, prefs, roles, store
from .importers import cvparse

STEPS = ("import", "review", "target", "confirm", "done")
PROFILE_KEYS = ("name", "headline", "contact", "summary", "expertise", "experience", "education",
                "extras_title", "extras")
POSTING_LANGS = ("fr", "de", "it", "en")
SENIORITY = {
    "entry": ["director", "directeur", "directrice", "head of", "chief", "vp", "vice president", "leiter*", "senior"],
    "mid": ["intern", "internship", "stage", "stagiaire", "apprenti*", "apprentice", "lehrstelle", "praktikum",
            "trainee", "director", "chief", "vp", "vice president"],
    "senior": ["junior", "intern", "internship", "stage", "stagiaire", "apprenti*", "apprentice", "lehrstelle",
               "praktikum", "trainee", "graduate", "werkstudent*", "student", "étudiant*"],
    "lead": ["junior", "intern", "internship", "stage", "stagiaire", "apprenti*", "apprentice", "lehrstelle",
             "praktikum", "trainee", "graduate", "werkstudent*", "student", "étudiant*", "assistant*"],
}
SENIORITY_LABELS = {"entry": "Entry level / first jobs", "mid": "Experienced (2-7 years)",
                    "senior": "Senior / expert", "lead": "Lead / manager / head of"}
FREE_PROVIDERS = ["ats", "jobup", "jobroom", "adzuna", "careerjet", "jooble"]
WATCHLISTS = os.path.join(os.path.dirname(__file__), "watchlists")


# ---- state ------------------------------------------------------------------------------
def state():
    try:
        s = json.loads(store.get_meta().get("onboarding") or "{}")
    except ValueError:
        s = {}
    s.setdefault("step", "import")
    s.setdefault("draft", {})
    s.setdefault("targets", {})
    return s


def save_state(s):
    store.set_meta(onboarding=json.dumps(s, ensure_ascii=False))


def needed():
    """True while a platform tenant has no profile yet (the wizard is then the home page)."""
    return config.ONBOARDING and not os.path.exists(config.PROFILE_PATH)


# ---- drafts -----------------------------------------------------------------------------
def empty_draft():
    return {"name": "", "headline": "", "contact": {}, "summary": "", "expertise": [], "experience": [],
            "education": [], "extras_title": "", "extras": [], "skills": [], "languages": []}


def merge(drafts):
    """One draft from several imports. The first source that has a field wins (CV before
    LinkedIn: it is usually more recent and better written); lists of skills and languages
    are combined."""
    out = empty_draft()
    for d in drafts:
        for k in ("name", "headline", "summary", "extras_title"):
            if not out[k] and d.get(k):
                out[k] = d[k]
        for k, v in (d.get("contact") or {}).items():
            out["contact"].setdefault(k, v)
        for k in ("expertise", "experience", "education", "extras"):
            if not out[k] and d.get(k):
                out[k] = d[k]
        for s in d.get("skills", []):
            if s not in out["skills"]:
                out["skills"].append(s)
        for lang in d.get("languages", []):
            have = next((x for x in out["languages"] if x["name"] == lang["name"]), None)
            if not have:
                out["languages"].append(dict(lang))
            elif not have.get("level"):
                have["level"] = lang.get("level", "")
    return out


def from_profile(profile):
    """A draft from an existing profile.json (to edit it with the same forms)."""
    d = empty_draft()
    d.update({k: profile.get(k, d[k]) for k in PROFILE_KEYS})
    text = json.dumps(profile, ensure_ascii=False)
    d["skills"] = [k.rstrip("*") for k in prefs.skills()] or cvparse.find_skills(text)
    lang_line = " ".join(x for x in profile.get("extras", []) if cvparse._languages(x))
    d["languages"] = cvparse._languages(lang_line)
    return d


# ---- guesses ------------------------------------------------------------------------------
YEAR = re.compile(r"(?:19|20)\d{2}")


def years_of_experience(draft):
    years = []
    for e in draft.get("experience", []):
        d = e.get("dates", "")
        ys = [int(y) for y in YEAR.findall(d)]
        if ys:
            years.append((min(ys), _this_year() if re.search(cvparse.NOW, d, re.I) else max(ys)))
    if not years:
        return 0
    return max(e for _, e in years) - min(s for s, _ in years)


def _this_year():
    import datetime
    return datetime.date.today().year


LEAD_WORDS = r"\b(head|director|directeur|directrice|chief|vp|leiter|responsable|manager|lead|chef|cheffe)\b"


def guess_seniority(draft):
    yrs = years_of_experience(draft)
    recent = " ".join(e.get("title", "") for e in draft.get("experience", [])[:2]).lower()
    if yrs >= 8 and re.search(LEAD_WORDS, recent):
        return "lead"
    if yrs >= 7:
        return "senior"
    if yrs >= 2:
        return "mid"
    return "entry"


def guess_langs(draft):
    """Posting languages: the ones the person works in (professional level or better)."""
    ok = [x["code"] for x in draft.get("languages", [])
          if x.get("code") in POSTING_LANGS and cvparse.LEVEL_RANK.get(x.get("level", ""), 3) >= 3]
    return ok or ["en"]


def guess_home(draft):
    loc = (draft.get("contact") or {}).get("location", "")
    p = places.find(loc.split(",")[0]) if loc else None
    return p[0][0] if p else ""


def default_targets(draft):
    return {"roles": roles.suggest(draft)[:3], "extra_titles": [], "seniority": guess_seniority(draft),
            "home": guess_home(draft), "radius": 30, "whole_country": False, "remote": True,
            "langs": guess_langs(draft), "avoid": []}


# ---- generation ---------------------------------------------------------------------------
def _uniq(xs):
    out = []
    for x in xs:
        x = " ".join(str(x).split())
        if x and x.lower() not in (o.lower() for o in out):
            out.append(x)
    return out


def score_keywords(skills):
    """The person's skills, one keyword each: matching expands a catalog skill to its spellings in
    the posting languages ("sales" also matches "vente"), see filters._hit_skill."""
    return _uniq(s.lower() for s in skills)[:80]


def language_keywords(draft):
    """Languages the person works in, as skills ("italian" matches "italien", "italiano"...)."""
    return _uniq(x["name"].lower() for x in draft.get("languages", [])
                 if cvparse.LEVEL_RANK.get(x.get("level", ""), 3) >= 3)


def settings_for(draft, t):
    """Search settings (config.EDITABLE names) for a reviewed draft and the chosen targets."""
    langs = [x for x in t.get("langs") or [] if x in POSTING_LANGS] or ["en"]
    chosen = [roles.get(r) for r in t.get("roles", []) if roles.get(r)]
    terms, titles = [], []
    for r in chosen:
        terms += roles.names(r, [x for x in langs if x != "en"] + ["en"])
        titles += r["titles"]
    for x in t.get("extra_titles", []):
        terms.append(x)
        titles.append(x.lower())
    home, radius = t.get("home") or "", int(t.get("radius") or 30)
    loc, cantons = places.search_area(home, radius, bool(t.get("whole_country")))
    if not loc:                          # unknown town: search where the person said, all Switzerland
        loc = _uniq([home.lower()] + places.COUNTRY_WORDS) if home else list(places.COUNTRY_WORDS)
    skills = score_keywords(draft.get("skills", [])) + language_keywords(draft)
    providers = FREE_PROVIDERS + (["remote"] if t.get("remote") else [])
    return {
        "SEARCH_TERMS": _uniq(terms)[:30],
        "WHERE": places.canton_names(cantons) or ([home] if home else []),
        "JOBROOM_CANTONS": cantons,
        "LANGUAGES": langs,
        "TITLE_KEYWORDS": _uniq(titles),
        "TITLE_EXCLUDE": SENIORITY.get(t.get("seniority"), SENIORITY["mid"]),
        "LOCATION_KEYWORDS": loc,
        "ALLOW_REMOTE": bool(t.get("remote")),
        "SCORE_KEYWORDS": _uniq(skills)[:100],
        "PROVIDERS": providers,
        "FETCH_INTERVAL_HOURS": 12,
    }


def profile_from_draft(draft):
    """profile.json content: the CV facts only. The languages line is added to the extras when
    the CV doesn't already have one."""
    p = {k: draft.get(k, empty_draft()[k]) for k in PROFILE_KEYS}
    p["contact"] = {k: v for k, v in (draft.get("contact") or {}).items() if v}
    langs = draft.get("languages") or []
    if langs and not any(cvparse._languages(x) for x in p["extras"]):
        line = "Languages: " + " • ".join(f"{x['name']} ({x['level']})" if x.get("level") else x["name"] for x in langs)
        p["extras"] = list(p["extras"]) + [line]
        if not p["extras_title"]:
            p["extras_title"] = "LANGUAGES"
        elif "LANG" not in p["extras_title"].upper():
            p["extras_title"] += " & LANGUAGES"
    return p


def watchlist_for(role_ids):
    fams = {roles.get(r)["family"] for r in role_ids if roles.get(r)}
    name = "it.json" if "it" in fams else "general.json"
    try:
        with open(os.path.join(WATCHLISTS, name)) as f:
            return json.load(f)
    except (OSError, ValueError):
        return []


def save_profile(draft):
    profile = profile_from_draft(draft)
    tmp = config.PROFILE_PATH + ".tmp"
    os.makedirs(os.path.dirname(config.PROFILE_PATH) or ".", exist_ok=True)
    with open(tmp, "w") as f:
        json.dump(profile, f, indent=1, ensure_ascii=False)
    os.replace(tmp, config.PROFILE_PATH)
    return profile


def finish(draft, targets, settings):
    """Write profile.json, settings.json, avoided words and (if none yet) the company boards."""
    profile = save_profile(draft)
    config.save_settings(settings)
    for w in targets.get("avoid", []):
        prefs.apply("avoid", w)
    if not os.path.exists(config.WATCHLIST_PATH):
        with open(config.WATCHLIST_PATH, "w") as f:
            json.dump(watchlist_for(targets.get("roles", [])), f, indent=2, ensure_ascii=False)
    prefs.invalidate()
    return profile


# ---- CV for a target role -------------------------------------------------------------------
def learned_skills(role, limit=15):
    """Skills most often asked for by the postings already found for this role (title match)."""
    counts = Counter()
    for j in store.list_jobs():
        title = (j.get("title") or "").lower()
        if any(filters._hit(k, title) for k in role["titles"]):
            for s in cvparse.find_skills(f"{j.get('title')} {j.get('description') or ''}"):
                counts[s] += 1
    return [s for s, _ in counts.most_common(limit)]


def _in_profile(skill, text):
    for sp in roles.spellings(skill):
        stem = sp.rstrip("*").lower()
        m = re.search(r"(?<!\w)" + re.escape(stem) + (r"\w*" if sp.endswith("*") else r"s?(?!\w)"), text, re.I)
        if m:
            return m.group(0)
    return None


def role_keywords(profile, role_id):
    """(supported, missing): the role's usual skills + those learned from postings, split by
    whether the profile already mentions them (as the profile spells them)."""
    role = roles.get(role_id)
    if not role:
        return [], []
    text = " ".join([profile.get("headline", ""), profile.get("summary", "")] + profile.get("expertise", []) +
                    [x for e in profile.get("experience", []) for x in [e.get("title", "")] + e.get("bullets", [])] +
                    profile.get("education", []) + profile.get("extras", []))
    sup, miss = [], []
    for s in _uniq(learned_skills(role) + role["skills"]):
        found = _in_profile(s, text)
        if found:
            found = found if found != found.lower() else found[0].upper() + found[1:]
            if found.lower() not in (x.lower() for x in sup):
                sup.append(found)
        else:
            miss.append(s)
    return sup, miss


def role_cv_path(role_id):
    from .tailor import CV_DIR
    return os.path.join(CV_DIR, f"role-{re.sub(r'[^a-z0-9-]', '', role_id)}.pdf")


def build_role_cv(profile, role_id, lang=None):
    """A CV aimed at a role (not one posting): key skills = the role's skills the profile
    supports; summary and bullet order chosen for the role. Returns (path, supported, missing)."""
    from . import compose, tailor
    role = roles.get(role_id)
    sup, miss = role_keywords(profile, role_id)
    own = tailor._profile_lang(profile)
    lang = lang or (own if own in tailor.HEADINGS else "en")
    job = {"id": 0, "title": roles.label(role, lang), "company": "",
           "description": " ".join(sp for s in role["skills"] for sp in roles.spellings(s)) + " " + " ".join(sup)}
    out = role_cv_path(role_id)
    tailor.render(profile, [s.lower() for s in sup], out, key_skills=sup[:14],
                  summary=compose.summary(profile, job, lang), lang=lang, job=job)
    return out, sup, miss
