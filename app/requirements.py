"""Conditions a posting states that a person should see before applying: a language they didn't list,
a permit or nationality condition, a driving licence, a criminal-record extract. Plain word matching
in French, German, Italian and English; it flags, it never hides a posting."""
import re

from . import config

LANGS = {     # canonical skill name -> how postings write it
    "german": r"allemand|deutsch(?:kenntnisse)?|german|tedesco|schweizerdeutsch|suisse[- ]allemand",
    "french": r"français|francais|französisch|franzosisch|french|francese",
    "english": r"anglais|englisch|english|inglese",
    "italian": r"italien(?:isch)?|italian|italiano",
}
LANG_LABEL = {"german": "German", "french": "French", "english": "English", "italian": "Italian"}
CONDITIONS = [
    ("permit", "Work permit or nationality condition",
     r"permis de travail|autorisation de travail|permis (?:de séjour )?[bcgl]\b|nationalité suisse|citoyen(?:ne)? suisse|"
     r"work permit|swiss (?:citizen|national)|eu/efta|ue/aele|arbeitsbewilligung|aufenthaltsbewilligung|"
     r"schweizer (?:bürger|staatsbürger|pass)|permesso di lavoro|cittadinanza svizzera"),
    ("driving", "Driving licence",
     r"permis de conduire|permis (?:cat\.? ?)?b\b(?! ou c)|véhicule (?:privé|personnel)|driving licen[cs]e|driver'?s licen[cs]e|"
     r"führerausweis|führerschein|patente di guida"),
    ("record", "Criminal-record extract",
     r"casier judiciaire|extrait de (?:la )?poursuite|criminal record|strafregister(?:auszug)?|betreibungsregister|casellario giudiziale"),
]


def flags(text):
    """[(kind, label)] for one posting's text."""
    t = (text or "").lower()
    if not t:
        return []
    mine = {s.lower() for s in config.SCORE_KEYWORDS}
    out = []
    for name, pat in LANGS.items():
        if name not in mine and re.search(rf"(?<!\w)(?:{pat})(?!\w)", t):
            out.append(("language", f"{LANG_LABEL[name]} (not in your skills)"))
    for kind, label, pat in CONDITIONS:
        if re.search(rf"(?<!\w)(?:{pat})", t):
            out.append((kind, label))
    return out
