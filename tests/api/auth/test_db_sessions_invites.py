"""Tests for session/invite/audit-log query functions — require a live Postgres."""
import asyncio
import os
import uuid
from datetime import datetime, timedelta, timezone

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
                "TRUNCATE tenants, users, oauth_identities, memberships, "
                "sessions, invites, audit_log CASCADE"
            )

    asyncio.run(_truncate())
    yield


async def _make_user_and_tenant(pool, *, email="test@example.com", subject=None):
    subject = subject or f"sub-{uuid.uuid4().hex[:8]}"
    user = await db.get_or_create_user(
        pool,
        email=email,
        display_name="Test User",
        provider="google",
        provider_subject=subject,
    )
    tenant = await db.create_tenant(
        pool, name="Test Tenant", slug=f"tenant-{uuid.uuid4().hex[:8]}"
    )
    await db.create_membership(
        pool, user_id=user["id"], tenant_id=tenant["id"], role="admin"
    )
    return user, tenant


def test_create_and_get_session():
    async def _run():
        pool = await db.get_pool()
        user, tenant = await _make_user_and_tenant(pool)
        expires_at = datetime.now(timezone.utc) + timedelta(days=7)
        session = await db.create_session(
            pool, user_id=user["id"], tenant_id=tenant["id"], expires_at=expires_at
        )
        fetched = await db.get_session(pool, session_id=str(session["id"]))
        return session, fetched

    session, fetched = asyncio.run(_run())
    assert fetched is not None
    assert fetched["id"] == session["id"]


def test_get_session_returns_none_for_unknown_id():
    async def _run():
        pool = await db.get_pool()
        return await db.get_session(pool, session_id=str(uuid.uuid4()))

    assert asyncio.run(_run()) is None


def test_update_session_tenant_switches_active_tenant():
    async def _run():
        pool = await db.get_pool()
        user, tenant_a = await _make_user_and_tenant(pool)
        tenant_b = await db.create_tenant(
            pool, name="Second Tenant", slug=f"tenant-b-{uuid.uuid4().hex[:8]}"
        )
        await db.create_membership(
            pool, user_id=user["id"], tenant_id=tenant_b["id"], role="member"
        )
        expires_at = datetime.now(timezone.utc) + timedelta(days=7)
        session = await db.create_session(
            pool, user_id=user["id"], tenant_id=tenant_a["id"], expires_at=expires_at
        )
        updated = await db.update_session_tenant(
            pool, session_id=str(session["id"]), tenant_id=tenant_b["id"]
        )
        return updated, tenant_b

    updated, tenant_b = asyncio.run(_run())
    assert updated["tenant_id"] == tenant_b["id"]


def test_delete_session_removes_it():
    async def _run():
        pool = await db.get_pool()
        user, tenant = await _make_user_and_tenant(pool)
        expires_at = datetime.now(timezone.utc) + timedelta(days=7)
        session = await db.create_session(
            pool, user_id=user["id"], tenant_id=tenant["id"], expires_at=expires_at
        )
        await db.delete_session(pool, session_id=str(session["id"]))
        return await db.get_session(pool, session_id=str(session["id"]))

    assert asyncio.run(_run()) is None


def test_create_invite_and_get_by_token():
    async def _run():
        pool = await db.get_pool()
        _, tenant = await _make_user_and_tenant(pool)
        expires_at = datetime.now(timezone.utc) + timedelta(days=3)
        invite = await db.create_invite(
            pool,
            tenant_id=tenant["id"],
            email="invitee@example.com",
            role="member",
            token="tok-abc123",
            expires_at=expires_at,
        )
        fetched = await db.get_invite_by_token(pool, token="tok-abc123")
        return invite, fetched

    invite, fetched = asyncio.run(_run())
    assert fetched is not None
    assert fetched["id"] == invite["id"]
    assert fetched["accepted_at"] is None


