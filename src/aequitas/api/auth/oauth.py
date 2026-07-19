"""Google OAuth client via authlib, OIDC discovery against Google's well-known config."""
from __future__ import annotations

from authlib.integrations.starlette_client import OAuth

from aequitas.api.config import ApiConfig

_oauth_client: OAuth | None = None


def get_google_oauth_client() -> OAuth:
    """Return a process-wide OAuth client with Google registered as a provider."""
    global _oauth_client
    if _oauth_client is None:
        cfg = ApiConfig()
        oauth = OAuth()
        oauth.register(
            name="google",
            client_id=cfg.google_client_id,
            client_secret=cfg.google_client_secret,
            server_metadata_url=(
                "https://accounts.google.com/.well-known/openid-configuration"
            ),
            client_kwargs={"scope": "openid email profile"},
        )
        _oauth_client = oauth
    return _oauth_client


def reset_oauth_client_for_tests() -> None:
    """Clear the cached OAuth client (tests only)."""
    global _oauth_client
    _oauth_client = None
