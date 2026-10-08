"""Onboarding: imports (CV text/PDF/DOCX, LinkedIn export and PDF), role catalog, places,
generated settings, the wizard end to end, settings page, role CV, multilingual skills."""
import io
import json
import zipfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

CV_PIPES = """ALEX EXAMPLE
CLOUD ENGINEER | AUTOMATION
Geneva, Switzerland | +41 79 000 00 00 | alex@example.org | linkedin.com/in/alex-example/
PROFESSIONAL PROFILE
Cloud engineer with 9 years of experience in AWS and Azure. Automates everything with Terraform.
CORE COMPETENCIES
AWS | Azure | Terraform | Kubernetes | Python
PROFESSIONAL EXPERIENCE
Cloud Engineer | Example Corp | Switzerland | Jan 2020 - Present
• Built the AWS landing zone with Terraform
and moved 40 applications to it.
• Ran Kubernetes clusters for 30 teams.
Environment: AWS, Terraform, Kubernetes
Example Group\tMar 2016 – Dec 2019
Senior Engineer (Mar 2018 – Dec 2019)
• Automated server builds with Ansible.
Engineer (Mar 2016 – Feb 2018)
• Wrote Python tooling.
EDUCATION & LANGUAGES
BSc Computer Science | EPFL | 2012 - 2015
English: fluent | French: native | German: B1
"""

CV_STACKED = """Marie Exemple
Assistante administrative
marie@example.org
📞  Lausanne, Suisse
Profil professionnel
Assistante polyvalente avec six ans d'expérience en administration et service client.
Expérience professionnelle
Assistante administrative  •  Exemple SA
2019 – aujourd'hui  |  Lausanne
● Gestion de la correspondance et de la facturation, avec un suivi des commandes et
des fournisseurs (plannings, intégration,
formation).
● Accueil des clients.
Réceptionniste  •  Hôtel Exemple
2016 – 2019  |  Montreux
● Réservations et accueil en français, anglais et italien.
Formation
CFC Employée de commerce  |  Lausanne  |  2016
Langues
Français (langue maternelle)  |  Anglais (courant)  |  Italien (notions)
"""


def test_cv_with_pipes_groups_and_tool_lines(env):
    from app.importers import cvparse
    d = cvparse.parse(CV_PIPES)
    assert d["name"] == "Alex Example" and d["headline"] == "Cloud Engineer | Automation"
    assert d["contact"] == {"email": "alex@example.org", "linkedin": "linkedin.com/in/alex-example",
                            "phone": "+41 79 000 00 00", "location": "Geneva, Switzerland"}
    assert d["summary"].startswith("Cloud engineer with 9 years")
    exp = d["experience"]
    assert [(e["title"], e["org"]) for e in exp] == [("Cloud Engineer", "Example Corp"),
                                                    ("Senior Engineer", "Example Group"), ("Engineer", "Example Group")]
    assert exp[0]["dates"] == "Jan 2020 - Present"
    assert exp[0]["bullets"][0] == "Built the AWS landing zone with Terraform and moved 40 applications to it."
    assert exp[0]["bullets"][-1].startswith("Environment:")          # kept; compose skips it in prose
    assert d["education"] == ["BSc Computer Science | EPFL | 2012 - 2015"]
    assert {x["name"]: x["level"] for x in d["languages"]} == {"English": "fluent", "French": "native",
                                                               "German": "intermediate"}
    assert {"aws", "terraform", "kubernetes", "python", "ansible"} <= set(d["skills"])
    assert d["expertise"][:3] == ["AWS", "Azure", "Terraform"]


def test_cv_stacked_french_layout(env):
    from app.importers import cvparse
    d = cvparse.parse(CV_STACKED)
    assert d["name"] == "Marie Exemple" and d["headline"] == "Assistante administrative"
    assert d["contact"]["location"] == "Lausanne, Suisse"
    exp = d["experience"]
    assert [(e["title"], e["org"], e["loc"]) for e in exp] == [
        ("Assistante administrative", "Exemple SA", "Lausanne"), ("Réceptionniste", "Hôtel Exemple", "Montreux")]
    # "formation)." at the start of a wrapped line is not the Education heading
    assert exp[0]["bullets"][0].endswith("(plannings, intégration, formation).")
    assert d["education"] == ["CFC Employée de commerce  |  Lausanne  |  2016"]
    assert {x["name"]: x["level"] for x in d["languages"]} == {"French": "native", "English": "fluent",
                                                               "Italian": "basic"}
    # French words map to the catalog's skills
    assert {"invoicing", "correspondence", "reception", "reservations", "supplier management"} <= set(d["skills"])


