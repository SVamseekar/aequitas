"""Tests for the Brevo invite-email client — HTTP calls mocked."""
from unittest.mock import MagicMock, patch

import pytest

from aequitas.api.auth.email import send_invite_email


@pytest.mark.asyncio
async def test_send_invite_email_success(monkeypatch):
    monkeypatch.setenv("BREVO_API_KEY", "test-brevo-key")

    mock_response = MagicMock()
    mock_response.status_code = 201
    with patch("requests.post", return_value=mock_response) as mock_post:
        result = await send_invite_email(
            to_email="invitee@example.com",
            tenant_name="Acme LTA",
            invite_link="https://example.com/invite/abc123",
        )

    assert result is True
    mock_post.assert_called_once()
    call_kwargs = mock_post.call_args.kwargs
    assert call_kwargs["headers"]["api-key"] == "test-brevo-key"
    assert "invitee@example.com" in str(call_kwargs["json"])


@pytest.mark.asyncio
async def test_send_invite_email_returns_false_on_non_2xx(monkeypatch):
    monkeypatch.setenv("BREVO_API_KEY", "test-brevo-key")

    mock_response = MagicMock()
    mock_response.status_code = 400
    mock_response.text = "Bad request"
    with patch("requests.post", return_value=mock_response):
        result = await send_invite_email(
            to_email="invitee@example.com",
            tenant_name="Acme LTA",
            invite_link="https://example.com/invite/abc123",
        )

    assert result is False


@pytest.mark.asyncio
async def test_send_invite_email_returns_false_on_network_error(monkeypatch):
    monkeypatch.setenv("BREVO_API_KEY", "test-brevo-key")

    with patch("requests.post", side_effect=ConnectionError("network down")):
        result = await send_invite_email(
            to_email="invitee@example.com",
            tenant_name="Acme LTA",
            invite_link="https://example.com/invite/abc123",
        )

    assert result is False


@pytest.mark.asyncio
async def test_send_invite_email_returns_false_without_api_key(monkeypatch):
    monkeypatch.delenv("BREVO_API_KEY", raising=False)

    result = await send_invite_email(
        to_email="invitee@example.com",
        tenant_name="Acme LTA",
        invite_link="https://example.com/invite/abc123",
    )

    assert result is False
