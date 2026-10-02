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
  used_by TEXT, used_at TEXT, revoked INTEGER NOT NULL DEFAULT 0);
CREATE TABLE IF NOT EXISTS audit (ts TEXT NOT NULL, actor TEXT, action TEXT, detail TEXT);
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


def audit(actor, action, detail=""):
    with conn() as c:
        c.execute("INSERT INTO audit VALUES (?,?,?,?)", (now(), actor, action, detail))


def tenant_for(email):
    with conn() as c:
        r = c.execute("SELECT * FROM tenants WHERE email=?", ((email or "").lower(),)).fetchone()
        return dict(r) if r else None


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


def _hash(token):
    return hashlib.sha256(token.encode()).hexdigest()


def create_invite(created_by, note="", days=7, email=""):
    """Returns the token (shown once; only its hash is stored)."""
    token = secrets.token_urlsafe(24)
    exp = (datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=days)).replace(microsecond=0)
    with conn() as c:
        c.execute("INSERT INTO invites (token_hash, note, email, created_by, created_at, expires_at) VALUES (?,?,?,?,?,?)",
                  (_hash(token), note, (email or "").lower() or None, created_by, now(), exp.isoformat()))
    return token


def invite(token):
    """The invite row if the token is valid (not used, revoked or expired), else None."""
    with conn() as c:
        r = c.execute("SELECT * FROM invites WHERE token_hash=?", (_hash(token or ""),)).fetchone()
    if not r or r["revoked"] or r["used_at"] or r["expires_at"] < now():
        return None
    return dict(r)


def use_invite(invite_id, email):
    with conn() as c:
        cur = c.execute("UPDATE invites SET used_by=?, used_at=? WHERE id=? AND used_at IS NULL AND revoked=0",
                        (email.lower(), now(), invite_id))
        return cur.rowcount == 1


def revoke_invite(invite_id):
    with conn() as c:
        c.execute("UPDATE invites SET revoked=1 WHERE id=?", (invite_id,))


def invites(limit=50):
    with conn() as c:
        return [dict(r) for r in c.execute("SELECT * FROM invites ORDER BY id DESC LIMIT ?", (limit,)).fetchall()]


def audit_log(limit=50):
    with conn() as c:
        return [dict(r) for r in c.execute("SELECT * FROM audit ORDER BY rowid DESC LIMIT ?", (limit,)).fetchall()]
