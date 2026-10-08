"""One-click changes of the search from the Stats page and the job page: skip a title word, stop
searching a town, never show a company. The change is saved like on the Settings page, and jobs still
in "new" that the new settings would not have kept are removed (reason: changed settings)."""
from . import config, filters, store

LISTS = {"TITLE_EXCLUDE", "LOCATION_KEYWORDS", "COMPANY_EXCLUDE"}


def change(action, name, value):
    """Add or remove one entry of a list setting. Returns how many open jobs were removed by it."""
    value = " ".join((value or "").lower().split())[:60]
    if name not in LISTS or action not in ("add", "remove") or not value:
        return None
    cur = list(getattr(config, name))
    if action == "add" and value not in cur:
        cur.append(value)
    elif action == "remove":
        cur = [x for x in cur if x != value]
    if name == "LOCATION_KEYWORDS" and not cur:          # never empty the towns: that would hide everything
        return None
    config.save_settings({**{k: getattr(config, k) for k in config.EDITABLE}, name: cur})
    return apply()


def apply():
    """Discard the jobs in "new" that no longer pass the title, company, work-rate and place settings."""
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