def test_pdf_and_docx_roundtrip_through_the_sandboxed_extractor(env, tmp_path):
    from app import tailor
    from app.importers import cvparse, extract
    profile = {"name": "Alex Example", "headline": "Cloud Engineer", "contact": {"email": "alex@example.org"},
               "summary": "Cloud engineer with AWS and Terraform experience across many teams and projects.",
               "expertise": ["AWS", "Terraform"],
               "experience": [{"title": "Cloud Engineer", "org": "Example Corp", "loc": "Geneva",
                               "dates": "Jan 2020 – Present", "bullets": ["Built the AWS landing zone."]}],
               "education": ["BSc EPFL"]}
    pdf = tmp_path / "cv.pdf"
    tailor.render(profile, [], str(pdf), lang="en")
    d = cvparse.parse_any(extract.text_of("cv.pdf", pdf.read_bytes()))
    assert d["name"] == "Alex Example" and d["experience"][0]["org"] == "Example Corp"
    assert "aws" in d["skills"]

    body = "".join(f"<w:p><w:r><w:t>{x}</w:t></w:r></w:p>" for x in CV_PIPES.splitlines())
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr("word/document.xml", f"<w:document><w:body>{body}</w:body></w:document>")
    d = cvparse.parse_any(extract.text_of("cv.docx", buf.getvalue()))
    assert d["experience"][0]["title"] == "Cloud Engineer"

    for name, data, msg in [("x.exe", b"MZ....", "Unsupported"), ("x.pdf", b"%PDF-1.4 garbage", "couldn't be read"),
                            ("x.pdf", b"%PDF-" + b"0" * (extract.MAX_UPLOAD + 1), "too large")]:
        with pytest.raises(extract.ImportError_, match=msg):
            extract.text_of(name, data)


def _linkedin_zip(tmp_path):
    files = {
        "Profile.csv": "First Name,Last Name,Maiden Name,Address,Birth Date,Headline,Summary,Industry,Zip Code,Geo Location\n"
                       'Alex,Example,,,,"Cloud Engineer at Example","Builds clouds.",IT,,"Geneva, Switzerland"\n',
        "Positions.csv": "Company Name,Title,Description,Location,Started On,Finished On\n"
                         'Example Corp,Cloud Engineer,"Built the landing zone. Ran Kubernetes.",Geneva,Jan 2020,\n'
                         "Old SA,Sysadmin,,Lausanne,Mar 2015,Dec 2019\n",
        "Skills.csv": "Name\nTerraform\nAmazon Web Services (AWS)\n",
        "Languages.csv": "Name,Proficiency\nFrench,Native or bilingual proficiency\nEnglish,Full professional proficiency\n",
        "Email Addresses.csv": "Email Address,Confirmed,Primary,Updated On\nold@example.org,Yes,No,\nalex@example.org,Yes,Yes,\n",
        "Connections.csv": "Notes:\n\"Some notes\"\n\nFirst Name,Last Name\nA,B\n",
    }
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        for n, c in files.items():
            z.writestr(f"Basic_LinkedInDataExport/{n}", c)
    return buf.getvalue()


def test_linkedin_export_zip(env, tmp_path):
    from app.importers import extract, linkedin
    d = linkedin.parse_zip(_linkedin_zip(tmp_path))
    assert d["name"] == "Alex Example" and d["headline"] == "Cloud Engineer at Example"
    assert d["contact"] == {"email": "alex@example.org", "location": "Geneva, Switzerland"}
    assert [(e["title"], e["dates"]) for e in d["experience"]] == [("Cloud Engineer", "Jan 2020 – Present"),
                                                                    ("Sysadmin", "Mar 2015 – Dec 2019")]
    assert d["experience"][0]["bullets"] == ["Built the landing zone.", "Ran Kubernetes."]
    assert {x["name"]: x["level"] for x in d["languages"]} == {"French": "native", "English": "fluent"}
    assert {"terraform", "aws", "kubernetes"} <= set(d["skills"])
    with pytest.raises(extract.ImportError_, match="LinkedIn"):
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as z:
            z.writestr("other.txt", "x")
        linkedin.parse_zip(buf.getvalue())


