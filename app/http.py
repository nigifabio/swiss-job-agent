"""Polite, resilient HTTP for the crawlers.

- Retries timeouts, connection errors, 429 and 5xx with exponential backoff
  (honouring Retry-After, capped at 60 s); other 4xx fail immediately.
- Optional minimum gap between two requests to the same host (min_gap).
- Tests swap TRANSPORT for an httpx.MockTransport and SLEEP for a no-op.
"""
import time

import httpx

TRANSPORT = None          # tests: httpx.MockTransport(handler)
SLEEP = time.sleep        # tests: lambda s: None
RETRY_STATUS = {429, 500, 502, 503, 504}
UA = "swiss-job-agent (+self-hosted job tracker)"


def _retry_after(r):
    try:
        return float(r.headers.get("retry-after", ""))
    except ValueError:
        return None


class Http:
    def __init__(self, timeout=20, headers=None, min_gap=0.0, tries=3, backoff=1.5):
        self.client = httpx.Client(timeout=timeout, headers=headers or {"User-Agent": UA},
                                   follow_redirects=True, trust_env=False, transport=TRANSPORT)
        self.min_gap, self.tries, self.backoff = min_gap, tries, backoff
        self._last = {}

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.client.close()

    def _pace(self, host):
        wait = self.min_gap - (time.monotonic() - self._last.get(host, float("-inf")))
        if wait > 0:
            SLEEP(wait)
        self._last[host] = time.monotonic()

    def get(self, url, **kw):
        return self.request("GET", url, **kw)

    def post(self, url, **kw):
        return self.request("POST", url, **kw)

    def request(self, method, url, **kw):
        host = httpx.URL(url).host
        for attempt in range(1, self.tries + 1):
            self._pace(host)
            try:
                r = self.client.request(method, url, **kw)
            except httpx.TransportError:          # timeouts, DNS, refused, reset
                if attempt == self.tries:
                    raise
                SLEEP(self.backoff * 2 ** (attempt - 1))
                continue
            if r.status_code in RETRY_STATUS and attempt < self.tries:
                SLEEP(min(_retry_after(r) or self.backoff * 2 ** (attempt - 1), 60))
                continue
            r.raise_for_status()
            return r
        raise RuntimeError("unreachable")

    def json(self, url, method="GET", **kw):
        return self.request(method, url, **kw).json()
