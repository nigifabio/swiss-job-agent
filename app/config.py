import os
import json


def _terms(raw):
    return [t.strip() for t in raw.split(";") if t.strip()]


def _csv(raw):
    return [t.strip().lower() for t in raw.split(",") if t.strip()]


SEARCH_TERMS = _terms(os.environ.get("SEARCH_TERMS", ""))
# One or more regions (";"-separated); Adzuna is queried once per term x region.
WHERE = _terms(os.environ.get("WHERE", "Vaud")) or [""]

ADZUNA_APP_ID = os.environ.get("ADZUNA_APP_ID", "")
ADZUNA_APP_KEY = os.environ.get("ADZUNA_APP_KEY", "")
ADZUNA_COUNTRY = os.environ.get("ADZUNA_COUNTRY", "ch")
RESULTS_PER_PAGE = int(os.environ.get("RESULTS_PER_PAGE", "50"))

FETCH_INTERVAL_HOURS = float(os.environ.get("FETCH_INTERVAL_HOURS", "12"))

DB_PATH = os.environ.get("DB_PATH", "/data/jobs.db")
# Candidate profile (JSON) for tailored CVs; lives with the data, not in git.
PROFILE_PATH = os.environ.get("PROFILE_PATH", os.path.join(os.path.dirname(DB_PATH) or ".", "profile.json"))

# --- providers ---
# Which providers run, in order. Options: ats, adzuna, jobup
PROVIDERS = _terms(os.environ.get("PROVIDERS", "ats").replace(",", ";"))

# --- ATS crawler ---
# On the bind-mounted /data volume so discover + web + scheduler all share it
# and it survives rebuilds. Falls back to the in-repo copy if /data is absent.
_wl_default = "/data/watchlist.json" if os.path.isdir("/data") else \
    os.path.join(os.path.dirname(__file__), "watchlist.json")
WATCHLIST_PATH = os.environ.get("WATCHLIST_PATH", _wl_default)

# Keep only postings in these languages (langdetect codes). Default: English + Italian
LANGUAGES = _csv(os.environ.get("LANGUAGES", "en,it"))

# Keep only postings whose title contains one of these (seniority targeting).
# Empty -> keep every title. Defaults cover EN + IT senior leadership titles.
_default_titles = ("vp,vice president,director,direttore,head of,responsabile,chief,"
                   "principal,staff,lead,gerente,capo,svp,evp")
TITLE_KEYWORDS = _csv(os.environ.get("TITLE_KEYWORDS", _default_titles))
# Drop titles containing any of these (e.g. junior,intern,stagiaire). Blank = drop nothing.
TITLE_EXCLUDE = _csv(os.environ.get("TITLE_EXCLUDE", ""))

# Keep only postings whose location mentions one of these. Default: anywhere in Switzerland.
_default_locations = ("switzerland,schweiz,suisse,svizzera,zurich,zürich,zurigo,vaud,lausanne,"
                      "geneva,genève,geneve,ginevra,romandie,basel,bern,berne,zug,lugano,ticino,"
                      "lucerne,luzern,st. gallen,st gallen,winterthur,fribourg,neuchâtel,neuchatel,"
                      "montreux,nyon,renens")
LOCATION_KEYWORDS = _csv(os.environ.get("LOCATION_KEYWORDS", _default_locations))
ALLOW_REMOTE = os.environ.get("ALLOW_REMOTE", "1") == "1"
# A remote role must name one of these regions (or be bare "Remote") to count.
REMOTE_REGIONS = _csv(os.environ.get("REMOTE_REGIONS",
                                     "switzerland,schweiz,suisse,svizzera,ch,europe,emea,eu,dach,anywhere,worldwide,global"))

# CV skills used to score postings 0-100 (comma-separated). Blank = no scoring.
SCORE_KEYWORDS = _csv(os.environ.get("SCORE_KEYWORDS", ""))

# --- access control (optional, defense in depth behind Cloudflare Access) ---
# When CF_TEAM_DOMAIN + CF_ACCESS_AUD are set, every request except /healthz must
# carry a valid Cloudflare Access JWT; the LAN port is then useless without it.
CF_TEAM_DOMAIN = os.environ.get("CF_TEAM_DOMAIN", "")      # e.g. your-team.cloudflareaccess.com
CF_ACCESS_AUD = os.environ.get("CF_ACCESS_AUD", "")        # Access app "Application Audience (AUD) Tag"
# Optional extra allowlist on the JWT email (comma-separated). Blank = trust the Access policy.
ALLOWED_EMAILS = [e.strip().lower() for e in os.environ.get("ALLOWED_EMAILS", "").split(",") if e.strip()]

# --- per-tenant settings (onboarding / Settings page) ---
# data/settings.json overrides the search settings above, so a tenant can change them from
# the web app without touching .env. A key absent from the file keeps its .env value.
SETTINGS_PATH = os.environ.get("SETTINGS_PATH", os.path.join(os.path.dirname(DB_PATH) or ".", "settings.json"))
# Onboarding wizard on until a profile exists (set by the platform for new tenants, or by install.sh).
ONBOARDING = os.environ.get("ONBOARDING", "") == "1"
# Runs as a tenant behind the multi-tenant platform gateway (account pages live there).
PLATFORM_TENANT = os.environ.get("PLATFORM_TENANT", "") == "1"

