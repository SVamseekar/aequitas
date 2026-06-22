"""Unit tests for verify_supabase_jwt dev-bypass boundary conditions."""
import time

import pytest
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials
from jose import jwt

from aequitas.api.auth import verify_supabase_jwt

SECRET = "test-secret"


def _make_token(secret: str = SECRET, exp_delta: int = 3600, audience: str = "authenticated") -> str:
    payload = {"sub": "real-user", "aud": audience, "exp": int(time.time()) + exp_delta}
    return jwt.encode(payload, secret, algorithm="HS256")


def _creds(token: str) -> HTTPAuthorizationCredentials:
    return HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)


def test_valid_token_returns_payload(monkeypatch):
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("SUPABASE_JWT_SECRET", SECRET)
    monkeypatch.delenv("DEV_AUTH_BYPASS", raising=False)

    payload = verify_supabase_jwt(_creds(_make_token()))
    assert payload["sub"] == "real-user"


def test_invalid_token_with_dev_bypass_still_raises_401(monkeypatch):
    """A *supplied but invalid* token must 401 even when dev bypass is enabled."""
    monkeypatch.setenv("ENVIRONMENT", "development")
    monkeypatch.setenv("DEV_AUTH_BYPASS", "true")
    monkeypatch.setenv("SUPABASE_JWT_SECRET", SECRET)

    bad_token = _make_token(secret="wrong-secret")
    with pytest.raises(HTTPException) as exc_info:
        verify_supabase_jwt(_creds(bad_token))
    assert exc_info.value.status_code == 401


def test_expired_token_with_dev_bypass_still_raises_401(monkeypatch):
    monkeypatch.setenv("ENVIRONMENT", "development")
    monkeypatch.setenv("DEV_AUTH_BYPASS", "true")
    monkeypatch.setenv("SUPABASE_JWT_SECRET", SECRET)

    expired_token = _make_token(exp_delta=-3600)
    with pytest.raises(HTTPException) as exc_info:
        verify_supabase_jwt(_creds(expired_token))
    assert exc_info.value.status_code == 401


def test_missing_credentials_with_dev_bypass_returns_dev_user(monkeypatch):
    monkeypatch.setenv("ENVIRONMENT", "development")
    monkeypatch.setenv("DEV_AUTH_BYPASS", "true")
    monkeypatch.setenv("SUPABASE_JWT_SECRET", SECRET)

    payload = verify_supabase_jwt(None)
    assert payload == {"sub": "dev-user"}


def test_missing_credentials_without_bypass_raises_401(monkeypatch):
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.delenv("DEV_AUTH_BYPASS", raising=False)
    monkeypatch.setenv("SUPABASE_JWT_SECRET", SECRET)

    with pytest.raises(HTTPException) as exc_info:
        verify_supabase_jwt(None)
    assert exc_info.value.status_code == 401


def test_invalid_token_in_production_raises_401(monkeypatch):
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("DEV_AUTH_BYPASS", "true")  # must be ignored in production
    monkeypatch.setenv("SUPABASE_JWT_SECRET", SECRET)

    bad_token = _make_token(secret="wrong-secret")
    with pytest.raises(HTTPException) as exc_info:
        verify_supabase_jwt(_creds(bad_token))
    assert exc_info.value.status_code == 401