"""Role catalog: what a target role means for the search and the CV, in EN/FR/DE/IT.

Each role gives
- names: job titles per language -> search terms for the job boards
- titles: title words -> TITLE_KEYWORDS (a posting's title must contain one; "coordinat*" = prefix)
- skills: what postings for the role typically ask for -> skill vocabulary for imports and
  the "CV for a role" page (a skill only reaches a CV when the profile already mentions it)
- family: groups roles for the company-board seed lists (app/watchlists/<family>.json)

Rule-based on purpose: the tenant can edit every generated list afterwards.
"""
import re
import unicodedata

ROLES = [
    # ---- IT -------------------------------------------------------------------------------
    {"id": "cloud-architect", "family": "it",
     "names": {"en": ["Cloud Architect", "Infrastructure Architect", "Solutions Architect"],
               "fr": ["Architecte cloud", "Architecte infrastructure"], "de": ["Cloud Architekt", "Infrastruktur Architekt"],
               "it": ["Architetto cloud"]},
     "titles": ["architect", "architecte", "architekt*", "architetto", "cloud", "infrastructure", "infrastruktur"],
     "skills": ["aws", "azure", "gcp", "terraform", "kubernetes", "docker", "ansible", "infrastructure as code",
                "hybrid cloud", "cloud migration", "networking", "linux", "python", "ci/cd", "finops",
                "solution design", "security architecture", "vmware"]},
    {"id": "devops-engineer", "family": "it",
     "names": {"en": ["DevOps Engineer", "Platform Engineer", "Site Reliability Engineer"],
               "fr": ["Ingénieur DevOps"], "de": ["DevOps Engineer"], "it": ["DevOps Engineer"]},
     "titles": ["devops", "sre", "site reliability", "platform engineer", "platform", "cloud engineer"],
     "skills": ["kubernetes", "docker", "terraform", "ansible", "ci/cd", "gitlab", "jenkins", "github actions",
                "prometheus", "grafana", "linux", "python", "bash", "aws", "azure", "helm", "argocd", "observability"]},
    {"id": "system-administrator", "family": "it",
     "names": {"en": ["System Administrator", "Systems Engineer"], "fr": ["Administrateur système", "Ingénieur système"],
               "de": ["Systemadministrator", "System Engineer"], "it": ["Amministratore di sistema", "Sistemista"]},
     "titles": ["system administrator", "sysadmin", "system engineer", "systems engineer", "ingénieur système",
                "administrateur système", "administrateur systèmes", "systemadministrator*", "systemtechniker*",
                "sistemista", "ict"],
     "skills": ["windows server", "linux", "active directory", "vmware", "powershell", "bash", "microsoft 365",
                "dns", "backup", "networking", "itil", "entra id", "intune", "hyper-v"]},
    {"id": "network-engineer", "family": "it",
     "names": {"en": ["Network Engineer"], "fr": ["Ingénieur réseau"], "de": ["Netzwerk Engineer"], "it": ["Network Engineer"]},
     "titles": ["network", "réseau", "réseaux", "netzwerk*", "rete", "reti"],
     "skills": ["cisco", "fortinet", "palo alto", "firewall", "routing", "switching", "bgp", "vpn", "sd-wan",
                "wifi", "tcp/ip", "networking", "ccna", "ccnp"]},
    {"id": "security-officer", "family": "it",
     "names": {"en": ["Information Security Officer", "Security Engineer", "Security Architect"],
               "fr": ["Responsable sécurité de l'information", "Ingénieur sécurité"],
               "de": ["Information Security Officer", "Security Engineer"], "it": ["Security Engineer"]},
     "titles": ["security", "sécurité", "sicherheit*", "sicurezza", "ciso", "iso", "soc", "cyber*"],
     "skills": ["iso 27001", "nist", "siem", "splunk", "sentinel", "edr", "iam", "pki", "vulnerability management",
                "risk assessment", "gdpr", "incident response", "firewall", "zero trust", "penetration testing",
                "tisax", "finma", "dora"]},
    {"id": "software-engineer", "family": "it",
     "names": {"en": ["Software Engineer", "Software Developer", "Full Stack Developer"],
               "fr": ["Développeur logiciel", "Ingénieur logiciel", "Développeur full stack"],
               "de": ["Softwareentwickler", "Software Engineer"], "it": ["Sviluppatore software"]},
     "titles": ["developer", "développeu*", "entwickler*", "sviluppatore", "software engineer", "software",
                "programmer", "full stack", "fullstack", "backend", "frontend", "front-end", "back-end"],
     "skills": ["python", "java", "javascript", "typescript", "c#", ".net", "react", "node.js", "sql", "git",
                "rest api", "docker", "agile", "scrum", "microservices", "angular", "vue", "golang", "kotlin"]},
    {"id": "data-analyst", "family": "it",
     "names": {"en": ["Data Analyst", "BI Analyst"], "fr": ["Analyste de données", "Analyste BI"],
               "de": ["Datenanalyst", "Data Analyst"], "it": ["Data Analyst"]},
     "titles": ["data analyst", "analyste de données", "datenanalyst*", "bi", "business intelligence", "reporting",
                "analytics"],
     "skills": ["sql", "excel", "power bi", "tableau", "python", "statistics", "reporting", "data visualization",
                "dashboards", "dax", "qlik"]},
    {"id": "data-engineer", "family": "it",
     "names": {"en": ["Data Engineer", "Data Scientist", "Machine Learning Engineer"],
               "fr": ["Ingénieur data", "Data scientist"], "de": ["Data Engineer", "Data Scientist"],
               "it": ["Data Engineer", "Data Scientist"]},
     "titles": ["data engineer", "data scientist", "machine learning", "ml engineer", "ai engineer", "data"],
     "skills": ["python", "sql", "spark", "databricks", "snowflake", "airflow", "kafka", "machine learning",
                "pandas", "dbt", "aws", "azure", "pytorch", "tensorflow", "llm"]},
    {"id": "it-support", "family": "it",
     "names": {"en": ["IT Support Specialist", "Service Desk Analyst"], "fr": ["Technicien support informatique", "Technicien helpdesk"],
               "de": ["IT Supporter", "ICT Supporter"], "it": ["Tecnico di supporto IT"]},
     "titles": ["support", "helpdesk", "help desk", "service desk", "technicien informatique", "technicien support",
                "supporter", "workplace", "desktop"],
     "skills": ["windows", "microsoft 365", "active directory", "itil", "servicenow", "hardware", "troubleshooting",
                "jira", "intune", "networking", "macos", "ticketing"]},
    {"id": "it-project-manager", "family": "it",
     "names": {"en": ["IT Project Manager", "Program Manager"], "fr": ["Chef de projet IT", "Chef de projet informatique"],
               "de": ["IT-Projektleiter", "Projektleiter IT"], "it": ["Project Manager IT"]},
     "titles": ["project manager", "chef de projet", "cheffe de projet", "projektleiter*", "capo progetto", "pmo",
                "program manager", "programme manager", "delivery manager"],
     "skills": ["project management", "prince2", "pmp", "agile", "scrum", "jira", "budget", "stakeholder management",
                "risk management", "ms project", "planning", "hermes", "safe"]},
    {"id": "product-manager", "family": "it",
     "names": {"en": ["Product Manager", "Product Owner"], "fr": ["Chef de produit", "Product Owner"],
               "de": ["Produktmanager", "Product Owner"], "it": ["Product Manager"]},
     "titles": ["product manager", "product owner", "chef de produit", "cheffe de produit", "produktmanager*",
                "product lead"],
     "skills": ["product management", "roadmap", "agile", "scrum", "jira", "user research", "stakeholder management",
                "data analysis", "a/b testing", "ux"]},
    {"id": "business-analyst", "family": "it",
     "names": {"en": ["Business Analyst"], "fr": ["Business analyst", "Analyste métier"], "de": ["Business Analyst"],
               "it": ["Business Analyst"]},
     "titles": ["business analyst", "analyste métier", "analyste d'affaires", "requirements engineer", "analyst"],
     "skills": ["requirements analysis", "bpmn", "sql", "jira", "confluence", "stakeholder management",
                "process improvement", "uml", "agile", "user stories"]},
    {"id": "it-manager", "family": "it",
     "names": {"en": ["IT Manager", "Head of IT"], "fr": ["Responsable informatique", "Directeur informatique"],
               "de": ["Leiter Informatik", "IT-Leiter"], "it": ["Responsabile IT"]},
     "titles": ["head of it", "it manager", "responsable informatique", "responsable it", "directeur informatique",
                "directeur des systèmes", "cio", "cto", "it director", "leiter informatik", "leiter it", "it-leiter*",
                "head of infrastructure", "head of engineering", "director"],
     "skills": ["it strategy", "budget", "vendor management", "itil", "team leadership", "it governance", "cloud",
                "security", "project management", "stakeholder management"]},
    {"id": "technical-manager", "family": "it",
     "names": {"en": ["Solutions Engineer", "Technical Account Manager", "Pre-Sales Engineer"],
               "fr": ["Ingénieur avant-vente", "Technical Account Manager"], "de": ["Solutions Engineer", "Presales Engineer"],
               "it": ["Solutions Engineer"]},
     "titles": ["solutions engineer", "solution engineer", "presales", "pre-sales", "avant-vente", "technical account manager",
                "technical manager", "sales engineer", "customer success engineer", "customer engineer"],
     "skills": ["solution design", "proof of concept", "customer advisory", "cloud", "networking", "presentations",
                "crm", "stakeholder management", "technical workshops"]},
    # ---- business --------------------------------------------------------------------------
    {"id": "sales-account-manager", "family": "business",
     "names": {"en": ["Account Manager", "Sales Manager", "Business Developer"],
               "fr": ["Account manager", "Responsable commercial", "Commercial"],
               "de": ["Account Manager", "Verkaufsleiter", "Key Account Manager"], "it": ["Account Manager", "Commerciale"]},
     "titles": ["sales", "account manager", "key account", "business development", "business developer", "commercial*",
                "vente", "verkauf*", "aussendienst*", "vendite", "kundenberater*"],
     "skills": ["b2b", "crm", "salesforce", "negotiation", "prospecting", "pipeline management", "closing",
                "key account management", "cold calling", "hubspot", "upselling"]},
    {"id": "retail-sales-advisor", "family": "retail",
     "names": {"en": ["Sales Advisor", "Sales Associate"], "fr": ["Conseiller de vente", "Conseillère de vente", "Vendeur"],
               "de": ["Verkaufsberater", "Verkäufer"], "it": ["Consulente di vendita", "Addetto vendite"]},
     "titles": ["conseiller de vente", "conseillère de vente", "conseiller en vente", "vendeu*", "sales advisor",
                "sales associate", "verkäufer*", "verkaufsberater*", "detailhandel*", "commesso", "commessa",
                "gérant de magasin", "store manager", "responsable de magasin", "filialleiter*"],
     "skills": ["customer service", "sales", "cash register", "visual merchandising", "stock management", "upselling",
                "customer advice", "retail", "ms office"]},
    {"id": "marketing", "family": "business",
     "names": {"en": ["Marketing Manager", "Digital Marketing Specialist", "Communications Specialist"],
               "fr": ["Chargé de marketing", "Responsable marketing", "Chargé de communication"],
               "de": ["Marketing Manager", "Marketingfachmann"], "it": ["Marketing Manager"]},
     "titles": ["marketing", "communication", "kommunikation", "brand", "content", "social media", "digital"],
     "skills": ["seo", "sem", "google analytics", "social media", "content marketing", "crm", "hubspot", "adobe",
                "copywriting", "campaign management", "email marketing", "wordpress", "canva"]},
    {"id": "customer-service", "family": "services",
     "names": {"en": ["Customer Service Representative", "Customer Support Specialist"],
               "fr": ["Conseiller service client", "Collaborateur service clientèle"],
               "de": ["Kundendienst Mitarbeiter", "Kundenberater"], "it": ["Addetto servizio clienti"]},
     "titles": ["customer service", "customer support", "customer care", "customer experience", "service client*",
                "service clientèle", "relation client*", "kundendienst*", "kundenservice*", "servizio clienti",
                "call center", "contact center", "customer success"],
     "skills": ["customer service", "crm", "zendesk", "complaint handling", "communication", "multilingual",
                "ticketing", "phone support", "salesforce", "ms office"]},
    {"id": "administrative-assistant", "family": "services",
     "names": {"en": ["Administrative Assistant", "Office Assistant"],
               "fr": ["Assistant administratif", "Assistante administrative", "Employé de commerce"],
               "de": ["Sachbearbeiter", "Kaufmännischer Mitarbeiter"], "it": ["Assistente amministrativo", "Impiegato di commercio"]},
     "titles": ["assistant*", "administrati*", "secrétaire", "secretary", "sachbearbeiter*", "back office",
                "employé de commerce", "employée de commerce", "kaufm*", "impiegat*", "segretari*"],
     "skills": ["ms office", "excel", "word", "outlook", "scheduling", "filing", "correspondence", "invoicing",
                "data entry", "sap", "reception", "minute taking"]},
    {"id": "office-manager", "family": "services",
     "names": {"en": ["Office Manager", "Office Coordinator"], "fr": ["Office manager", "Gestionnaire administratif"],
               "de": ["Office Manager"], "it": ["Office Manager"]},
     "titles": ["office manager", "office coordinator", "gestionnaire administrati*", "facility", "office"],
     "skills": ["office management", "facility management", "procurement", "budget", "events", "scheduling",
                "vendor management", "onboarding", "ms office", "coordination"]},
    {"id": "receptionist", "family": "services",
     "names": {"en": ["Receptionist", "Front Desk Agent"], "fr": ["Réceptionniste", "Collaborateur accueil"],
               "de": ["Rezeptionist", "Empfangsmitarbeiter"], "it": ["Receptionist", "Addetto alla reception"]},
     "titles": ["réception*", "receptionist", "front desk", "front office", "accueil", "empfang*", "rezeption*"],
     "skills": ["reception", "switchboard", "customer service", "scheduling", "ms office", "multilingual", "booking"]},
    {"id": "accountant", "family": "finance",
     "names": {"en": ["Accountant", "Bookkeeper"], "fr": ["Comptable", "Aide-comptable"],
               "de": ["Buchhalter", "Sachbearbeiter Buchhaltung"], "it": ["Contabile"]},
     "titles": ["accountant", "accounting", "comptable", "comptabilité", "buchhalter*", "buchhaltung", "contabil*",
                "fiduciaire", "treuhand*", "bookkeeper", "finance"],
     "skills": ["accounting", "bookkeeping", "vat", "sap", "abacus", "excel", "financial statements",
                "reconciliation", "accounts payable", "accounts receivable", "payroll", "ifrs", "swiss gaap"]},
    {"id": "financial-controller", "family": "finance",
     "names": {"en": ["Financial Controller", "Financial Analyst"], "fr": ["Contrôleur de gestion", "Analyste financier"],
               "de": ["Controller", "Finanzanalyst"], "it": ["Controller"]},
     "titles": ["controller", "contrôleur de gestion", "contrôleuse de gestion", "controlling", "fp&a",
                "financial analyst", "analyste financier", "finanzanalyst*"],
     "skills": ["budgeting", "forecasting", "reporting", "excel", "sap", "ifrs", "variance analysis", "power bi",
                "consolidation", "swiss gaap"]},
    {"id": "hr", "family": "services",
     "names": {"en": ["HR Generalist", "Recruiter", "HR Business Partner"],
               "fr": ["Gestionnaire RH", "Chargé de recrutement", "HR Business Partner"],
               "de": ["HR Fachfrau", "Recruiter", "HR Business Partner"], "it": ["HR Generalist", "Recruiter"]},
     "titles": ["hr", "human resources", "ressources humaines", "rh", "personal*", "recruiter", "recruteu*",
                "talent acquisition", "recrutement", "payroll", "risorse umane"],
     "skills": ["recruiting", "onboarding", "payroll", "hr administration", "labour law", "workday", "sap hr",
                "employee relations", "sourcing", "linkedin recruiter"]},
    {"id": "logistics", "family": "logistics",
     "names": {"en": ["Logistics Coordinator", "Supply Chain Specialist"], "fr": ["Coordinateur logistique", "Gestionnaire supply chain"],
               "de": ["Logistiker", "Supply Chain Spezialist"], "it": ["Coordinatore logistico"]},
     "titles": ["logisti*", "supply chain", "warehouse", "entrepôt", "magasinier*", "lager*", "dispatch*",
                "transport*", "shipping", "spedizion*", "magazzin*"],
     "skills": ["supply chain", "inventory management", "sap", "wms", "incoterms", "customs", "planning",
                "forklift", "erp", "shipping", "order management"]},
    {"id": "procurement", "family": "logistics",
     "names": {"en": ["Buyer", "Procurement Specialist"], "fr": ["Acheteur", "Acheteuse", "Gestionnaire achats"],
               "de": ["Einkäufer", "Einkaufssachbearbeiter"], "it": ["Buyer", "Addetto acquisti"]},
     "titles": ["buyer", "acheteu*", "einkäufer*", "einkauf*", "procurement", "purchasing", "achats", "sourcing",
                "acquisti"],
     "skills": ["procurement", "negotiation", "supplier management", "sap", "contract management", "sourcing",
                "erp", "cost analysis", "incoterms"]},
    {"id": "operations-coordinator", "family": "services",
     "names": {"en": ["Operations Coordinator", "Operations Manager"], "fr": ["Coordinateur des opérations", "Coordinatrice des opérations"],
               "de": ["Operations Koordinator", "Disponent"], "it": ["Coordinatore operativo"]},
     "titles": ["coordinat*", "operations", "opérations", "planning", "planificat*", "disponent*", "koordinat*"],
     "skills": ["coordination", "planning", "scheduling", "logistics", "excel", "erp", "reporting",
                "supplier management", "customer service", "order management"]},
    {"id": "event-coordinator", "family": "services",
     "names": {"en": ["Event Coordinator", "Event Manager"], "fr": ["Coordinateur événementiel", "Chargé d'événements"],
               "de": ["Event Manager", "Eventkoordinator"], "it": ["Event Coordinator"]},
     "titles": ["event*", "événement*", "événementiel*", "veranstaltung*", "eventi"],
     "skills": ["event planning", "logistics", "supplier management", "budget", "hospitality", "coordination",
                "customer relations"]},
    {"id": "hospitality", "family": "hospitality",
     "names": {"en": ["Guest Relations Agent", "Hotel Front Office Agent", "Restaurant Manager"],
               "fr": ["Réceptionniste d'hôtel", "Responsable de salle", "Guest relations"],
               "de": ["Réceptionist Hotel", "Restaurantleiter"], "it": ["Receptionist d'albergo", "Responsabile di sala"]},
     "titles": ["hospitality", "hôtellerie", "hotel", "hôtel", "guest", "concierge", "restaurant manager",
                "responsable de salle", "f&b", "food and beverage", "restaurantleiter*", "gastronomie"],
     "skills": ["customer service", "reservations", "opera", "pms", "team management", "multilingual", "events",
                "upselling"]},
    {"id": "interior-design", "family": "design",
     "names": {"en": ["Interior Design Advisor", "Kitchen Designer"],
               "fr": ["Conseiller en aménagement intérieur", "Cuisiniste", "Architecte d'intérieur"],
               "de": ["Küchenplaner", "Innenarchitekt", "Einrichtungsberater"], "it": ["Progettista d'interni", "Consulente d'arredo"]},
     "titles": ["aménagement", "interior design*", "architecte d'intérieur", "designer d'intérieur", "cuisiniste",
                "küchenplaner*", "innenarchitekt*", "einrichtungsberater*", "kitchen designer", "arredo",
                "agenceu*", "décoration"],
     "skills": ["3d design", "autocad", "sketchup", "3cad", "space planning", "technical drawings", "sales",
                "customer advice", "materials", "quotes", "winner design"]},
    {"id": "graphic-designer", "family": "design",
     "names": {"en": ["Graphic Designer", "UX/UI Designer"], "fr": ["Graphiste", "Designer UX/UI"],
               "de": ["Grafiker", "UX Designer"], "it": ["Grafico", "UX Designer"]},
     "titles": ["graphiste", "graphic designer", "grafik*", "grafic*", "ux", "ui", "designer"],
     "skills": ["photoshop", "illustrator", "indesign", "figma", "ux", "ui", "branding", "typography", "adobe"]},
    {"id": "teacher-trainer", "family": "education",
     "names": {"en": ["Trainer", "Teacher"], "fr": ["Formateur", "Enseignant"], "de": ["Trainer", "Lehrperson"],
               "it": ["Formatore", "Insegnante"]},
     "titles": ["teacher", "trainer", "formateur", "formatrice", "enseignant*", "lehrer*", "lehrperson*",
                "insegnante", "formatore", "formatrice", "tutor"],
     "skills": ["teaching", "training", "curriculum", "e-learning", "coaching", "presentations"]},
    {"id": "nurse", "family": "health",
     "names": {"en": ["Registered Nurse", "Care Assistant"], "fr": ["Infirmier", "Infirmière", "Assistant en soins"],
               "de": ["Pflegefachperson", "Fachperson Gesundheit"], "it": ["Infermiere"]},
     "titles": ["infirmi*", "nurse", "pflege*", "soins", "soignant*", "infermier*", "fage"],
     "skills": ["patient care", "medication", "clinical documentation", "hygiene", "first aid", "geriatrics"]},
    {"id": "mechanical-engineer", "family": "engineering",
     "names": {"en": ["Mechanical Engineer", "Design Engineer"], "fr": ["Ingénieur mécanique", "Constructeur"],
               "de": ["Maschineningenieur", "Konstrukteur"], "it": ["Ingegnere meccanico"]},
     "titles": ["mechanical", "mécanique", "maschinenbau*", "maschineningenieur*", "konstrukteur*", "constructeur",
                "meccanic*", "r&d engineer", "design engineer"],
     "skills": ["cad", "solidworks", "catia", "creo", "fea", "manufacturing", "lean", "six sigma", "gd&t"]},
    {"id": "maintenance-technician", "family": "engineering",
     "names": {"en": ["Maintenance Technician", "Electrician"], "fr": ["Technicien de maintenance", "Électricien"],
               "de": ["Servicetechniker", "Elektriker"], "it": ["Tecnico di manutenzione", "Elettricista"]},
     "titles": ["maintenance", "technicien de maintenance", "électricien*", "electrician", "elektriker*",
                "servicetechniker*", "instandhaltung*", "manutenzione", "elettricista"],
     "skills": ["electrical installation", "maintenance", "plc", "troubleshooting", "safety", "hydraulics",
                "pneumatics"]},
    {"id": "legal-compliance", "family": "finance",
     "names": {"en": ["Legal Counsel", "Compliance Officer"], "fr": ["Juriste", "Compliance officer"],
               "de": ["Jurist", "Compliance Officer"], "it": ["Giurista", "Compliance Officer"]},
     "titles": ["juriste", "legal", "jurist*", "paralegal", "compliance", "giurist*", "avocat*"],
     "skills": ["contract law", "compliance", "gdpr", "regulatory", "due diligence", "kyc", "aml", "finma"]},
    {"id": "banking-client-advisor", "family": "finance",
     "names": {"en": ["Client Advisor", "Relationship Manager", "KYC Analyst"],
               "fr": ["Conseiller clientèle", "Gestionnaire de fortune", "Analyste KYC"],
               "de": ["Kundenberater Bank", "Relationship Manager"], "it": ["Consulente clientela"]},
     "titles": ["relationship manager", "client advisor", "conseiller clientèle", "gestionnaire de fortune",
                "kyc", "wealth", "private bank*", "kundenberater*", "onboarding"],
     "skills": ["kyc", "aml", "wealth management", "compliance", "avaloq", "temenos", "finma", "client onboarding"]},
]

