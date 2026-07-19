"""Tests for tenant-scoped app data routers (conversations, analyses, notes, regions)."""
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
                "sessions, conversations, messages, saved_analyses, "
                "policy_notes, saved_regions, profiles CASCADE"
            )

    asyncio.run(_truncate())
    yield


def test_conversations_crud(api_client):
    create = api_client.post("/api/conversations", json={"title": "First chat"})
    assert create.status_code == 201, create.text
    conv_id = create.json()["id"]

    listed = api_client.get("/api/conversations")
    assert listed.status_code == 200
    assert any(c["id"] == conv_id for c in listed.json())

    msg = api_client.post(
        f"/api/conversations/{conv_id}/messages",
        json={"role": "user", "content": "hello"},
    )
    assert msg.status_code == 201

    messages = api_client.get(f"/api/conversations/{conv_id}/messages")
    assert messages.status_code == 200
    assert len(messages.json()) == 1

    deleted = api_client.delete(f"/api/conversations/{conv_id}")
    assert deleted.status_code == 204


def test_saved_analyses_crud(api_client):
    create = api_client.post(
        "/api/saved-analyses",
        json={"title": "Gini note", "content": "0.57", "dimension": "equity"},
    )
    assert create.status_code == 201, create.text
    analysis_id = create.json()["id"]

    listed = api_client.get("/api/saved-analyses")
    assert listed.status_code == 200
    assert any(a["id"] == analysis_id for a in listed.json())

    deleted = api_client.delete(f"/api/saved-analyses/{analysis_id}")
    assert deleted.status_code == 204


def test_policy_notes_crud(api_client):
    create = api_client.post(
        "/api/policy-notes",
        json={
            "dimension": "equity",
            "stance": "priority",
            "thesis": "Buses need more funding",
        },
    )
    assert create.status_code == 201, create.text
    note_id = create.json()["id"]

    listed = api_client.get("/api/policy-notes")
    assert listed.status_code == 200
    assert any(n["id"] == note_id for n in listed.json())

    deleted = api_client.delete(f"/api/policy-notes/{note_id}")
    assert deleted.status_code == 204


def test_saved_regions_crud(api_client):
    create = api_client.post(
        "/api/saved-regions",
        json={"region_code": "E12000007", "region_name": "London"},
    )
    assert create.status_code == 201, create.text
    region_id = create.json()["id"]

    listed = api_client.get("/api/saved-regions")
    assert listed.status_code == 200
    assert any(r["id"] == region_id for r in listed.json())

    deleted = api_client.delete(f"/api/saved-regions/{region_id}")
    assert deleted.status_code == 204


def test_profile_policy_interests(api_client):
    get_resp = api_client.get("/api/profile")
    assert get_resp.status_code == 200, get_resp.text

    patch = api_client.patch(
        "/api/profile", json={"policy_interests": ["equity", "access"]}
    )
    assert patch.status_code == 200, patch.text
    assert patch.json()["policy_interests"] == ["equity", "access"]
