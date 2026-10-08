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


# ---- follow-up after an application without an answer --------------------------------------
FOLLOWUP = {
    "en": ("Subject: My application for {title}",
           "Dear Sir or Madam,",
           "On {date} I applied for the position of {title}{at}. I am still very interested in this role and would be glad "
           "to know where the selection process stands.",
           "I remain at your disposal for any further information or an interview.",
           "Kind regards,"),
    "fr": ("Objet : Ma candidature au poste de {title}",
           "Madame, Monsieur,",
           "Le {date}, je vous ai adressé ma candidature pour le poste de {title}{at}. Ce poste m'intéresse toujours vivement "
           "et je me permets de vous demander où en est le processus de sélection.",
           "Je reste à votre disposition pour tout complément d'information ou pour un entretien.",
           "Je vous prie d'agréer, Madame, Monsieur, mes salutations distinguées."),
    "de": ("Betreff: Meine Bewerbung als {title}",
           "Sehr geehrte Damen und Herren",
           "Am {date} habe ich mich bei Ihnen um die Stelle als {title}{at} beworben. Die Stelle interessiert mich nach wie vor "
           "sehr, und ich erlaube mir nachzufragen, wie weit das Auswahlverfahren fortgeschritten ist.",
           "Für weitere Auskünfte oder ein persönliches Gespräch stehe ich Ihnen gerne zur Verfügung.",
           "Freundliche Grüsse"),
    "it": ("Oggetto: La mia candidatura per la posizione di {title}",
           "Gentili Signore e Signori,",
           "Il {date} vi ho inviato la mia candidatura per la posizione di {title}{at}. Sono tuttora molto interessato/a a questo "
           "ruolo e mi permetto di chiedervi a che punto si trova la selezione.",
           "Resto a disposizione per ulteriori informazioni o per un colloquio.",
           "Cordiali saluti,"),
}


def followup(profile, job, lang):
    """A short, polite follow-up message for an application without an answer (subject line first)."""
    lang = lang if lang in FOLLOWUP else "en"
    subject, hello, body, offer, bye = FOLLOWUP[lang]
    d = job.get("applied_date") or ""
    try:
        import datetime
        d = datetime.date.fromisoformat(d).strftime("%d.%m.%Y")
    except ValueError:
        pass
    company = (job.get("company") or "").strip()
    fill = {"title": (job.get("title") or "").strip(), "date": d, "at": WORDS[lang]["at"].format(company) if company else ""}
    return "\n\n".join([subject.format(**fill), hello, body.format(**fill), offer, bye, profile.get("name", "")])


