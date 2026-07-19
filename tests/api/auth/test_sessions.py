"""Tests for session cookie signing/verification — no live Postgres required."""
from aequitas.api.auth import sessions


def test_sign_and_unsign_roundtrip(monkeypatch):
    monkeypatch.setenv("SESSION_SECRET", "test-secret")
    token = sessions.sign_session_id("session-id-123")
    result = sessions.unsign_session_id(token)
    assert result == "session-id-123"


def test_unsign_rejects_tampered_token(monkeypatch):
    monkeypatch.setenv("SESSION_SECRET", "test-secret")
    token = sessions.sign_session_id("session-id-123")
    # Corrupt the payload section (before the first dot) so signature fails.
    parts = token.split(".")
    assert len(parts) >= 2
    parts[0] = ("X" if parts[0][0] != "X" else "Y") + parts[0][1:]
    tampered = ".".join(parts)
    assert sessions.unsign_session_id(tampered) is None


def test_unsign_rejects_expired_token(monkeypatch):
    monkeypatch.setenv("SESSION_SECRET", "test-secret")
    token = sessions.sign_session_id("session-id-123")
    assert sessions.unsign_session_id(token, max_age_seconds=0) is None


def test_unsign_rejects_garbage_input(monkeypatch):
    monkeypatch.setenv("SESSION_SECRET", "test-secret")
    assert sessions.unsign_session_id("not-a-valid-token") is None


def test_different_secrets_cannot_cross_verify(monkeypatch):
    monkeypatch.setenv("SESSION_SECRET", "secret-a")
    token = sessions.sign_session_id("session-id-123")
    monkeypatch.setenv("SESSION_SECRET", "secret-b")
    assert sessions.unsign_session_id(token) is None


def test_cookie_constants():
    assert sessions.COOKIE_NAME == "aequitas_session"
    assert sessions.COOKIE_MAX_AGE_SECONDS == 604800
