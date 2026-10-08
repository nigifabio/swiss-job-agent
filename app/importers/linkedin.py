"""LinkedIn data export (Settings > Data privacy > Get a copy of your data) -> draft profile.

The ZIP holds CSV files; the ones used here: Profile.csv, Positions.csv, Education.csv,
Skills.csv, Languages.csv, Certifications.csv, Email Addresses.csv, PhoneNumbers.csv.
LinkedIn itself isn't contacted: the user downloads the export and uploads it.
"""
import csv
import io
import re
import zipfile

from . import cvparse
from .extract import ImportError_

MAX_MEMBER = 5 * 1024 * 1024
MAX_ZIP = 25 * 1024 * 1024            # a full export with messages and media is far bigger than a CV
WANTED = ("profile.csv", "positions.csv", "education.csv", "skills.csv", "languages.csv",
          "certifications.csv", "email addresses.csv", "phonenumbers.csv")
LI_LEVELS = {"native or bilingual": "native", "full professional": "fluent", "professional working": "professional",
             "limited working": "intermediate", "elementary": "basic"}


def _rows(z, name):
    """Rows (dicts) of one CSV, found anywhere in the ZIP; LinkedIn prepends "Notes:" lines to some."""
    member = next((i for i in z.infolist() if i.filename.lower().rsplit("/", 1)[-1] == name), None)
    if member is None:
        return []
    if member.file_size > MAX_MEMBER:
        raise ImportError_(f"{member.filename} is unexpectedly large.")
    return _csv_rows(z.read(member))


def _csv_rows(data):
    raw = data.decode("utf-8-sig", "replace")
    lines = raw.splitlines()
    if lines and lines[0].lower().startswith("notes"):
        while lines and lines[0].strip():          # the notes block ends with an empty line
            lines.pop(0)
    while lines and not lines[0].strip():
        lines.pop(0)
    return list(csv.DictReader(io.StringIO("\n".join(lines))))


def _get(row, *names):
    low = {(k or "").strip().lower(): (v or "").strip() for k, v in row.items()}
    for n in names:
        if low.get(n.lower()):
            return low[n.lower()]
    return ""


def _range(start, end):
    if not start and not end:
        return ""
    return f"{start or '?'} – {end or 'Present'}"


def _bullets(text):
    parts = [p.strip(" -•*·\t") for p in re.split(r"\n+|\s[•·]\s|(?<=[.!?])\s+(?=[A-ZÀ-Ü])", text or "")]
    return [p for p in parts if len(p) > 3][:10]


PARTS = {"profile.csv": "profile", "positions.csv": "positions", "education.csv": "education", "skills.csv": "skills",
         "languages.csv": "languages", "certifications.csv": "certifications", "email addresses.csv": "e-mail",
         "phonenumbers.csv": "phone"}
MAIN = ("profile.csv", "positions.csv")


def parse_zip(data):
    """Draft from a LinkedIn export, complete or partial: LinkedIn's first, quick archive and an export
    of a few categories only hold some of the files. Whatever is there is used; the draft's "_parts"
    lists the files found so the person can be told what is still to fill in."""
    if len(data) > MAX_ZIP:
        raise ImportError_(f"This ZIP is too large (max {MAX_ZIP // (1024 * 1024)} MB). In LinkedIn, ask for the export "
                           "with only Profile, Positions, Education, Skills, Languages and Certifications.")
    try:
        z = zipfile.ZipFile(io.BytesIO(data))
    except zipfile.BadZipFile:
        raise ImportError_("This isn't a valid ZIP file (an interrupted download?). Download it again from LinkedIn.")
    with z:
        if sum(i.file_size for i in z.infolist()) > 400 * 1024 * 1024:
            raise ImportError_("This ZIP is too large once unpacked.")
        names = {i.filename.lower().rsplit("/", 1)[-1] for i in z.infolist()}
        found = sorted(names & set(WANTED))
        if not found:
            raise ImportError_("None of LinkedIn's files (Profile.csv, Positions.csv, Skills.csv...) is inside: "
                               "is this the LinkedIn data export?")
        tables = {n: _rows(z, n) for n in found}
    return dict(_draft(tables), _parts=found)


