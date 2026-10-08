import os
import fcntl
from contextlib import contextmanager

import json

from .store import init_db, upsert_jobs, rescore, set_meta, get_meta, now
from . import config, filters, prefs, scanlog
from .providers import adzuna, ats, careerjet, jobroom, jobup, jooble, mailalerts, remote

# name in PROVIDERS -> module. Keyed/mailbox ones stay silent until configured.
MODULES = {"ats": ats, "jobup": jobup, "jobroom": jobroom, "remote": remote, "adzuna": adzuna,
           "careerjet": careerjet, "jooble": jooble, "email": mailalerts}


AVOID_PENALTY = 25     # points per avoided word a posting mentions


def score_job(job):
    sc = filters.score(job)
    if sc is None:
        return None, None
    hits, bad = filters.matched(job), filters.avoided_hits(job)
    why = ("matches: " + ", ".join(hits)) if hits else "no CV keyword matches"
    if bad:
        sc = max(0, sc - AVOID_PENALTY * len(bad))
        why += " · avoid: " + ", ".join(bad)
    return sc, why


LOCK_PATH = os.path.join(os.path.dirname(config.DB_PATH) or ".", "fetch.lock")


@contextmanager
def _single_run():
    """One scan at a time across the web ("Scan now") and scheduler containers."""
    os.makedirs(os.path.dirname(LOCK_PATH) or ".", exist_ok=True)
    with open(LOCK_PATH, "w") as f:
        try:
            fcntl.flock(f, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            yield False
            return
        try:
            yield True
        finally:
            fcntl.flock(f, fcntl.LOCK_UN)


def is_running():
    with _single_run() as got:
        return not got


def run():
    """Scan every provider. Returns the number of new jobs, or None if a scan was already running."""
    with _single_run() as got:
        if not got:
            print("[fetch] a scan is already running; skipping")
            return None
        init_db()
        config.refresh_settings()   # pick up settings saved in the web app
        prefs.invalidate()          # pick up skill clicks made in the web app
        set_meta(scan_started_at=now())
        scanlog.start()
        new = _run()
        report = scanlog.result()
        for chore in (_commutes, _closed, _weekly):          # extras: never fail a scan
            try:
                chore()
            except Exception as e:  # noqa: BLE001
                print(f"[fetch] {chore.__name__} skipped: {type(e).__name__}: {str(e)[:120]}")
        try:
            previous = json.loads(get_meta().get("last_scan_report") or "{}")
        except ValueError:
            previous = {}
        set_meta(last_scan_at=now(), last_scan_new=new, last_scan_report=json.dumps(report),
                 last_scan_warnings=json.dumps(scanlog.warnings(report, previous)))
        return new


def _commutes():
    from . import commute
    commute.fill()


def _weekly():
    from . import weekly
    weekly.send_if_due()


def _closed():
    from . import closed
    closed.check()


def _run():
    total = new = 0
    for name in config.PROVIDERS:
        mod = MODULES.get(name)
        if not mod:
            print(f"[fetch] unknown provider '{name}' — skipping")
            continue
        try:
            jobs = mod.fetch()
        except Exception as e:  # noqa: BLE001
            scanlog.error(name, f"provider crashed: {type(e).__name__}: {str(e)[:150]}")
            continue
        jobs = [j for j in jobs if filters.company_ok(j.get("company")) and filters.rate_ok(j.get("title"))]
        for job in jobs:
            job["title"] = " ".join((job.get("title") or "").split())
            job["score"], job["score_rationale"] = score_job(job)
        total += len(jobs)
        new += upsert_jobs(jobs)
    print(f"[fetch] processed {total} postings, {new} new")
    return new


if __name__ == "__main__":
    import sys
    if "--rescore" in sys.argv:
        init_db()
        prefs.invalidate()
        print(f"[fetch] rescored {rescore(score_job)} jobs")
    else:
        run()
