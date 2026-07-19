"""Cross-tenant isolation — highest-priority Plan 04 guarantee."""
from __future__ import annotations

import asyncio
import os
import uuid
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

from aequitas.api.auth import db
from aequitas.api.auth.sessions import sign_session_id
from aequitas.api.app import create_app


def _requires_database_url():
    if "DATABASE_URL" not in os.environ:
        pytest.skip("DATABASE_URL not set")


@pytest.fixture
def two_tenants(monkeypatch):
    """Seed tenant A and B with separate sessions; return (client_a, client_b, ids)."""
    _requires_database_url()
    monkeypatch.setenv("SESSION_SECRET", "isolation-secret")
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.delenv("DEV_AUTH_BYPASS", raising=False)

    async def _seed():
        pool = await db.get_pool()
        await db.run_migrations(pool)
        async with pool.acquire() as conn:
            await conn.execute(
                "TRUNCATE tenants, users, oauth_identities, memberships, sessions, "
                "conversations, messages, saved_analyses, policy_notes, saved_regions CASCADE"
            )

        user_a = await db.get_or_create_user(
            pool,
            email="a@iso.test",
            display_name="A",
            provider="google",
            provider_subject=f"sub-a-{uuid.uuid4().hex[:8]}",
        )
        user_b = await db.get_or_create_user(
            pool,
            email="b@iso.test",
            display_name="B",
            provider="google",
            provider_subject=f"sub-b-{uuid.uuid4().hex[:8]}",
        )
        tenant_a = await db.create_tenant(
            pool, name="Tenant A", slug=f"ta-{uuid.uuid4().hex[:8]}"
        )
        tenant_b = await db.create_tenant(
            pool, name="Tenant B", slug=f"tb-{uuid.uuid4().hex[:8]}"
        )
        await db.create_membership(
            pool, user_id=user_a["id"], tenant_id=tenant_a["id"], role="admin"
        )
        await db.create_membership(
            pool, user_id=user_b["id"], tenant_id=tenant_b["id"], role="admin"
        )
        expires = datetime.now(timezone.utc) + timedelta(days=1)
        sess_a = await db.create_session(
            pool,
            user_id=user_a["id"],
            tenant_id=tenant_a["id"],
            expires_at=expires,
        )
        sess_b = await db.create_session(
            pool,
            user_id=user_b["id"],
            tenant_id=tenant_b["id"],
            expires_at=expires,
        )
        return user_a, user_b, tenant_a, tenant_b, sess_a, sess_b

    user_a, user_b, tenant_a, tenant_b, sess_a, sess_b = asyncio.run(_seed())

    app = create_app()
    client_a = TestClient(app)
    client_b = TestClient(app)
    client_a.cookies.set("aequitas_session", sign_session_id(str(sess_a["id"])))
    client_b.cookies.set("aequitas_session", sign_session_id(str(sess_b["id"])))
    return {
        "a": client_a,
        "b": client_b,
        "tenant_a": str(tenant_a["id"]),
        "tenant_b": str(tenant_b["id"]),
    }


def test_conversations_not_visible_across_tenants(two_tenants):
    t = two_tenants
    created = t["a"].post("/api/conversations", json={"title": "secret A"})
    assert created.status_code == 201
    cid = created.json()["id"]

    # B cannot list A's conversation
    listed_b = t["b"].get("/api/conversations")
    assert listed_b.status_code == 200
    assert all(c["id"] != cid for c in listed_b.json())

    # B cannot read messages
    msgs = t["b"].get(f"/api/conversations/{cid}/messages")
    assert msgs.status_code == 404

    # B cannot delete
    deleted = t["b"].delete(f"/api/conversations/{cid}")
    assert deleted.status_code == 404

    # A still has it
    listed_a = t["a"].get("/api/conversations")
    assert any(c["id"] == cid for c in listed_a.json())


def test_saved_analyses_not_visible_across_tenants(two_tenants):
    t = two_tenants
    created = t["a"].post(
        "/api/saved-analyses",
        json={"title": "secret", "content": "private", "dimension": "equity"},
    )
    assert created.status_code == 201
    aid = created.json()["id"]
    listed_b = t["b"].get("/api/saved-analyses")
    assert listed_b.status_code == 200
    assert all(x["id"] != aid for x in listed_b.json())


def test_policy_notes_not_visible_across_tenants(two_tenants):
    t = two_tenants
    created = t["a"].post(
        "/api/policy-notes",
        json={"dimension": "equity", "stance": "priority", "thesis": "private"},
    )
    assert created.status_code == 201
    nid = created.json()["id"]
    listed_b = t["b"].get("/api/policy-notes")
    assert all(x["id"] != nid for x in listed_b.json())


def test_saved_regions_not_visible_across_tenants(two_tenants):
    t = two_tenants
    created = t["a"].post(
        "/api/saved-regions",
        json={"region_code": "E12000001", "region_name": "North East"},
    )
    assert created.status_code == 201
    rid = created.json()["id"]
    listed_b = t["b"].get("/api/saved-regions")
    assert all(x["id"] != rid for x in listed_b.json())