LI_PDF = """Contact
alex@example.org
www.linkedin.com/in/alex-example (LinkedIn)
Top Skills
Terraform
Amazon Web Services (AWS)
Kubernetes
Languages
French (Native or Bilingual)
English (Full Professional)
Alex Example
Cloud Engineer at Example Corp
Geneva, Switzerland
Summary
I build and run cloud platforms.
Experience
Example Corp
5 years 9 months
Cloud Engineer
January 2022 - Present (3 years 9 months)
Geneva, Switzerland
Built the landing zone.
Engineer
January 2020 - December 2021 (2 years)
Wrote tooling.
Old SA
Sysadmin
March 2015 - December 2019 (4 years 10 months)
Lausanne
Education
EPFL
BSc, Computer Science · (2012 - 2015)
Page 1 of 2
"""


def test_linkedin_profile_pdf_text(env):
    from app.importers import cvparse
    assert cvparse.is_linkedin_pdf(LI_PDF) and not cvparse.is_linkedin_pdf(CV_PIPES)
    d = cvparse.parse_any(LI_PDF)
    assert d["name"] == "Alex Example" and d["headline"] == "Cloud Engineer at Example Corp"
    assert d["contact"]["location"] == "Geneva, Switzerland"
    assert d["expertise"] == ["Terraform", "Amazon Web Services (AWS)", "Kubernetes"]
    assert [(e["title"], e["org"], e["loc"]) for e in d["experience"]] == [
        ("Cloud Engineer", "Example Corp", "Geneva, Switzerland"), ("Engineer", "Example Corp", ""),
        ("Sysadmin", "Old SA", "Lausanne")]
    assert d["experience"][0]["bullets"] == ["Built the landing zone."]
    assert d["education"] == ["EPFL BSc, Computer Science , (2012 - 2015)"]
    assert d["summary"] == "I build and run cloud platforms."


def test_roles_places_and_generated_settings(env):
    from app import onboard, places, roles
    from app.importers import cvparse
    assert roles.match_title("Senior Cloud Architect")[0] == "cloud-architect"
    assert roles.match_title("Assistante administrative")[0] == "administrative-assistant"
    assert places.find("geneva")[3] == "GE" and places.find("Lausanne VD")[3] == "VD" and not places.find("Atlantis")
    words, cantons = places.search_area("Lausanne", 30)
    assert cantons[0] == "VD" and "morges" in words and "zurich" not in words and "romandie" in words
    assert "switzerland" not in words and "switzerland" in places.search_area("Lausanne", 30, True)[0]

    d = onboard.merge([cvparse.parse(CV_STACKED)])
    t = onboard.default_targets(d)
    assert t["roles"][0] in ("administrative-assistant", "receptionist")
    assert t["home"] == "Lausanne" and t["langs"] == ["en", "fr"] and t["seniority"] == "senior"   # since 2016
    st = onboard.settings_for(d, t)
    assert "Assistante administrative" in st["SEARCH_TERMS"] and "Administrative Assistant" in st["SEARCH_TERMS"]
    assert st["JOBROOM_CANTONS"][0] == "VD" and st["WHERE"][0] == "Vaud"
    assert "intern" in st["TITLE_EXCLUDE"] and "junior" in st["TITLE_EXCLUDE"]
    assert "junior" not in onboard.settings_for(d, dict(t, seniority="entry"))["TITLE_EXCLUDE"]
    assert "invoicing" in st["SCORE_KEYWORDS"] and "french" in st["SCORE_KEYWORDS"]
    assert "italian" not in st["SCORE_KEYWORDS"]            # only "notions": not a working language
    assert "remote" in st["PROVIDERS"] and st["LANGUAGES"] == ["en", "fr"]


def test_skills_match_in_every_posting_language(env, monkeypatch):
    monkeypatch.setattr(env.config, "LANGUAGES", ["fr", "en"])
    job = {"title": "Conseiller de vente", "description": "La vente et le conseil client. Anglais un atout. Terraform."}
    assert env.filters.matched(job, ["sales", "customer advice", "english", "logistics"]) == \
        ["sales", "customer advice", "english"]
    assert env.compose.surface("sales", job) == "vente"
    monkeypatch.setattr(env.config, "LANGUAGES", ["en"])
    assert env.filters.matched(job, ["sales"]) == []          # French spellings only when searching French


