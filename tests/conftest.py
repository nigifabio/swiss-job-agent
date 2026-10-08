import importlib
import json

import httpx
import pytest

MODULES = ["config", "normalize", "http", "scanlog", "filters", "store", "prefs", "skills", "enrich", "compose", "tailor", "letter",
           "commute", "requirements", "closed", "tune", "prep", "locales_it", "locales", "i18n", "report", "twins", "suggest", "docs", "strength", "weekly", "agenda", "providers.adzuna", "providers.ats", "providers.jobup", "providers.jobroom",
           "providers.remote", "providers.careerjet", "providers.jooble", "providers.mailalerts", "fetch", "auth",
           "scheduler", "roles", "places", "importers.extract", "importers.cvparse", "importers.linkedin", "onboard",
           "web"]


def _no_network(request):
    raise AssertionError(f"test tried to reach the network: {request.method} {request.url}")


@pytest.fixture
def env(tmp_path, monkeypatch):
    """Fresh app on a temp DB with test config. No real network: any HTTP request
    fails the test unless the test installs its own handler via `net`."""
    monkeypatch.setenv("DB_PATH", str(tmp_path / "jobs.db"))
    monkeypatch.setenv("WATCHLIST_PATH", str(tmp_path / "watchlist.json"))
    monkeypatch.setenv("TITLE_KEYWORDS", "architect,devops")
    monkeypatch.setenv("TITLE_EXCLUDE", "junior,intern")
    monkeypatch.setenv("LOCATION_KEYWORDS", "geneva,genève,lausanne")
    monkeypatch.setenv("SCORE_KEYWORDS", "aws,azure,terraform,api")
    monkeypatch.setenv("LANGUAGES", "en")
    monkeypatch.setenv("PUBLIC_BOARDS", "0")          # the boards everybody gets are tested on their own
    for var in ("CF_TEAM_DOMAIN", "CF_ACCESS_AUD", "ALLOWED_EMAILS", "CAREERJET_API_KEY", "JOOBLE_API_KEY",
                "IMAP_HOST", "JOBROOM_CANTONS", "ONBOARDING", "PLATFORM_TENANT", "SETTINGS_PATH", "PROFILE_PATH"):
        monkeypatch.delenv(var, raising=False)
    import app  # noqa: F401
    mods = {}
    for name in MODULES:
        mods[name] = importlib.reload(importlib.import_module(f"app.{name}"))
    mods["http"].TRANSPORT = httpx.MockTransport(_no_network)
    mods["http"].SLEEP = lambda s: None
    monkeypatch.setattr(mods["enrich"].httpx, "get",
                        lambda url, **k: _no_network(httpx.Request("GET", url)))

    # "Scan now" runs inline in tests instead of leaking a background thread
    monkeypatch.setattr(mods["web"], "_start_background", lambda fn: fn())
    import app as pkg
    for name in ("adzuna", "ats", "jobup", "jobroom", "remote", "careerjet", "jooble", "mailalerts"):
        setattr(pkg.providers, name, mods[f"providers.{name}"])
    return pkg


@pytest.fixture
def net(env):
    """Route crawler HTTP to a dict of {url_prefix: handler(request) -> httpx.Response}."""
    routes = {}

    def handler(request):
        url = str(request.url)
        for prefix, fn in sorted(routes.items(), key=lambda kv: -len(kv[0])):
            if url.startswith(prefix):
                return fn(request)
        return _no_network(request)
    env.http.TRANSPORT = httpx.MockTransport(handler)
    return routes


def jresp(data, status=200, **headers):
    return httpx.Response(status, content=json.dumps(data).encode(), headers={"content-type": "application/json", **headers})
