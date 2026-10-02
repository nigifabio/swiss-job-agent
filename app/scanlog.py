"""Per-source results of the current scan, so problems show up on the dashboard
instead of only in container logs: counts per source and any errors."""

_sources = {}


def start():
    _sources.clear()


def count(source, n):
    _sources.setdefault(source, {"count": 0, "errors": []})["count"] += n


def error(source, message):
    _sources.setdefault(source, {"count": 0, "errors": []})["errors"].append(str(message)[:200])
    print(f"[{source}] {message}")


def result():
    return {k: dict(v) for k, v in _sources.items()}


def warnings(current, previous):
    """Human-readable problems: errors, and sources that dropped to 0 after returning jobs
    (usually the site changed its API or blocked us)."""
    out = []
    for src, r in sorted(current.items()):
        if r["errors"]:
            out.append(f"{src}: {len(r['errors'])} error(s), e.g. {r['errors'][0]}")
        before = (previous or {}).get(src, {}).get("count", 0)
        if r["count"] == 0 and before > 0:
            out.append(f"{src} returned 0 postings (had {before} last scan): the site may have changed or blocked the scan")
    return out
