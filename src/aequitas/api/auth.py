"""Supabase JWT validation middleware."""
from __future__ import annotations

from fastapi import HTTPException, Security
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from loguru import logger

from aequitas.api.config import ApiConfig

_bearer = HTTPBearer(auto_error=False)


def verify_supabase_jwt(
    credentials: HTTPAuthorizationCredentials | None = Security(_bearer),
) -> dict:
    """Validate Supabase JWT and return decoded payload with user sub.

    Dev mode: if supabase_jwt_secret is empty, any token (or none) is accepted
    and a placeholder dev-user payload is returned.
    """
    cfg = ApiConfig()

    if not cfg.supabase_jwt_secret:
        logger.warning("SUPABASE_JWT_SECRET not set — JWT validation DISABLED (dev mode)")
        return {"sub": "dev-user"}

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
        raise HTTPException(status_code=401, detail=f"Invalid token: {exc}") from exc
