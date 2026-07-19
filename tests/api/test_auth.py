"""Tests for session-based auth dependencies (replaces Supabase JWT tests)."""
import os

import pytest
from fastapi import HTTPException, Request

from aequitas.api.auth import dependencies


def _make_request(cookie_value: str | None = None) -> Request:
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


@pytest.mark.asyncio
async def test_dev_bypass_returns_admin_session(monkeypatch):
    monkeypatch.setenv("ENVIRONMENT", "development")
    monkeypatch.setenv("DEV_AUTH_BYPASS", "true")
    monkeypatch.delenv("DATABASE_URL", raising=False)
    result = await dependencies.require_session(_make_request(None))
    assert result["role"] == "admin"
    assert result["session_id"] == "dev-session"


@pytest.mark.asyncio
async def test_missing_cookie_without_bypass_raises_401(monkeypatch):
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("DEV_AUTH_BYPASS", "true")  # must be ignored
    with pytest.raises(HTTPException) as exc:
        await dependencies.require_session(_make_request(None))
    assert exc.value.status_code == 401


@pytest.mark.asyncio
async def test_invalid_cookie_raises_401(monkeypatch):
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.delenv("DEV_AUTH_BYPASS", raising=False)
    monkeypatch.setenv("SESSION_SECRET", "test-secret")
    with pytest.raises(HTTPException) as exc:
        await dependencies.require_session(_make_request("not-valid"))
    assert exc.value.status_code == 401