# ---- interview preparation sheet ------------------------------------------------------------
PREP = {
    "en": {"title": "Interview preparation", "asks": "What the posting asks for", "have": "You have", "gap": "Prepare an answer for",
           "yours": "Your experience to mention", "q": "Questions you will probably get", "ask": "Questions to ask them",
           "practical": "Practical", "applied": "Applied on", "contact": "Contact", "travel": "Travel time", "min": "min by public transport",
           "questions": ["Tell me about yourself.", "Why do you want this job, and why our company?",
                         "What are your strengths for this role? And a weakness?", "Describe a difficult situation at work and how you handled it.",
                         "Why did you leave your last job (or why are you looking now)?", "What salary do you expect, and at what work rate?",
                         "When could you start?", "Where do you see yourself in three years?"],
           "theirs": ["What does a typical day or week look like in this role?", "Who would I work with, and who would I report to?",
                      "What are the first things you expect from the person in the first three months?",
                      "How is the work organised (hours, on-site and remote days)?", "What are the next steps of the process, and when?"]},
    "fr": {"title": "Préparation de l'entretien", "asks": "Ce que demande l'annonce", "have": "Vous avez", "gap": "Préparez une réponse pour",
           "yours": "Votre expérience à mentionner", "q": "Questions qu'on vous posera probablement", "ask": "Questions à leur poser",
           "practical": "Pratique", "applied": "Candidature du", "contact": "Contact", "travel": "Trajet", "min": "min en transports publics",
           "questions": ["Parlez-moi de vous.", "Pourquoi ce poste, et pourquoi notre entreprise ?",
                         "Quels sont vos points forts pour ce poste ? Et un point faible ?", "Décrivez une situation difficile au travail et comment vous l'avez gérée.",
                         "Pourquoi avez-vous quitté votre dernier emploi (ou pourquoi cherchez-vous maintenant) ?",
                         "Quelles sont vos prétentions salariales, et à quel taux d'activité ?", "Quand pourriez-vous commencer ?",
                         "Où vous voyez-vous dans trois ans ?"],
           "theirs": ["À quoi ressemble une journée ou une semaine type dans ce poste ?", "Avec qui travaillerais-je, et qui serait mon ou ma responsable ?",
                      "Qu'attendez-vous de la personne durant les trois premiers mois ?",
                      "Comment le travail est-il organisé (horaires, présence sur site et télétravail) ?",
                      "Quelles sont les prochaines étapes du processus, et dans quel délai ?"]},
    "de": {"title": "Vorbereitung auf das Vorstellungsgespräch", "asks": "Was das Inserat verlangt", "have": "Das bringen Sie mit", "gap": "Bereiten Sie eine Antwort vor zu",
           "yours": "Ihre Erfahrung, die Sie erwähnen sollten", "q": "Fragen, die Sie wahrscheinlich erhalten", "ask": "Fragen, die Sie stellen können",
           "practical": "Praktisches", "applied": "Beworben am", "contact": "Kontakt", "travel": "Reisezeit", "min": "Min. mit dem öffentlichen Verkehr",
           "questions": ["Erzählen Sie etwas über sich.", "Warum diese Stelle, und warum unser Unternehmen?",
                         "Was sind Ihre Stärken für diese Stelle? Und eine Schwäche?", "Beschreiben Sie eine schwierige Situation bei der Arbeit und wie Sie damit umgegangen sind.",
                         "Warum haben Sie Ihre letzte Stelle verlassen (oder warum suchen Sie jetzt)?",
                         "Welche Lohnvorstellung haben Sie, und bei welchem Pensum?", "Wann könnten Sie anfangen?", "Wo sehen Sie sich in drei Jahren?"],
           "theirs": ["Wie sieht ein typischer Tag oder eine typische Woche in dieser Funktion aus?", "Mit wem würde ich arbeiten, und wem wäre ich unterstellt?",
                      "Was erwarten Sie von der Person in den ersten drei Monaten?", "Wie ist die Arbeit organisiert (Arbeitszeiten, vor Ort und Homeoffice)?",
                      "Wie geht es im Verfahren weiter, und bis wann?"]},
    "it": {"title": "Preparazione al colloquio", "asks": "Cosa chiede l'annuncio", "have": "Lei ha", "gap": "Prepari una risposta per",
           "yours": "La sua esperienza da citare", "q": "Domande che probabilmente riceverà", "ask": "Domande da fare",
           "practical": "In pratica", "applied": "Candidatura del", "contact": "Contatto", "travel": "Tragitto", "min": "min con i mezzi pubblici",
           "questions": ["Mi parli di lei.", "Perché questo posto, e perché la nostra azienda?", "Quali sono i suoi punti di forza per questo ruolo? E un punto debole?",
                         "Descriva una situazione difficile sul lavoro e come l'ha gestita.", "Perché ha lasciato l'ultimo impiego (o perché cerca adesso)?",
                         "Quali sono le sue aspettative salariali, e a quale grado d'occupazione?", "Quando potrebbe iniziare?", "Dove si vede fra tre anni?"],
           "theirs": ["Com'è una giornata o una settimana tipo in questo ruolo?", "Con chi lavorerei, e a chi riferirei?",
                      "Cosa vi aspettate dalla persona nei primi tre mesi?", "Com'è organizzato il lavoro (orari, presenza in sede e telelavoro)?",
                      "Quali sono le prossime tappe della selezione, e con quali tempi?"]},
}
