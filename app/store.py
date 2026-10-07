import os
import re
import sqlite3
import datetime
from contextlib import contextmanager

from .config import DB_PATH
from .normalize import content_hash, loose_key

STATUSES = ["new", "shortlisted", "applied", "interview", "offer", "rejected", "discarded"]

SCHEMA = """
CREATE TABLE IF NOT EXISTS jobs (
  id              INTEGER PRIMARY KEY AUTOINCREMENT,
  content_hash    TEXT UNIQUE,
  source          TEXT,
  title           TEXT,
  company         TEXT,
  location        TEXT,
  description     TEXT,
  url             TEXT,
  salary          TEXT,
  posted_at       TEXT,
  status          TEXT DEFAULT 'new',
  origin          TEXT DEFAULT 'scraped',
  contact         TEXT,
  recruiter       TEXT,
  cv_version      TEXT,
  applied_date    TEXT,
  followup_date   TEXT,
  notes           TEXT,
  score           INTEGER,
  score_rationale TEXT,
  created_at      TEXT,
  work_rate       TEXT,
  apply_method    TEXT,
  orp_assigned    INTEGER DEFAULT 0,
  outcome_note    TEXT,
  enriched_at     TEXT,
  letter          TEXT,
  loose_key       TEXT,
  dimmed          INTEGER DEFAULT 0
);
CREATE TABLE IF NOT EXISTS status_history (
  id          INTEGER PRIMARY KEY AUTOINCREMENT,
  job_id      INTEGER,
  status      TEXT,
  changed_at  TEXT
);
CREATE INDEX IF NOT EXISTS idx_jobs_status ON jobs(status);
CREATE INDEX IF NOT EXISTS idx_history_job ON status_history(job_id);
CREATE TABLE IF NOT EXISTS meta (k TEXT PRIMARY KEY, v TEXT);
CREATE INDEX IF NOT EXISTS idx_jobs_loose ON jobs(loose_key);
"""


_RATE_RANGE = re.compile(r"(\d{2,3})\s*%?\s*(?:-|–|à|a|to|bis)\s*(\d{2,3})\s*%")
_RATE_ONE = re.compile(r"(\d{2,3})\s*%")


def guess_work_rate(title):
    """'Coordinator 80-100%' -> '80-100%'; no percentage -> '100%' (Swiss postings omit it for full time)."""
    t = title or ""
    m = _RATE_RANGE.search(t)
    if m:
        return f"{m.group(1)}-{m.group(2)}%"
    m = _RATE_ONE.search(t)
    return f"{m.group(1)}%" if m else "100%"


def now():
    return datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None).isoformat(timespec="seconds")


def today():
    return datetime.date.today().isoformat()


@contextmanager
def conn():
    d = os.path.dirname(DB_PATH)
    if d:
        os.makedirs(d, exist_ok=True)
    # web + scheduler write concurrently: WAL + a busy timeout avoid "database is locked"
    c = sqlite3.connect(DB_PATH, timeout=15)
    c.row_factory = sqlite3.Row
    c.execute("PRAGMA journal_mode=WAL")
    try:
        yield c
        c.commit()
    finally:
        c.close()


# Columns added after v1: (name, declaration). init_db adds any that are missing,
# so older databases upgrade in place.
MIGRATIONS = [
    ("work_rate", "TEXT"), ("apply_method", "TEXT"), ("orp_assigned", "INTEGER DEFAULT 0"),
    ("outcome_note", "TEXT"), ("enriched_at", "TEXT"), ("letter", "TEXT"), ("loose_key", "TEXT"),
    ("dimmed", "INTEGER DEFAULT 0"),
]

# How an application was made, as the ORP "preuves de recherches" form asks it.
APPLY_METHODS = {"written": "Écrite / e-mail / en ligne", "phone": "Téléphonique", "in_person": "Personnelle"}


def init_db():
    with conn() as c:
        have = {r["name"] for r in c.execute("PRAGMA table_info(jobs)").fetchall()}
        for col, decl in MIGRATIONS:
            if have and col not in have:
                c.execute(f"ALTER TABLE jobs ADD COLUMN {col} {decl}")
        c.executescript(SCHEMA)
        # an application recorded only by its date (job page) belongs in "applied", like the report counts it
        for r in c.execute("SELECT id FROM jobs WHERE status IN ('new','shortlisted') "
                           "AND COALESCE(applied_date,'') != ''").fetchall():
            c.execute("UPDATE jobs SET status='applied', dimmed=0, apply_method=COALESCE(NULLIF(apply_method,''),'written') "
                      "WHERE id=?", (r["id"],))
            c.execute("INSERT INTO status_history (job_id, status, changed_at) VALUES (?,?,?)", (r["id"], "applied", now()))
        # backfill the loose fingerprint for rows stored before it existed
        for r in c.execute("SELECT id, title, company, location FROM jobs WHERE loose_key IS NULL "
                           "AND origin != 'manual'").fetchall():
            c.execute("UPDATE jobs SET loose_key=? WHERE id=?",
                      (loose_key(r["title"], r["company"], r["location"]), r["id"]))


