"""One-click changes of the search from the Stats page and the job page: skip a title word, stop
searching a town, never show a company; and, from the "add a posting" page, search for what a posting
showed was missing (a title word, a search term, a language, a canton). The change is saved like on the
Settings page, and jobs still in "new" that the new settings would not have kept are removed (reason:
changed settings)."""
import re

from . import config, filters, store

LISTS = {"TITLE_EXCLUDE", "LOCATION_KEYWORDS", "COMPANY_EXCLUDE"}       # add or remove
ADD_ONLY = {"SEARCH_TERMS", "TITLE_KEYWORDS", "LANGUAGES", "JOBROOM_CANTONS"}       # only ever widen the search
LANGUAGES = ("fr", "de", "it", "en")
_BAD = re.compile(r"[;,|<>\x00-\x1f]")        # the separators the lists are stored and read with


def clean(name, value):
    """The value as it is stored, or None when it is not acceptable for that setting."""
    value = " ".join((value or "").split())
    if name in LISTS:
        return value.lower()[:60] or None
    if not value or len(value) > 60 or _BAD.search(value):
        return None
    if name == "LANGUAGES":
        return value.lower() if value.lower() in LANGUAGES else None
    if name == "JOBROOM_CANTONS":
        return value.upper() if re.fullmatch(r"[A-Za-z]{2}", value) else None
    return value if name == "SEARCH_TERMS" else value.lower()          # search terms are typed into job sites as written


def widens(action, name):
    """Does this change make the search look at more postings (so a scan is worth starting)?"""
    if action == "add":
        return name in ADD_ONLY or name == "LOCATION_KEYWORDS"
    return name in ("TITLE_EXCLUDE", "COMPANY_EXCLUDE")


def change(action, name, value):
    """Add or remove one entry of a list setting. Returns how many open jobs were removed by it
    (None when the name, the action or the value is not allowed)."""
    if action not in ("add", "remove") or name not in LISTS | ADD_ONLY or (action == "remove" and name in ADD_ONLY):
        return None
    value = clean(name, value)
    if not value:
        return None
    cur = list(getattr(config, name))
    if name == "JOBROOM_CANTONS" and not cur:
        from .providers import jobroom
        cur = jobroom.cantons()              # empty means "the cantons of WHERE": keep those when naming one
    if action == "add" and value.lower() not in [x.lower() for x in cur]:
        cur.append(value)
    elif action == "remove":
        cur = [x for x in cur if x != value]
    if name == "LOCATION_KEYWORDS" and not cur:          # never empty the towns: that would hide everything
        return None
    config.save_settings({**{k: getattr(config, k) for k in config.EDITABLE}, name: cur})
    return apply()


def apply():
    """Discard the jobs in "new" that no longer pass the title, company, work-rate and place settings.
    The title rule holds every profile's title words (filters.title_ok): adding a profile never removes a job,
    and removing one removes only the jobs that no profile still asks for."""
    n = 0
    for j in store.list_jobs("new"):
        if j.get("origin") == "manual":
            continue
        if (filters.title_ok(j.get("title")) and filters.company_ok(j.get("company")) and filters.rate_ok(j.get("title"))
                and filters.location_ok(j.get("location"), j.get("description"))):
            continue
        store.dismiss(j["id"], "filtered", True)
        n += 1
    return n
