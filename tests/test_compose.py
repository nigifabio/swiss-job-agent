"""Rule-based writer: relevance ranking, tailored summary, letter body."""
PROFILE = {"summary": "Cloud and infrastructure architect with 14 years of experience. "
                      "Background in security governance and ISO 27001. Works in English and Italian.",
           "experience": [
               {"title": "Technical Manager", "org": "GTT", "bullets": [
                   "Evaluate vendors through total-cost-of-ownership assessment.",
                   "Drive automation initiatives with Python and APIs.",
                   "Environment: AWS, Azure, Python."]},
               {"title": "Senior Infrastructure Engineer", "org": "PwC", "bullets": [
                   "Automated DevOps infrastructure across AWS and Azure with Terraform."]}]}
JOB = {"title": "DevOps Engineer", "company": "Acme SA",
       "description": "We automate our AWS platform with Terraform and Python. Strong DevOps culture."}


def test_facts_ranked_by_relevance_and_tool_lists_skipped(env):
    facts = [b for _, b, _ in env.compose.rank_facts(PROFILE, JOB)]
    assert facts[0].startswith("Automated DevOps infrastructure")        # most shared words + skills
    assert all(not f.startswith("Environment:") for f in facts)
    assert facts[-1].startswith("Evaluate vendors")                        # nothing in common: last


def test_summary_uses_only_profile_sentences_plus_matched_skills(env):
    s = env.compose.summary(PROFILE, JOB, "en")
    assert s.startswith("Cloud and infrastructure architect with 14 years of experience.")
    assert "Directly relevant to this role: AWS and Terraform." in s
    assert "security governance" not in s             # unrelated sentence left out
    assert env.compose.summary(PROFILE, JOB, "fr").endswith(".") and "Atouts directement liés à ce poste" in env.compose.summary(PROFILE, JOB, "fr")
    assert env.compose.summary({"summary": ""}, JOB, "en") == ""


def test_letter_body_is_built_from_profile_facts(env):
    body = env.compose.letter_body(PROFILE, JOB, "en")
    paras = body.split("\n\n")
    assert paras[0] == "I am applying for the DevOps Engineer position at Acme SA."
    assert paras[1] == "Cloud and infrastructure architect with 14 years of experience. Background in security governance and ISO 27001."   # own words
    assert paras[2] == "In my current role as Technical Manager at GTT, my experience covers the key points of your posting: AWS and Terraform."
    assert "– Automated DevOps infrastructure across AWS and Azure with Terraform." in paras[3]
    assert paras[4].startswith("I would now like to put this experience and my motivation to work at Acme SA")
    assert paras[-1].startswith("I would be glad to meet you") and paras[-1].endswith("Thank you for considering my application.") and len(paras) == 6
    named = env.compose.letter_body(dict(PROFILE, headline="Cloud Architect"), dict(JOB, company=""), "en").split("\n\n")
    assert named[0] == "As a Cloud Architect, I am applying for the DevOps Engineer position." and "in your company" in named[4]
    tag = env.compose.letter_body(dict(PROFILE, headline="Cloud | Security | Leadership"), JOB, "en")
    assert tag.startswith("I am applying for the DevOps Engineer position at Acme SA.")          # a tag line is not a title
    fr = env.compose.letter_body(dict(PROFILE, headline="Dessinatrice en bâtiment"), JOB, "fr").split("\n\n")
    assert fr[0] == "Dessinatrice en bâtiment, je vous adresse ma candidature pour le poste de DevOps Engineer au sein de Acme SA."
    assert "au service de Acme SA" in fr[4] and fr[-1].endswith("Je vous remercie de l'attention portée à ma candidature.")
    it = env.compose.letter_body(PROFILE, JOB, "it")
    assert it.startswith("Vi sottopongo la mia candidatura per la posizione di DevOps Engineer presso Acme SA.")


def test_letter_uses_posting_spelling_and_hides_confidential_employer(env, monkeypatch):
    monkeypatch.setattr(env.config, "SCORE_KEYWORDS", ["coordinat*", "terraform", "aws"])
    env.prefs.invalidate()
    prof = {"summary": "Ops.", "experience": [{"title": "Coordinatrice", "org": "Confidential",
                                               "bullets": ["Coordination des fournisseurs."]}]}
    job = {"title": "Coordinateur de commandes", "company": "Acme",
           "description": "Coordinateur de commandes. Poste de coordination avec Terraform sur AWS. "
                          "Vous assurez la coordination des livraisons."}
    body = env.compose.letter_body(prof, job, "fr")
    assert "Dans mon poste actuel de Coordinatrice, mon expérience couvre" in body   # no "chez Confidential"
    assert ": coordination, Terraform et AWS." in body       # posting's spelling, from the text not the title
    assert "coordinat," not in body and "coordinat " not in body                  # stem never shown
    prof["experience"][0]["org"] = "GTT"
    assert "Coordinatrice chez GTT" in env.compose.letter_body(prof, job, "fr")