def test_settings_json_overrides_env_and_is_picked_up_by_the_next_scan(env, monkeypatch):
    c = env.config
    assert c.TITLE_KEYWORDS == ["architect", "devops"]
    c.save_settings({"TITLE_KEYWORDS": ["Coordinat*", "Réception*"], "ALLOW_REMOTE": False, "BOGUS": 1,
                     "FETCH_INTERVAL_HOURS": 0})
    assert c.TITLE_KEYWORDS == ["coordinat*", "réception*"] and c.ALLOW_REMOTE is False
    assert c.FETCH_INTERVAL_HOURS == 1.0 and "BOGUS" not in json.loads(Path(c.SETTINGS_PATH).read_text())
    # another process saved new settings: the scan reloads them, and only then
    Path(c.SETTINGS_PATH).write_text(json.dumps({"TITLE_KEYWORDS": ["office"]}))
    import os
    os.utime(c.SETTINGS_PATH, ns=(1, 1))
    monkeypatch.setattr(c, "PROVIDERS", [])
    env.fetch.run()
    assert c.TITLE_KEYWORDS == ["office"] and c.ALLOW_REMOTE is True      # absent key -> .env value again


@pytest.fixture
def client(env, monkeypatch):
    monkeypatch.setattr(env.config, "ONBOARDING", True)
    monkeypatch.setattr(env.config, "PROVIDERS", [])
    return TestClient(env.web.app)


def test_wizard_end_to_end(env, client, tmp_path):
    c = client
    r = c.get("/jobs", follow_redirects=False)
    assert r.status_code == 303 and r.headers["location"] == "/onboarding"      # no profile yet
    assert c.get("/healthz").status_code == 200
    assert "Choose at least one file" in c.post("/onboarding/import", data={}).text

    r = c.post("/onboarding/import", files={"cv": ("cv.txt", CV_STACKED.encode(), "text/plain"),
                                             "linkedin_zip": ("li.zip", _linkedin_zip(tmp_path), "application/zip")})
    assert r.status_code == 200 and "Marie Exemple" in r.text and "Read from: CV, LinkedIn export" in r.text
    st = env.onboard.state()
    assert st["step"] == "review" and st["draft"]["name"] == "Marie Exemple"
    assert st["draft"]["experience"][0]["org"] == "Exemple SA"               # the CV wins over LinkedIn

    form = {"name": "Marie Exemple", "headline": "Assistante administrative", "email": "marie@example.org",
            "phone": "", "linkedin": "", "location": "Lausanne, Suisse", "summary": "Assistante polyvalente.",
            "skills": "invoicing, reception, excel", "expertise": "Facturation\nAccueil",
            "languages": "Français, langue maternelle\nEnglish, fluent", "n_exp": "1",
            "exp-0-title": "Assistante administrative", "exp-0-org": "Exemple SA", "exp-0-loc": "Lausanne",
            "exp-0-dates": "2019 – aujourd'hui", "exp-0-bullets": "Facturation et correspondance.\nAccueil des clients.",
            "education": "CFC Employée de commerce", "extras_title": "", "extras": ""}
    c.post("/onboarding/review", data=dict(form, action="add"))
    assert len(env.onboard.state()["draft"]["experience"]) == 2
    c.post("/onboarding/review", data=dict(form, action="del-0"))
    assert env.onboard.state()["draft"]["experience"] == []
    r = c.post("/onboarding/review", data=dict(form, action="next"))
    assert env.onboard.state()["step"] == "target" and "What are you looking for?" in r.text
    assert env.onboard.state()["draft"]["languages"] == [{"name": "French", "code": "fr", "level": "langue maternelle"},
                                                         {"name": "English", "code": "en", "level": "fluent"}]

    assert "Pick at least one role" in c.post("/onboarding/target", data={"home": "Lausanne", "langs": ["fr"]}).text
    r = c.post("/onboarding/target", data={"roles": ["administrative-assistant", "not-a-role"], "home": "Lausanne",
                                           "radius": "20", "langs": ["fr", "en"], "seniority": "mid", "remote": "1",
                                           "avoid": "night shifts"})
    assert "Your search, ready to go" in r.text and "/cv/role/administrative-assistant.pdf" in r.text
    pdf = c.get("/cv/role/administrative-assistant.pdf")
    assert pdf.status_code == 200 and pdf.content[:5] == b"%PDF-"
    st = env.onboard.state()
    assert st["targets"]["roles"] == ["administrative-assistant"] and st["settings"]["JOBROOM_CANTONS"][0] == "VD"

    fields = {k: "\n".join(v) if isinstance(v, list) else str(v) for k, v in st["settings"].items()}
    fields.pop("ALLOW_REMOTE")
    r = c.post("/onboarding/finish", data=fields, follow_redirects=False)
    assert r.status_code == 303 and r.headers["location"] == "/jobs?status=new"
    profile = json.loads(Path(env.config.PROFILE_PATH).read_text())
    assert profile["name"] == "Marie Exemple" and "skills" not in profile and "languages" not in profile
    assert profile["extras_title"] == "LANGUAGES" and profile["extras"][0].startswith("Languages: French")
    assert env.config.ALLOW_REMOTE is False and "vaud" in env.config.LOCATION_KEYWORDS
    assert json.loads(Path(env.config.WATCHLIST_PATH).read_text())               # seed boards
    assert env.prefs.avoided() == ["night shifts"]
    assert env.store.get_meta().get("last_scan_at")                              # first scan ran
    assert c.get("/jobs").status_code == 200                                     # wizard no longer in the way
    assert c.get("/onboarding", follow_redirects=False).headers["location"] == "/jobs?status=new"

    # edit the profile later: back to the review form, saving keeps the search settings
    before = env.config.SEARCH_TERMS
    c.post("/onboarding/edit")
    assert "Marie Exemple" in c.get("/onboarding").text
    r = c.post("/onboarding/review", data=dict(form, headline="Office assistant", action="next"), follow_redirects=False)
    assert r.headers["location"] == "/cv"
    assert json.loads(Path(env.config.PROFILE_PATH).read_text())["headline"] == "Office assistant"
    assert env.config.SEARCH_TERMS == before


