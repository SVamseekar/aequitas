"""Tests for user/tenant/membership query functions — require a live Postgres."""
import asyncio
import os
import uuid

import pytest

from aequitas.api.auth import db


def _requires_database_url():
    if "DATABASE_URL" not in os.environ:
        pytest.skip("DATABASE_URL not set; requires a live Postgres instance")


@pytest.fixture(autouse=True)
def _clean_tables():
    _requires_database_url()

    async def _truncate():
        pool = await db.get_pool()
        await db.run_migrations(pool)
        async with pool.acquire() as conn:
            await conn.execute(
                "TRUNCATE tenants, users, oauth_identities, memberships CASCADE"
            )

    asyncio.run(_truncate())
    yield


def test_get_or_create_user_creates_new_user_and_identity():
    async def _run():
        pool = await db.get_pool()
        return await db.get_or_create_user(
            pool,
            email="alice@example.com",
            display_name="Alice",
            provider="google",
            provider_subject="google-sub-1",
        )

    user = asyncio.run(_run())
    assert user["email"] == "alice@example.com"
    assert user["display_name"] == "Alice"


def test_get_or_create_user_returns_same_user_on_repeat_login():
    async def _run():
        pool = await db.get_pool()
        first = await db.get_or_create_user(
            pool,
            email="bob@example.com",
            display_name="Bob",
            provider="google",
            provider_subject="google-sub-2",
        )
        second = await db.get_or_create_user(
            pool,
            email="bob@example.com",
            display_name="Bob",
            provider="google",
            provider_subject="google-sub-2",
        )
        return first, second

    first, second = asyncio.run(_run())
    assert first["id"] == second["id"]


def test_create_tenant_and_membership():
    async def _run():
        pool = await db.get_pool()
        user = await db.get_or_create_user(
            pool,
            email="carol@example.com",
            display_name="Carol",
            provider="google",
            provider_subject="google-sub-3",
        )
        tenant = await db.create_tenant(
            pool, name="Carol's Workspace", slug=f"carol-{uuid.uuid4().hex[:8]}"
        )
        membership = await db.create_membership(
            pool, user_id=user["id"], tenant_id=tenant["id"], role="admin"
        )
        return user, tenant, membership

    user, tenant, membership = asyncio.run(_run())
    assert membership["user_id"] == user["id"]
    assert membership["tenant_id"] == tenant["id"]
    assert membership["role"] == "admin"


def test_get_membership_returns_none_when_absent():
    async def _run():
        pool = await db.get_pool()
        return await db.get_membership(
            pool, user_id=str(uuid.uuid4()), tenant_id=str(uuid.uuid4())
        )

    assert asyncio.run(_run()) is None


def test_list_memberships_for_user_includes_tenant_name():
    async def _run():
        pool = await db.get_pool()
        user = await db.get_or_create_user(
            pool,
            email="dave@example.com",
            display_name="Dave",
            provider="google",
            provider_subject="google-sub-4",
        )
        tenant = await db.create_tenant(
            pool, name="Dave Org", slug=f"dave-{uuid.uuid4().hex[:8]}"
        )
        await db.create_membership(
            pool, user_id=user["id"], tenant_id=tenant["id"], role="admin"
        )
        return await db.list_memberships_for_user(pool, user_id=user["id"])

    memberships = asyncio.run(_run())
    assert len(memberships) == 1
    assert memberships[0]["tenant_name"] == "Dave Org"
    assert memberships[0]["role"] == "admin"
