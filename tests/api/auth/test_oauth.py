"""Tests for the Google OAuth client registration."""
from aequitas.api.auth.oauth import get_google_oauth_client, reset_oauth_client_for_tests


def test_get_google_oauth_client_registers_google(monkeypatch):
    reset_oauth_client_for_tests()
    monkeypatch.setenv("GOOGLE_CLIENT_ID", "test-client-id")
    monkeypatch.setenv("GOOGLE_CLIENT_SECRET", "test-client-secret")

    client = get_google_oauth_client()

    assert client.google is not None
    assert client.google.client_id == "test-client-id"


def test_get_google_oauth_client_is_cached(monkeypatch):
    reset_oauth_client_for_tests()
    monkeypatch.setenv("GOOGLE_CLIENT_ID", "test-client-id")
    monkeypatch.setenv("GOOGLE_CLIENT_SECRET", "test-client-secret")

    first = get_google_oauth_client()
    second = get_google_oauth_client()

    assert first is second