def test_settings_page_and_role_cv_page(env, client):
    Path(env.config.PROFILE_PATH).write_text(json.dumps({
        "name": "Alex Example", "summary": "Cloud engineer. Terraform on AWS every day.", "expertise": ["AWS"],
        "experience": [{"title": "Cloud Engineer", "org": "Example Corp", "loc": "Geneva", "dates": "2020 – Present",
                        "bullets": ["Built the AWS landing zone with Terraform."]}], "education": []}))
    c = client
    assert "Search settings" in c.get("/settings").text
    r = c.post("/settings", data={"SEARCH_TERMS": "Cloud Engineer\nDevOps, SRE", "TITLE_KEYWORDS": "cloud",
                                  "FETCH_INTERVAL_HOURS": "6", "LANGUAGES": "en"}, follow_redirects=False)
    assert r.headers["location"] == "/settings?saved=1"
    assert env.config.SEARCH_TERMS == ["Cloud Engineer", "DevOps", "SRE"] and env.config.ALLOW_REMOTE is False
    assert env.config.FETCH_INTERVAL_HOURS == 6.0
    r = c.post("/cv/role", data={"role": "cloud-architect"})
    assert "Open CV for Cloud Architect" in r.text and "✓ AWS" in r.text and "✓ Terraform" in r.text
    assert "kubernetes" in r.text                                   # usual for the role, missing from the profile
    assert c.get("/cv/role/cloud-architect.pdf").content[:5] == b"%PDF-"
    assert c.get("/cv/role/../../etc.pdf").status_code == 404


def test_letter_spaced_headings_of_designed_cvs_are_read(env):
    from app.importers import cvparse
    assert cvparse._unspace("C O N T A C T") == "CONTACT" and cvparse._unspace("CO M P É T E N C E S") == "COMPÉTENCES"
    assert cvparse._unspace("M A R I E  E X E M P L E") == "MARIE EXEMPLE"
    for keep in ("BSc in IT", "A B C", "Plans de A à Z", "AWS | GCP | K8S | CI"):
        assert cvparse._unspace(keep) == keep
    d = cvparse.parse("P R O F I L\nAssistante polyvalente avec six ans d'expérience.\n\nC O M P É T E N C E S\n"
                      "• Accueil des clients\n• Facturation\n\nL A N G U E S\nFrançais : langue maternelle\nAnglais : C1\n")
    assert d["summary"].startswith("Assistante polyvalente") and "Facturation" in d["expertise"]
    assert {x["name"] for x in d["languages"]} == {"French", "English"}


