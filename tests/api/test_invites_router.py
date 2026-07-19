"""Tests for invite creation and lookup routes."""
import os
from unittest.mock import patch

import pytest


def _requires_database_url():
    if "DATABASE_URL" not in os.environ:
        pytest.skip("DATABASE_URL not set; requires a live Postgres instance")


@pytest.fixture(autouse=True)
def _clean_tables():
    _requires_database_url()
    import asyncio

    from aequitas.api.auth import db

    async def _truncate():
        pool = await db.get_pool()
        await db.run_migrations(pool)
        async with pool.acquire() as conn:
            await conn.execute(
                "TRUNCATE tenants, users, oauth_identities, memberships, "
                "sessions, invites, audit_log CASCADE"
            )

    asyncio.run(_truncate())
    yield


def test_create_invite_returns_token_and_link(api_client):
    with patch("aequitas.api.routers.auth.send_invite_email", return_value=True):
        resp = api_client.post(
            "/api/tenants/00000000-0000-0000-0000-000000000002/invites",
            json={"email": "newmember@example.com", "role": "member"},
        )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert "token" in body
    assert "link" in body


def test_create_invite_writes_audit_log_entry(api_client):
    with patch("aequitas.api.routers.auth.send_invite_email", return_value=True):
        api_client.post(
            "/api/tenants/00000000-0000-0000-0000-000000000002/invites",
            json={"email": "another@example.com", "role": "member"},
        )
    resp = api_client.get(
        "/api/tenants/00000000-0000-0000-0000-000000000002/audit-log"
    )
    assert resp.status_code == 200
    entries = resp.json()
    assert any(e["action"] == "invite_created" for e in entries)


def test_create_invite_succeeds_even_if_email_fails(api_client):
    with patch("aequitas.api.routers.auth.send_invite_email", return_value=False):
        resp = api_client.post(
            "/api/tenants/00000000-0000-0000-0000-000000000002/invites",
            json={"email": "thirdmember@example.com", "role": "member"},
        )
    assert resp.status_code == 200
    assert "token" in resp.json()


def test_get_invite_by_token_returns_tenant_name(api_client):
    with patch("aequitas.api.routers.auth.send_invite_email", return_value=True):
        create_resp = api_client.post(
            "/api/tenants/00000000-0000-0000-0000-000000000002/invites",
            json={"email": "lookup@example.com", "role": "member"},
        )
    token = create_resp.json()["token"]
    resp = api_client.get(f"/api/invites/{token}")
    assert resp.status_code == 200
    assert "tenant_name" in resp.json()
    assert resp.json()["role"] == "member"


def test_get_invite_by_unknown_token_returns_404(api_client):
    resp = api_client.get("/api/invites/nonexistent-token")
    assert resp.status_code == 404
