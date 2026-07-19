"""Tests for the asyncpg pool and migration runner — require a live Postgres."""
import asyncio
import os

import pytest

from aequitas.api.auth import db


def _requires_database_url():
    if "DATABASE_URL" not in os.environ:
        pytest.skip("DATABASE_URL not set; requires a live Postgres instance")


def test_get_pool_returns_pool():
    _requires_database_url()

    async def _run():
        pool = await db.get_pool()
        assert pool is not None
        return pool

    asyncio.run(_run())


def test_run_migrations_creates_tenants_table():
    _requires_database_url()

    async def _run():
        pool = await db.get_pool()
        await db.run_migrations(pool)
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                "select table_name from information_schema.tables where table_name = 'tenants'"
            )
            return row

    row = asyncio.run(_run())
    assert row is not None


def test_run_migrations_creates_all_expected_tables():
    _requires_database_url()

    expected = {
        "tenants",
        "users",
        "oauth_identities",
        "memberships",
        "sessions",
        "invites",
        "audit_log",
        "profiles",
        "conversations",
        "messages",
        "saved_analyses",
        "policy_notes",
        "saved_regions",
    }

    async def _run():
        pool = await db.get_pool()
        await db.run_migrations(pool)
        async with pool.acquire() as conn:
            rows = await conn.fetch(
                "select table_name from information_schema.tables where table_schema = 'public'"
            )
            return {r["table_name"] for r in rows}

    actual = asyncio.run(_run())
    assert expected.issubset(actual)