def upsert_jobs(jobs):
    """Insert scraped postings in one transaction. Returns how many were new.
    A posting is skipped if its exact fingerprint or its loose one (same job written
    differently by another source) is already stored; the first source found is kept."""
    new = 0
    with conn() as c:
        for job in jobs:
            lk = loose_key(job.get("title"), job.get("company"), job.get("location"))
            if c.execute("SELECT 1 FROM jobs WHERE loose_key=? LIMIT 1", (lk,)).fetchone():
                continue
            cur = c.execute(
                """INSERT OR IGNORE INTO jobs (content_hash, source, title, company, location,
                   description, url, salary, posted_at, status, origin, score, score_rationale,
                   created_at, loose_key)
                   VALUES (?,?,?,?,?,?,?,?,?,'new','scraped',?,?,?,?)""",
                (job["content_hash"], job.get("source"), job.get("title"), job.get("company"),
                 job.get("location"), job.get("description"), job.get("url"), job.get("salary"),
                 job.get("posted_at"), job.get("score"), job.get("score_rationale"), now(), lk),
            )
            new += cur.rowcount
    return new


def rescore(fn):
    """Re-apply fn(job) -> (score, rationale) to every open job, e.g. after SCORE_KEYWORDS change."""
    with conn() as c:
        rows = c.execute("SELECT id, title, description FROM jobs "
                         "WHERE status NOT IN ('rejected','discarded')").fetchall()
        for r in rows:
            sc, why = fn(dict(r))
            c.execute("UPDATE jobs SET score=?, score_rationale=? WHERE id=?", (sc, why, r["id"]))
    return len(rows)


def add_manual(f):
    ch = content_hash(f.get("title", ""), f.get("company", ""), f.get("location", ""), now())
    status = f.get("status", "shortlisted")
    with conn() as c:
        cur = c.execute(
            """INSERT INTO jobs (content_hash, source, title, company, location,
               description, url, status, origin, created_at)
               VALUES (?,?,?,?,?,?,?,?,?,?)""",
            (ch, f.get("source", "manual"), f.get("title"), f.get("company"),
             f.get("location"), f.get("description"), f.get("url"), status,
             f.get("origin", "manual"), now()),
        )
        jid = cur.lastrowid
        c.execute("INSERT INTO status_history (job_id, status, changed_at) VALUES (?,?,?)",
                  (jid, status, now()))
        return jid


def list_jobs(status=None):
    with conn() as c:
        if status:
            rows = c.execute(
                "SELECT * FROM jobs WHERE status=? "
                "ORDER BY COALESCE(score,-1) DESC, created_at DESC", (status,)).fetchall()
        else:
            rows = c.execute("SELECT * FROM jobs ORDER BY created_at DESC").fetchall()
        return [dict(r) for r in rows]


def counts():
    with conn() as c:
        rows = c.execute("SELECT status, COUNT(*) n FROM jobs GROUP BY status").fetchall()
        return {r["status"]: r["n"] for r in rows}


def get_job(jid):
    with conn() as c:
        r = c.execute("SELECT * FROM jobs WHERE id=?", (jid,)).fetchone()
        if not r:
            return None
        hist = c.execute(
            "SELECT * FROM status_history WHERE job_id=? ORDER BY changed_at", (jid,)).fetchall()
        d = dict(r)
        d["history"] = [dict(h) for h in hist]
        return d


def update_status(jid, status):
    if status not in STATUSES:
        return
    with conn() as c:
        c.execute("UPDATE jobs SET status=?, dimmed=0 WHERE id=?", (status, jid))
        if status in ("new", "shortlisted"):      # not applied after all: out of the report and the stats too
            c.execute("UPDATE jobs SET applied_date=NULL WHERE id=?", (jid,))
        if status == "applied":
            c.execute("UPDATE jobs SET applied_date=COALESCE(NULLIF(applied_date,''),?), "
                      "apply_method=COALESCE(NULLIF(apply_method,''),'written') WHERE id=?", (today(), jid))
            row = c.execute("SELECT title, work_rate FROM jobs WHERE id=?", (jid,)).fetchone()
            if row and not row["work_rate"]:
                c.execute("UPDATE jobs SET work_rate=? WHERE id=?", (guess_work_rate(row["title"]), jid))
        c.execute("INSERT INTO status_history (job_id, status, changed_at) VALUES (?,?,?)",
                  (jid, status, now()))