def _zip(files):
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        for name, text in files.items():
            z.writestr(name, text)
    return buf.getvalue()


def test_partial_linkedin_export_single_csv_and_misplaced_files_are_accepted(env, monkeypatch):
    from app.importers import linkedin
    skills = "Name\nArchicad\nAutocad\n"
    langs = "Name,Proficiency\nFrench,Native or bilingual proficiency\nEnglish,Professional working proficiency\n"
    positions = "Company Name,Title,Description,Location,Started On,Finished On\nAcme SA,Coordinator,Planned deliveries.,Lausanne,Jan 2020,\n"
    # LinkedIn's quick archive: no Profile.csv, no Positions.csv
    d = linkedin.parse_zip(_zip({"Basic_Export/Skills.csv": skills, "Basic_Export/Languages.csv": langs}))
    assert d["_parts"] == ["languages.csv", "skills.csv"] and d["expertise"] == ["Archicad", "Autocad"] and d["experience"] == []
    assert {x["name"] for x in d["languages"]} == {"French", "English"} and d["name"] == ""
    assert linkedin.coverage(d["_parts"]) == ("languages, skills", "profile, positions")
    d = linkedin.parse_csv("C:\\\\Users\\\\me\\\\Positions.csv", positions.encode())
    assert d["experience"][0]["title"] == "Coordinator" and d["_parts"] == ["positions.csv"]
    for bad in (lambda: linkedin.parse_csv("Connections.csv", b"a,b\n"), lambda: linkedin.parse_zip(_zip({"readme.txt": "x"})),
                lambda: linkedin.parse_zip(b"PK\x03\x04 cut off"), lambda: linkedin.parse_zip(b"x" * (linkedin.MAX_ZIP + 1))):
        with pytest.raises(Exception) as e:
            bad()
        assert type(e.value).__name__ == "ImportError_"
    # in the wizard: a partial export alone moves on, and says what is still to fill in
    monkeypatch.setattr(env.config, "ONBOARDING", True)
    c = TestClient(env.web.app)
    r = c.post("/onboarding/import", files={"linkedin_zip": ("export.zip", _zip({"Skills.csv": skills}), "application/zip")}, follow_redirects=True)
    st = env.onboard.state()
    assert st["step"] == "review" and st["sources"] == ["LinkedIn export"] and "archicad" in st["draft"]["skills"]
    assert "Partial LinkedIn export: read skills. Not in the file: profile, positions." in r.text and "_parts" not in st["draft"]
    # several single CSV files at once, and a ZIP dropped into the CV field: both understood
    c.post("/onboarding/restart")
    c.post("/onboarding/import", files=[("linkedin_zip", ("Positions.csv", positions.encode(), "text/csv")),
                                        ("linkedin_zip", ("Languages.csv", langs.encode(), "text/csv"))])
    st = env.onboard.state()
    assert st["draft"]["experience"][0]["org"] == "Acme SA" and len(st["draft"]["languages"]) == 2
    c.post("/onboarding/restart")
    c.post("/onboarding/import", files={"cv": ("linkedin.zip", _zip({"Profile.csv": "First Name,Last Name,Headline\nSam,Test,Coordinator\n",
                                                                     "Positions.csv": positions}), "application/zip")})
    st = env.onboard.state()
    assert st["step"] == "review" and st["draft"]["name"] == "Sam Test" and st["errors"] == []           # complete: no notice
    # one bad file next to a good one: the good one is used, the bad one named
    c.post("/onboarding/restart")
    r = c.post("/onboarding/import", files=[("cv", ("cv.txt", CV_PIPES.encode(), "text/plain")),
                                            ("linkedin_zip", ("broken.zip", b"PK\x03\x04 cut", "application/zip"))], follow_redirects=True)
    st = env.onboard.state()
    assert st["step"] == "review" and st["draft"]["name"] == "Alex Example" and "broken.zip" in r.text