BY_ID = {r["id"]: r for r in ROLES}
LANGS = ("en", "fr", "de", "it")


def _fold(s):
    return unicodedata.normalize("NFKD", s or "").encode("ascii", "ignore").decode().lower()


def _hit(kw, text):
    end = "" if kw.endswith("*") else r"(?!\w)"
    return re.search(r"(?<!\w)" + re.escape(_fold(kw.rstrip("*"))) + end, _fold(text)) is not None


def get(role_id):
    return BY_ID.get(role_id)


def names(role, langs):
    """Search terms for a role in the given posting languages (English always as fallback)."""
    out = []
    for lang in list(langs) + ["en"]:
        for n in role["names"].get(lang, []):
            if n not in out:
                out.append(n)
    return out


def label(role, lang="en"):
    return (role["names"].get(lang) or role["names"]["en"])[0]


def match_title(title):
    """Roles whose names or title words match a job title, best first (full-name hits first,
    then the number of title words that hit)."""
    scored = []
    for r in ROLES:
        full = any(_fold(n) in _fold(title) for ns in r["names"].values() for n in ns)
        words = sum(1 for t in r["titles"] if _hit(t, title))
        if full or words:
            scored.append((0 if full else 1, -words, r["id"]))
    return [rid for _, _, rid in sorted(scored)]


