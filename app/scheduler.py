import time
import datetime

from . import config, store
from .fetch import run


def seconds_until_due(interval, meta, now=None):
    """0 if a scan is due, else seconds left: a restart (e.g. a deploy) doesn't trigger
    an extra scan when the last one is recent."""
    last = meta.get("last_scan_at")
    if not last:
        return 0
    now = now or datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None)
    elapsed = (now - datetime.datetime.fromisoformat(last)).total_seconds()
    return max(0, interval - elapsed)


def main():
    interval = max(0.05, config.FETCH_INTERVAL_HOURS) * 3600
    print(f"[scheduler] starting; fetch every {config.FETCH_INTERVAL_HOURS}h")
    store.init_db()
    wait = seconds_until_due(interval, store.get_meta())
    if wait:
        print(f"[scheduler] last scan is recent; next in {wait / 3600:.1f}h")
        time.sleep(wait)
    while True:
        try:
            run()
        except Exception as e:  # noqa: BLE001
            print(f"[scheduler] run failed: {e}")
        config.refresh_settings()           # the interval may have changed on the Settings page
        time.sleep(max(0.05, config.FETCH_INTERVAL_HOURS) * 3600)


if __name__ == "__main__":
    main()
