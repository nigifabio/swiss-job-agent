"""The same job advertised several times (by the employer and by one or more agencies, or on two
boards under slightly different company names) shown as one card.

Two postings are one job when they share the title and the town and their texts are close; a staffing
agency on one side lowers the bar, since agencies reword the employer's text. Titles alone are never
enough: "Vendeuse, Lausanne" at two shops is two jobs. Nothing is merged in the database: the list
groups them, and what you do to the card (discard, applied...) is done to its copies too."""
import re

from .normalize import title_key

AGENCY = re.compile(
    r"\b(adecco|manpower|randstad|michael page|page personnel|hays|kelly|careerplus|interiman|valjob|robert half|"
    r"experis|academic work|job impuls|one placement|universal[- ]job|approach people|gi group|synergie|axepta|"
    r"helvetic emploi|lhh|spring professional|work selection|ok job|multi personnel|albedis|proman|flexsis|"
    r"personnel|personal|recrutement|recruitment|recruiting|placement|int[ée]rim|staffing|emploi|stellenvermittlung)\b", re.I)
SAME, SAME_AGENCY, MIN_WORDS = 0.55, 0.3, 25


def _words(job):
    text = re.sub(r"<[^>]+>", " ", (job.get("description") or "")[:2500]).lower()
    return {w for w in re.findall(r"[^\W\d_]{4,}", text)}


def same(a, b, wa=None, wb=None):
    wa, wb = wa if wa is not None else _words(a), wb if wb is not None else _words(b)
    if len(wa) < MIN_WORDS or len(wb) < MIN_WORDS:
        return False
    close = len(wa & wb) / len(wa | wb)
    agency = bool(AGENCY.search(a.get("company") or "")) != bool(AGENCY.search(b.get("company") or ""))
    return close >= (SAME_AGENCY if agency else SAME)


def group(jobs):
    """The list with copies folded into the first posting of each job (lists come best first):
    every returned job has "twins": [the copies]."""
    out, by_key = [], {}
    for j in jobs:
        j["twins"] = []
        if j.get("origin") == "manual":
            out.append(j)
            continue
        words, bucket = _words(j), by_key.setdefault(title_key(j.get("title"), j.get("location")), [])
        lead = next((l for l, lw in bucket if same(l, j, lw, words)), None)
        if lead is not None:
            lead["twins"].append(j)
        else:
            bucket.append((j, words))
            out.append(j)
    return out


def expand(ids, jobs):
    """ids plus the copies of each (for an action on several cards at once)."""
    ids, out = [int(i) for i in ids], []
    twins = {j["id"]: [t["id"] for t in j["twins"]] for j in group(jobs)}
    for i in ids:
        for x in [i] + twins.get(i, []):
            if x not in out:
                out.append(x)
    return out
