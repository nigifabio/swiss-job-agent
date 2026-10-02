"""Rule-based writing for CVs and cover letters: no language model, no API.

Everything is built from the candidate's own profile (in the posting's language when a
translated profile exists) and ranked against the posting:

- posting_terms(job): the posting's content words (stop words removed; title words count double)
- rank_facts(profile, job): the profile's bullet points, most relevant to the posting first
  (shared words + CV skills the posting mentions weigh most; ties keep the most recent role first)
- summary(profile, job, lang): the profile's own opening sentence, its most relevant other
  sentence, and a "relevant to this role" line listing the CV skills the posting asks for
- letter_body(profile, job, lang): four short paragraphs from those pieces
"""
import re

from . import filters

STOP = set("""
a an and are as at be been but by can for from has have in into is it its of on or our
that the their this to we will with you your who what which about more than all also
le la les un une des du de d l et ou en au aux pour par sur dans avec vous nous notre
nos votre vos est sont être qui que ce cet cette ces se sa son ses leur leurs plus
il elle ils elles ne pas y a à é
il lo la i gli le un uno una di da del della dei delle e o in con per su tra fra che
chi è sono essere nostro nostra nostri vostro vostra si al alla ai alle
der die das ein eine und oder in im mit für von zu auf ist sind sie wir ihr den dem des
""".split())
_WORD = re.compile(r"[a-zà-ÿ0-9][a-zà-ÿ0-9+#/.-]{2,}", re.IGNORECASE)

WORDS = {
    "en": {"strengths": "Directly relevant to this role: {}.", "and": "and",
           "open": "I am applying for the {title} position{at_company}.",
           "at": " at {}", "current": "In my current role as {role_at}, my experience covers the key points of your posting: {skills}.",
           "current_noskill": "In my current role as {role_at}, I bring experience that matches your posting.", "employer": "{role} at {org}",
           "examples": "A few concrete examples from my experience:",
           "close": "I would welcome the opportunity to discuss how I can contribute to your team."},
    "fr": {"strengths": "Atouts directement liés à ce poste : {}.", "and": "et",
           "open": "Je vous adresse ma candidature pour le poste de {title}{at_company}.",
           "at": " au sein de {}", "current": "Dans mon poste actuel de {role_at}, mon expérience couvre les points clés de votre annonce : {skills}.",
           "current_noskill": "Dans mon poste actuel de {role_at}, j'ai acquis une expérience qui correspond à votre annonce.", "employer": "{role} chez {org}",
           "examples": "Quelques exemples concrets de mon expérience :",
           "close": "Je serais heureux·se de vous présenter plus en détail ma motivation lors d'un entretien."},
    "it": {"strengths": "Punti di forza per questo ruolo: {}.", "and": "e",
           "open": "Vi sottopongo la mia candidatura per la posizione di {title}{at_company}.",
           "at": " presso {}", "current": "Nel mio ruolo attuale di {role_at}, la mia esperienza copre i punti chiave del vostro annuncio: {skills}.",
           "current_noskill": "Nel mio ruolo attuale di {role_at} ho maturato un'esperienza in linea con il vostro annuncio.", "employer": "{role} presso {org}",
           "examples": "Alcuni esempi concreti della mia esperienza:",
           "close": "Sarei lieto/a di illustrarvi la mia motivazione in un colloquio."},
    "de": {"strengths": "Für diese Stelle besonders relevant: {}.", "and": "und",
           "open": "Hiermit bewerbe ich mich um die Stelle als {title}{at_company}.",
           "at": " bei {}", "current": "In meiner aktuellen Funktion als {role_at} deckt meine Erfahrung die Kernpunkte Ihrer Ausschreibung ab: {skills}.",
           "current_noskill": "In meiner aktuellen Funktion als {role_at} habe ich Erfahrung gesammelt, die zu Ihrer Ausschreibung passt.", "employer": "{role} bei {org}",
           "examples": "Einige konkrete Beispiele aus meiner Erfahrung:",
           "close": "Gerne überzeuge ich Sie in einem persönlichen Gespräch von meiner Motivation."},
}


def _tokens(text):
    return [w.lower().strip(".-/") for w in _WORD.findall(text or "") if w.lower() not in STOP]


def posting_terms(job):
    """{word: weight}: content words of the posting, title words count double."""
    terms = {}
    for w in _tokens(job.get("description")):
        terms[w] = 1
    for w in _tokens(job.get("title")):
        terms[w] = 2
    return terms


def _score(text, terms, skills):
    words = set(_tokens(text))
    low = (text or "").lower()
    return sum(terms.get(w, 0) for w in words) + 3 * sum(1 for k in skills if k in low)


