"""Tests for require_session / require_admin dependencies."""
import asyncio
import os
import uuid
from datetime import datetime, timedelta, timezone

import pytest
from fastapi import HTTPException, Request

from aequitas.api.auth import db, dependencies


def _requires_database_url():
    if "DATABASE_URL" not in os.environ:
        pytest.skip("DATABASE_URL not set; requires a live Postgres instance")


@pytest.fixture(autouse=True)
def _clean_tables():
    _requires_database_url()

    async def _truncate():
        pool = await db.get_pool()
        await db.run_migrations(pool)
        async with pool.acquire() as conn:
            await conn.execute(
                "TRUNCATE tenants, users, oauth_identities, memberships, sessions CASCADE"
            )

    asyncio.run(_truncate())
    yield


def _make_request(cookie_value: str | None) -> Request:
    headers = []
    if cookie_value is not None:
        headers.append((b"cookie", f"aequitas_session={cookie_value}".encode()))
    scope = {
        "type": "http",
        "headers": headers,
        "method": "GET",
        "path": "/",
        "query_string": b"",
    }
    return Request(scope)


async def _make_session():
    pool = await db.get_pool()
    user = await db.get_or_create_user(
        pool,
        email="test@example.com",
        display_name="Test",
        provider="google",
        provider_subject=f"sub-{uuid.uuid4().hex[:8]}",
    )
    tenant = await db.create_tenant(
        pool, name="Test Tenant", slug=f"tenant-{uuid.uuid4().hex[:8]}"
    )
    await db.create_membership(
        pool, user_id=user["id"], tenant_id=tenant["id"], role="admin"
    )
    expires_at = datetime.now(timezone.utc) + timedelta(days=7)
    session = await db.create_session(
        pool, user_id=user["id"], tenant_id=tenant["id"], expires_at=expires_at
    )
    return user, tenant, session


def test_require_session_valid_cookie_passes(monkeypatch):
    monkeypatch.setenv("SESSION_SECRET", "test-secret")
    monkeypatch.delenv("DEV_AUTH_BYPASS", raising=False)

    async def _run():
        user, tenant, session = await _make_session()
        from aequitas.api.auth.sessions import sign_session_id

        token = sign_session_id(str(session["id"]))
        request = _make_request(token)
        result = await dependencies.require_session(request)
        return result, user, tenant

    result, user, tenant = asyncio.run(_run())
    assert result["user_id"] == str(user["id"])
    assert result["tenant_id"] == str(tenant["id"])
    assert result["role"] == "admin"


def test_require_session_missing_cookie_raises_401(monkeypatch):
    monkeypatch.setenv("SESSION_SECRET", "test-secret")
    monkeypatch.delenv("DEV_AUTH_BYPASS", raising=False)
    monkeypatch.setenv("ENVIRONMENT", "production")

    async def _run():
        request = _make_request(None)
        await dependencies.require_session(request)

    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(_run())
    assert exc_info.value.status_code == 401


def test_require_session_invalid_cookie_raises_401(monkeypatch):
    monkeypatch.setenv("SESSION_SECRET", "test-secret")
    monkeypatch.delenv("DEV_AUTH_BYPASS", raising=False)
    monkeypatch.setenv("ENVIRONMENT", "production")

    async def _run():
        request = _make_request("garbage-token")
        await dependencies.require_session(request)

    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(_run())
    assert exc_info.value.status_code == 401


def test_require_session_expired_session_row_raises_401(monkeypatch):
    monkeypatch.setenv("SESSION_SECRET", "test-secret")
    monkeypatch.delenv("DEV_AUTH_BYPASS", raising=False)
    monkeypatch.setenv("ENVIRONMENT", "production")

    async def _run():
        pool = await db.get_pool()
        user = await db.get_or_create_user(
            pool,
            email="expired@example.com",
            display_name="Expired",
            provider="google",
            provider_subject=f"sub-{uuid.uuid4().hex[:8]}",
        )
        tenant = await db.create_tenant(
            pool, name="Expired Tenant", slug=f"tenant-{uuid.uuid4().hex[:8]}"
        )
        await db.create_membership(
            pool, user_id=user["id"], tenant_id=tenant["id"], role="admin"
        )
        expires_at = datetime.now(timezone.utc) - timedelta(days=1)
        session = await db.create_session(
            pool, user_id=user["id"], tenant_id=tenant["id"], expires_at=expires_at
        )

        from aequitas.api.auth.sessions import sign_session_id

        token = sign_session_id(str(session["id"]))
        request = _make_request(token)
        await dependencies.require_session(request)

    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(_run())
    assert exc_info.value.status_code == 401


def test_require_session_dev_bypass_without_cookie(monkeypatch):
    monkeypatch.setenv("SESSION_SECRET", "test-secret")
    monkeypatch.setenv("ENVIRONMENT", "development")
    monkeypatch.setenv("DEV_AUTH_BYPASS", "true")

    async def _run():
        request = _make_request(None)
        return await dependencies.require_session(request)

    result = asyncio.run(_run())
    assert result["role"] == "admin"
    assert result["session_id"] == "dev-session"


def test_require_session_dev_bypass_never_fires_in_production(monkeypatch):
    monkeypatch.setenv("SESSION_SECRET", "test-secret")
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("DEV_AUTH_BYPASS", "true")  # must be ignored

    async def _run():
        request = _make_request(None)
        await dependencies.require_session(request)

    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(_run())
    assert exc_info.value.status_code == 401


def test_require_admin_passes_for_admin_role(monkeypatch):
    monkeypatch.setenv("SESSION_SECRET", "test-secret")

    async def _run():
        user, tenant, session = await _make_session()
        session_dict = {
            "user_id": str(user["id"]),
            "tenant_id": str(tenant["id"]),
            "role": "admin",
            "session_id": str(session["id"]),
        }
        return await dependencies.require_admin(session_dict)

    result = asyncio.run(_run())
    assert result["role"] == "admin"


def test_require_admin_raises_403_for_member_role():
    session_dict = {
        "user_id": str(uuid.uuid4()),
        "tenant_id": str(uuid.uuid4()),
        "role": "member",
        "session_id": "some-session",
    }

    async def _run():
        await dependencies.require_admin(session_dict)

    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(_run())
    assert exc_info.value.status_code == 403
