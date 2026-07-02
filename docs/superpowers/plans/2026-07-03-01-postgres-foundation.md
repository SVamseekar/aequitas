# Postgres Foundation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Stand up the new self-hosted Postgres database and its schema (`tenants`, `users`, `oauth_identities`, `memberships`, `sessions`, `invites`, `audit_log`, plus tenant-scoped `conversations`/`messages`/`saved_analyses`/`policy_notes`/`saved_regions` and a properly-keyed `profiles`), an asyncpg connection pool, and typed query functions (`db.py`) covering full CRUD for every table — with no HTTP routes wired up yet. This is the dependency every later plan (`02` OAuth/sessions, `03` tenants/invites/audit, `04` router migration) is built on.

**Architecture:** New `src/aequitas/api/auth/` package, following the reference project WorkforceGuard AI's pattern (`/Users/souravamseekarmarti/Projects/WorkforceGuard-AI/dashboard/backend/auth/db.py` + `schema.sql`) but extended with Aequitas's additional tables (`invites`, `audit_log`, the five tenant-scoped app tables, `profiles`). One `schema.sql` file (idempotent `CREATE TABLE IF NOT EXISTS`), one `db.py` module with an `asyncpg.Pool` singleton plus one function per query. `ApiConfig` gains the new env-backed fields this package needs. No FastAPI routes or dependencies are added in this plan — that's Plans 02/03.