def rank_facts(profile, job):
    """[(score, bullet, role)] most relevant first; ties keep profile order (most recent role first)."""
    terms, skills = posting_terms(job), filters.matched(job)
    facts, i = [], 0
    for role in profile.get("experience", []):
        for b in role.get("bullets", []):
            if b.lower().startswith(("environment:", "environnement :", "ambiente:", "umgebung:")):
                continue            # tool lists read badly inside prose
            facts.append((_score(b, terms, skills), i, b, role))
            i += 1
    facts.sort(key=lambda f: (-f[0], f[1]))
    return [(s, b, r) for s, _, b, r in facts]


def _sentences(text):
    return [s.strip() for s in re.split(r"(?<=[.!?])\s+", text or "") if s.strip()]


def _join(items, lang):
    items = list(items)
    if len(items) <= 1:
        return "".join(items)
    return ", ".join(items[:-1]) + f" {WORDS[lang]['and']} " + items[-1]


CONFIDENTIAL = {"", "confidential", "confidentiel", "confidenziale", "vertraulich"}


def _org(role):
    """Employer name for prose, or "" when the profile keeps it confidential."""
    org = (role.get("org") or "").strip()
    return "" if org.lower() in CONFIDENTIAL else org


SPECIAL = {"devops": "DevOps", "ci/cd": "CI/CD", "powershell": "PowerShell", "vmware": "VMware",
           "iso 27001": "ISO 27001", "entra id": "Entra ID", "iac": "IaC", "aws": "AWS", "gcp": "GCP",
           "sap": "SAP", "crm": "CRM", "erp": "ERP", "api": "API", "pki": "PKI", "dns": "DNS"}


def surface(term, job):
    """The CV skill as the posting writes it ('coordinat*' -> 'coordination', 'terraform' ->
    'Terraform', 'sales' -> 'vente' in a French posting); known technical names get their usual
    casing; SHOUTED words are lowered."""
    from . import config, roles
    text = f"{job.get('title') or ''} {job.get('description') or ''}"
    for sp in roles.spellings_for(term, config.LANGUAGES):
        if sp != term and filters._hit(sp.lower(), text.lower()):
            return _surface_one(sp, job)
    return _surface_one(term, job)


def _surface_one(term, job):
    stem = term.rstrip("*")
    rx = re.compile(r"(?<!\w)" + re.escape(stem) + (r"\w*" if term.endswith("*") else r"(?!\w)"), re.IGNORECASE)
    if term.endswith("*"):            # word family (coordinat* ...): ordinary words, never brand names
        forms = [w.lower() for w in rx.findall(job.get("description") or "") or rx.findall(job.get("title") or "")]
        if forms:
            return max(dict.fromkeys(forms), key=forms.count)    # most frequent form, first on ties
        return stem
    m = rx.search(job.get("description") or "")
    found = m.group(0) if m else None
    if found is None:                 # only in the title: title case isn't the word's own spelling
        m = rx.search(job.get("title") or "")
        found = m.group(0).lower() if m else stem
    if found.lower() in SPECIAL:
        return SPECIAL[found.lower()]
    return found.lower() if found.isupper() and len(found) > 4 else found


def _skills_for(job, lang, n):
    from . import prefs
    kws = [k for k in prefs.skills() if k.rstrip("*") in filters.matched(job)]
    out = []
    for k in kws:
        w = surface(k, job)
        if w.lower() not in (x.lower() for x in out):
            out.append(w)
    return out[:n]


def summary(profile, job, lang):
    """Profile summary tailored to the posting: its opening sentence, its most relevant other
    sentence, and the CV skills the posting asks for. Only the profile's own words."""
    lang = lang if lang in WORDS else "en"
    sents = _sentences(profile.get("summary", ""))
    if not sents:
        return ""
    terms, skills = posting_terms(job), filters.matched(job)
    out = [sents[0]]
    rest = sorted(sents[1:], key=lambda s: -_score(s, terms, skills))
    if rest and _score(rest[0], terms, skills) > 0:
        out.append(rest[0])
    shown = _skills_for(job, lang, 5)
    if shown:
        out.append(WORDS[lang]["strengths"].format(_join(shown, lang)))
    return " ".join(out)


def letter_body(profile, job, lang):
    lang = lang if lang in WORDS else "en"
    w = WORDS[lang]
    title = (job.get("title") or "").strip()
    company = (job.get("company") or "").strip()
    skills = _skills_for(job, lang, 4)
    role = (profile.get("experience") or [{}])[0]
    org, title_now = _org(role), (role.get("title") or "").strip()
    role_at = w["employer"].format(role=title_now, org=org) if org else title_now
    paras = [w["open"].format(title=title, at_company=w["at"].format(company) if company else "")]
    if skills:
        paras.append(w["current"].format(role_at=role_at, skills=_join(skills, lang)))
    else:
        paras.append(w["current_noskill"].format(role_at=role_at))
    top = [b for _, b, _ in rank_facts(profile, job)[:3]]
    if top:
        paras.append(w["examples"] + "\n" + "\n".join(f"– {b.rstrip('.')}." for b in top))
    paras.append(w["close"])
    return "\n\n".join(paras)
