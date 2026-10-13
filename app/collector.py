"""The collector: one crawler for a whole platform, with one shared database of postings.

Instead of every workspace querying the same sources, the collector queries each source once for
the union of what the workspaces search, and each workspace takes from it what matches its owner
(app/providers/pool.py), then filters, ranks and tracks on its own as before.

What is here is public: postings (title, company, place, text, link). What a workspace sends is
what it searches (terms, regions, places, languages), never who its owner is; nothing personal
(profile, applications, notes, scores) ever comes here.

  POST /pull    {"since": ts, "spec": {...}}   register the search, get the postings found since
  GET  /status                                  counts for the operator
Both need the platform's pool token. Run: python -m app.collector   (COLLECT_HOURS, POOL_PROVIDERS)
Sources crawled here are the shared ones (Job-Room, the public employers' career sites, remote
boards, keyed aggregators); a person's own sources stay in their workspace."""
import contextlib
import datetime
import hashlib
import hmac
import json
import os
import threading

from fastapi import FastAPI, Request
from fastapi.responses import PlainTextResponse

from . import config, filters, scanlog, store

PROVIDERS = [p.strip() for p in os.environ.get("POOL_PROVIDERS", "jobroom,ats,remote,adzuna,careerjet,jooble").split(",") if p.strip()]
HOURS = float(os.environ.get("COLLECT_HOURS", "6") or 6)
KEEP_DAYS = int(os.environ.get("POOL_DEMAND_DAYS", "21"))      # a search nobody asked for in this long is no longer crawled
KINDS = ("terms", "where", "cantons", "places", "langs")
MAX_VALUES, MAX_PULL = 60, 4000
SCHEMA = """CREATE TABLE IF NOT EXISTS demand (kind TEXT NOT NULL, value TEXT NOT NULL, first_asked TEXT NOT NULL,
  last_asked TEXT NOT NULL, crawled_at TEXT, PRIMARY KEY (kind, value));"""
_wake = threading.Event()
_lock = threading.Lock()


def token():
    """What workspaces show: POOL_TOKEN, or derived from the platform's own secret (never that secret itself)."""
    t = os.environ.get("POOL_TOKEN", "")
    if not t and os.environ.get("PROVISIONER_TOKEN"):
        t = hmac.new(os.environ["PROVISIONER_TOKEN"].encode(), b"pool", hashlib.sha256).hexdigest()
    return t


def init():
    store.init_db()
    with store.conn() as c:
        c.executescript(SCHEMA)


def _clean(spec):
    out = {}
    for k in KINDS:
        vals = spec.get(k) if isinstance(spec, dict) else None
        vals = vals if isinstance(vals, list) else []
        out[k] = list(dict.fromkeys(" ".join(str(v).split())[:80] for v in vals if str(v).strip()))[:MAX_VALUES]
        if k != "terms":
            out[k] = [v.lower() if k != "cantons" else v.upper() for v in out[k]]
    out["remote"] = bool(isinstance(spec, dict) and spec.get("remote"))
    return out


def register(spec):
    """Note what is searched (so it is crawled from now on). Returns whether everything this search
    needs to be answered from the pool has been crawled at least once."""
    now, ready, new = store.now(), True, False
    with store.conn() as c:
        for k in KINDS:
            for v in spec[k]:
                row = c.execute("SELECT crawled_at FROM demand WHERE kind=? AND value=?", (k, v)).fetchone()
                if row is None:
                    c.execute("INSERT INTO demand (kind, value, first_asked, last_asked) VALUES (?,?,?,?)", (k, v, now, now))
                    new = True
                else:
                    c.execute("UPDATE demand SET last_asked=? WHERE kind=? AND value=?", (now, k, v))
                if (row is None or not row["crawled_at"]) and k in ("terms", "where", "cantons", "places"):
                    ready = False
        if spec["remote"]:
            c.execute("INSERT INTO demand (kind, value, first_asked, last_asked) VALUES ('remote','1',?,?) "
                      "ON CONFLICT(kind, value) DO UPDATE SET last_asked=excluded.last_asked", (now, now))
    if new:
        _wake.set()                           # something nobody searched before: crawl soon, not in six hours
    return ready


def plan():
    """{kind: [values]} to crawl: everything asked for in the last KEEP_DAYS days."""
    since = (datetime.datetime.fromisoformat(store.now()) - datetime.timedelta(days=KEEP_DAYS)).isoformat(timespec="seconds")
    out = {k: [] for k in KINDS + ("remote",)}
    with store.conn() as c:
        for r in c.execute("SELECT kind, value FROM demand WHERE last_asked >= ? ORDER BY first_asked", (since,)).fetchall():
            out.setdefault(r["kind"], []).append(r["value"])
    return out


