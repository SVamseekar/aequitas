"""Session cookie signing and verification via itsdangerous."""
from __future__ import annotations

import os

from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer

from aequitas.api.config import ApiConfig

COOKIE_NAME = "aequitas_session"
COOKIE_MAX_AGE_SECONDS = 604800  # 7 days, matches WorkforceGuard's pattern


def session_cookie_secure() -> bool:
    """Use Secure cookies only when explicitly set or frontend is HTTPS.

    Localhost HTTP (http://localhost:5173) must keep Secure=False so the
    browser stores the cookie after OAuth redirect.
    """
    explicit = os.environ.get("SESSION_COOKIE_SECURE", "").strip().lower()
    if explicit in ("1", "true", "yes"):
        return True
    if explicit in ("0", "false", "no"):
        return False
    cfg = ApiConfig()
    return cfg.frontend_url.startswith("https://")


def _serializer() -> URLSafeTimedSerializer:
    cfg = ApiConfig()
    return URLSafeTimedSerializer(cfg.session_secret, salt="aequitas-session-cookie")


def sign_session_id(session_id: str) -> str:
    """Produce a signed, timestamped token embedding the session id."""
    return _serializer().dumps(session_id)


def unsign_session_id(
    token: str, max_age_seconds: int = COOKIE_MAX_AGE_SECONDS
) -> str | None:
    """Recover the session id from a signed token, or None if invalid/expired/tampered."""
    try:
        # itsdangerous treats max_age=0 as "no limit"; reject non-positive ages.
        if max_age_seconds is not None and max_age_seconds <= 0:
            return None
        return _serializer().loads(token, max_age=max_age_seconds)
    except (BadSignature, SignatureExpired):
        return None
