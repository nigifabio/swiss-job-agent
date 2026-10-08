"""What needs the operator's attention, from totals only: an app that is down, a workspace whose
scans stopped, a job source failing (and for how many workspaces), a nightly backup that didn't run.
The gateway asks each workspace for counts (/ops/summary); nothing here reads a title, a company or a name."""
import datetime

STALE_SCAN_HOURS = 36
STALE_BACKUP_HOURS = 36


def _age_hours(ts, now):
    try:
        t = datetime.datetime.fromisoformat(ts)
    except (TypeError, ValueError):
        return None
    if t.tzinfo is None:
        t = t.replace(tzinfo=datetime.timezone.utc)
    return (now - t).total_seconds() / 3600


def problems(rows, backup=None, now=None):
    """rows: the admin page's workspaces (slug, status, web, ops). Returns a list of plain lines."""
    now = now or datetime.datetime.now(datetime.timezone.utc)
    out, by_source, active = [], {}, [t for t in rows if t.get("status") == "active"]
    for t in active:
        if "healthy" not in str(t.get("web", "")):
            out.append(f"{t['slug']}: app is {t.get('web', '?')}")
        o = t.get("ops") or {}
        if not o:
            continue
        age = _age_hours(o.get("last_scan_at"), now)
        if o.get("setup_done") and (age is None or age > STALE_SCAN_HOURS):
            out.append(f"{t['slug']}: no scan " + ("yet" if age is None else f"for {int(age)} h"))
        for src, r in (o.get("sources") or {}).items():
            if r.get("errors"):
                by_source.setdefault((src, r.get("kind") or "error"), []).append(t["slug"])
    for (src, kind), slugs in sorted(by_source.items()):
        out.append(f"source {src}: {kind} for {len(slugs)} of {len(active)} workspaces ({', '.join(sorted(slugs))})")
    if backup is not None and backup.get("hour") is not None:
        age = _age_hours(backup.get("at"), now)
        if age is None:
            out.append("backup: none yet")
        elif age > STALE_BACKUP_HOURS:
            out.append(f"backup: last one {int(age)} h ago")
        if backup.get("failed"):
            out.append("backup: failed for " + ", ".join(backup["failed"]))
    return out
