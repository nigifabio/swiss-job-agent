"""Cloudflare Access JWT check. Off unless CF_TEAM_DOMAIN and CF_ACCESS_AUD are set."""
import jwt

from . import config

ENABLED = bool(config.CF_TEAM_DOMAIN and config.CF_ACCESS_AUD)
_jwks = jwt.PyJWKClient(f"https://{config.CF_TEAM_DOMAIN}/cdn-cgi/access/certs",
                        cache_keys=True, lifespan=3600) if ENABLED else None


def user_email(token):
    """Return the verified email for an Access token, or None if it isn't valid."""
    if not token:
        return None
    try:
        key = _jwks.get_signing_key_from_jwt(token).key
        claims = jwt.decode(token, key, algorithms=["RS256"], audience=config.CF_ACCESS_AUD,
                            issuer=f"https://{config.CF_TEAM_DOMAIN}")
    except Exception:  # noqa: BLE001
        return None
    email = (claims.get("email") or "").lower()
    if config.ALLOWED_EMAILS and email not in config.ALLOWED_EMAILS:
        return None
    return email or None
