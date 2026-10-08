"""What to send with an application: a checklist per job. Documents the posting asks for by name
(work certificates, diplomas, references, extracts...) are marked; the person ticks what is ready.
Swiss applications usually want the full file ("dossier complet"): CV, letter, certificates, diplomas."""
import json
import re

ITEMS = [   # key, label, how postings ask for it (fr / de / it / en)
    ("cv", "CV", r"\bcv\b|curriculum|lebenslauf|resume"),
    ("letter", "Cover letter", r"lettre de motivation|motivationsschreiben|bewerbungsschreiben|lettera di (?:motivazione|presentazione)|cover letter"),
    ("certificates", "Work certificates", r"certificats? de travail|arbeitszeugnis|zeugnisse|certificati di lavoro|work certificates?|reference letters?"),
    ("diplomas", "Diplomas and training certificates", r"dipl[ôo]mes?|diplom(?:e|a|i)\b|attestations? de formation|ausbildungsnachweis|degree certificates?"),
    ("references", "References (names and phone numbers)", r"r[ée]f[ée]rences?|referenzen|referenze"),
    ("permit", "Copy of residence or work permit", r"permis de (?:travail|s[ée]jour)|copie du permis|aufenthaltsbewilligung|arbeitsbewilligung|permesso di (?:lavoro|soggiorno)|work permit"),
    ("record", "Criminal-record extract", r"casier judiciaire|strafregister|casellario giudiziale|criminal record"),
    ("debt", "Debt-register extract", r"extrait (?:de l'office )?des? poursuites|betreibungs(?:register)?auszug|estratto (?:del registro )?(?:delle )?esecuzioni|debt[- ](?:collection|register) extract"),
    ("salary", "Salary expectations", r"pr[ée]tentions? (?:de salaire|salariales?)|gehaltsvorstellung|lohnvorstellung|pretese salariali|salary expectations?"),
    ("photo", "Photo", r"\bphoto\b|\bfoto\b|passbild"),
]
ALWAYS = ("cv", "letter")
KEYS = [k for k, _, _ in ITEMS]


def asked(text):
    t = (text or "").lower()
    return {k for k, _, pat in ITEMS if k in ALWAYS or (t and re.search(rf"(?<!\w)(?:{pat})", t))}


def done(job):
    try:
        got = json.loads(job.get("docs") or "[]")
    except ValueError:
        got = []
    return [k for k in got if k in KEYS] if isinstance(got, list) else []


def checklist(job):
    """[{key, label, asked, done}]: the documents the posting names first."""
    want, have = asked(job.get("description")), set(done(job))
    rows = [{"key": k, "label": label, "asked": k in want, "done": k in have} for k, label, _ in ITEMS]
    return sorted(rows, key=lambda r: not r["asked"])


def dump(keys):
    return json.dumps([k for k in KEYS if k in set(keys)])
