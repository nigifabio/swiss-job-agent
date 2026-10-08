"""Gateway state (SQLite): who owns which tenant, invites, and an audit log."""
import datetime
import hashlib
import os
import re
import secrets
import sqlite3

PATH = os.environ.get("PLATFORM_DB", "/state/platform.db")

SCHEMA = """
CREATE TABLE IF NOT EXISTS tenants (
  slug TEXT PRIMARY KEY, email TEXT UNIQUE NOT NULL, status TEXT NOT NULL DEFAULT 'active',
  created_at TEXT NOT NULL, invite_id INTEGER);
CREATE TABLE IF NOT EXISTS invites (
  id INTEGER PRIMARY KEY AUTOINCREMENT, token_hash TEXT UNIQUE NOT NULL, note TEXT,
  email TEXT, created_by TEXT, created_at TEXT NOT NULL, expires_at TEXT NOT NULL,
  used_by TEXT, used_at TEXT, revoked INTEGER NOT NULL DEFAULT 0,
  max_uses INTEGER NOT NULL DEFAULT 1, uses INTEGER NOT NULL DEFAULT 0);
CREATE TABLE IF NOT EXISTS aliases (email TEXT PRIMARY KEY, slug TEXT NOT NULL, added_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS requests (
  email TEXT PRIMARY KEY, name TEXT, note TEXT, status TEXT NOT NULL DEFAULT 'pending',
  created_at TEXT NOT NULL, decided_at TEXT, decided_by TEXT);
CREATE TABLE IF NOT EXISTS audit (ts TEXT NOT NULL, actor TEXT, action TEXT, detail TEXT);
CREATE TABLE IF NOT EXISTS kv (k TEXT PRIMARY KEY, v TEXT);
CREATE TABLE IF NOT EXISTS feedback (id INTEGER PRIMARY KEY AUTOINCREMENT, ts TEXT NOT NULL, email TEXT NOT NULL,
  kind TEXT NOT NULL, page TEXT, text TEXT NOT NULL, done INTEGER NOT NULL DEFAULT 0);
CREATE TABLE IF NOT EXISTS forum_topics (id INTEGER PRIMARY KEY AUTOINCREMENT, cat TEXT NOT NULL, title TEXT NOT NULL,
  slug TEXT NOT NULL, created_at TEXT NOT NULL, last_at TEXT NOT NULL, replies INTEGER NOT NULL DEFAULT 0);
CREATE TABLE IF NOT EXISTS forum_posts (id INTEGER PRIMARY KEY AUTOINCREMENT, topic_id INTEGER NOT NULL, slug TEXT NOT NULL,
  text TEXT NOT NULL, created_at TEXT NOT NULL, deleted INTEGER NOT NULL DEFAULT 0);
CREATE INDEX IF NOT EXISTS idx_forum_posts_topic ON forum_posts(topic_id);
"""


def now():
    return datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0).isoformat()


def conn():
    os.makedirs(os.path.dirname(PATH) or ".", exist_ok=True)
    c = sqlite3.connect(PATH, timeout=10)
    c.row_factory = sqlite3.Row
    c.execute("PRAGMA journal_mode=WAL")
    return c


def init():
    with conn() as c:
        c.executescript(SCHEMA)
        cols = {r["name"] for r in c.execute("PRAGMA table_info(invites)").fetchall()}
        if "max_uses" not in cols:              # databases created before shareable invites
            c.execute("ALTER TABLE invites ADD COLUMN max_uses INTEGER NOT NULL DEFAULT 1")
            c.execute("ALTER TABLE invites ADD COLUMN uses INTEGER NOT NULL DEFAULT 0")
            c.execute("UPDATE invites SET uses=1 WHERE used_at IS NOT NULL")
        if "last_seen" not in {r["name"] for r in c.execute("PRAGMA table_info(tenants)").fetchall()}:
            c.execute("ALTER TABLE tenants ADD COLUMN last_seen TEXT")
        if "league_name" not in {r["name"] for r in c.execute("PRAGMA table_info(tenants)").fetchall()}:
            c.execute("ALTER TABLE tenants ADD COLUMN league_name TEXT")
        if "in_league" not in {r["name"] for r in c.execute("PRAGMA table_info(tenants)").fetchall()}:
            c.execute("ALTER TABLE tenants ADD COLUMN in_league INTEGER NOT NULL DEFAULT 1")       # whoever had a nickname was in the league


