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
  dimmed          INTEGER DEFAULT 0,
  discard_reason  TEXT,
  orp_deadline    TEXT,
  followed_up_at  TEXT,
  url_checked_at  TEXT,
  closed_at       TEXT,
  commute_min     INTEGER,
  interview_at    TEXT,
  docs            TEXT,
  cv_text         TEXT
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
CREATE TABLE IF NOT EXISTS cv_versions (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL, text TEXT NOT NULL,
  is_default INTEGER NOT NULL DEFAULT 0, created_at TEXT NOT NULL, updated_at TEXT NOT NULL, kind TEXT NOT NULL DEFAULT 'cv');
CREATE INDEX IF NOT EXISTS idx_jobs_loose ON jobs(loose_key);
CREATE TABLE IF NOT EXISTS commutes (home TEXT NOT NULL, place TEXT NOT NULL, minutes INTEGER, checked_at TEXT NOT NULL,
  PRIMARY KEY (home, place));
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
    ("dimmed", "INTEGER DEFAULT 0"), ("discard_reason", "TEXT"),
    ("orp_deadline", "TEXT"), ("followed_up_at", "TEXT"), ("url_checked_at", "TEXT"), ("closed_at", "TEXT"),
    ("commute_min", "INTEGER"), ("interview_at", "TEXT"), ("docs", "TEXT"), ("cv_text", "TEXT"),
]

# Why a posting was discarded (the list's "Why?" menu). Read on the Stats page to tune the search:
# each reason points at a setting (title words, exclusions, towns, languages, sources).
DISCARD_REASONS = {
    "wrong_role": "Not my kind of job",
    "too_senior": "Too senior / too much experience asked",
    "too_junior": "Too junior / internship / apprenticeship",
    "location": "Too far / wrong place",
    "language": "A language I don't speak",
    "workload": "Wrong work rate or contract (part-time, temporary...)",
    "conditions": "Salary or conditions",
    "company": "Not this company / recruitment agency",
    "duplicate": "Duplicate / already seen",
    "filled": "Position filled or expired",
    "other": "Other",
    "filtered": "Removed by a change of the search settings",       # set by the app, not in the menu
}

# How an application was made, as the ORP "preuves de recherches" form asks it.
APPLY_METHODS = {"written": "Écrite / e-mail / en ligne", "phone": "Téléphonique", "in_person": "Personnelle"}


def init_db():
    with conn() as c:
        have = {r["name"] for r in c.execute("PRAGMA table_info(jobs)").fetchall()}
        for col, decl in MIGRATIONS:
            if have and col not in have:
                c.execute(f"ALTER TABLE jobs ADD COLUMN {col} {decl}")
        c.executescript(SCHEMA)
        if "kind" not in {r["name"] for r in c.execute("PRAGMA table_info(cv_versions)").fetchall()}:
            c.execute("ALTER TABLE cv_versions ADD COLUMN kind TEXT NOT NULL DEFAULT 'cv'")      # versions were CVs only at first
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
        if status != "discarded":                 # back in play: the old reason no longer applies
            c.execute("UPDATE jobs SET discard_reason=NULL WHERE id=?", (jid,))
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


def dismiss(jid, reason=None, now_=False):
    """The "not for me" button of the list: the first click greys the job out (it stays where it is),
    a click on a greyed job, or choosing a reason, discards it. Returns "dimmed", "discarded" or None."""
    reason = reason if reason in DISCARD_REASONS else None
    with conn() as c:
        row = c.execute("SELECT dimmed, status FROM jobs WHERE id=?", (jid,)).fetchone()
        if not row or row["status"] == "discarded":
            return None
        if not row["dimmed"] and not reason and not now_:
            c.execute("UPDATE jobs SET dimmed=1 WHERE id=?", (jid,))
            return "dimmed"
    update_status(jid, "discarded")
    if reason:
        with conn() as c:
            c.execute("UPDATE jobs SET discard_reason=? WHERE id=?", (reason, jid))
    return "discarded"


def below_score(status, score):
    """Ids of the scored jobs of one list under `score`; never one the ORP assigned or one typed in by hand."""
    with conn() as c:
        return [r["id"] for r in c.execute(
            "SELECT id FROM jobs WHERE status=? AND score IS NOT NULL AND score < ? AND COALESCE(orp_assigned,0)=0 "
            "AND origin != 'manual'", (status, int(score))).fetchall()]


def open_jobs(limit=600):
    """Postings still in play (not refused, not discarded), newest first: what the person's market asks for."""
    with conn() as c:
        return [dict(r) for r in c.execute(
            "SELECT id, title, description, status, score, created_at FROM jobs WHERE status NOT IN ('rejected','discarded') "
            "AND COALESCE(dimmed,0)=0 ORDER BY id DESC LIMIT ?", (limit,)).fetchall()]


def interviews():
    with conn() as c:
        return [dict(r) for r in c.execute(
            "SELECT * FROM jobs WHERE COALESCE(interview_at,'') != '' AND status NOT IN ('rejected','discarded') "
            "ORDER BY interview_at").fetchall()]


def created_since(ts):
    with conn() as c:
        return [dict(r) for r in c.execute(
            "SELECT * FROM jobs WHERE created_at >= ? AND origin != 'manual' ORDER BY COALESCE(score,-1) DESC, id DESC", (ts,)).fetchall()]


def discarded():
    with conn() as c:
        return [dict(r) for r in c.execute(
            "SELECT j.id, j.title, j.company, j.location, j.source, j.score, j.discard_reason, "
            "(SELECT MAX(changed_at) FROM status_history h WHERE h.job_id=j.id AND h.status='discarded') AS discarded_at "
            "FROM jobs j WHERE j.status='discarded' ORDER BY discarded_at DESC").fetchall()]