def dismiss(jid):
    """The "not for me" button of the list: the first click greys the job out (it stays where it is),
    a click on a greyed job discards it. Returns the new state: "dimmed", "discarded" or None."""
    with conn() as c:
        row = c.execute("SELECT dimmed, status FROM jobs WHERE id=?", (jid,)).fetchone()
        if not row or row["status"] == "discarded":
            return None
        if not row["dimmed"]:
            c.execute("UPDATE jobs SET dimmed=1 WHERE id=?", (jid,))
            return "dimmed"
    update_status(jid, "discarded")
    return "discarded"


def keep(jid):
    """Undo the grey-out."""
    with conn() as c:
        c.execute("UPDATE jobs SET dimmed=0 WHERE id=?", (jid,))


def update_fields(jid, fields):
    allowed = ["contact", "recruiter", "cv_version", "applied_date", "followup_date", "notes",
               "work_rate", "apply_method", "orp_assigned", "outcome_note", "location", "letter"]
    sets, vals = [], []
    for k in allowed:
        if k in fields:
            sets.append(f"{k}=?")
            vals.append(fields[k])
    if not sets:
        return
    vals.append(jid)
    with conn() as c:
        c.execute(f"UPDATE jobs SET {', '.join(sets)} WHERE id=?", vals)
        row = c.execute("SELECT status, applied_date FROM jobs WHERE id=?", (jid,)).fetchone()
    # an applied date means "I applied": the job moves to Applied (the report and stats go by the date)
    if row and row["applied_date"] and row["status"] in ("new", "shortlisted"):
        update_status(jid, "applied")


FILLED_NOTE = "Poste déjà pourvu"      # in French: it is shown in the ORP report's "Résultat" column


def mark_filled(jid):
    """The position is no longer open. Applied to already: it becomes a refusal with that reason
    (it stays in the report); not applied: it leaves the list. Returns the new status, or None."""
    job = get_job(jid)
    if not job or job["status"] in ("rejected", "discarded"):
        return None
    status = "rejected" if job["status"] in ("applied", "interview", "offer") or job.get("applied_date") else "discarded"
    update_status(jid, status)
    with conn() as c:
        c.execute("UPDATE jobs SET outcome_note=? WHERE id=? AND COALESCE(outcome_note,'')=''", (FILLED_NOTE, jid))
    return status


def known_hashes():
    with conn() as c:
        return frozenset(r[0] for r in c.execute("SELECT content_hash FROM jobs"))


def set_description(jid, text):
    with conn() as c:
        c.execute("UPDATE jobs SET description=?, enriched_at=? WHERE id=?", (text, now(), jid))


def applications(start, end):
    """Jobs applied to with applied_date in [start, end] (ISO dates), oldest first."""
    with conn() as c:
        rows = c.execute(
            """SELECT * FROM jobs WHERE applied_date IS NOT NULL AND applied_date != ''
                 AND applied_date >= ? AND applied_date <= ?
               ORDER BY applied_date, id""", (start, end)).fetchall()
        return [dict(r) for r in rows]


def all_applied():
    with conn() as c:
        rows = c.execute("SELECT * FROM jobs WHERE applied_date IS NOT NULL AND applied_date != ''").fetchall()
        return [dict(r) for r in rows]


def history_all():
    with conn() as c:
        return [dict(r) for r in c.execute("SELECT * FROM status_history ORDER BY changed_at").fetchall()]


def followups_due(days=14):
    cutoff = (datetime.date.today() + datetime.timedelta(days=days)).isoformat()
    with conn() as c:
        rows = c.execute(
            """SELECT * FROM jobs
               WHERE followup_date IS NOT NULL AND followup_date != ''
                 AND followup_date <= ?
                 AND status NOT IN ('rejected','discarded','offer')
               ORDER BY followup_date""", (cutoff,)).fetchall()
        return [dict(r) for r in rows]


def set_meta(**kv):
    with conn() as c:
        c.executemany("INSERT INTO meta (k, v) VALUES (?, ?) ON CONFLICT(k) DO UPDATE SET v=excluded.v",
                      [(k, str(v)) for k, v in kv.items()])


def get_meta():
    with conn() as c:
        return {r["k"]: r["v"] for r in c.execute("SELECT k, v FROM meta").fetchall()}
