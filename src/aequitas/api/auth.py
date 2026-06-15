"""Supabase JWT validation middleware."""
from __future__ import annotations

import os

from fastapi import HTTPException, Security
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from loguru import logger

from aequitas.api.config import ApiConfig

_bearer = HTTPBearer(auto_error=False)


def _is_dev_bypass_allowed() -> bool:
    """Check if dev auth bypass is permitted (never in production)."""
    env = os.getenv("ENVIRONMENT", "development")
    if env == "production":
        return False
    return os.getenv("DEV_AUTH_BYPASS", "").lower() in ("1", "true", "yes")


def verify_supabase_jwt(
    credentials: HTTPAuthorizationCredentials | None = Security(_bearer),
) -> dict:
    """Validate Supabase JWT and return decoded payload with user sub.

    Dev mode: when ENVIRONMENT is not production AND DEV_AUTH_BYPASS=true, a
    placeholder dev-user payload is returned for missing credentials, an
    unconfigured supabase_jwt_secret, or an invalid/expired token — not just
    when no secret is configured. DEV_AUTH_BYPASS must never be set to true
    in production.
    """
    cfg = ApiConfig()

    if _is_dev_bypass_allowed():
        if not credentials:
            logger.info("Using dev bypass: missing authorization token")
            return {"sub": "dev-user"}

    if not cfg.supabase_jwt_secret:
        if _is_dev_bypass_allowed():
            logger.warning("SUPABASE_JWT_SECRET not set — JWT validation DISABLED (dev bypass)")
            return {"sub": "dev-user"}
        raise HTTPException(
            status_code=500,
            detail="Authentication not configured. Set SUPABASE_JWT_SECRET.",
        )

    if not credentials:
        raise HTTPException(status_code=401, detail="Missing authorization token")

    try:
        payload = jwt.decode(
            credentials.credentials,
            cfg.supabase_jwt_secret,
            algorithms=["HS256"],
            audience="authenticated",
        )
        return payload
    except JWTError as exc:
        if _is_dev_bypass_allowed():
            logger.warning(f"Invalid token ({exc}) — using dev bypass fallback")
            return {"sub": "dev-user"}
        raise HTTPException(status_code=401, detail=f"Invalid token: {exc}") from exc