def dim(jid):
    with conn() as c:
        c.execute("UPDATE jobs SET dimmed=1 WHERE id=? AND status != 'discarded'", (jid,))


def keep(jid):
    """Undo the grey-out."""
    with conn() as c:
        c.execute("UPDATE jobs SET dimmed=0 WHERE id=?", (jid,))


def update_fields(jid, fields):
    allowed = ["contact", "recruiter", "cv_version", "applied_date", "followup_date", "notes",
               "work_rate", "apply_method", "orp_assigned", "outcome_note", "location", "letter",
               "orp_deadline", "followed_up_at", "interview_at", "docs", "cv_text"]
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
    if fields.get("interview_at") and row and row["status"] in ("new", "shortlisted", "applied"):
        update_status(jid, "interview")          # an interview date means "I got an interview"


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
        if status == "discarded":
            c.execute("UPDATE jobs SET discard_reason='filled' WHERE id=?", (jid,))
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


def assignments_open():
    """Jobs the ORP assigned that aren't applied to yet, most urgent first (days_left may be None)."""
    today = datetime.date.today()
    with conn() as c:
        rows = [dict(r) for r in c.execute(
            "SELECT * FROM jobs WHERE orp_assigned=1 AND status IN ('new','shortlisted')").fetchall()]
    for r in rows:
        try:
            r["days_left"] = (datetime.date.fromisoformat(r["orp_deadline"]) - today).days
        except (TypeError, ValueError):
            r["days_left"] = None
    return sorted(rows, key=lambda r: (r["days_left"] is None, r["days_left"] or 0))


def awaiting_answer(days=10, again=14):
    """Applications without an answer for `days` days that weren't followed up in the last `again` days."""
    today = datetime.date.today()
    with conn() as c:
        rows = [dict(r) for r in c.execute(
            "SELECT * FROM jobs WHERE status='applied' AND COALESCE(applied_date,'') != '' AND applied_date <= ? "
            "AND (COALESCE(followed_up_at,'') = '' OR followed_up_at <= ?) "
            "AND (COALESCE(followup_date,'') = '' OR followup_date <= ?) ORDER BY applied_date",
            ((today - datetime.timedelta(days=days)).isoformat(), (today - datetime.timedelta(days=again)).isoformat(),
             today.isoformat())).fetchall()]
    for r in rows:
        r["days_waiting"] = (today - datetime.date.fromisoformat(r["applied_date"])).days
    return rows


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


# ---- named versions: CV texts and cover letters the person wrote once and applies to jobs ----
MAX_CV_VERSIONS = 30          # per kind
KINDS = ("cv", "letter")


def cv_versions(kind="cv"):
    with conn() as c:
        return [dict(r) for r in c.execute("SELECT * FROM cv_versions WHERE kind=? ORDER BY is_default DESC, name COLLATE NOCASE",
                                           (kind,)).fetchall()]


def cv_version(vid, kind=None):
    with conn() as c:
        r = c.execute("SELECT * FROM cv_versions WHERE id=?", (vid,)).fetchone()
        return dict(r) if r and kind in (None, r["kind"]) else None


def default_cv_version(kind="cv"):
    with conn() as c:
        r = c.execute("SELECT * FROM cv_versions WHERE is_default=1 AND kind=? LIMIT 1", (kind,)).fetchone()
        return dict(r) if r else None


def save_cv_version(name, text, vid=None, default=None, kind="cv"):
    """Create a version, or change one (vid). A name already used by another version of the same kind
    replaces that version's text instead of making a second one with the same name. Returns its id,
    or None (no name, a name taken when renaming, or the limit of versions is reached)."""
    name = " ".join((name or "").split())[:60]
    if not name or kind not in KINDS:
        return None
    with conn() as c:
        if vid is not None:
            row = c.execute("SELECT kind FROM cv_versions WHERE id=?", (vid,)).fetchone()
            if not row:
                return None
            kind = row["kind"]
        same = c.execute("SELECT id FROM cv_versions WHERE name=? COLLATE NOCASE AND kind=?", (name, kind)).fetchone()
        if vid is None and same:
            vid = same["id"]
        elif vid is not None and same and same["id"] != vid:
            return None
        if vid is None:
            if c.execute("SELECT COUNT(*) FROM cv_versions WHERE kind=?", (kind,)).fetchone()[0] >= MAX_CV_VERSIONS:
                return None
            vid = c.execute("INSERT INTO cv_versions (name, text, kind, created_at, updated_at) VALUES (?,?,?,?,?)",
                            (name, text, kind, now(), now())).lastrowid
        else:
            c.execute("UPDATE cv_versions SET name=?, text=?, updated_at=? WHERE id=?", (name, text, now(), vid))
        if default:
            c.execute("UPDATE cv_versions SET is_default = (id = ?) WHERE kind=?", (vid, kind))
        elif default is False:
            c.execute("UPDATE cv_versions SET is_default=0 WHERE id=?", (vid,))
    return vid


def delete_cv_version(vid):
    with conn() as c:
        c.execute("DELETE FROM cv_versions WHERE id=?", (vid,))


def set_meta(**kv):
    with conn() as c:
        c.executemany("INSERT INTO meta (k, v) VALUES (?, ?) ON CONFLICT(k) DO UPDATE SET v=excluded.v",
                      [(k, str(v)) for k, v in kv.items()])


def get_meta():
    with conn() as c:
        return {r["k"]: r["v"] for r in c.execute("SELECT k, v FROM meta").fetchall()}