def suggest(profile, limit=4):
    """Target roles suggested from the profile: the roles matching its headline and job titles,
    the most recent job counting most."""
    votes = {}
    texts = [profile.get("headline", "")] + [e.get("title", "") for e in profile.get("experience", [])]
    for i, t in enumerate(texts):
        weight = 3 if i <= 1 else 1
        for rank, rid in enumerate(match_title(t)[:2]):
            votes[rid] = votes.get(rid, 0) + weight * (2 if rank == 0 else 1)
    return [rid for rid, _ in sorted(votes.items(), key=lambda kv: -kv[1])][:limit]


def vocabulary():
    """Every skill the catalog knows (lowercase), for skill extraction from CVs."""
    out = []
    for r in ROLES:
        for s in r["skills"]:
            if s not in out:
                out.append(s)
    return out


# Non-technical skills are written differently in each language: a French CV says "vente", a
# German posting "Verkauf". Canonical (English) skill -> spellings per language. Used to read
# skills from a CV in any language, and to score postings in each language the tenant searches.
SKILL_I18N = {
    "sales": {"fr": ["vente", "vente conseil"], "de": ["verkauf"], "it": ["vendita", "vendite"]},
    "customer service": {"fr": ["service client*", "service clientèle"], "de": ["kundendienst", "kundenservice"],
                         "it": ["servizio clienti", "assistenza clienti"]},
    "customer relations": {"fr": ["relation* client*"], "de": ["kundenbeziehung*", "kundenbetreuung"],
                           "it": ["relazioni con i clienti"]},
    "customer advice": {"fr": ["conseil client*", "conseil à la clientèle"], "de": ["kundenberatung"],
                        "it": ["consulenza clienti", "consulenza al cliente"]},
    "negotiation": {"fr": ["négociation"], "de": ["verhandlung*"], "it": ["negoziazione", "trattativ*"]},
    "planning": {"fr": ["planification", "planning"], "de": ["planung"], "it": ["pianificazione"]},
    "scheduling": {"fr": ["plannings", "gestion des plannings"], "de": ["terminplanung", "einsatzplanung"],
                   "it": ["programmazione"]},
    "coordination": {"fr": ["coordination"], "de": ["koordination"], "it": ["coordinamento"]},
    "logistics": {"fr": ["logistique"], "de": ["logistik"], "it": ["logistica"]},
    "accounting": {"fr": ["comptabilité"], "de": ["buchhaltung", "rechnungswesen"], "it": ["contabilità"]},
    "invoicing": {"fr": ["facturation"], "de": ["fakturierung", "rechnungsstellung"], "it": ["fatturazione"]},
    "payroll": {"fr": ["salaires", "gestion des salaires"], "de": ["lohnbuchhaltung", "lohnwesen"], "it": ["paghe"]},
    "budget": {"fr": ["budget"], "de": ["budget"], "it": ["budget"]},
    "reporting": {"fr": ["reporting", "rapports"], "de": ["reporting", "berichtswesen"], "it": ["reportistica"]},
    "training": {"fr": ["formation des*", "formation de nouveaux*"], "de": ["schulung*"], "it": ["formazione"]},
    "recruiting": {"fr": ["recrutement"], "de": ["rekrutierung"], "it": ["reclutamento", "selezione del personale"]},
    "onboarding": {"fr": ["intégration", "onboarding"], "de": ["einarbeitung", "onboarding"], "it": ["inserimento"]},
    "quotes": {"fr": ["devis"], "de": ["offerte*", "offerten"], "it": ["preventiv*"]},
    "space planning": {"fr": ["aménagement de l'espace", "implantation*"], "de": ["raumplanung"],
                       "it": ["progettazione degli spazi"]},
    "technical drawings": {"fr": ["fiches techniques", "plans techniques", "dessins techniques"],
                           "de": ["technische zeichnungen"], "it": ["disegni tecnici", "schede tecniche"]},
    "materials": {"fr": ["matériaux"], "de": ["materialien"], "it": ["materiali"]},
    "event planning": {"fr": ["organisation d'événements", "événementiel"], "de": ["eventorganisation", "veranstaltungsplanung"],
                       "it": ["organizzazione eventi"]},
    "events": {"fr": ["événements", "evenements"], "de": ["events", "veranstaltungen"], "it": ["eventi"]},
    "order management": {"fr": ["gestion des commandes", "suivi de commande*", "commandes"],
                         "de": ["auftragsabwicklung", "bestellwesen"], "it": ["gestione ordini"]},
    "supplier management": {"fr": ["fournisseur*", "gestion des fournisseurs"], "de": ["lieferantenmanagement", "lieferanten"],
                            "it": ["fornitori", "gestione fornitori"]},
    "inventory management": {"fr": ["gestion des stocks", "stocks"], "de": ["lagerbewirtschaftung", "lagerverwaltung"],
                             "it": ["gestione magazzino", "gestione scorte"]},
    "stock management": {"fr": ["gestion de stock*", "réassort"], "de": ["warenbewirtschaftung"], "it": ["gestione stock"]},
    "complaint handling": {"fr": ["réclamations", "service après-vente", "sav"], "de": ["reklamation*", "beschwerdemanagement"],
                           "it": ["reclami", "assistenza post-vendita"]},
    "after-sales service": {"fr": ["service après-vente", "après-vente"], "de": ["kundendienst", "after-sales"],
                            "it": ["post-vendita", "assistenza post vendita"]},
    "reception": {"fr": ["accueil", "réception"], "de": ["empfang", "rezeption"], "it": ["accoglienza", "reception"]},
    "team management": {"fr": ["gestion d'équipe", "management d'équipe", "encadrement"], "de": ["teamführung", "mitarbeiterführung"],
                        "it": ["gestione del team", "gestione del personale"]},
    "team leadership": {"fr": ["direction d'équipe", "leadership"], "de": ["führung", "leadership"], "it": ["leadership"]},
    "project management": {"fr": ["gestion de projet*", "conduite de projet*"], "de": ["projektmanagement", "projektleitung"],
                           "it": ["gestione progetti", "project management"]},
    "stakeholder management": {"fr": ["parties prenantes"], "de": ["stakeholder"], "it": ["stakeholder"]},
    "multilingual": {"fr": ["multilingue", "trilingue", "bilingue"], "de": ["mehrsprachig"], "it": ["multilingue"]},
    "hospitality": {"fr": ["hôtellerie", "restauration"], "de": ["hotellerie", "gastronomie"], "it": ["ospitalità", "ristorazione"]},
    "reservations": {"fr": ["réservations"], "de": ["reservationen", "reservierungen"], "it": ["prenotazioni"]},
    "data entry": {"fr": ["saisie de données", "saisie"], "de": ["datenerfassung"], "it": ["inserimento dati"]},
    "correspondence": {"fr": ["correspondance"], "de": ["korrespondenz"], "it": ["corrispondenza"]},
    "filing": {"fr": ["classement", "archivage"], "de": ["ablage"], "it": ["archiviazione"]},
    "ms office": {"fr": ["ms office", "suite office"], "de": ["ms office", "ms-office"], "it": ["pacchetto office"]},
    "procurement": {"fr": ["achats", "approvisionnement"], "de": ["einkauf", "beschaffung"], "it": ["acquisti", "approvvigionamento"]},
    "customs": {"fr": ["douane"], "de": ["zoll"], "it": ["dogana"]},
    "shipping": {"fr": ["expédition*"], "de": ["versand", "spedition"], "it": ["spedizion*"]},
    "retail": {"fr": ["commerce de détail", "magasin"], "de": ["detailhandel"], "it": ["commercio al dettaglio", "negozio"]},
    "visual merchandising": {"fr": ["merchandising"], "de": ["visual merchandising"], "it": ["visual merchandising"]},
    "cash register": {"fr": ["caisse"], "de": ["kasse"], "it": ["cassa"]},
    "upselling": {"fr": ["vente additionnelle"], "de": ["zusatzverkauf"], "it": ["vendita aggiuntiva"]},
    "teaching": {"fr": ["enseignement"], "de": ["unterricht"], "it": ["insegnamento"]},
    "patient care": {"fr": ["soins"], "de": ["pflege"], "it": ["assistenza ai pazienti"]},
    "maintenance": {"fr": ["maintenance", "entretien"], "de": ["instandhaltung", "wartung"], "it": ["manutenzione"]},
    "safety": {"fr": ["sécurité au travail"], "de": ["arbeitssicherheit"], "it": ["sicurezza sul lavoro"]},
    "compliance": {"fr": ["conformité"], "de": ["compliance"], "it": ["conformità"]},
    "contract management": {"fr": ["gestion des contrats"], "de": ["vertragsmanagement"], "it": ["gestione contratti"]},
    "process improvement": {"fr": ["amélioration des processus", "amélioration continue"], "de": ["prozessoptimierung"],
                            "it": ["miglioramento dei processi"]},
    "risk management": {"fr": ["gestion des risques"], "de": ["risikomanagement"], "it": ["gestione dei rischi"]},
    "vendor management": {"fr": ["gestion des fournisseurs"], "de": ["lieferantenmanagement"], "it": ["gestione fornitori"]},
    "presentations": {"fr": ["présentations"], "de": ["präsentationen"], "it": ["presentazioni"]},
    "communication": {"fr": ["communication"], "de": ["kommunikation"], "it": ["comunicazione"]},
    "3d design": {"fr": ["conception 3d", "3d"], "de": ["3d-planung", "3d"], "it": ["progettazione 3d", "3d"]},
    "interior design": {"fr": ["aménagement intérieur", "architecture d'intérieur", "décoration"],
                        "de": ["innenarchitektur", "inneneinrichtung"], "it": ["arredamento", "interior design"]},
}