def parse_csv(filename, data):
    """Draft from one CSV taken out of the export (Positions.csv, Skills.csv...)."""
    name = (filename or "").replace("\\", "/").rsplit("/", 1)[-1].lower()
    if name not in WANTED:
        raise ImportError_("This CSV isn't one of LinkedIn's export files (Profile.csv, Positions.csv, Education.csv, "
                           "Skills.csv, Languages.csv, Certifications.csv).")
    if len(data) > MAX_MEMBER:
        raise ImportError_("This CSV is unexpectedly large.")
    return dict(_draft({name: _csv_rows(data)}), _parts=[name])


def coverage(parts):
    """("skills, languages", "profile, positions"): what an import held, and the main files it lacked."""
    return ", ".join(PARTS[p] for p in parts), ", ".join(PARTS[p] for p in MAIN if p not in parts)


def _draft(tables):
    prof = (tables.get("profile.csv") or [{}])[0]
    positions, education = tables.get("positions.csv", []), tables.get("education.csv", [])
    skills, langs = tables.get("skills.csv", []), tables.get("languages.csv", [])
    certs, emails, phones = (tables.get("certifications.csv", []), tables.get("email addresses.csv", []),
                             tables.get("phonenumbers.csv", []))
    name = " ".join(x for x in (_get(prof, "First Name"), _get(prof, "Last Name")) if x)
    email = next((_get(e, "Email Address") for e in emails if _get(e, "Primary").lower() == "yes"),
                 _get(emails[0], "Email Address") if emails else "")
    contact = {k: v for k, v in {
        "email": email,
        "phone": _get(phones[0], "Number") if phones else "",
        "location": _get(prof, "Geo Location", "Address"),
    }.items() if v}
    experience = [{
        "title": _get(p, "Title"), "org": _get(p, "Company Name"), "loc": _get(p, "Location"),
        "dates": _range(_get(p, "Started On"), _get(p, "Finished On")),
        "bullets": _bullets(_get(p, "Description")),
    } for p in positions if _get(p, "Title") or _get(p, "Company Name")]
    edu = []
    for e in education:
        bits = [_get(e, "Degree Name"), _get(e, "School Name"), _range(_get(e, "Start Date"), _get(e, "End Date"))]
        edu.append(" | ".join(b for b in bits if b))
    languages = []
    for row in langs:
        lname = _get(row, "Name")
        found = cvparse._languages(lname)
        prof_ = _get(row, "Proficiency").lower()
        level = next((v for k, v in LI_LEVELS.items() if k in prof_), "")
        if found:
            languages.append(dict(found[0], level=level or found[0]["level"]))
    skill_names = [_get(s, "Name") for s in skills if _get(s, "Name")]
    cert_lines = []
    for c in certs:
        bits = [_get(c, "Name"), _get(c, "Authority"), _get(c, "Started On")]
        if bits[0]:
            cert_lines.append(", ".join(b for b in bits if b))
    text = " ".join([_get(prof, "Headline"), _get(prof, "Summary")] + skill_names +
                    [" ".join([x["title"]] + x["bullets"]) for x in experience])
    found_skills = cvparse.find_skills(text)
    found_skills += [s.lower() for s in skill_names if s.lower() not in found_skills and len(s) <= 40]
    return {
        "name": name, "headline": _get(prof, "Headline"), "contact": contact,
        "summary": " ".join(_get(prof, "Summary").split()),
        "expertise": skill_names[:16], "experience": experience, "education": edu,
        "extras_title": "CERTIFICATIONS" if cert_lines else "", "extras": cert_lines[:10],
        "languages": languages, "skills": found_skills[:60],
    }
