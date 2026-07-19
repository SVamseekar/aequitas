"""FastAPI dependencies for session and admin-role enforcement."""
from __future__ import annotations

import os
from datetime import datetime, timezone

from fastapi import Depends, HTTPException, Request

import asyncpg

from aequitas.api.auth import db
from aequitas.api.auth.sessions import COOKIE_NAME, unsign_session_id

_DEV_USER_ID = "00000000-0000-0000-0000-000000000001"
_DEV_TENANT_ID = "00000000-0000-0000-0000-000000000002"


def _is_dev_bypass_allowed() -> bool:
    env = os.getenv("ENVIRONMENT", "development")
    if env == "production":
        return False
    return os.getenv("DEV_AUTH_BYPASS", "").lower() in ("1", "true", "yes")


async def _ensure_dev_tenant(pool: asyncpg.Pool) -> None:
    await db.run_migrations(pool)
    existing = await db._fetch_tenant(pool, tenant_id=_DEV_TENANT_ID)
    if existing is not None:
        return
    async with pool.acquire() as conn:
        await conn.execute(
            """
            INSERT INTO users (id, email, display_name)
            VALUES ($1, $2, $3)
            ON CONFLICT (id) DO NOTHING
            """,
            _DEV_USER_ID,
            "dev@localhost",
            "Dev User",
        )
        await conn.execute(
            """
            INSERT INTO tenants (id, name, slug)
            VALUES ($1, $2, $3)
            ON CONFLICT (id) DO NOTHING
            """,
            _DEV_TENANT_ID,
            "Dev Workspace",
            "dev-workspace",
        )
        await conn.execute(
            """
            INSERT INTO memberships (user_id, tenant_id, role)
            VALUES ($1, $2, $3)
            ON CONFLICT DO NOTHING
            """,
            _DEV_USER_ID,
            _DEV_TENANT_ID,
            "admin",
        )
        await conn.execute(
            """
            INSERT INTO profiles (user_id, display_name)
            VALUES ($1, $2)
            ON CONFLICT (user_id) DO NOTHING
            """,
            _DEV_USER_ID,
            "Dev User",
        )


async def require_session(request: Request) -> dict:
    """Load and validate the session from the signed cookie.

    Raises 401 if the cookie is missing/invalid/expired, the session row
    has expired, or the session's tenant no longer has a membership for
    this user (e.g. they were removed after the session was issued).
    """
    cookie_value = request.cookies.get(COOKIE_NAME)

    if cookie_value is None:
        if _is_dev_bypass_allowed():
            try:
                pool = await db.get_pool()
                await _ensure_dev_tenant(pool)
            except Exception:
                # Still return synthetic session if DB unavailable
                pass
            return {
                "user_id": _DEV_USER_ID,
                "tenant_id": _DEV_TENANT_ID,
                "role": "admin",
                "session_id": "dev-session",
            }
        raise HTTPException(status_code=401, detail="Missing session cookie")

    session_id = unsign_session_id(cookie_value)
    if session_id is None:
        raise HTTPException(status_code=401, detail="Invalid or expired session cookie")

    pool = await db.get_pool()
    session_row = await db.get_session(pool, session_id=session_id)
    if session_row is None:
        raise HTTPException(status_code=401, detail="Session not found")

    expires_at = session_row["expires_at"]
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    if expires_at < datetime.now(timezone.utc):
        raise HTTPException(status_code=401, detail="Session expired")

    membership = await db.get_membership(
        pool,
        user_id=str(session_row["user_id"]),
        tenant_id=str(session_row["tenant_id"]),
    )
    if membership is None:
        raise HTTPException(
            status_code=401,
            detail="No active membership for this session's tenant",
        )

    return {
        "user_id": str(session_row["user_id"]),
        "tenant_id": str(session_row["tenant_id"]),
        "role": membership["role"],
        "session_id": str(session_row["id"]),
    }


async def require_admin(session: dict = Depends(require_session)) -> dict:
    """Wrap require_session, raising 403 if the caller isn't admin in the active tenant."""
    if session["role"] != "admin":
        raise HTTPException(status_code=403, detail="Admin role required")
    return session