def test_accept_invite_sets_accepted_at():
    async def _run():
        pool = await db.get_pool()
        _, tenant = await _make_user_and_tenant(pool)
        expires_at = datetime.now(timezone.utc) + timedelta(days=3)
        await db.create_invite(
            pool,
            tenant_id=tenant["id"],
            email="invitee2@example.com",
            role="member",
            token="tok-def456",
            expires_at=expires_at,
        )
        return await db.accept_invite(pool, token="tok-def456")

    accepted = asyncio.run(_run())
    assert accepted is not None
    assert accepted["accepted_at"] is not None


def test_accept_invite_fails_on_already_accepted_token():
    async def _run():
        pool = await db.get_pool()
        _, tenant = await _make_user_and_tenant(pool)
        expires_at = datetime.now(timezone.utc) + timedelta(days=3)
        await db.create_invite(
            pool,
            tenant_id=tenant["id"],
            email="invitee3@example.com",
            role="member",
            token="tok-ghi789",
            expires_at=expires_at,
        )
        first = await db.accept_invite(pool, token="tok-ghi789")
        second = await db.accept_invite(pool, token="tok-ghi789")
        return first, second

    first, second = asyncio.run(_run())
    assert first is not None
    assert second is None


def test_accept_invite_fails_on_expired_token():
    async def _run():
        pool = await db.get_pool()
        _, tenant = await _make_user_and_tenant(pool)
        expires_at = datetime.now(timezone.utc) - timedelta(days=1)
        await db.create_invite(
            pool,
            tenant_id=tenant["id"],
            email="invitee4@example.com",
            role="member",
            token="tok-expired",
            expires_at=expires_at,
        )
        return await db.accept_invite(pool, token="tok-expired")

    assert asyncio.run(_run()) is None


def test_remove_membership():
    async def _run():
        pool = await db.get_pool()
        user, tenant = await _make_user_and_tenant(pool)
        await db.remove_membership(pool, user_id=user["id"], tenant_id=tenant["id"])
        return await db.get_membership(
            pool, user_id=user["id"], tenant_id=tenant["id"]
        )

    assert asyncio.run(_run()) is None


def test_update_membership_role():
    async def _run():
        pool = await db.get_pool()
        user, tenant = await _make_user_and_tenant(pool)
        return await db.update_membership_role(
            pool, user_id=user["id"], tenant_id=tenant["id"], role="member"
        )

    updated = asyncio.run(_run())
    assert updated["role"] == "member"


def test_write_and_list_audit_log():
    async def _run():
        pool = await db.get_pool()
        user, tenant = await _make_user_and_tenant(pool)
        await db.write_audit_log(
            pool,
            tenant_id=tenant["id"],
            actor_user_id=user["id"],
            action="invite_created",
            target_user_id=None,
            metadata={"invited_email": "x@example.com", "role": "member"},
        )
        return await db.list_audit_log(pool, tenant_id=tenant["id"])

    entries = asyncio.run(_run())
    assert len(entries) == 1
    assert entries[0]["action"] == "invite_created"
    assert entries[0]["metadata"]["invited_email"] == "x@example.com"


def test_list_audit_log_newest_first():
    async def _run():
        pool = await db.get_pool()
        user, tenant = await _make_user_and_tenant(pool)
        await db.write_audit_log(
            pool,
            tenant_id=tenant["id"],
            actor_user_id=user["id"],
            action="invite_created",
            target_user_id=None,
            metadata={"seq": 1},
        )
        await db.write_audit_log(
            pool,
            tenant_id=tenant["id"],
            actor_user_id=user["id"],
            action="invite_created",
            target_user_id=None,
            metadata={"seq": 2},
        )
        return await db.list_audit_log(pool, tenant_id=tenant["id"])

    entries = asyncio.run(_run())
    assert entries[0]["metadata"]["seq"] == 2
    assert entries[1]["metadata"]["seq"] == 1