SKILL_I18N.update({   # spoken languages, as skills
    "english": {"fr": ["anglais"], "de": ["englisch"], "it": ["inglese"]},
    "french": {"fr": ["français", "francais"], "de": ["französisch"], "it": ["francese"]},
    "german": {"fr": ["allemand"], "de": ["deutsch"], "it": ["tedesco"]},
    "italian": {"fr": ["italien"], "de": ["italienisch"], "it": ["italiano"]},
    "spanish": {"fr": ["espagnol"], "de": ["spanisch"], "it": ["spagnolo"]},
    "portuguese": {"fr": ["portugais"], "de": ["portugiesisch"], "it": ["portoghese"]},
})
_cache = {}


def spellings_for(term, langs):
    """spellings() for a stored skill keyword (any case, may end in *), cached: used on every match."""
    key = (term, tuple(langs))
    if key not in _cache:
        low = term.lower()
        _cache[key] = spellings(low, [x for x in LANGS if x in langs] or LANGS) if low in SKILL_I18N else [term]
    return _cache[key]


def spellings(skill, langs=LANGS):
    """The skill as written in the given languages (the canonical name first)."""
    out = [skill]
    for lang in langs:
        for s in SKILL_I18N.get(skill, {}).get(lang, []):
            if s not in out:
                out.append(s)
    return out
