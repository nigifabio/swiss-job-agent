import os
import fcntl
from contextlib import contextmanager

import json

from .store import init_db, upsert_jobs, rescore, set_meta, get_meta, now
from . import config, filters, prefs, profiles, scanlog
from .providers import adzuna, ats, careerjet, jobroom, jobup, jooble, mailalerts, pool, remote

# name in PROVIDERS -> module. Keyed/mailbox ones stay silent until configured.
MODULES = {"ats": ats, "jobup": jobup, "jobroom": jobroom, "remote": remote, "adzuna": adzuna,
           "careerjet": careerjet, "jooble": jooble, "email": mailalerts}


AVOID_PENALTY = 25     # points per avoided word a posting mentions


def score_job(job, skills=None, avoid=None):
    """(score, why) of a posting against a skill list and avoided words: the main profile's by default."""
    skills = prefs.skills() if skills is None else skills
    avoid = prefs.avoided() if avoid is None else avoid
    sc = filters.score(job, skills)
    if sc is None:
        return None, None
    hits, bad = filters.matched(job, skills), filters.avoided_hits(job, avoid)
    why = ("matches: " + ", ".join(hits)) if hits else "no CV keyword matches"
    if bad:
        sc = max(0, sc - AVOID_PENALTY * len(bad))
        why += " · avoid: " + ", ".join(bad)
    return sc, why


def tag_job(job, locked=None):
    """A posting's tags and score. Every profile whose title words or search terms occur in the title
    matches; none matching (typed in by hand, found through the shared pool...) means the main profile.
    The matching profile with the highest score is the main tag and its score is the job's (on a tie a role
    wins over the main profile, which matches broadly, then the oldest role); `locked` is a profile the person
    chose by hand for it. Returns a dict:
    score, why, profile (main tag), profiles ("0,2": every tag, the main one first), locked (0/1)."""
    ids = profiles.matching(job.get("title")) or [profiles.MAIN]
    if locked is not None and profiles.exists(locked):
        ids = sorted(set(ids) | {locked})
    else:
        locked = None
    results = {pid: score_job(job, profiles.skills_of(pid), profiles.avoid_of(pid)) for pid in ids}
    main = locked if locked is not None else max(ids, key=lambda pid: (-1 if results[pid][0] is None else results[pid][0],
                                                                         pid != profiles.MAIN, -pid))
    ordered = [main] + [pid for pid in ids if pid != main]
    return {"score": results[main][0], "why": results[main][1], "profile": main,
            "profiles": ",".join(map(str, ordered)), "locked": int(locked is not None)}


def retag_job(job):
    """For store.rescore: (score, why, profile, profiles, locked) of an open job, keeping the person's own choice
    of main tag when that profile still exists."""
    t = tag_job(job, job.get("profile") if job.get("profile_locked") else None)
    return t["score"], t["why"], t["profile"], t["profiles"], t["locked"]


def rescore_all():
    """Tag and score again every open job: after a change of profiles, of their search words or of the skills."""
    return rescore(retag_job)


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
        profiles.invalidate()       # ... and profile changes
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


def _keep(jobs):
    """The postings this person may see, scored: company and work-rate rules apply to every source."""
    jobs = [j for j in jobs if filters.company_ok(j.get("company")) and filters.rate_ok(j.get("title"))]
    for job in jobs:
        job["title"] = " ".join((job.get("title") or "").split())
        t = tag_job(job)
        job["score"], job["score_rationale"], job["profile"], job["profiles"] = t["score"], t["why"], t["profile"], t["profiles"]
    return jobs


def _run():
    total = new = 0
    pooled = set()                 # sources the platform's collector answered for: not queried again from here
    if pool.enabled():
        try:
            jobs, pooled, mark = pool.pull()
            jobs = _keep(jobs)
            total += len(jobs)
            new += upsert_jobs(jobs)
            if mark:
                set_meta(**mark)
        except Exception as e:  # noqa: BLE001  (collector down or busy: this scan crawls everything itself, as before)
            pooled = set()
            print(f"[fetch] collector not available ({type(e).__name__}: {str(e)[:120]}); crawling from here")
    for name in config.PROVIDERS:
        mod = MODULES.get(name)
        if not mod:
            print(f"[fetch] unknown provider '{name}' — skipping")
            continue
        if name in pooled and name != "ats":
            continue
        ats.PUBLIC = "ats" not in pooled         # own company boards stay here; the public employers came from the collector
        try:
            jobs = mod.fetch()
        except Exception as e:  # noqa: BLE001
            scanlog.error(name, f"provider crashed: {type(e).__name__}: {str(e)[:150]}")
            continue
        finally:
            ats.PUBLIC = True
        jobs = _keep(jobs)
        total += len(jobs)
        new += upsert_jobs(jobs)
    print(f"[fetch] processed {total} postings, {new} new")
    return new


if __name__ == "__main__":
    import sys
    if "--rescore" in sys.argv:
        init_db()
        prefs.invalidate()
        profiles.invalidate()
        print(f"[fetch] rescored {rescore_all()} jobs")
    else:
        run()
