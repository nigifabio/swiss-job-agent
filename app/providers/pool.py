"""Postings from the platform's shared collector (app/collector.py) instead of this workspace
querying the shared sources itself. Set by the platform (POOL_URL, POOL_TOKEN); without them, or
whenever the collector can't answer, the workspace crawls on its own as before.

Sent: what is searched (terms, regions, places, languages). Never who searches, never anything
from the profile. Received: postings, which then go through this workspace's own filters."""
import hashlib
import json
import os

import httpx

from .. import config, filters, profiles, scanlog, store

URL = os.environ.get("POOL_URL", "").rstrip("/")
TOKEN = os.environ.get("POOL_TOKEN", "")


def enabled():
    return bool(URL and TOKEN)


def spec():
    return {"terms": profiles.search_terms(),     # every profile's terms: the pool is asked for the union
            "where": [w for w in config.WHERE if w], "cantons": list(config.JOBROOM_CANTONS),
            "places": list(config.LOCATION_KEYWORDS), "langs": list(config.LANGUAGES), "remote": bool(config.ALLOW_REMOTE)}


def _post(payload):
    r = httpx.post(URL + "/pull", json=payload, headers={"Authorization": f"Bearer {TOKEN}"}, timeout=90)
    r.raise_for_status()
    return r.json()


def pull():
    """(postings that pass this workspace's filters, sources the collector covers, mark to keep once they are stored).
    covers is empty when the collector hasn't crawled this search yet: the workspace then crawls itself this time."""
    s = spec()
    # what decides which postings this person gets: when any of it changes, start again from the whole pool
    # (the title, company and work-rate rules stay here: they are part of the mark, not of what is sent)
    local = [config.TITLE_KEYWORDS, config.TITLE_EXCLUDE, config.COMPANY_EXCLUDE, config.WORK_RATE_MIN, config.WORK_RATE_MAX]
    if profiles.extra_title_words():
        local.append(profiles.extra_title_words())            # (nothing added without extra profiles: the mark of a search stays)
    digest = hashlib.sha256(json.dumps([s, local], sort_keys=True).encode()).hexdigest()[:16]
    meta = store.get_meta()
    since = meta.get("pool_since", "") if meta.get("pool_spec") == digest else ""     # a changed search starts from the whole pool
    d = _post({"since": since, "spec": s})
    if not d.get("ready"):
        return [], set(), None
    jobs = [j for j in d.get("jobs") or []
            if j.get("content_hash") and filters.title_ok(j.get("title")) and filters.location_ok(j.get("location"), j.get("description"))
            and filters.language_ok(j.get("title"), j.get("description"))]
    scanlog.count("pool", len(jobs))
    print(f"[pool] {len(jobs)} of {len(d.get('jobs') or [])} postings kept (since {since or 'the beginning'})")
    return jobs, set(d.get("covers") or []), {"pool_since": d.get("now", ""), "pool_spec": digest}
