"""What the person's own job market asks for, read from the postings found for them: the skills they
miss most (and in which jobs), the ones they have that are asked most, languages and their level,
experience and qualifications asked, conditions and documents. To decide what to study or prepare.

Plain counting over the postings still in play; nothing is sent anywhere and nothing is stored."""
import re
from collections import Counter

from . import config, docs, listfilter, prefs, requirements, roles, skills, store

LEVELS = [("native", r"langue maternelle|maternelle|native|muttersprach\w*|madrelingua"),
          ("fluent", r"courant\w*|fluent|fliessend|verhandlungssicher|fluente|excellent\w*|sehr gut\w*|ottim\w+|parfait\w*|ma[iî]tris\w+"),
          ("C2", r"\bc2\b"), ("C1", r"\bc1\b"), ("B2", r"\bb2\b"), ("B1", r"\bb1\b"), ("A2", r"\ba2\b"), ("A1", r"\ba1\b"),
          ("basic", r"notions|bonnes connaissances|connaissances|basic|grundkenntnisse|gute kenntnisse|kenntnisse|conoscenz\w+")]
QUALS = [   # label, how postings write it (fr / de / it / en)
    ("Vocational diploma (CFC / EFZ / AFC)", r"\bcfc\b|\befz\b|\bafc\b|certificat fédéral de capacité|fähigkeitszeugnis|attestato federale di capacità"),
    ("Federal certificate or diploma (brevet, Fachausweis)", r"brevet fédéral|diplôme fédéral|fachausweis|eidg\w*\.? diplom|attestato professionale federale|maîtrise fédérale"),
    ("College of higher education (ES / HF)", r"école supérieure|diplôme es\b|dipl\w*\.? hf\b|höhere fachschule|scuola specializzata superiore"),
    ("Bachelor / university of applied sciences (HES / FH)", r"bachelor|haute école|\bhes(?:-so)?\b|fachhochschule|scuola universitaria professionale|\bsupsi\b"),
    ("Master / university (EPF, Uni)", r"master\b|\bepf[lz]?\b|\beth\b|universit\w+|hochschulabschluss"),
    ("Further training (CAS / DAS / MAS)", r"\bcas\b|\bdas\b|\bmas\b|formation continue|weiterbildung|formazione continua"),
]
YEARS = re.compile(r"(\d{1,2})\s*(?:\+|à\s*\d{1,2}|-\s*\d{1,2}|bis\s*\d{1,2}|to\s*\d{1,2})?\s*(?:ans?|années?|years?|jahren?|anni)\b[^.\n]{0,50}?"
                   r"(?:exp[ée]rien|erfahrung|esperienz|pratique|praxis)", re.I)
_cache = {}


def _level(text, start):
    """The level written right after a language name ("allemand B2", "English (fluent)"), or ""."""
    near = re.split(r"[,.;\n]| et | and | und | ed? | ou | or | oder ", text[start:start + 60])[0]     # this language's own words only
    for name, pat in sorted(LEVELS, key=lambda l: len(l[0]) != 2):                                 # a stated level (B2) says more than a word

        if re.search(pat, near):
            return name
    return ""


def analyse(kind="", lang="en"):
    jobs = store.open_jobs()
    key = (len(jobs), jobs[0]["id"] if jobs else 0, tuple(prefs.skills()), tuple(prefs.avoided()), tuple(prefs.ignored()),
           tuple(config.TITLE_KEYWORDS), kind, lang)
    if _cache.get("key") != key:
        _cache.update(key=key, value=_analyse(jobs, kind, lang))
    return _cache["value"]


