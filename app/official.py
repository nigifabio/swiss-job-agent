"""The official unemployment-insurance form 716.007 "Preuves des recherches personnelles effectuées en
vue de trouver un emploi" (SECO), filled from the month's applications.

The form is not shipped with the app: it is downloaded once from the SECO site (ORP_FORM_URL) and kept
in the data folder. It has 14 lines; a month with more applications gives several copies in one PDF.
If the form can't be fetched, the app's own report is used instead.

Fields (verified 2026-10-08): "Nom et prénoms", "No AVS", "Mois et année", and per line n = 1..14:
"jour-mois n", "Entreprise adresse_n", "Description du poste_n", "Motif_n" and the check boxes
"Assignation ORP_n", "à plein temps_n", "à temps partiel_n", "par lettre_n", "visite personnelle_n",
"par téléphone_n", "en suspens_n", "entretien_n", "engagement_n", "négatif_n" (checked = /Ja).
"""
import datetime
import io
import os

from . import config, store
from .http import Http

URL = os.environ.get("ORP_FORM_URL", "https://www.secoalv.admin.ch/dam/secoalv/fr/dokumente/formulare/arbeitslose/"
                                     "716.007_neu.pdf.download.pdf/716.007_neu.pdf")
LINES = 14
MONTHS = ["janvier", "février", "mars", "avril", "mai", "juin", "juillet", "août", "septembre", "octobre", "novembre", "décembre"]
METHOD = {"written": "par lettre", "phone": "par téléphone", "in_person": "visite personnelle"}
RESULT = {"interview": "entretien", "offer": "engagement", "rejected": "négatif"}      # anything else: en suspens


def template_path():
    return os.path.join(os.path.dirname(config.DB_PATH) or ".", "orp-form-716.007.pdf")


def template():
    """Path of the blank official form (downloaded on first use), or None when it can't be had."""
    path = template_path()
    if os.path.exists(path) and os.path.getsize(path) > 10_000:
        return path
    try:
        with Http(timeout=25, tries=2) as c:
            data = c.get(URL, follow_redirects=True).content
        if not data.startswith(b"%PDF") or len(data) < 10_000:
            return None
        tmp = path + ".tmp"
        with open(tmp, "wb") as f:
            f.write(data)
        os.replace(tmp, path)
        return path
    except Exception:  # noqa: BLE001
        return None


def month_label(key):
    y, m = key.split("-")
    return f"{MONTHS[int(m) - 1].capitalize()} {y}"


def line_values(job, n):
    """Field values of form line n (1-based) for one application."""
    d = datetime.date.fromisoformat(job["applied_date"])
    who = ", ".join(x for x in (job.get("company"), job.get("location")) if x)
    if job.get("contact"):
        who += f"\n{job['contact']}"
    rate = (job.get("work_rate") or store.guess_work_rate(job.get("title"))).replace(" ", "")
    full = rate in ("100%", "")
    title = (job.get("title") or "").strip()
    v = {f"jour-mois {n}": d.strftime("%d  %m"), f"Entreprise adresse_{n}": who[:160],
         f"Description du poste_{n}": (title if full or rate.rstrip("%") in title.replace(" ", "") else f"{title} ({rate})")[:120],
         f"à plein temps_{n}": "/Ja" if full else "/Off", f"à temps partiel_{n}": "/Off" if full else "/Ja",
         f"Assignation ORP_{n}": "/Ja" if job.get("orp_assigned") else "/Off"}
    how = METHOD.get(job.get("apply_method") or "written", "par lettre")
    for k in METHOD.values():
        v[f"{k}_{n}"] = "/Ja" if k == how else "/Off"
    res = RESULT.get(job.get("status"), "en suspens")
    for k in ("en suspens", "entretien", "engagement", "négatif"):
        v[f"{k}_{n}"] = "/Ja" if k == res else "/Off"
    v[f"Motif_{n}"] = (job.get("outcome_note") or "")[:60] if res == "négatif" else ""
    return v


def fill(jobs, name, key, out):
    """Write the official form for the month `key` ("2026-10") to `out`. Returns out, or None when the
    blank form isn't available."""
    blank = template()
    if not blank:
        return None
    from pypdf import PdfReader, PdfWriter
    from pypdf.generic import NameObject, TextStringObject, BooleanObject
    chunks = [jobs[i:i + LINES] for i in range(0, len(jobs), LINES)] or [[]]
    final = PdfWriter()
    for ci, chunk in enumerate(chunks):
        w = PdfWriter(clone_from=PdfReader(blank))
        values = {"Nom et prénoms": name or "", "Mois et année": month_label(key)}
        for n, job in enumerate(chunk, 1):
            values.update(line_values(job, n))
        for page in w.pages:
            w.update_page_form_field_values(page, values, auto_regenerate=False)
        w.set_need_appearances_writer(True)
        if len(chunks) > 1:                       # several copies in one file: field names must differ
            for page in w.pages:
                for a in page.get("/Annots", []):
                    o = a.get_object()
                    if "/T" in o:
                        o[NameObject("/T")] = TextStringObject(f"{o['/T']} p{ci + 1}")
        buf = io.BytesIO()
        w.write(buf)
        buf.seek(0)
        final.append(buf)
    try:
        final._root_object["/AcroForm"][NameObject("/NeedAppearances")] = BooleanObject(True)
    except KeyError:
        pass
    os.makedirs(os.path.dirname(out) or ".", exist_ok=True)
    with open(out, "wb") as f:
        final.write(f)
    return out