# ---- bug reports and feature requests ---------------------------------------------------------
def add_feedback(email, kind, page, text, per_day=8):
    """Keep one message. Returns its id, or None when this person already sent many today."""
    with conn() as c:
        since = (datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=1)).replace(microsecond=0).isoformat()
        if c.execute("SELECT COUNT(*) FROM feedback WHERE email=? AND ts >= ?", (email, since)).fetchone()[0] >= per_day:
            return None
        return c.execute("INSERT INTO feedback (ts, email, kind, page, text) VALUES (?,?,?,?,?)", (now(), email, kind, page, text)).lastrowid


def feedback(limit=50):
    with conn() as c:
        return [dict(r) for r in c.execute("SELECT * FROM feedback ORDER BY done, id DESC LIMIT ?", (limit,)).fetchall()]


def close_feedback(fid, done=1):
    with conn() as c:
        c.execute("UPDATE feedback SET done=? WHERE id=?", (done, fid))


# ---- the league: people who chose to compare their points, under a nickname ---------------------
NICK = re.compile(r"^[^\W_](?:[^\W_]|[ .-](?=[^\W_])){1,19}$")


def set_nickname(slug, name, league=None):
    """The person's one username on the platform (league and forum). league=True/False also joins or
    leaves the league; None leaves that as it is (a first nickname taken for the forum is not a league entry).
    Returns the nickname kept, or None (not a usable nickname, or already someone else's)."""
    name = " ".join((name or "").split())
    if not NICK.match(name) or "@" in name:
        return None
    with conn() as c:
        if c.execute("SELECT 1 FROM tenants WHERE lower(league_name)=lower(?) AND slug != ?", (name, slug)).fetchone():
            return None
        had = c.execute("SELECT COALESCE(league_name,'') FROM tenants WHERE slug=?", (slug,)).fetchone()
        if league is None and had is not None and not had[0]:
            league = False
        c.execute("UPDATE tenants SET league_name=? WHERE slug=?", (name, slug))
        if league is not None:
            c.execute("UPDATE tenants SET in_league=? WHERE slug=?", (1 if league else 0, slug))
    return name


def join_league(slug, name):
    return set_nickname(slug, name, league=True)


def leave_league(slug):
    """Off the board; the nickname stays (it may sign forum messages)."""
    with conn() as c:
        c.execute("UPDATE tenants SET in_league=0 WHERE slug=?", (slug,))


def league():
    with conn() as c:
        return [dict(r) for r in c.execute("SELECT * FROM tenants WHERE COALESCE(league_name,'') != '' AND in_league=1 AND status='active'").fetchall()]


# ---- the forum: topics about the job search, signed with the nickname ---------------------------
FORUM_CATS = ("cv", "interviews", "orp", "training", "leads", "other")


def forum_topics(cat="", limit=100):
    with conn() as c:
        q = ("SELECT t.*, COALESCE(n.league_name, '') AS author FROM forum_topics t LEFT JOIN tenants n ON n.slug = t.slug "
             + ("WHERE t.cat=? " if cat else "") + "ORDER BY t.last_at DESC LIMIT ?")
        return [dict(r) for r in c.execute(q, ((cat, limit) if cat else (limit,))).fetchall()]


def forum_topic(tid):
    with conn() as c:
        t = c.execute("SELECT t.*, COALESCE(n.league_name, '') AS author FROM forum_topics t LEFT JOIN tenants n ON n.slug = t.slug WHERE t.id=?",
                      (tid,)).fetchone()
        if not t:
            return None, []
        posts = c.execute("SELECT p.*, COALESCE(n.league_name, '') AS author FROM forum_posts p LEFT JOIN tenants n ON n.slug = p.slug "
                          "WHERE p.topic_id=? ORDER BY p.id", (tid,)).fetchall()
        return dict(t), [dict(p) for p in posts]


def _forum_room(c, slug, per_day):
    since = (datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=1)).replace(microsecond=0).isoformat()
    return c.execute("SELECT COUNT(*) FROM forum_posts WHERE slug=? AND created_at >= ?", (slug, since)).fetchone()[0] < per_day


