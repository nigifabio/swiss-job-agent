"""Interface languages: every translated fragment still matches its template, every page renders in
French and German, the setting wins over the browser."""
import datetime
import json
import os
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from test_features import PROFILE, _job

TEMPLATES = Path(__file__).resolve().parent.parent / "app" / "templates"


def test_every_fragment_still_occurs_in_its_template(env):
    for name, entries in env.locales.TEMPLATES.items():
        source = (TEMPLATES / name).read_text()
        assert env.i18n.missing(source, entries) == [], name
        assert all(len(e) == 3 and all(e) for e in entries), name
    assert all(len(v) == 2 and all(v) for v in env.locales.STRINGS.values())
    assert set(env.locales.TEMPLATES) == {p.name for p in TEMPLATES.glob("*.html")}      # no page forgotten


@pytest.mark.parametrize("lang", ["fr", "de"])
def test_all_templates_compile_in_every_language(env, lang):
    e = env.i18n.environments(str(TEMPLATES), env.locales.TEMPLATES)[lang]
    e.filters["safe_url"] = lambda u: u
    for p in TEMPLATES.glob("*.html"):
        e.get_template(p.name)                                           # a broken translated fragment fails here


def _populate(env):
    Path(env.config.PROFILE_PATH).write_text(json.dumps(PROFILE))
    a = _job(env, "Cloud Architect", description="AWS and Terraform. Allemand C1. Permis de conduire.")
    b = _job(env, "DevOps Engineer", "applied")
    env.store.update_fields(b, {"applied_date": (datetime.date.today() - datetime.timedelta(days=12)).isoformat()})
    c = _job(env, "Assigned")
    env.store.update_fields(c, {"orp_assigned": 1, "orp_deadline": (datetime.date.today() + datetime.timedelta(days=3)).isoformat()})
    env.store.dismiss(_job(env, "Industrial Architect"), "wrong_role")
    env.store.dismiss(_job(env, "Industrial Engineer Architect"), "wrong_role")
    return a, b


@pytest.mark.parametrize("lang,words", [
    ("fr", ["Rechercher maintenant", "Objectif ORP", "Assignations de l'ORP", "relancer ?", "Pas pour moi", "nouvelles (", "Réglages"]),
    ("de", ["Jetzt suchen", "RAV-Ziel", "Zuweisungen des RAV", "nachfassen?", "Nichts für mich", "neu (", "Einstellungen"]),
])
def test_pages_render_in_french_and_german(env, lang, words):
    a, b = _populate(env)
    c = TestClient(env.web.app, headers={"accept-language": f"{lang}-CH,{lang};q=0.9,en;q=0.5"})
    home = c.get("/jobs?status=new").text
    for w in words:
        assert w in home, w
    assert f'<html lang="{lang}">' in home and "↻ Scan now" not in home and "✕ Not for me" not in home
    pages = {"/job/%d" % a: {"fr": ["Poste déjà pourvu", "Allemand (pas dans vos compétences)", "Permis de conduire", "Lettre de motivation", "Pourquoi ? (facultatif)"],
                             "de": ["Stelle bereits besetzt", "Deutsch (nicht in Ihren Kompetenzen)", "Führerausweis", "Motivationsschreiben", "Warum? (freiwillig)"]},
             "/job/%d" % b: {"fr": ["Message de relance", "Fiche de préparation"], "de": ["Nachfass-Nachricht", "Vorbereitungsblatt"]},
             "/stats": {"fr": ["Pourquoi des offres ont été écartées", "Pas mon type de poste", "ignorer les titres avec « industrial »"],
                        "de": ["Warum Stellen verworfen wurden", "Nicht meine Art von Stelle", "Titel mit «industrial» überspringen"]},
             "/report": {"fr": ["Formulaire officiel ORP", "Imprimer"], "de": ["Offizielles RAV-Formular", "Drucken"]},
             "/cv": {"fr": ["Compétences et préférences", "CV à partir de mots-clés"], "de": ["Kompetenzen und Vorlieben", "Lebenslauf aus Stichwörtern"]},
             "/settings": {"fr": ["Réglages de la recherche", "Rayon de recherche (km)", "Langue de ce site"], "de": ["Sucheinstellungen", "Suchradius (km)", "Sprache dieser Website"]},
             "/add": {"fr": ["Ajouter une candidature", "Titre du poste *"], "de": ["Bewerbung hinzufügen", "Stellentitel *"]},
             "/add?kind=spontaneous": {"fr": ["Candidature spontanée", "Personne de contact"], "de": ["Spontanbewerbung", "Kontaktperson"]},
             "/jobs?status=discarded": {"fr": ["Pas mon type de poste", "Remettre dans les nouvelles"], "de": ["Nicht meine Art von Stelle", "Zurück zu neu"]}}
    for url, expect in pages.items():
        r = c.get(url)
        assert r.status_code == 200, url
        for w in expect[lang]:
            assert w in r.text, (url, w)
    # the buttons still work in the translated pages
    assert c.post(f"/job/{a}/dismiss", data={"reason": "location"}, headers={"x-requested-with": "fetch"}).json()["state"] == "discarded"


def test_setting_wins_over_the_browser_and_english_is_the_default(env):
    c = TestClient(env.web.app)
    assert "Scan now" in c.get("/jobs").text                                                       # no header: English
    assert "Scan now" in c.get("/jobs", headers={"accept-language": "it-IT,it;q=0.9"}).text         # no Italian interface
    assert "Rechercher maintenant" in c.get("/jobs", headers={"accept-language": "it;q=0.9,fr;q=0.8"}).text
    form = {k: (",".join(map(str, v)) if isinstance(v, list) else str(int(v) if isinstance(v, (bool, float)) else v))
            for k, v in ((k, getattr(env.config, k)) for k in env.config.EDITABLE)}
    form["UI_LANG"] = "de"
    c.post("/settings", data=form)
    assert env.config.UI_LANG == "de" and "Jetzt suchen" in c.get("/jobs", headers={"accept-language": "fr"}).text
    form["UI_LANG"] = "xx"
    c.post("/settings", data=form)
    assert env.config.UI_LANG == "" and env.i18n.pick("", "de-CH") == "de" and env.i18n.pick("fr", "de") == "fr"


def test_wizard_pages_render_in_french(env, monkeypatch):
    monkeypatch.setattr(env.config, "ONBOARDING", True)
    c = TestClient(env.web.app, headers={"accept-language": "fr"})
    page = c.get("/onboarding").text
    assert "Préparons votre recherche d'emploi" in page and "1 · Importer" in page and "Lire mes fichiers" in page
    c.post("/onboarding/import", data={"skip": "1"})
    page = c.get("/onboarding").text
    assert "Votre profil" in page and "Nom complet" in page and "Enregistrer et continuer" in page
