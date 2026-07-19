"""Tests for tenant-scoped conversations router."""
import os

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
                "sessions, conversations, messages CASCADE"
            )

    asyncio.run(_truncate())
    yield


def test_list_conversations_empty(api_client):
    resp = api_client.get("/api/conversations")
    assert resp.status_code == 200
    assert resp.json() == []


def test_create_and_list_conversation(api_client):
    create = api_client.post("/api/conversations", json={"title": "Hello"})
    assert create.status_code == 201
    listed = api_client.get("/api/conversations")
    assert len(listed.json()) == 1
    assert listed.json()[0]["title"] == "Hello"
