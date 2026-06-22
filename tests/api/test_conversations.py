"""Tests for conversations router Supabase client scoping."""
from unittest.mock import MagicMock, patch

from aequitas.api.routers.conversations import _get_supabase


def test_get_supabase_uses_anon_key_and_forwards_user_token(monkeypatch):
    monkeypatch.setenv("SUPABASE_URL", "https://example.supabase.co")
    monkeypatch.setenv("SUPABASE_ANON_KEY", "anon-key-value")
    monkeypatch.setenv("SUPABASE_SERVICE_ROLE_KEY", "service-role-key-value")

    mock_client = MagicMock()
    with patch("supabase.create_client", return_value=mock_client) as mock_create:
        result = _get_supabase(access_token="user-jwt-token")

    # Must be created with the anon key, never the service-role key, when a
    # user token is available — RLS only applies to the anon/authenticated role.
    mock_create.assert_called_once_with("https://example.supabase.co", "anon-key-value")
    mock_client.postgrest.auth.assert_called_once_with("user-jwt-token")
    assert result is mock_client


def test_get_supabase_falls_back_to_service_role_without_token(monkeypatch):
    """Dev-bypass mode has no raw JWT — fall back to service role so dev flows keep working."""
    monkeypatch.setenv("SUPABASE_URL", "https://example.supabase.co")
    monkeypatch.setenv("SUPABASE_ANON_KEY", "anon-key-value")
    monkeypatch.setenv("SUPABASE_SERVICE_ROLE_KEY", "service-role-key-value")

    mock_client = MagicMock()
    with patch("supabase.create_client", return_value=mock_client) as mock_create:
        _get_supabase(access_token=None)

    mock_create.assert_called_once_with("https://example.supabase.co", "service-role-key-value")