# Companies and agencies never shown (whole words of the company name).
COMPANY_EXCLUDE = _csv(os.environ.get("COMPANY_EXCLUDE", ""))
# Work rate wanted, in %: a posting whose title states a rate outside it is skipped (0-100 = any).
WORK_RATE_MIN = int(os.environ.get("WORK_RATE_MIN", "0") or 0)
WORK_RATE_MAX = int(os.environ.get("WORK_RATE_MAX", "100") or 100)
# Applications per month the ORP / RAV office asked for.
ORP_MONTHLY_TARGET = int(os.environ.get("ORP_MONTHLY_TARGET", "10") or 10)
# Home town, for the public-transport time to each job; COMMUTE_MAX minutes greys out the ones further (0 = off).
HOME_TOWN = os.environ.get("HOME_TOWN", "")
COMMUTE_MAX = int(os.environ.get("COMMUTE_MAX", "0") or 0)
# Language of the interface: en, fr or de ("" = the browser's).
UI_LANG = os.environ.get("UI_LANG", "")
# Search radius around the home town, in km: when set, the towns and cantons searched are computed
# from home + radius each time either changes on the Settings page (0 = the towns are kept as typed).
RADIUS_KM = int(os.environ.get("RADIUS_KM", "0") or 0)
INT_BOUNDS = {"WORK_RATE_MIN": (0, 100), "WORK_RATE_MAX": (10, 100), "ORP_MONTHLY_TARGET": (1, 60), "COMMUTE_MAX": (0, 240),
              "RADIUS_KM": (0, 150)}

EDITABLE = {   # name -> kind
    "SEARCH_TERMS": "list", "WHERE": "list", "PROVIDERS": "list", "LANGUAGES": "lower",
    "TITLE_KEYWORDS": "lower", "TITLE_EXCLUDE": "lower", "LOCATION_KEYWORDS": "lower",
    "SCORE_KEYWORDS": "lower", "ALLOW_REMOTE": "bool", "FETCH_INTERVAL_HOURS": "hours",
    "JOBROOM_CANTONS": "list", "COMPANY_EXCLUDE": "lower", "WORK_RATE_MIN": "int", "WORK_RATE_MAX": "int",
    "ORP_MONTHLY_TARGET": "int", "HOME_TOWN": "text", "RADIUS_KM": "int", "COMMUTE_MAX": "int", "UI_LANG": "text",
}
JOBROOM_CANTONS = _terms(os.environ.get("JOBROOM_CANTONS", "").replace(",", ";"))
_ENV_DEFAULTS = {k: globals()[k] for k in EDITABLE}


def _coerce(kind, v, name=""):
    if kind == "bool":
        return bool(v)
    if kind == "int":
        lo, hi = INT_BOUNDS.get(name, (0, 10 ** 6))
        return min(hi, max(lo, int(float(v))))
    if kind == "text":
        v = " ".join(str(v).split())[:60]
        return (v if v in ("en", "fr", "de") else "") if name == "UI_LANG" else v
    if kind == "hours":
        return min(168.0, max(1.0, float(v)))
    items = v if isinstance(v, list) else str(v).replace(";", ",").split(",")
    items = [" ".join(str(x).split()) for x in items if str(x).strip()]
    return [x.lower() for x in items] if kind == "lower" else items


def load_settings():
    """The tenant's saved settings ({} when none)."""
    try:
        with open(SETTINGS_PATH) as f:
            data = json.load(f)
    except (OSError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}


def reload_settings():
    """Re-apply settings.json over the .env values (called at start-up, before each scan and
    after a save): the web and scheduler processes both pick up a change."""
    data = load_settings()
    for k, kind in EDITABLE.items():
        val = _ENV_DEFAULTS[k]
        if k in data:
            try:
                val = _coerce(kind, data[k], k)
            except (TypeError, ValueError):
                pass
        globals()[k] = val
    if not globals()["WHERE"]:
        globals()["WHERE"] = [""]


_loaded_mtime = None


def _mtime():
    try:
        return os.stat(SETTINGS_PATH).st_mtime_ns
    except OSError:
        return None


def refresh_settings():
    """reload_settings() only if settings.json changed since the last load (another process saved it)."""
    global _loaded_mtime
    m = _mtime()
    if m != _loaded_mtime:
        reload_settings()
        _loaded_mtime = m


def save_settings(values):
    """Validate, write atomically, apply. Unknown keys are ignored."""
    clean = {}
    for k, kind in EDITABLE.items():
        if k in values:
            try:
                clean[k] = _coerce(kind, values[k], k)
            except (TypeError, ValueError):
                pass
    tmp = SETTINGS_PATH + ".tmp"
    os.makedirs(os.path.dirname(SETTINGS_PATH) or ".", exist_ok=True)
    with open(tmp, "w") as f:
        json.dump(clean, f, indent=2, ensure_ascii=False)
    os.replace(tmp, SETTINGS_PATH)
    reload_settings()
    global _loaded_mtime
    _loaded_mtime = _mtime()
    return clean


reload_settings()
_loaded_mtime = _mtime()