def crawl():
    """One round over the shared sources for the union of what is searched. Returns the number of new postings."""
    from . import fetch
    with _lock:
        p = plan()
        if not (p["terms"] or p["places"]):
            return 0                           # nobody searches anything yet
        config.SEARCH_TERMS, config.WHERE, config.JOBROOM_CANTONS = p["terms"], p["where"] or [""], p["cantons"]
        config.LOCATION_KEYWORDS, config.ALLOW_REMOTE = p["places"], bool(p["remote"])
        config.LANGUAGES = p["langs"] or ["fr", "de", "it", "en"]
        config.TITLE_KEYWORDS, config.TITLE_EXCLUDE, config.COMPANY_EXCLUDE = [], [], []      # every title: each workspace filters its own
        started, new = store.now(), 0
        scanlog.start()
        for name in PROVIDERS:
            mod = fetch.MODULES.get(name)
            if not mod:
                continue
            try:
                jobs = mod.fetch()
            except Exception as e:  # noqa: BLE001
                scanlog.error(name, f"provider crashed: {type(e).__name__}: {str(e)[:150]}")
                continue
            for j in jobs:
                j["title"] = " ".join((j.get("title") or "").split())
                j["score"] = j["score_rationale"] = None
            new += store.upsert_jobs(jobs)
        with store.conn() as c:
            for k in KINDS:
                for v in p[k]:
                    c.execute("UPDATE demand SET crawled_at=? WHERE kind=? AND value=? AND first_asked <= ?", (store.now(), k, v, started))
        store.set_meta(last_scan_at=store.now(), last_scan_new=new, last_scan_report=json.dumps(scanlog.result()))
        print(f"[collector] {new} new postings for {len(p['terms'])} terms, {len(p['places'])} places")
        return new


def _loop():
    while True:
        woke = _wake.wait(timeout=max(0.05, HOURS) * 3600)
        if woke:
            _wake.clear()
            _wake.wait(timeout=45)            # several workspaces registering at once: one round for all
            _wake.clear()
        try:
            crawl()
        except Exception as e:  # noqa: BLE001
            print(f"[collector] round failed: {type(e).__name__}: {str(e)[:200]}")


def postings(since, spec):
    """Postings found since `since` that are in one of the places asked for (or remote, when asked):
    a first, generous cut; the workspace applies its own title, place and language rules."""
    places = [v for v in spec["places"] if v]
    with store.conn() as c:
        rows = c.execute("SELECT content_hash, source, title, company, location, description, url, salary, posted_at, created_at "
                         "FROM jobs WHERE created_at > ? ORDER BY id DESC LIMIT ?", (since or "", MAX_PULL * 5)).fetchall()
    out = []
    for r in rows:
        loc = (r["location"] or "").lower()
        if places and loc and not any(filters._hit(p, loc) for p in places) and not (spec["remote"] and filters._has(loc, filters.REMOTE_KW)):
            continue
        d = dict(r)
        d["description"] = (d["description"] or "")[:8000]
        out.append(d)
        if len(out) >= MAX_PULL:
            break
    return out


@contextlib.asynccontextmanager
async def lifespan(_app):
    init()
    threading.Thread(target=_loop, daemon=True).start()
    _wake.set()                               # a round soon after start (demand is remembered across restarts)
    yield


app = FastAPI(title="jobplatform collector", docs_url=None, redoc_url=None, openapi_url=None, lifespan=lifespan)


def _allowed(request):
    t = token()
    return bool(t) and hmac.compare_digest(request.headers.get("authorization", "").encode(), f"Bearer {t}".encode())


@app.get("/healthz")
def healthz():
    return {"ok": True}


@app.post("/pull")
async def pull(request: Request):
    if not _allowed(request):
        return PlainTextResponse("Not found", status_code=404)
    try:
        body = await request.json()
    except ValueError:
        body = {}
    spec = _clean(body.get("spec") or {})
    now = store.now()                          # taken before reading: nothing found meanwhile is skipped next time
    ready = register(spec)
    since = str(body.get("since") or "")[:19]
    return {"ready": ready, "covers": PROVIDERS, "now": now, "jobs": postings(since, spec) if ready else []}


@app.get("/status")
def status(request: Request):
    if not _allowed(request):
        return PlainTextResponse("Not found", status_code=404)
    meta = store.get_meta()
    with store.conn() as c:
        n = c.execute("SELECT COUNT(*) FROM jobs").fetchone()[0]
        by = {r[0]: r[1] for r in c.execute("SELECT source, COUNT(*) FROM jobs GROUP BY source").fetchall()}
        demand = {r[0]: r[1] for r in c.execute("SELECT kind, COUNT(*) FROM demand GROUP BY kind").fetchall()}
        waiting = c.execute("SELECT COUNT(*) FROM demand WHERE crawled_at IS NULL AND kind IN ('terms','where','cantons','places')").fetchone()[0]
    try:
        report = json.loads(meta.get("last_scan_report") or "{}")
    except ValueError:
        report = {}
    return {"postings": n, "by_source": by, "demand": demand, "waiting": waiting, "last_round_at": meta.get("last_scan_at", ""),
            "last_round_new": meta.get("last_scan_new", ""), "providers": PROVIDERS, "hours": HOURS,
            "sources": {s: {"count": r.get("count", 0), "errors": len(r.get("errors") or [])} for s, r in report.items()}}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("COLLECTOR_PORT", "8092")))