**Tech Stack:** `asyncpg` (new dependency), Postgres (local dev, `postgresql://localhost/aequitas`), `uv`, `pytest` (tests skip when no live Postgres `DATABASE_URL` is set, matching WorkforceGuard's `test_auth_db.py` pattern).

## Global Constraints

- Backend test commands must always be prefixed `uv run` (bare `python -m pytest` fails — `loguru` and other deps aren't on the bare interpreter's path).
- All work happens on `feature/enterprise-oauth-tenancy` (created in Plan 00) — confirm this is the checked-out branch before starting.
- New Postgres database, local dev connection string: `postgresql://localhost/aequitas`, owned entirely by the application — no Supabase involvement of any kind in this schema.
- Existing application tables (`conversations`, `messages`, `saved_analyses`, `policy_notes`, `saved_regions`) are **recreated fresh** in this new database with `tenant_id UUID NOT NULL REFERENCES tenants(id)` replacing `user_id`-as-scoping-key. `user_id` is retained on each row for display (who created it), but access control filters on `tenant_id`. No RLS — every query filters by `tenant_id` explicitly in application code.
- `profiles` stays `user_id`-scoped (per-person, not shared), keyed on the new `users.id`.
- No data migration from Supabase — existing local Supabase data is discarded (confirmed no real users).
- Tests against a live Postgres database skip cleanly (not fail/error) when `DATABASE_URL` is unset, per WorkforceGuard's `test_auth_db.py` pattern — this plan's tests must run in CI without a live Postgres instance available, and also run fully when a developer has one locally.
- Exact new `pyproject.toml` dependency: `"asyncpg>=0.29.0"`.

---

### Task 1: Add `asyncpg` dependency and scaffold the `auth` package

**Files:**
- Modify: `pyproject.toml`
- Create: `src/aequitas/api/auth/__init__.py`

**Interfaces:**
- Consumes: nothing
- Produces: an importable `aequitas.api.auth` package that Task 2 (`schema.sql`) and Task 3 (`db.py`) add to; `asyncpg` importable in the environment

- [ ] **Step 1: Add `asyncpg` to `pyproject.toml` dependencies**

In `pyproject.toml`, add `"asyncpg>=0.29.0",` to the `dependencies` list (after `"reportlab>=4.5.1",` and before `"supabase>=2.0.0",` — `supabase` itself is removed later in Plan 07's cleanup, not this plan).

- [ ] **Step 2: Sync dependencies**

Run: `uv sync --all-extras`
Expected: completes with `asyncpg` installed; no errors

- [ ] **Step 3: Create the package directory**

Create `src/aequitas/api/auth/__init__.py`:

```python
"""Google OAuth + multi-tenant auth package — replaces the old Supabase-JWT auth.py."""
```

- [ ] **Step 4: Verify the package imports**

Run: `uv run python -c "import aequitas.api.auth; print('ok')"`
Expected: prints `ok`

- [ ] **Step 5: Commit**

```bash
git add pyproject.toml uv.lock src/aequitas/api/auth/__init__.py
git commit -m "Add asyncpg dependency and scaffold auth package"
```

---

### Task 2: Write the full Postgres schema

**Files:**
- Create: `src/aequitas/api/auth/schema.sql`

**Interfaces:**
- Consumes: nothing
- Produces: a `schema.sql` file that Task 3's `run_migrations()` executes; defines every table Tasks 4-6's query functions and every later plan depend on

- [ ] **Step 1: Write `schema.sql`**

Create `src/aequitas/api/auth/schema.sql`:

```sql
CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE IF NOT EXISTS tenants (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL,
    slug TEXT NOT NULL UNIQUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email TEXT NOT NULL UNIQUE,
    display_name TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS oauth_identities (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    provider TEXT NOT NULL CHECK (provider IN ('google')),
    provider_subject TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (provider, provider_subject)
);

CREATE TABLE IF NOT EXISTS memberships (
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    role TEXT NOT NULL CHECK (role IN ('admin', 'member')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (user_id, tenant_id)
);

CREATE TABLE IF NOT EXISTS sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    expires_at TIMESTAMPTZ NOT NULL
);

CREATE TABLE IF NOT EXISTS invites (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    email TEXT NOT NULL,
    role TEXT NOT NULL CHECK (role IN ('admin', 'member')),
    token TEXT NOT NULL UNIQUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    expires_at TIMESTAMPTZ NOT NULL,
    accepted_at TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS audit_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    actor_user_id UUID NOT NULL REFERENCES users(id),
    action TEXT NOT NULL CHECK (action IN ('invite_created', 'invite_accepted', 'member_removed', 'role_changed')),
    target_user_id UUID REFERENCES users(id),
    metadata JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS profiles (
    user_id UUID PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
    display_name TEXT,
    bio TEXT,
    policy_interests TEXT[] NOT NULL DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS conversations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES users(id),
    title TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    conversation_id UUID NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES users(id),
    role TEXT NOT NULL CHECK (role IN ('user', 'assistant')),
    content TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS saved_analyses (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES users(id),
    title TEXT NOT NULL,
    content TEXT NOT NULL,
    section_id TEXT,
    dimension TEXT,
    tags TEXT[] NOT NULL DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS policy_notes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES users(id),
    dimension TEXT NOT NULL,
    region TEXT NOT NULL DEFAULT 'all',
    stance TEXT CHECK (stance IN ('priority', 'monitor', 'adequate')),
    thesis TEXT NOT NULL,
    critique TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS saved_regions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES users(id),
    region_code TEXT NOT NULL,
    region_name TEXT NOT NULL,
    notes TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_memberships_tenant ON memberships(tenant_id);
CREATE INDEX IF NOT EXISTS idx_sessions_expires ON sessions(expires_at);
CREATE INDEX IF NOT EXISTS idx_invites_token ON invites(token);
CREATE INDEX IF NOT EXISTS idx_audit_log_tenant ON audit_log(tenant_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_conversations_tenant ON conversations(tenant_id);
CREATE INDEX IF NOT EXISTS idx_messages_conversation ON messages(conversation_id);
CREATE INDEX IF NOT EXISTS idx_saved_analyses_tenant ON saved_analyses(tenant_id);
CREATE INDEX IF NOT EXISTS idx_policy_notes_tenant ON policy_notes(tenant_id);
CREATE INDEX IF NOT EXISTS idx_saved_regions_tenant ON saved_regions(tenant_id);
```

Note: `conversations`, `messages`, `saved_analyses`, `policy_notes`, `saved_regions`, and `profiles` column shapes above are copied 1:1 from the existing Supabase schema (`supabase/migrations/001_initial.sql`), with `user_id UUID REFERENCES auth.users(id)` replaced by `tenant_id UUID NOT NULL REFERENCES tenants(id)` as the scoping column (per the spec's Data model section) and `user_id` retained as a plain FK to the new `users` table. This means Plan 04's rewritten routers can reuse the exact field names `db.ts` and the old Supabase routers already used (`section_id`, `dimension`, `tags`, `stance`, `thesis`, `critique`, `region_code`, `region_name`, `notes`, `policy_interests`) — no reshaping needed at the API boundary.

- [ ] **Step 2: Commit**

```bash
git add src/aequitas/api/auth/schema.sql
git commit -m "Add Postgres schema for multi-tenant auth and tenant-scoped app tables"
```

---

### Task 3: `db.py` — connection pool and migration runner

**Files:**
- Create: `src/aequitas/api/auth/db.py`
- Test: `tests/api/auth/test_db_pool.py`

**Interfaces:**
- Consumes: `DATABASE_URL` env var; `schema.sql` from Task 2
- Produces: `get_pool() -> asyncpg.Pool` (async, singleton, one pool per running event loop), `run_migrations(pool: asyncpg.Pool) -> None` — both consumed by every later task in this plan and by Plans 02/03's route handlers

- [ ] **Step 1: Write the failing test**

Create `tests/api/auth/__init__.py` (empty file) and `tests/api/auth/test_db_pool.py`:

```python
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
        "tenants", "users", "oauth_identities", "memberships", "sessions",
        "invites", "audit_log", "profiles", "conversations", "messages",
        "saved_analyses", "policy_notes", "saved_regions",
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
```

- [ ] **Step 2: Run test to verify it fails (or skips) as expected**

Run: `uv run pytest tests/api/auth/test_db_pool.py -v`
Expected: FAIL with `ModuleNotFoundError` or `AttributeError` (no `db` module / no `get_pool` yet) if `DATABASE_URL` unset the test still fails at import/collection since `db.py` doesn't exist — this confirms the test file is wired up correctly before implementation exists

- [ ] **Step 3: Write `db.py`'s pool and migration runner**

Create `src/aequitas/api/auth/db.py`:

```python
"""asyncpg connection pool and query functions for the tenancy/auth schema."""
from __future__ import annotations

import asyncio
import os
from pathlib import Path

import asyncpg

_pool: asyncpg.Pool | None = None
_pool_loop_id: int | None = None


async def get_pool() -> asyncpg.Pool:
    """Return a process-wide asyncpg pool, recreating it if the event loop changed.

    Pytest (and some ASGI test clients) can run different tests on different
    event loops; a pool bound to a closed loop raises on use, so we detect
    the loop change and recreate rather than reuse a dead pool.
    """
    global _pool, _pool_loop_id
    loop_id = id(asyncio.get_running_loop())
    if _pool is not None and _pool_loop_id != loop_id:
        try:
            await _pool.close()
        except Exception:
            pass
        _pool = None
        _pool_loop_id = None
    if _pool is None:
        database_url = os.environ["DATABASE_URL"]
        _pool = await asyncpg.create_pool(database_url, min_size=1, max_size=10)
        _pool_loop_id = loop_id
    return _pool


async def run_migrations(pool: asyncpg.Pool) -> None:
    """Apply schema.sql — idempotent, safe to call on every app startup."""
    schema_path = Path(__file__).resolve().parent / "schema.sql"
    sql = schema_path.read_text()
    async with pool.acquire() as conn:
        await conn.execute(sql)
```

- [ ] **Step 4: Run test to verify it passes (or skips cleanly) without a live Postgres**

Run: `uv run pytest tests/api/auth/test_db_pool.py -v`
Expected: 3 tests, all `SKIPPED` (DATABASE_URL not set) — zero failures/errors

- [ ] **Step 5: If a local Postgres is available, verify against it**

If you have Postgres running locally (`postgresql://localhost/aequitas`, database created via `createdb aequitas` if it doesn't exist):

Run: `DATABASE_URL=postgresql://localhost/aequitas uv run pytest tests/api/auth/test_db_pool.py -v`
Expected: 3 passed

If no local Postgres is available, skip this step — CI and later plans will exercise it. Note in the task-completion summary whether this step ran.

- [ ] **Step 6: Commit**

```bash
git add tests/api/auth/__init__.py tests/api/auth/test_db_pool.py src/aequitas/api/auth/db.py
git commit -m "Add asyncpg pool and migration runner for tenancy schema"
```

---

### Task 4: `db.py` — users, oauth_identities, tenants, memberships queries

**Files:**
- Modify: `src/aequitas/api/auth/db.py`
- Test: `tests/api/auth/test_db_users_tenants.py`

**Interfaces:**
- Consumes: `get_pool()` from Task 3
- Produces:
  - `get_or_create_user(pool, *, email: str, display_name: str | None, provider: str, provider_subject: str) -> dict` — returns the `users` row as a dict (via `dict(record)`), creating a `users` row + `oauth_identities` row if the `(provider, provider_subject)` pair is new, or returning the existing linked user if not
  - `create_tenant(pool, *, name: str, slug: str) -> dict` — returns the `tenants` row
  - `create_membership(pool, *, user_id: str, tenant_id: str, role: str) -> dict` — returns the `memberships` row
  - `get_membership(pool, *, user_id: str, tenant_id: str) -> dict | None`
  - `list_memberships_for_user(pool, *, user_id: str) -> list[dict]` — each dict includes joined `tenant_name` and `tenant_slug` alongside `role`

- [ ] **Step 1: Write the failing tests**

Create `tests/api/auth/test_db_users_tenants.py`:

```python
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
            pool, email="bob@example.com", display_name="Bob",
            provider="google", provider_subject="google-sub-2",
        )
        second = await db.get_or_create_user(
            pool, email="bob@example.com", display_name="Bob",
            provider="google", provider_subject="google-sub-2",
        )
        return first, second

    first, second = asyncio.run(_run())
    assert first["id"] == second["id"]


def test_create_tenant_and_membership():
    async def _run():
        pool = await db.get_pool()
        user = await db.get_or_create_user(
            pool, email="carol@example.com", display_name="Carol",
            provider="google", provider_subject="google-sub-3",
        )
        tenant = await db.create_tenant(pool, name="Carol's Workspace", slug=f"carol-{uuid.uuid4().hex[:8]}")
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
            pool, email="dave@example.com", display_name="Dave",
            provider="google", provider_subject="google-sub-4",
        )
        tenant = await db.create_tenant(pool, name="Dave Org", slug=f"dave-{uuid.uuid4().hex[:8]}")
        await db.create_membership(pool, user_id=user["id"], tenant_id=tenant["id"], role="admin")
        return await db.list_memberships_for_user(pool, user_id=user["id"])

    memberships = asyncio.run(_run())
    assert len(memberships) == 1
    assert memberships[0]["tenant_name"] == "Dave Org"
    assert memberships[0]["role"] == "admin"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/api/auth/test_db_users_tenants.py -v`
Expected: FAIL (`AttributeError: module 'aequitas.api.auth.db' has no attribute 'get_or_create_user'`) if `DATABASE_URL` is set, or SKIPPED if not — either way, confirms no premature pass

- [ ] **Step 3: Append the query functions to `db.py`**

Append to `src/aequitas/api/auth/db.py`:

```python


async def get_or_create_user(
    pool: asyncpg.Pool,
    *,
    email: str,
    display_name: str | None,
    provider: str,
    provider_subject: str,
) -> dict:
    """Look up a user by OAuth identity, creating user + identity rows if new."""
    async with pool.acquire() as conn:
        async with conn.transaction():
            identity = await conn.fetchrow(
                """
                SELECT user_id FROM oauth_identities
                WHERE provider = $1 AND provider_subject = $2
                """,
                provider, provider_subject,
            )
            if identity is not None:
                user_row = await conn.fetchrow(
                    "SELECT * FROM users WHERE id = $1", identity["user_id"]
                )
                return dict(user_row)

            user_row = await conn.fetchrow(
                """
                INSERT INTO users (email, display_name)
                VALUES ($1, $2)
                ON CONFLICT (email) DO UPDATE SET email = EXCLUDED.email
                RETURNING *
                """,
                email, display_name,
            )
            await conn.execute(
                """
                INSERT INTO oauth_identities (user_id, provider, provider_subject)
                VALUES ($1, $2, $3)
                """,
                user_row["id"], provider, provider_subject,
            )
            return dict(user_row)


async def create_tenant(pool: asyncpg.Pool, *, name: str, slug: str) -> dict:
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "INSERT INTO tenants (name, slug) VALUES ($1, $2) RETURNING *",
            name, slug,
        )
        return dict(row)


async def create_membership(
    pool: asyncpg.Pool, *, user_id: str, tenant_id: str, role: str
) -> dict:
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            INSERT INTO memberships (user_id, tenant_id, role)
            VALUES ($1, $2, $3)
            RETURNING *
            """,
            user_id, tenant_id, role,
        )
        return dict(row)


async def get_membership(
    pool: asyncpg.Pool, *, user_id: str, tenant_id: str
) -> dict | None:
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT * FROM memberships WHERE user_id = $1 AND tenant_id = $2",
            user_id, tenant_id,
        )
        return dict(row) if row is not None else None


async def list_memberships_for_user(pool: asyncpg.Pool, *, user_id: str) -> list[dict]:
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT m.tenant_id, m.role, m.created_at, t.name AS tenant_name, t.slug AS tenant_slug
            FROM memberships m
            JOIN tenants t ON t.id = m.tenant_id
            WHERE m.user_id = $1
            ORDER BY m.created_at ASC
            """,
            user_id,
        )
        return [dict(r) for r in rows]
```

- [ ] **Step 4: Run tests to verify they pass (if `DATABASE_URL` set) or skip cleanly**

Run: `uv run pytest tests/api/auth/test_db_users_tenants.py -v`
Expected: 5 passed (if `DATABASE_URL` set to a live local Postgres) or 5 skipped (if not)

- [ ] **Step 5: Commit**

```bash
git add src/aequitas/api/auth/db.py tests/api/auth/test_db_users_tenants.py
git commit -m "Add user/tenant/membership query functions to db.py"
```

---

### Task 5: `db.py` — sessions, invites, audit_log queries

**Files:**
- Modify: `src/aequitas/api/auth/db.py`
- Test: `tests/api/auth/test_db_sessions_invites.py`

**Interfaces:**
- Consumes: `get_pool()`, `get_or_create_user`, `create_tenant`, `create_membership` from Tasks 3-4
- Produces:
  - `create_session(pool, *, user_id: str, tenant_id: str, expires_at: datetime) -> dict`
  - `get_session(pool, *, session_id: str) -> dict | None`
  - `update_session_tenant(pool, *, session_id: str, tenant_id: str) -> dict | None`
  - `delete_session(pool, *, session_id: str) -> None`
  - `create_invite(pool, *, tenant_id: str, email: str, role: str, token: str, expires_at: datetime) -> dict`
  - `get_invite_by_token(pool, *, token: str) -> dict | None`
  - `accept_invite(pool, *, token: str) -> dict | None` — sets `accepted_at`, returns the updated invite row, or `None` if the token doesn't exist, is already accepted, or is expired
  - `remove_membership(pool, *, user_id: str, tenant_id: str) -> None`
  - `update_membership_role(pool, *, user_id: str, tenant_id: str, role: str) -> dict | None`
  - `write_audit_log(pool, *, tenant_id: str, actor_user_id: str, action: str, target_user_id: str | None, metadata: dict | None) -> dict`
  - `list_audit_log(pool, *, tenant_id: str) -> list[dict]` — newest first

- [ ] **Step 1: Write the failing tests**

Create `tests/api/auth/test_db_sessions_invites.py`:

```python
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
        pool, email=email, display_name="Test User",
        provider="google", provider_subject=subject,
    )
    tenant = await db.create_tenant(pool, name="Test Tenant", slug=f"tenant-{uuid.uuid4().hex[:8]}")
    await db.create_membership(pool, user_id=user["id"], tenant_id=tenant["id"], role="admin")
    return user, tenant


def test_create_and_get_session():
    async def _run():
        pool = await db.get_pool()
        user, tenant = await _make_user_and_tenant(pool)
        expires_at = datetime.now(timezone.utc) + timedelta(days=7)
        session = await db.create_session(pool, user_id=user["id"], tenant_id=tenant["id"], expires_at=expires_at)
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
        tenant_b = await db.create_tenant(pool, name="Second Tenant", slug=f"tenant-b-{uuid.uuid4().hex[:8]}")
        await db.create_membership(pool, user_id=user["id"], tenant_id=tenant_b["id"], role="member")
        expires_at = datetime.now(timezone.utc) + timedelta(days=7)
        session = await db.create_session(pool, user_id=user["id"], tenant_id=tenant_a["id"], expires_at=expires_at)
        updated = await db.update_session_tenant(pool, session_id=str(session["id"]), tenant_id=tenant_b["id"])
        return updated, tenant_b

    updated, tenant_b = asyncio.run(_run())
    assert updated["tenant_id"] == tenant_b["id"]


def test_delete_session_removes_it():
    async def _run():
        pool = await db.get_pool()
        user, tenant = await _make_user_and_tenant(pool)
        expires_at = datetime.now(timezone.utc) + timedelta(days=7)
        session = await db.create_session(pool, user_id=user["id"], tenant_id=tenant["id"], expires_at=expires_at)
        await db.delete_session(pool, session_id=str(session["id"]))
        return await db.get_session(pool, session_id=str(session["id"]))

    assert asyncio.run(_run()) is None


def test_create_invite_and_get_by_token():
    async def _run():
        pool = await db.get_pool()
        _, tenant = await _make_user_and_tenant(pool)
        expires_at = datetime.now(timezone.utc) + timedelta(days=3)
        invite = await db.create_invite(
            pool, tenant_id=tenant["id"], email="invitee@example.com",
            role="member", token="tok-abc123", expires_at=expires_at,
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
            pool, tenant_id=tenant["id"], email="invitee2@example.com",
            role="member", token="tok-def456", expires_at=expires_at,
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
            pool, tenant_id=tenant["id"], email="invitee3@example.com",
            role="member", token="tok-ghi789", expires_at=expires_at,
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
            pool, tenant_id=tenant["id"], email="invitee4@example.com",
            role="member", token="tok-expired", expires_at=expires_at,
        )
        return await db.accept_invite(pool, token="tok-expired")

    assert asyncio.run(_run()) is None


def test_remove_membership():
    async def _run():
        pool = await db.get_pool()
        user, tenant = await _make_user_and_tenant(pool)
        await db.remove_membership(pool, user_id=user["id"], tenant_id=tenant["id"])
        return await db.get_membership(pool, user_id=user["id"], tenant_id=tenant["id"])

    assert asyncio.run(_run()) is None


def test_update_membership_role():
    async def _run():
        pool = await db.get_pool()
        user, tenant = await _make_user_and_tenant(pool)
        return await db.update_membership_role(pool, user_id=user["id"], tenant_id=tenant["id"], role="member")

    updated = asyncio.run(_run())
    assert updated["role"] == "member"


def test_write_and_list_audit_log():
    async def _run():
        pool = await db.get_pool()
        user, tenant = await _make_user_and_tenant(pool)
        await db.write_audit_log(
            pool, tenant_id=tenant["id"], actor_user_id=user["id"],
            action="invite_created", target_user_id=None,
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
            pool, tenant_id=tenant["id"], actor_user_id=user["id"],
            action="invite_created", target_user_id=None, metadata={"seq": 1},
        )
        await db.write_audit_log(
            pool, tenant_id=tenant["id"], actor_user_id=user["id"],
            action="invite_created", target_user_id=None, metadata={"seq": 2},
        )
        return await db.list_audit_log(pool, tenant_id=tenant["id"])

    entries = asyncio.run(_run())
    assert entries[0]["metadata"]["seq"] == 2
    assert entries[1]["metadata"]["seq"] == 1
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/api/auth/test_db_sessions_invites.py -v`
Expected: FAIL (`AttributeError`) if `DATABASE_URL` is set, or SKIPPED if not

- [ ] **Step 3: Append the query functions to `db.py`**

Append to `src/aequitas/api/auth/db.py`:

```python


async def create_session(
    pool: asyncpg.Pool, *, user_id: str, tenant_id: str, expires_at
) -> dict:
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            INSERT INTO sessions (user_id, tenant_id, expires_at)
            VALUES ($1, $2, $3)
            RETURNING *
            """,
            user_id, tenant_id, expires_at,
        )
        return dict(row)


async def get_session(pool: asyncpg.Pool, *, session_id: str) -> dict | None:
    async with pool.acquire() as conn:
        row = await conn.fetchrow("SELECT * FROM sessions WHERE id = $1", session_id)
        return dict(row) if row is not None else None


async def update_session_tenant(
    pool: asyncpg.Pool, *, session_id: str, tenant_id: str
) -> dict | None:
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "UPDATE sessions SET tenant_id = $1 WHERE id = $2 RETURNING *",
            tenant_id, session_id,
        )
        return dict(row) if row is not None else None


async def delete_session(pool: asyncpg.Pool, *, session_id: str) -> None:
    async with pool.acquire() as conn:
        await conn.execute("DELETE FROM sessions WHERE id = $1", session_id)


async def create_invite(
    pool: asyncpg.Pool, *, tenant_id: str, email: str, role: str, token: str, expires_at
) -> dict:
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            INSERT INTO invites (tenant_id, email, role, token, expires_at)
            VALUES ($1, $2, $3, $4, $5)
            RETURNING *
            """,
            tenant_id, email, role, token, expires_at,
        )
        return dict(row)


async def get_invite_by_token(pool: asyncpg.Pool, *, token: str) -> dict | None:
    async with pool.acquire() as conn:
        row = await conn.fetchrow("SELECT * FROM invites WHERE token = $1", token)
        return dict(row) if row is not None else None


async def accept_invite(pool: asyncpg.Pool, *, token: str) -> dict | None:
    """Mark an invite accepted. Returns None if missing, already accepted, or expired."""
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            UPDATE invites
            SET accepted_at = now()
            WHERE token = $1 AND accepted_at IS NULL AND expires_at > now()
            RETURNING *
            """,
            token,
        )
        return dict(row) if row is not None else None


async def remove_membership(pool: asyncpg.Pool, *, user_id: str, tenant_id: str) -> None:
    async with pool.acquire() as conn:
        await conn.execute(
            "DELETE FROM memberships WHERE user_id = $1 AND tenant_id = $2",
            user_id, tenant_id,
        )


async def update_membership_role(
    pool: asyncpg.Pool, *, user_id: str, tenant_id: str, role: str
) -> dict | None:
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            UPDATE memberships SET role = $1
            WHERE user_id = $2 AND tenant_id = $3
            RETURNING *
            """,
            role, user_id, tenant_id,
        )
        return dict(row) if row is not None else None


async def write_audit_log(
    pool: asyncpg.Pool,
    *,
    tenant_id: str,
    actor_user_id: str,
    action: str,
    target_user_id: str | None,
    metadata: dict | None,
) -> dict:
    import json

    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            INSERT INTO audit_log (tenant_id, actor_user_id, action, target_user_id, metadata)
            VALUES ($1, $2, $3, $4, $5)
            RETURNING *
            """,
            tenant_id, actor_user_id, action, target_user_id,
            json.dumps(metadata) if metadata is not None else None,
        )
        return dict(row)


async def list_audit_log(pool: asyncpg.Pool, *, tenant_id: str) -> list[dict]:
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT * FROM audit_log WHERE tenant_id = $1 ORDER BY created_at DESC",
            tenant_id,
        )
        return [dict(r) for r in rows]
```

Note: `metadata` is stored via `json.dumps` and asyncpg returns JSONB columns as Python strings by default unless a codec is set — Step 4 will reveal whether `entries[0]["metadata"]["invited_email"]` needs `json.loads` first. If the test fails with `TypeError: string indices must be integers`, add this codec setup inside `get_pool()`'s pool creation (register once per pool):

```python
async def _init_connection(conn: asyncpg.Connection) -> None:
    await conn.set_type_codec(
        "jsonb", encoder=json.dumps, decoder=json.loads, schema="pg_catalog"
    )
```

and pass `init=_init_connection` to `asyncpg.create_pool(...)` in `get_pool()`. Only make this change if Step 4 shows the failure — don't add it speculatively.

- [ ] **Step 4: Run tests to verify they pass (if `DATABASE_URL` set) or skip cleanly**

Run: `uv run pytest tests/api/auth/test_db_sessions_invites.py -v`
Expected: 12 passed (if `DATABASE_URL` set) or 12 skipped (if not). If `DATABASE_URL` is set and the `metadata` JSONB assertions fail with a string-indexing error, apply the codec fix described in Step 3's note, then re-run.

- [ ] **Step 5: Commit**

```bash
git add src/aequitas/api/auth/db.py tests/api/auth/test_db_sessions_invites.py
git commit -m "Add session/invite/membership-mutation/audit-log query functions to db.py"
```

---

### Task 6: Wire `ApiConfig` fields (keep `supabase_jwt_secret` — Plan 04 removes it)

**Files:**
- Modify: `src/aequitas/api/config.py`
- Test: `tests/api/test_config.py` (new — no config test exists today for `ApiConfig`)

**Interfaces:**
- Consumes: nothing new from this plan
- Produces: `ApiConfig.database_url`, `ApiConfig.session_secret`, `ApiConfig.google_client_id`, `ApiConfig.google_client_secret`, `ApiConfig.brevo_api_key` — consumed by Plan 02 (`oauth.py`, `sessions.py`) and Plan 03 (`email.py`)

**Important — do not delete `supabase_jwt_secret` in this plan.** `src/aequitas/api/auth.py`'s `verify_supabase_jwt` reads `ApiConfig().supabase_jwt_secret` directly (confirmed: `cfg = ApiConfig(); ... if not cfg.supabase_jwt_secret: ...`) — it is *not* a raw `os.environ.get()` read. `verify_supabase_jwt` is still the live auth dependency on `conversations.py`, `chat.py`, and `export.py` until Plan 04 rewrites them. Deleting the field here would raise `AttributeError` on every request to those three routers for the entire span of Plans 01-03, and nothing in this plan runs the full existing test suite to catch it. `supabase_jwt_secret` is removed in Plan 04's Task 7, once no router imports `verify_supabase_jwt` anymore.

- [ ] **Step 1: Write the failing test**

Create `tests/api/test_config.py`:

```python
"""Tests for ApiConfig's new tenancy/auth env fields."""
from aequitas.api.config import ApiConfig


def test_database_url_defaults_to_local_dev(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    cfg = ApiConfig()
    assert cfg.database_url == "postgresql://localhost/aequitas"


def test_database_url_reads_env(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql://example.com/aequitas_prod")
    cfg = ApiConfig()
    assert cfg.database_url == "postgresql://example.com/aequitas_prod"


def test_session_secret_reads_env(monkeypatch):
    monkeypatch.setenv("SESSION_SECRET", "test-secret-value")
    cfg = ApiConfig()
    assert cfg.session_secret == "test-secret-value"


def test_google_client_id_and_secret_read_env(monkeypatch):
    monkeypatch.setenv("GOOGLE_CLIENT_ID", "client-id-123")
    monkeypatch.setenv("GOOGLE_CLIENT_SECRET", "client-secret-456")
    cfg = ApiConfig()
    assert cfg.google_client_id == "client-id-123"
    assert cfg.google_client_secret == "client-secret-456"


def test_brevo_api_key_reads_env(monkeypatch):
    monkeypatch.setenv("BREVO_API_KEY", "brevo-key-789")
    cfg = ApiConfig()
    assert cfg.brevo_api_key == "brevo-key-789"


def test_supabase_jwt_secret_still_present():
    """Must stay until Plan 04 removes verify_supabase_jwt's last call site."""
    cfg = ApiConfig()
    assert hasattr(cfg, "supabase_jwt_secret")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/api/test_config.py -v`
Expected: FAIL — the five new-field tests fail with `AttributeError` (fields don't exist yet); `test_supabase_jwt_secret_still_present` already passes (field exists today) — that's fine, it's a regression guard for later steps, not something this task makes pass

- [ ] **Step 3: Add the five new fields to `ApiConfig`, alongside the existing `supabase_jwt_secret`**

In `src/aequitas/api/config.py`, add after the existing `supabase_jwt_secret` field (do not remove it):

```python
    database_url: str = field(
        default_factory=lambda: os.environ.get("DATABASE_URL", "postgresql://localhost/aequitas")
    )
    session_secret: str = field(
        default_factory=lambda: os.environ.get("SESSION_SECRET", "")
    )
    google_client_id: str = field(
        default_factory=lambda: os.environ.get("GOOGLE_CLIENT_ID", "")
    )
    google_client_secret: str = field(
        default_factory=lambda: os.environ.get("GOOGLE_CLIENT_SECRET", "")
    )
    brevo_api_key: str = field(
        default_factory=lambda: os.environ.get("BREVO_API_KEY", "")
    )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/api/test_config.py -v`
Expected: 6 passed

- [ ] **Step 5: Run the full existing backend suite to confirm zero regressions**

Run: `uv run pytest tests/ -q`
Expected: all previously-passing tests (509 at spec time) still pass — this specifically confirms `tests/api/test_auth.py` (which exercises `verify_supabase_jwt` via `ApiConfig().supabase_jwt_secret`) is unaffected by this task's additive-only config change

- [ ] **Step 6: Commit**

```bash
git add src/aequitas/api/config.py tests/api/test_config.py
git commit -m "Add tenancy/OAuth config fields to ApiConfig (supabase_jwt_secret kept until Plan 04)"
```

---

## Handoff

At the end of this plan: `src/aequitas/api/auth/` contains `schema.sql` (full tenancy + tenant-scoped app schema) and `db.py` (pool + migration runner + full CRUD for `users`, `oauth_identities`, `tenants`, `memberships`, `sessions`, `invites`, `audit_log`). `ApiConfig` has the five new env-backed fields Plans 02/03 need. No FastAPI routes exist yet, and the old `src/aequitas/api/auth.py` (Supabase JWT) is untouched — it still runs in parallel until Plan 02 replaces its call sites.

Plan `02-oauth-sessions-backend.md` begins here: it builds `oauth.py` (Google OAuth client), `sessions.py` (cookie signing), `dependencies.py` (`require_session`/`require_admin`), and the `/api/auth/*` routes, all on top of the `db.py` functions this plan produced.
