"""Skill highlighting for a posting: green = in the candidate's skills (prefs.skills()),
red = a known skill the posting asks for that isn't, grey strike = a word the user avoids.

"Known skills" = the lexicon below + SKILL_LEXICON (comma-separated, per instance).
Synonym groups (e.g. languages) count as one skill: if any spelling is in the CV,
every spelling in the posting is green.
"""
import os
import re

from markupsafe import Markup, escape

from . import prefs

# Each entry is one skill; alternatives are spellings/translations of the same skill.
GROUPS = [
    # languages
    ("english", "anglais", "englisch", "inglese"),
    ("french", "français", "francais", "französisch", "francese"),
    ("german", "allemand", "deutsch", "tedesco"),
    ("swiss german", "suisse allemand", "schweizerdeutsch"),
    ("italian", "italien", "italienisch", "italiano"),
    ("spanish", "espagnol", "spanisch", "spagnolo"),
    ("portuguese", "portugais", "portugiesisch", "portoghese"),
    # cloud / infra / devops
    ("kubernetes", "k8s"), ("docker",), ("openshift",), ("helm",), ("gitops",), ("argocd", "argo cd"),
    ("jenkins",), ("gitlab",), ("github actions",), ("azure devops",), ("ci/cd",),
    ("terraform",), ("ansible",), ("pulumi",), ("cloudformation",), ("bicep",),
    ("aws", "amazon web services"), ("azure",), ("gcp", "google cloud"), ("vmware",), ("hyper-v",),
    ("linux",), ("windows server",), ("prometheus",), ("grafana",), ("datadog",), ("observability",),
    ("python",), ("powershell",), ("bash",), ("java",), ("golang",), ("javascript",), ("typescript",),
    ("c#", ".net"), ("sql",), ("postgresql",), ("oracle",), ("mongodb",), ("kafka",), ("elasticsearch",),
    ("snowflake",), ("databricks",), ("finops",),
    # security
    ("siem",), ("splunk",), ("sentinel",), ("edr",), ("crowdstrike",), ("okta",), ("entra id", "azure ad"),
    ("iam",), ("sso",), ("zero trust",), ("pki",), ("active directory",), ("firewall",), ("palo alto",),
    ("fortinet",), ("cisco",), ("iso 27001",), ("nist",), ("soc 2",), ("pci dss", "pci-dss"), ("gdpr", "rgpd"),
    ("finma",), ("dora",), ("cissp",), ("cism",), ("cisa",), ("ccsp",), ("tisax",),
    # methods / certifications
    ("itil",), ("togaf",), ("prince2",), ("pmp",), ("scrum",), ("agile",), ("scaled agile",), ("lean",), ("six sigma",),
    # business / office / operations
    ("sap",), ("salesforce",), ("hubspot",), ("servicenow",), ("zendesk",), ("jira",), ("confluence",),
    ("excel",), ("power bi",), ("tableau",), ("crm",), ("erp",), ("ms office", "microsoft office", "office 365", "microsoft 365"),
    ("abacus",), ("opera",), ("comptabilité", "accounting", "buchhaltung"), ("facturation", "invoicing"),
    ("supply chain",), ("procurement", "achats"), ("incoterms",), ("douane", "customs"),
    ("négociation", "negotiation"), ("b2b",), ("b2c",), ("cfc",), ("brevet fédéral", "federal diploma"),
    ("permis de conduire", "driving licence", "driving license", "führerschein"),
]


def _groups():
    extra = [(k,) for k in (t.strip().lower() for t in os.environ.get("SKILL_LEXICON", "").split(",")) if k]
    from . import roles
    cv = [tuple(roles.spellings_for(k, roles.LANGS)) for k in prefs.skills()]
    avoid = [(k,) for k in prefs.avoided()]
    return GROUPS + extra + cv + avoid


def _pattern(term):
    end = "" if term.endswith("*") else r"(?!\w)"
    return r"(?<!\w)" + re.escape(term.rstrip("*")) + end


def plan():
    """What analyse() looks for, worked out once: (regex or None, terms, {term: (skill, class)}).
    Pass it to analyse() when reading many postings in a row."""
    kws, avoid = prefs.skills(), [k.rstrip("*") for k in prefs.avoided()]
    cv_terms = [k.rstrip("*") for k in kws]
    groups, term_group = _groups(), {}
    for g in groups:
        if any(t.rstrip("*") in avoid for t in g):
            cls = "avoid"
        elif any(t.rstrip("*") in cv_terms or any(re.fullmatch(_pattern(k), t) for k in kws) for t in g):
            cls = "have"
        else:
            cls = "miss"
        for t in g:
            term_group.setdefault(t, (g[0].rstrip("*"), cls))
    terms = sorted(term_group, key=len, reverse=True)
    rx = re.compile("|".join(f"({_pattern(t)})" for t in terms), re.IGNORECASE) if terms else None
    return rx, terms, term_group


def analyse(text, plan_=None):
    """Return (html, have, missing, avoided): the text with <mark>s, and the skill lists."""
    text = text or ""
    rx, terms, term_group = plan_ or plan()
    if not terms or not text:
        return Markup(escape(text)), [], [], []
    found = {"have": [], "miss": [], "avoid": []}
    tips = {"have": "in your CV", "miss": "not in your CV", "avoid": "you avoid this"}
    out, pos = [], 0
    for m in rx.finditer(text):
        name, cls = term_group[terms[m.lastindex - 1]]
        out.append(escape(text[pos:m.start()]))
        out.append(Markup(f'<mark class="{cls}" title="{tips[cls]}">') + escape(m.group(0)) + Markup("</mark>"))
        found[cls].append(name)
        pos = m.end()
    out.append(escape(text[pos:]))
    uniq = lambda xs: list(dict.fromkeys(xs))  # noqa: E731
    return Markup("").join(out), uniq(found["have"]), uniq(found["miss"]), uniq(found["avoid"])
