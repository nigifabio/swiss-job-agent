"""Notice postings that went offline. Once a week each open posting's address is asked again; a
clear "gone" answer (404 or 410) marks the job "position filled" (new / shortlisted) or notes it on
the job page (applied). Anything else (blocked, error, redirect to a search page) changes nothing.
CLOSED_CHECK=0 turns it off."""
import datetime
import os

import httpx

from . import store
from .http import Http

PER_SCAN = int(os.environ.get("CLOSED_PER_SCAN", "40"))
EVERY_DAYS = 7
MIN_AGE_DAYS = 6
UA = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/124.0 Safari/537.36"}


def check(limit=None):
    if os.environ.get("CLOSED_CHECK", "1") == "0":
        return 0
    limit = PER_SCAN if limit is None else limit
    now = datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None)
    old = (now - datetime.timedelta(days=MIN_AGE_DAYS)).isoformat(timespec="seconds")
    again = (now - datetime.timedelta(days=EVERY_DAYS)).isoformat(timespec="seconds")
    with store.conn() as c:
        jobs = [dict(r) for r in c.execute(
            "SELECT id, url, status FROM jobs WHERE status IN ('new','shortlisted','applied') AND origin != 'manual' "
            "AND url LIKE 'http%' AND closed_at IS NULL AND created_at <= ? "
            "AND (url_checked_at IS NULL OR url_checked_at <= ?) ORDER BY url_checked_at IS NOT NULL, url_checked_at LIMIT ?",
            (old, again, limit)).fetchall()]
    gone = 0
    with Http(timeout=12, min_gap=0.7, tries=1, headers=UA) as client:
        for j in jobs:
            code = None
            try:
                code = client.get(j["url"], follow_redirects=True).status_code
            except httpx.HTTPStatusError as e:
                code = e.response.status_code
            except Exception:  # noqa: BLE001  (unreachable now: ask again next week)
                pass
            with store.conn() as c:
                c.execute("UPDATE jobs SET url_checked_at=? WHERE id=?", (store.now(), j["id"]))
                if code in (404, 410):
                    c.execute("UPDATE jobs SET closed_at=? WHERE id=?", (store.now(), j["id"]))
            if code in (404, 410):
                gone += 1
                if j["status"] in ("new", "shortlisted"):
                    store.mark_filled(j["id"])
    if gone:
        print(f"[closed] {gone} posting(s) no longer online")
    return gone