def forum_new_topic(slug, cat, title, text, per_day=30):
    """Returns the topic id, or None when this person wrote a lot today."""
    with conn() as c:
        if not _forum_room(c, slug, per_day):
            return None
        tid = c.execute("INSERT INTO forum_topics (cat, title, slug, created_at, last_at) VALUES (?,?,?,?,?)",
                        (cat if cat in FORUM_CATS else "other", title, slug, now(), now())).lastrowid
        c.execute("INSERT INTO forum_posts (topic_id, slug, text, created_at) VALUES (?,?,?,?)", (tid, slug, text, now()))
        return tid


def forum_reply(slug, tid, text, per_day=30):
    with conn() as c:
        if not c.execute("SELECT 1 FROM forum_topics WHERE id=?", (tid,)).fetchone() or not _forum_room(c, slug, per_day):
            return None
        pid = c.execute("INSERT INTO forum_posts (topic_id, slug, text, created_at) VALUES (?,?,?,?)", (tid, slug, text, now())).lastrowid
        c.execute("UPDATE forum_topics SET last_at=?, replies=replies+1 WHERE id=?", (now(), tid))
        return pid


def forum_delete_post(pid, slug=None):
    """Remove a message (its own author, or anyone when slug is None: the administrator). A topic whose
    messages are all removed goes too. Returns the topic id, or None."""
    with conn() as c:
        p = c.execute("SELECT * FROM forum_posts WHERE id=?", (pid,)).fetchone()
        if not p or (slug is not None and p["slug"] != slug):
            return None
        c.execute("UPDATE forum_posts SET deleted=1, text='' WHERE id=?", (pid,))
        if not c.execute("SELECT 1 FROM forum_posts WHERE topic_id=? AND deleted=0", (p["topic_id"],)).fetchone():
            c.execute("DELETE FROM forum_posts WHERE topic_id=?", (p["topic_id"],))
            c.execute("DELETE FROM forum_topics WHERE id=?", (p["topic_id"],))
        return p["topic_id"]


def touch(slug):
    """The owner just used their workspace (kept to the minute: the admin page shows who is still active)."""
    with conn() as c:
        c.execute("UPDATE tenants SET last_seen=? WHERE slug=?", (now(), slug))


def get_kv(k, default=""):
    with conn() as c:
        r = c.execute("SELECT v FROM kv WHERE k=?", (k,)).fetchone()
        return r["v"] if r else default


def set_kv(k, v):
    with conn() as c:
        c.execute("INSERT INTO kv (k, v) VALUES (?, ?) ON CONFLICT(k) DO UPDATE SET v=excluded.v", (k, str(v)))


def audit(actor, action, detail=""):
    with conn() as c:
        c.execute("INSERT INTO audit VALUES (?,?,?,?)", (now(), actor, action, detail))


def tenant_for(email):
    """The workspace this verified address opens: its owner address, or one of its extra addresses."""
    email = (email or "").lower()
    with conn() as c:
        r = c.execute("SELECT * FROM tenants WHERE email=?", (email,)).fetchone() or c.execute(
            "SELECT t.* FROM tenants t JOIN aliases a ON a.slug = t.slug WHERE a.email=?", (email,)).fetchone()
        return dict(r) if r else None


def aliases(slug):
    with conn() as c:
        return [r["email"] for r in c.execute("SELECT email FROM aliases WHERE slug=? ORDER BY added_at", (slug,)).fetchall()]


def add_alias(slug, email):
    """False when the address already opens a workspace (its own or someone else's)."""
    email = (email or "").strip().lower()
    if not email or tenant_for(email) or not tenant(slug):
        return False
    with conn() as c:
        c.execute("INSERT INTO aliases (email, slug, added_at) VALUES (?,?,?)", (email, slug, now()))
    return True


def remove_alias(slug, email):
    with conn() as c:
        c.execute("DELETE FROM aliases WHERE slug=? AND email=?", (slug, (email or "").lower()))


def tenant(slug):
    with conn() as c:
        r = c.execute("SELECT * FROM tenants WHERE slug=?", (slug,)).fetchone()
        return dict(r) if r else None


def tenants():
    with conn() as c:
        return [dict(r) for r in c.execute("SELECT * FROM tenants ORDER BY created_at").fetchall()]


def new_slug(email):
    """A readable, unique tenant id from the email's local part: 'jane.doe' -> 'jane-doe'."""
    base = re.sub(r"[^a-z0-9]+", "-", (email or "").split("@")[0].lower()).strip("-")[:24] or "user"
    if len(base) < 3:
        base = f"{base}-user"
    slug, n = base, 2
    while tenant(slug):
        slug, n = f"{base}-{n}", n + 1
    return slug