def _analyse(jobs, kind, lang="en"):
    terms = [(t.rstrip("*").lower(), re.compile(skills._pattern(t), re.IGNORECASE), name, cls)
             for t, (name, cls) in skills.plan()[2].items() if cls in ("miss", "have")]
    ignored = set(prefs.ignored())
    kinds_all = Counter()
    for j in jobs:
        j["kinds"] = listfilter._kinds(j.get("title"))
        kinds_all.update(j["kinds"])
    mine = [j for j in jobs if not kind or kind in j["kinds"]]
    miss, have, only, strong = Counter(), Counter(), Counter(), Counter()
    where, cover = {}, []
    langs = {name: {"n": 0, "levels": Counter()} for name in requirements.LANGS}
    conds, papers, quals, years = Counter(), Counter(), Counter(), []
    per_kind = {}
    for j in sorted(mine, key=lambda j: -(j.get("score") or 0)):
        text = f"{j.get('title') or ''}\n{j.get('description') or ''}".lower()
        m = {name for t, rx, name, cls in terms if cls == "miss" and name not in ignored and t in text and rx.search(text)}
        h = {name for t, rx, name, cls in terms if cls == "have" and t in text and rx.search(text)}
        miss.update(m)
        have.update(h)
        if len(m) == 1:
            only.update(m)                                  # the one thing between the person and a full match
        if j.get("status") in ("shortlisted", "applied", "interview", "offer"):
            strong.update(m)                                # asked by the jobs the person chose
        for name in m:
            where.setdefault(name, []).append(j)
        if m or h:
            cover.append(len(h) / (len(h) + len(m)))
        for name, pat in requirements.LANGS.items():
            hit = re.search(rf"(?<!\w)(?:{pat})(?!\w)", text)
            if hit:
                langs[name]["n"] += 1
                lv = _level(text, hit.end())
                if lv:
                    langs[name]["levels"][lv] += 1
        for k, label, pat in requirements.CONDITIONS:
            if re.search(rf"(?<!\w)(?:{pat})", text):
                conds[label] += 1
        for k in docs.asked(j.get("description")) - set(docs.ALWAYS):
            papers[k] += 1
        for label, pat in QUALS:
            if re.search(rf"(?<!\w)(?:{pat})", text):
                quals[label] += 1
        y = [int(x) for x in YEARS.findall(text) if 0 < int(x) <= 20]
        if y:
            years.append(min(y))
        for k in j["kinds"]:
            pk = per_kind.setdefault(k, {"n": 0, "score": [], "miss": Counter()})
            pk["n"] += 1
            pk["miss"].update(m)
            if j.get("score") is not None:
                pk["score"].append(j["score"])
    n = len(mine) or 1
    my_langs = {s.rstrip("*").lower() for s in prefs.skills()}

    def label(k):
        return (k[3:].rstrip("*") + ("…" if k.endswith("*") else "")) if k.startswith("kw:") else roles.label(roles.get(k), lang)
    missing = [{"skill": s, "n": c, "pct": round(100 * c / n), "only": only[s], "chosen": strong[s],
                "jobs": [{"id": j["id"], "title": j.get("title") or ""} for j in where[s][:3]],
                "kinds": [label(k) for k, _ in Counter(k for j in where[s] for k in j["kinds"]).most_common(2)]}
               for s, c in miss.most_common(25)]
    doc_labels = {k: lab for k, lab, _ in docs.ITEMS}
    buckets = [("1-2", sum(1 for y in years if y <= 2)), ("3-5", sum(1 for y in years if 3 <= y <= 5)), ("6+", sum(1 for y in years if y >= 6))]
    return {
        "total": len(mine), "all": len(jobs), "kind": kind,
        "kinds": sorted(((label(k), k, c) for k, c in kinds_all.items()), key=lambda r: (-r[2], r[0])),
        "coverage": round(100 * sum(cover) / len(cover)) if cover else None,
        "full": sum(1 for c in cover if c == 1), "missing": missing,
        "quick": [m for m in missing if m["only"]][:5],
        "strengths": [{"skill": s, "n": c, "pct": round(100 * c / n)} for s, c in have.most_common(12)],
        "langs": [{"name": requirements.LANG_LABEL[k], "n": v["n"], "pct": round(100 * v["n"] / n), "mine": k in my_langs,
                   "levels": v["levels"].most_common(3)} for k, v in sorted(langs.items(), key=lambda kv: -kv[1]["n"]) if v["n"]],
        "conditions": [(lab, c, round(100 * c / n)) for lab, c in conds.most_common()],
        "papers": [(doc_labels[k], c, round(100 * c / n)) for k, c in papers.most_common()],
        "quals": [(lab, c, round(100 * c / n)) for lab, c in quals.most_common()],
        "years": buckets if years else [], "years_n": len(years),
        "by_kind": sorted(({"label": label(k), "key": k, "n": v["n"],
                            "score": round(sum(v["score"]) / len(v["score"])) if v["score"] else None,
                            "miss": v["miss"].most_common(4)} for k, v in per_kind.items() if v["n"] >= 2),
                          key=lambda r: -r["n"])[:8],
    }