def add_tenant(slug, email, invite_id=None):
    with conn() as c:
        c.execute("INSERT INTO tenants (slug, email, created_at, invite_id) VALUES (?,?,?,?)",
                  (slug, email.lower(), now(), invite_id))


def set_status(slug, status):
    with conn() as c:
        c.execute("UPDATE tenants SET status=? WHERE slug=?", (status, slug))


def remove_tenant(slug):
    with conn() as c:
        c.execute("DELETE FROM tenants WHERE slug=?", (slug,))
        c.execute("DELETE FROM aliases WHERE slug=?", (slug,))


# ---- account requests (from the home page; the address is the verified sign-in address) --------
def request_for(email):
    with conn() as c:
        r = c.execute("SELECT * FROM requests WHERE email=?", ((email or "").lower(),)).fetchone()
        return dict(r) if r else None


def add_request(email, name, note, max_pending=100):
    """"created", "exists" (one request per address) or "full" (too many waiting)."""
    email = (email or "").lower()
    with conn() as c:
        if c.execute("SELECT 1 FROM requests WHERE email=?", (email,)).fetchone():
            return "exists"
        if c.execute("SELECT COUNT(*) FROM requests WHERE status='pending'").fetchone()[0] >= max_pending:
            return "full"
        c.execute("INSERT INTO requests (email, name, note, created_at) VALUES (?,?,?,?)", (email, name, note, now()))
    return "created"


def decide_request(email, status, by):
    with conn() as c:
        cur = c.execute("UPDATE requests SET status=?, decided_at=?, decided_by=? WHERE email=? AND status='pending'",
                        (status, now(), by, (email or "").lower()))
        return cur.rowcount == 1


def close_request(email):
    with conn() as c:
        c.execute("UPDATE requests SET status='done' WHERE email=? AND status='approved'", ((email or "").lower(),))


def requests(limit=100):
    with conn() as c:
        return [dict(r) for r in c.execute(
            "SELECT * FROM requests ORDER BY (status='pending') DESC, created_at DESC LIMIT ?", (limit,)).fetchall()]


def _hash(token):
    return hashlib.sha256(token.encode()).hexdigest()


def create_invite(created_by, note="", days=7, email="", max_uses=1):
    """Returns the token (shown once; only its hash is stored). max_uses > 1: one link for several people."""
    token = secrets.token_urlsafe(24)
    exp = (datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=days)).replace(microsecond=0)
    with conn() as c:
        c.execute("INSERT INTO invites (token_hash, note, email, created_by, created_at, expires_at, max_uses) "
                  "VALUES (?,?,?,?,?,?,?)", (_hash(token), note, (email or "").lower() or None, created_by, now(),
                                             exp.isoformat(), max(1, int(max_uses))))
    return token


def invite(token):
    """The invite row if the token is valid (uses left, not revoked or expired), else None."""
    with conn() as c:
        r = c.execute("SELECT * FROM invites WHERE token_hash=?", (_hash(token or ""),)).fetchone()
    if not r or r["revoked"] or r["uses"] >= r["max_uses"] or r["expires_at"] < now():
        return None
    return dict(r)


def use_invite(invite_id, email):
    with conn() as c:
        cur = c.execute("UPDATE invites SET uses=uses+1, used_by=?, used_at=? "
                        "WHERE id=? AND uses < max_uses AND revoked=0 AND expires_at >= ?",
                        (email.lower(), now(), invite_id, now()))
        return cur.rowcount == 1


def release_invite(invite_id):
    """Give a use back when the workspace couldn't be created."""
    with conn() as c:
        c.execute("UPDATE invites SET uses=MAX(uses-1, 0) WHERE id=?", (invite_id,))


def revoke_invite(invite_id):
    with conn() as c:
        c.execute("UPDATE invites SET revoked=1 WHERE id=?", (invite_id,))


def invites(limit=50):
    with conn() as c:
        return [dict(r) for r in c.execute("SELECT * FROM invites ORDER BY id DESC LIMIT ?", (limit,)).fetchall()]


def audit_log(limit=50):
    with conn() as c:
        return [dict(r) for r in c.execute("SELECT * FROM audit ORDER BY rowid DESC LIMIT ?", (limit,)).fetchall()]
