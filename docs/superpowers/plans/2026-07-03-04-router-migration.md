# Router Migration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** This is the riskiest plan in the migration — it's where old Supabase-dependent code actually gets replaced. Rewrite `conversations.py` to use `require_session` + `db.py` (dropping the per-request Supabase client entirely), switch `chat.py` and `export.py` to `require_session`, and add four new tenant-scoped routers (`saved_analyses.py`, `policy_notes.py`, `saved_regions.py`, `profiles.py`) that previously existed only as direct-Supabase calls in the frontend's `db.ts`. After this plan, every backend route the frontend needs is tenant-scoped and Supabase-free — but the frontend itself (`AuthContext`, `db.ts`, `ChatSidebar.tsx`) still talks to Supabase until Plan 05.

**Architecture:** `conversations.py`'s five endpoints are rewritten in place against `db.py`'s `conversations`/`messages` tables (added to `db.py` in this plan — Plan 01 only created the schema, not the query functions, since conversations/messages CRUD is app-data, not tenancy-foundation). `chat.py`/`export.py` get a one-line dependency swap each, no logic change. The four new routers follow the same shape as the rewritten `conversations.py` — tenant-scoped list/create/(update)/delete, mirroring `db.ts`'s existing field names exactly so Plan 05's frontend rewrite is a mechanical fetch-call swap, not a data-reshaping exercise.

**Tech Stack:** No new dependencies. Builds entirely on `db.py`'s pool (Plan 01) and `require_session` (Plan 02).

## Global Constraints

- Backend test commands must always be prefixed `uv run`.
- All work happens on `feature/enterprise-oauth-tenancy`.
- **Cross-tenant isolation is the highest-priority test category in this plan** — every one of the five tenant-scoped resources (`conversations`, `messages`, `saved_analyses`, `policy_notes`, `saved_regions`) needs an explicit test proving a user in tenant A cannot read/write tenant B's rows, not just incidental happy-path coverage.
- `profiles` is user-scoped, not tenant-scoped — its router filters by `user_id`, not `tenant_id`. Only `policy_interests` is wired to the frontend in this migration (per the spec); `display_name`/`bio` fields exist in the schema but no route needs to expose them yet beyond what's specified below.
- This plan does not touch the frontend at all — `frontend/src/lib/db.ts` still exists and Plan 05 is what deletes it and repoints the UI.
- This plan does not delete `src/aequitas/api/auth.py` — Plan 07 does, once nothing imports `verify_supabase_jwt` anymore. By the end of this plan, nothing under `src/aequitas/api/routers/` should still import it (verify in Task 5).
- Rewritten routers keep the same URL paths and JSON response shapes as today wherever the spec doesn't call for a change — this is a backend auth-and-storage swap, not a REST API redesign.

---

### Task 1: `db.py` — conversations and messages query functions

**Files:**
- Modify: `src/aequitas/api/auth/db.py`
- Test: `tests/api/auth/test_db_conversations.py`

**Interfaces:**
- Consumes: `get_pool()` (Plan 01)
- Produces:
  - `list_conversations(pool, *, tenant_id: str) -> list[dict]` — newest-updated first, capped at 50
  - `create_conversation(pool, *, tenant_id: str, user_id: str, title: str) -> dict`
  - `get_conversation(pool, *, tenant_id: str, conversation_id: str) -> dict | None`
  - `update_conversation_title(pool, *, tenant_id: str, conversation_id: str, title: str) -> dict | None`
  - `touch_conversation(pool, *, tenant_id: str, conversation_id: str) -> None` — bumps `updated_at`
  - `delete_conversation(pool, *, tenant_id: str, conversation_id: str) -> None`
  - `list_messages(pool, *, tenant_id: str, conversation_id: str, offset: int, limit: int) -> list[dict]`
  - `create_message(pool, *, tenant_id: str, conversation_id: str, user_id: str, role: str, content: str) -> dict`
  All queries filter by `tenant_id` as the isolation boundary, consumed by Task 2's rewritten `conversations.py`.

- [ ] **Step 1: Write the failing tests**

Create `tests/api/auth/test_db_conversations.py`:

```python
"""Tests for conversations/messages query functions — require a live Postgres."""
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
                "TRUNCATE tenants, users, oauth_identities, memberships, conversations, messages CASCADE"
            )

    asyncio.run(_truncate())
    yield


async def _make_user_and_tenant(pool, email="test@example.com"):
    user = await db.get_or_create_user(
        pool, email=email, display_name="Test",
        provider="google", provider_subject=f"sub-{uuid.uuid4().hex[:8]}",
    )
    tenant = await db.create_tenant(pool, name="Test Tenant", slug=f"tenant-{uuid.uuid4().hex[:8]}")
    await db.create_membership(pool, user_id=user["id"], tenant_id=tenant["id"], role="admin")
    return user, tenant


def test_create_and_list_conversations():
    async def _run():
        pool = await db.get_pool()
        user, tenant = await _make_user_and_tenant(pool)
        await db.create_conversation(pool, tenant_id=tenant["id"], user_id=user["id"], title="First chat")
        return await db.list_conversations(pool, tenant_id=tenant["id"])

    conversations = asyncio.run(_run())
    assert len(conversations) == 1
    assert conversations[0]["title"] == "First chat"


def test_conversations_scoped_to_tenant_not_visible_across_tenants():
    async def _run():
        pool = await db.get_pool()
        user_a, tenant_a = await _make_user_and_tenant(pool, email="a@example.com")
        user_b, tenant_b = await _make_user_and_tenant(pool, email="b@example.com")
        await db.create_conversation(pool, tenant_id=tenant_a["id"], user_id=user_a["id"], title="Tenant A chat")
        return await db.list_conversations(pool, tenant_id=tenant_b["id"])

    conversations = asyncio.run(_run())
    assert conversations == []


def test_get_conversation_returns_none_for_wrong_tenant():
    async def _run():
        pool = await db.get_pool()
        user_a, tenant_a = await _make_user_and_tenant(pool, email="c@example.com")
        _, tenant_b = await _make_user_and_tenant(pool, email="d@example.com")
        conv = await db.create_conversation(pool, tenant_id=tenant_a["id"], user_id=user_a["id"], title="Private")
        return await db.get_conversation(pool, tenant_id=tenant_b["id"], conversation_id=str(conv["id"]))

    assert asyncio.run(_run()) is None


def test_update_conversation_title():
    async def _run():
        pool = await db.get_pool()
        user, tenant = await _make_user_and_tenant(pool)
        conv = await db.create_conversation(pool, tenant_id=tenant["id"], user_id=user["id"], title="Old")
        return await db.update_conversation_title(pool, tenant_id=tenant["id"], conversation_id=str(conv["id"]), title="New")

    updated = asyncio.run(_run())
    assert updated["title"] == "New"


def test_delete_conversation_removes_it_and_cascades_messages():
    async def _run():
        pool = await db.get_pool()
        user, tenant = await _make_user_and_tenant(pool)
        conv = await db.create_conversation(pool, tenant_id=tenant["id"], user_id=user["id"], title="To delete")
        await db.create_message(
            pool, tenant_id=tenant["id"], conversation_id=str(conv["id"]),
            user_id=user["id"], role="user", content="hello",
        )
        await db.delete_conversation(pool, tenant_id=tenant["id"], conversation_id=str(conv["id"]))
        remaining_convs = await db.list_conversations(pool, tenant_id=tenant["id"])
        pool2 = await db.get_pool()
        async with pool2.acquire() as c:
            remaining_messages = await c.fetch("SELECT * FROM messages WHERE conversation_id = $1", conv["id"])
        return remaining_convs, remaining_messages

    remaining_convs, remaining_messages = asyncio.run(_run())
    assert remaining_convs == []
    assert remaining_messages == []


def test_create_and_list_messages():
    async def _run():
        pool = await db.get_pool()
        user, tenant = await _make_user_and_tenant(pool)
        conv = await db.create_conversation(pool, tenant_id=tenant["id"], user_id=user["id"], title="Chat")
        await db.create_message(
            pool, tenant_id=tenant["id"], conversation_id=str(conv["id"]),
            user_id=user["id"], role="user", content="hi",
        )
        await db.create_message(
            pool, tenant_id=tenant["id"], conversation_id=str(conv["id"]),
            user_id=user["id"], role="assistant", content="hello there",
        )
        return await db.list_messages(pool, tenant_id=tenant["id"], conversation_id=str(conv["id"]), offset=0, limit=100)

    messages = asyncio.run(_run())
    assert len(messages) == 2
    assert messages[0]["content"] == "hi"
    assert messages[1]["content"] == "hello there"


def test_messages_scoped_to_tenant_not_visible_across_tenants():
    async def _run():
        pool = await db.get_pool()
        user_a, tenant_a = await _make_user_and_tenant(pool, email="e@example.com")
        _, tenant_b = await _make_user_and_tenant(pool, email="f@example.com")
        conv = await db.create_conversation(pool, tenant_id=tenant_a["id"], user_id=user_a["id"], title="A chat")
        await db.create_message(
            pool, tenant_id=tenant_a["id"], conversation_id=str(conv["id"]),
            user_id=user_a["id"], role="user", content="secret",
        )
        return await db.list_messages(pool, tenant_id=tenant_b["id"], conversation_id=str(conv["id"]), offset=0, limit=100)

    assert asyncio.run(_run()) == []


def test_touch_conversation_updates_timestamp():
    async def _run():
        pool = await db.get_pool()
        user, tenant = await _make_user_and_tenant(pool)
        conv = await db.create_conversation(pool, tenant_id=tenant["id"], user_id=user["id"], title="Chat")
        original_updated_at = conv["updated_at"]
        await db.touch_conversation(pool, tenant_id=tenant["id"], conversation_id=str(conv["id"]))
        refreshed = await db.get_conversation(pool, tenant_id=tenant["id"], conversation_id=str(conv["id"]))
        return original_updated_at, refreshed["updated_at"]

    original, refreshed = asyncio.run(_run())
    assert refreshed >= original
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/api/auth/test_db_conversations.py -v`
Expected: FAIL — functions don't exist yet

- [ ] **Step 3: Append query functions to `db.py`**

Append to `src/aequitas/api/auth/db.py`:

```python


async def list_conversations(pool: asyncpg.Pool, *, tenant_id: str) -> list[dict]:
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT * FROM conversations WHERE tenant_id = $1
            ORDER BY updated_at DESC LIMIT 50
            """,
            tenant_id,
        )
        return [dict(r) for r in rows]


async def create_conversation(pool: asyncpg.Pool, *, tenant_id: str, user_id: str, title: str) -> dict:
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            INSERT INTO conversations (tenant_id, user_id, title)
            VALUES ($1, $2, $3)
            RETURNING *
            """,
            tenant_id, user_id, title,
        )
        return dict(row)


async def get_conversation(pool: asyncpg.Pool, *, tenant_id: str, conversation_id: str) -> dict | None:
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT * FROM conversations WHERE id = $1 AND tenant_id = $2",
            conversation_id, tenant_id,
        )
        return dict(row) if row is not None else None


async def update_conversation_title(
    pool: asyncpg.Pool, *, tenant_id: str, conversation_id: str, title: str
) -> dict | None:
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            UPDATE conversations SET title = $1, updated_at = now()
            WHERE id = $2 AND tenant_id = $3
            RETURNING *
            """,
            title, conversation_id, tenant_id,
        )
        return dict(row) if row is not None else None


async def touch_conversation(pool: asyncpg.Pool, *, tenant_id: str, conversation_id: str) -> None:
    async with pool.acquire() as conn:
        await conn.execute(
            "UPDATE conversations SET updated_at = now() WHERE id = $1 AND tenant_id = $2",
            conversation_id, tenant_id,
        )


async def delete_conversation(pool: asyncpg.Pool, *, tenant_id: str, conversation_id: str) -> None:
    async with pool.acquire() as conn:
        await conn.execute(
            "DELETE FROM conversations WHERE id = $1 AND tenant_id = $2",
            conversation_id, tenant_id,
        )


async def list_messages(
    pool: asyncpg.Pool, *, tenant_id: str, conversation_id: str, offset: int, limit: int
) -> list[dict]:
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT * FROM messages WHERE conversation_id = $1 AND tenant_id = $2
            ORDER BY created_at ASC OFFSET $3 LIMIT $4
            """,
            conversation_id, tenant_id, offset, limit,
        )
        return [dict(r) for r in rows]


async def create_message(
    pool: asyncpg.Pool, *, tenant_id: str, conversation_id: str, user_id: str, role: str, content: str
) -> dict:
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            INSERT INTO messages (tenant_id, conversation_id, user_id, role, content)
            VALUES ($1, $2, $3, $4, $5)
            RETURNING *
            """,
            tenant_id, conversation_id, user_id, role, content,
        )
        return dict(row)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/api/auth/test_db_conversations.py -v`
Expected: 8 passed (given `DATABASE_URL` set)

- [ ] **Step 5: Commit**

```bash
git add src/aequitas/api/auth/db.py tests/api/auth/test_db_conversations.py
git commit -m "Add tenant-scoped conversations/messages query functions to db.py"
```

---

### Task 2: Rewrite `conversations.py` against `require_session` + `db.py`

**Files:**
- Modify: `src/aequitas/api/routers/conversations.py`
- Delete: `tests/api/test_conversations.py` (replaced — its entire subject, `_get_supabase`, no longer exists)
- Test: `tests/api/test_conversations.py` (new content, same filename)

**Interfaces:**
- Consumes: `require_session` (Plan 02), `list_conversations`/`create_conversation`/`get_conversation`/`update_conversation_title`/`touch_conversation`/`delete_conversation`/`list_messages`/`create_message` (Task 1)
- Produces: same five HTTP endpoints as before (`GET /conversations`, `POST /conversations`, `GET /conversations/{id}/messages`, `POST /conversations/{id}/messages`, `DELETE /conversations/{id}`), now tenant-scoped and Supabase-free — consumed by Plan 05's `ChatSidebar.tsx` repoint

- [ ] **Step 1: Delete the old test file's content and write the new failing tests**

The existing `tests/api/test_conversations.py` tests `_get_supabase`, which this task deletes. Replace its entire content:

```python
"""Tests for the tenant-scoped conversations router (post-Supabase rewrite)."""
import os
import uuid

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
                "TRUNCATE tenants, users, oauth_identities, memberships, conversations, messages CASCADE"
            )

    asyncio.run(_truncate())
    yield


def test_list_conversations_empty_initially(api_client):
    resp = api_client.get("/api/conversations")
    assert resp.status_code == 200
    assert resp.json() == []


def test_create_and_list_conversation(api_client):
    create_resp = api_client.post("/api/conversations", json={"title": "My chat"})
    assert create_resp.status_code == 201
    assert create_resp.json()["title"] == "My chat"

    list_resp = api_client.get("/api/conversations")
    assert len(list_resp.json()) == 1


def test_add_and_get_messages(api_client):
    create_resp = api_client.post("/api/conversations", json={"title": "My chat"})
    conv_id = create_resp.json()["id"]

    add_resp = api_client.post(
        f"/api/conversations/{conv_id}/messages",
        json={"role": "user", "content": "hello"},
    )
    assert add_resp.status_code == 201

    messages_resp = api_client.get(f"/api/conversations/{conv_id}/messages")
    assert len(messages_resp.json()) == 1
    assert messages_resp.json()[0]["content"] == "hello"


def test_add_message_rejects_invalid_role(api_client):
    create_resp = api_client.post("/api/conversations", json={"title": "My chat"})
    conv_id = create_resp.json()["id"]

    resp = api_client.post(
        f"/api/conversations/{conv_id}/messages",
        json={"role": "system", "content": "hello"},
    )
    assert resp.status_code == 400


def test_add_message_to_nonexistent_conversation_returns_404(api_client):
    resp = api_client.post(
        f"/api/conversations/{uuid.uuid4()}/messages",
        json={"role": "user", "content": "hello"},
    )
    assert resp.status_code == 404


def test_delete_conversation(api_client):
    create_resp = api_client.post("/api/conversations", json={"title": "To delete"})
    conv_id = create_resp.json()["id"]

    delete_resp = api_client.delete(f"/api/conversations/{conv_id}")
    assert delete_resp.status_code == 204

    list_resp = api_client.get("/api/conversations")
    assert list_resp.json() == []


def test_cross_tenant_isolation_list_conversations(api_client, monkeypatch):
    """A conversation created directly in another tenant must never appear in this tenant's list."""
    import asyncio
    from aequitas.api.auth import db

    async def _seed_other_tenant():
        pool = await db.get_pool()
        other_user = await db.get_or_create_user(
            pool, email="other@example.com", display_name="Other",
            provider="google", provider_subject=f"sub-{uuid.uuid4().hex[:8]}",
        )
        other_tenant = await db.create_tenant(pool, name="Other Tenant", slug=f"other-{uuid.uuid4().hex[:8]}")
        await db.create_membership(pool, user_id=other_user["id"], tenant_id=other_tenant["id"], role="admin")
        await db.create_conversation(pool, tenant_id=other_tenant["id"], user_id=other_user["id"], title="Other tenant's secret chat")

    asyncio.run(_seed_other_tenant())

    resp = api_client.get("/api/conversations")
    titles = [c["title"] for c in resp.json()]
    assert "Other tenant's secret chat" not in titles


def test_cross_tenant_isolation_get_messages(api_client):
    """A conversation id from another tenant must 404, not leak messages."""
    import asyncio
    from aequitas.api.auth import db

    async def _seed_other_tenant_conversation():
        pool = await db.get_pool()
        other_user = await db.get_or_create_user(
            pool, email="other2@example.com", display_name="Other2",
            provider="google", provider_subject=f"sub-{uuid.uuid4().hex[:8]}",
        )
        other_tenant = await db.create_tenant(pool, name="Other Tenant 2", slug=f"other2-{uuid.uuid4().hex[:8]}")
        await db.create_membership(pool, user_id=other_user["id"], tenant_id=other_tenant["id"], role="admin")
        conv = await db.create_conversation(pool, tenant_id=other_tenant["id"], user_id=other_user["id"], title="Secret")
        await db.create_message(
            pool, tenant_id=other_tenant["id"], conversation_id=str(conv["id"]),
            user_id=other_user["id"], role="user", content="secret content",
        )
        return str(conv["id"])

    other_conv_id = asyncio.run(_seed_other_tenant_conversation())

    resp = api_client.get(f"/api/conversations/{other_conv_id}/messages")
    assert resp.json() == []
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/api/test_conversations.py -v`
Expected: FAIL — router still uses `verify_supabase_jwt`/Supabase client, response shapes differ

- [ ] **Step 3: Rewrite `conversations.py`**

Replace the entire content of `src/aequitas/api/routers/conversations.py`:

```python
"""Conversations router — tenant-scoped CRUD for persisted chat sessions."""
from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from aequitas.api.auth import db
from aequitas.api.auth.dependencies import require_session

router = APIRouter(tags=["conversations"])


class ConversationCreate(BaseModel):
    title: str


class MessageCreate(BaseModel):
    role: str
    content: str


@router.get("/conversations")
async def list_conversations(session: dict = Depends(require_session)) -> list[dict]:
    """List the active tenant's conversations, newest first."""
    pool = await db.get_pool()
    rows = await db.list_conversations(pool, tenant_id=session["tenant_id"])
    return [_serialize_conversation(r) for r in rows]


@router.post("/conversations", status_code=201)
async def create_conversation(
    body: ConversationCreate,
    session: dict = Depends(require_session),
) -> dict:
    """Create a new conversation in the active tenant."""
    pool = await db.get_pool()
    row = await db.create_conversation(
        pool, tenant_id=session["tenant_id"], user_id=session["user_id"], title=body.title
    )
    return _serialize_conversation(row)


@router.get("/conversations/{conversation_id}/messages")
async def get_messages(
    conversation_id: UUID,
    session: dict = Depends(require_session),
    offset: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
) -> list[dict]:
    """Return messages for a conversation with pagination, scoped to the active tenant."""
    pool = await db.get_pool()
    rows = await db.list_messages(
        pool, tenant_id=session["tenant_id"], conversation_id=str(conversation_id),
        offset=offset, limit=limit,
    )
    return [_serialize_message(r) for r in rows]


@router.post("/conversations/{conversation_id}/messages", status_code=201)
async def add_message(
    conversation_id: UUID,
    body: MessageCreate,
    session: dict = Depends(require_session),
) -> dict:
    """Add a message to a conversation, scoped to the active tenant."""
    if body.role not in ("user", "assistant"):
        raise HTTPException(400, "role must be 'user' or 'assistant'")

    pool = await db.get_pool()
    conversation = await db.get_conversation(
        pool, tenant_id=session["tenant_id"], conversation_id=str(conversation_id)
    )
    if conversation is None:
        raise HTTPException(404, "Conversation not found")

    row = await db.create_message(
        pool, tenant_id=session["tenant_id"], conversation_id=str(conversation_id),
        user_id=session["user_id"], role=body.role, content=body.content,
    )
    await db.touch_conversation(pool, tenant_id=session["tenant_id"], conversation_id=str(conversation_id))
    return _serialize_message(row)


@router.delete("/conversations/{conversation_id}", status_code=204)
async def delete_conversation(
    conversation_id: UUID,
    session: dict = Depends(require_session),
) -> None:
    """Delete a conversation and its messages (cascades via FK), scoped to the active tenant."""
    pool = await db.get_pool()
    await db.delete_conversation(pool, tenant_id=session["tenant_id"], conversation_id=str(conversation_id))


def _serialize_conversation(row: dict) -> dict:
    return {
        "id": str(row["id"]),
        "user_id": str(row["user_id"]),
        "title": row["title"],
        "created_at": row["created_at"].isoformat(),
        "updated_at": row["updated_at"].isoformat(),
    }


def _serialize_message(row: dict) -> dict:
    return {
        "id": str(row["id"]),
        "conversation_id": str(row["conversation_id"]),
        "user_id": str(row["user_id"]),
        "role": row["role"],
        "content": row["content"],
        "created_at": row["created_at"].isoformat(),
    }
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/api/test_conversations.py -v`
Expected: 8 passed (given `DATABASE_URL`/`SESSION_SECRET` set)

- [ ] **Step 5: Commit**

```bash
git add src/aequitas/api/routers/conversations.py tests/api/test_conversations.py
git commit -m "Rewrite conversations router as tenant-scoped, dropping Supabase client"
```

---

### Task 3: Switch `chat.py` and `export.py` to `require_session`

**Files:**
- Modify: `src/aequitas/api/routers/chat.py`
- Modify: `src/aequitas/api/routers/export.py`
- Modify: `tests/api/test_export.py`

**Interfaces:**
- Consumes: `require_session` (Plan 02)
- Produces: same routes (`POST /api/chat`, `GET /api/export/{dimension}`), now cookie-session-authenticated instead of JWT-authenticated — no other behavior change

- [ ] **Step 1: Update `chat.py`'s import and dependency**

In `src/aequitas/api/routers/chat.py`, replace:

```python
from aequitas.api.auth import verify_supabase_jwt
```

with:

```python
from aequitas.api.auth.dependencies import require_session
```

Then replace the route signature:

```python
@router.post("/chat")
async def chat(
    req: ChatRequest,
    user: dict = Depends(verify_supabase_jwt),
) -> EventSourceResponse:
    """Stream Gemini response grounded in FAISS-retrieved narratives."""
    _check_rate_limit(user.get("sub", "anon"))
```

with:

```python
@router.post("/chat")
async def chat(
    req: ChatRequest,
    session: dict = Depends(require_session),
) -> EventSourceResponse:
    """Stream Gemini response grounded in FAISS-retrieved narratives."""
    _check_rate_limit(session["user_id"])
```

- [ ] **Step 2: Update `export.py`'s import and dependency**

In `src/aequitas/api/routers/export.py`, replace:

```python
from aequitas.api.auth import verify_supabase_jwt
```

with:

```python
from aequitas.api.auth.dependencies import require_session
```

Then replace the route signature:

```python
@router.get("/export/{dimension}")
async def export_dimension_pdf(
    dimension: str,
    region: str = Query("all"),
    urban_rural: str = Query("all"),
    db: duckdb.DuckDBPyConnection | None = Depends(get_db),
    user: dict = Depends(verify_supabase_jwt),
) -> StreamingResponse:
```

with:

```python
@router.get("/export/{dimension}")
async def export_dimension_pdf(
    dimension: str,
    region: str = Query("all"),
    urban_rural: str = Query("all"),
    db: duckdb.DuckDBPyConnection | None = Depends(get_db),
    session: dict = Depends(require_session),
) -> StreamingResponse:
```

(No other line in the function body references `user`, so no further changes are needed inside `export_dimension_pdf`.)

- [ ] **Step 3: Update `tests/api/test_export.py`'s auth-negative test**

The existing test forces `SUPABASE_JWT_SECRET`/production-mode Supabase-JWT-401 behavior, which no longer applies. Replace `tests/api/test_export.py`'s content:

```python
def test_export_without_auth_returns_401(api_client, monkeypatch):
    """Export must require a session like chat/conversations do."""
    monkeypatch.delenv("DEV_AUTH_BYPASS", raising=False)
    monkeypatch.setenv("ENVIRONMENT", "production")
    resp = api_client.get("/api/export/equity")
    assert resp.status_code == 401


def test_export_with_dev_bypass_succeeds(api_client):
    """With dev bypass enabled (set in conftest), export still works."""
    resp = api_client.get("/api/export/equity")
    assert resp.status_code == 200
    assert resp.headers["content-type"] == "application/pdf"
```

(This is nearly identical to the original — only the `SUPABASE_JWT_SECRET` env var setup line is removed, since `require_session`'s production-mode 401 doesn't depend on a JWT secret being configured, just the absence of a valid session cookie.)

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/api/test_export.py tests/api/test_chat.py -v`
Expected: 3 passed (`test_export.py`'s 2 tests + `test_chat.py`'s 1 unaffected test) — `test_export_with_dev_bypass_succeeds` requires `DATABASE_URL` to be reachable if dev-bypass's `require_session` path now touches the database (per Plan 02 Task 5's note about dev-bypass needing a live DB for downstream routes that call `db.py` functions); `export_dimension_pdf` itself doesn't call any `db.py` function beyond what `require_session` already resolves, so this should pass even without `DATABASE_URL` as long as Plan 03 Task 3 Step 6's dev-tenant-seeding change was applied to `require_session`. If it wasn't (i.e. Plan 03 wasn't executed, or the seeding logic isn't present), export needs no seeded row itself — but `require_session`'s dev-bypass must still resolve without raising, so confirm this test passes standalone before moving on.

- [ ] **Step 5: Commit**

```bash
git add src/aequitas/api/routers/chat.py src/aequitas/api/routers/export.py tests/api/test_export.py
git commit -m "Switch chat and export routers from Supabase JWT to require_session"
```

---

### Task 4: `db.py` — saved_analyses, policy_notes, saved_regions query functions

**Files:**
- Modify: `src/aequitas/api/auth/db.py`
- Test: `tests/api/auth/test_db_saved_resources.py`

**Interfaces:**
- Consumes: `get_pool()` (Plan 01)
- Produces:
  - `list_saved_analyses(pool, *, tenant_id: str) -> list[dict]`, `create_saved_analysis(pool, *, tenant_id, user_id, title, content, section_id, dimension, tags) -> dict`, `delete_saved_analysis(pool, *, tenant_id, analysis_id) -> None`
  - `list_policy_notes(pool, *, tenant_id: str) -> list[dict]`, `create_policy_note(pool, *, tenant_id, user_id, dimension, region, stance, thesis) -> dict`, `update_policy_note(pool, *, tenant_id, note_id, stance, thesis, critique) -> dict | None` (returns `None` if `note_id` doesn't exist in `tenant_id`), `delete_policy_note(pool, *, tenant_id, note_id) -> None`
  - `list_saved_regions(pool, *, tenant_id: str) -> list[dict]`, `create_saved_region(pool, *, tenant_id, user_id, region_code, region_name, notes) -> dict`, `delete_saved_region(pool, *, tenant_id, region_id) -> None`
  All consumed by Task 5's three new routers.

- [ ] **Step 1: Write the failing tests**

Create `tests/api/auth/test_db_saved_resources.py`:

```python
"""Tests for saved_analyses/policy_notes/saved_regions query functions — require a live Postgres."""
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
                "TRUNCATE tenants, users, oauth_identities, memberships, "
                "saved_analyses, policy_notes, saved_regions CASCADE"
            )

    asyncio.run(_truncate())
    yield


async def _make_user_and_tenant(pool, email="test@example.com"):
    user = await db.get_or_create_user(
        pool, email=email, display_name="Test",
        provider="google", provider_subject=f"sub-{uuid.uuid4().hex[:8]}",
    )
    tenant = await db.create_tenant(pool, name="Test Tenant", slug=f"tenant-{uuid.uuid4().hex[:8]}")
    await db.create_membership(pool, user_id=user["id"], tenant_id=tenant["id"], role="admin")
    return user, tenant


def test_create_and_list_saved_analysis():
    async def _run():
        pool = await db.get_pool()
        user, tenant = await _make_user_and_tenant(pool)
        await db.create_saved_analysis(
            pool, tenant_id=tenant["id"], user_id=user["id"], title="Gini analysis",
            content="Gini is 0.5741", section_id="f1_gini", dimension="equity", tags=["priority"],
        )
        return await db.list_saved_analyses(pool, tenant_id=tenant["id"])

    analyses = asyncio.run(_run())
    assert len(analyses) == 1
    assert analyses[0]["title"] == "Gini analysis"
    assert analyses[0]["tags"] == ["priority"]


def test_saved_analyses_scoped_to_tenant():
    async def _run():
        pool = await db.get_pool()
        user_a, tenant_a = await _make_user_and_tenant(pool, email="a@example.com")
        _, tenant_b = await _make_user_and_tenant(pool, email="b@example.com")
        await db.create_saved_analysis(
            pool, tenant_id=tenant_a["id"], user_id=user_a["id"], title="A's analysis",
            content="content", section_id=None, dimension=None, tags=[],
        )
        return await db.list_saved_analyses(pool, tenant_id=tenant_b["id"])

    assert asyncio.run(_run()) == []


def test_delete_saved_analysis():
    async def _run():
        pool = await db.get_pool()
        user, tenant = await _make_user_and_tenant(pool)
        row = await db.create_saved_analysis(
            pool, tenant_id=tenant["id"], user_id=user["id"], title="To delete",
            content="content", section_id=None, dimension=None, tags=[],
        )
        await db.delete_saved_analysis(pool, tenant_id=tenant["id"], analysis_id=str(row["id"]))
        return await db.list_saved_analyses(pool, tenant_id=tenant["id"])

    assert asyncio.run(_run()) == []


def test_create_and_list_policy_note():
    async def _run():
        pool = await db.get_pool()
        user, tenant = await _make_user_and_tenant(pool)
        await db.create_policy_note(
            pool, tenant_id=tenant["id"], user_id=user["id"], dimension="equity",
            region="all", stance="priority", thesis="Gini is too high",
        )
        return await db.list_policy_notes(pool, tenant_id=tenant["id"])

    notes = asyncio.run(_run())
    assert len(notes) == 1
    assert notes[0]["thesis"] == "Gini is too high"


def test_policy_notes_scoped_to_tenant():
    async def _run():
        pool = await db.get_pool()
        user_a, tenant_a = await _make_user_and_tenant(pool, email="c@example.com")
        _, tenant_b = await _make_user_and_tenant(pool, email="d@example.com")
        await db.create_policy_note(
            pool, tenant_id=tenant_a["id"], user_id=user_a["id"], dimension="equity",
            region="all", stance="priority", thesis="A's thesis",
        )
        return await db.list_policy_notes(pool, tenant_id=tenant_b["id"])

    assert asyncio.run(_run()) == []


def test_delete_policy_note():
    async def _run():
        pool = await db.get_pool()
        user, tenant = await _make_user_and_tenant(pool)
        row = await db.create_policy_note(
            pool, tenant_id=tenant["id"], user_id=user["id"], dimension="equity",
            region="all", stance="monitor", thesis="thesis",
        )
        await db.delete_policy_note(pool, tenant_id=tenant["id"], note_id=str(row["id"]))
        return await db.list_policy_notes(pool, tenant_id=tenant["id"])

    assert asyncio.run(_run()) == []


def test_update_policy_note():
    """The spec calls for policy_notes to support update (unlike saved_analyses/saved_regions,
    which are list/create/delete only) — a policy note is a living document, edited over time."""
    async def _run():
        pool = await db.get_pool()
        user, tenant = await _make_user_and_tenant(pool)
        row = await db.create_policy_note(
            pool, tenant_id=tenant["id"], user_id=user["id"], dimension="equity",
            region="all", stance="monitor", thesis="Initial thesis",
        )
        return await db.update_policy_note(
            pool, tenant_id=tenant["id"], note_id=str(row["id"]),
            stance="priority", thesis="Revised thesis", critique="New evidence changes this",
        )

    updated = asyncio.run(_run())
    assert updated["stance"] == "priority"
    assert updated["thesis"] == "Revised thesis"
    assert updated["critique"] == "New evidence changes this"


def test_update_policy_note_returns_none_for_wrong_tenant():
    async def _run():
        pool = await db.get_pool()
        user_a, tenant_a = await _make_user_and_tenant(pool, email="g@example.com")
        _, tenant_b = await _make_user_and_tenant(pool, email="h@example.com")
        row = await db.create_policy_note(
            pool, tenant_id=tenant_a["id"], user_id=user_a["id"], dimension="equity",
            region="all", stance="monitor", thesis="A's thesis",
        )
        return await db.update_policy_note(
            pool, tenant_id=tenant_b["id"], note_id=str(row["id"]),
            stance="priority", thesis="Attempted cross-tenant edit", critique=None,
        )

    assert asyncio.run(_run()) is None


def test_create_and_list_saved_region():
    async def _run():
        pool = await db.get_pool()
        user, tenant = await _make_user_and_tenant(pool)
        await db.create_saved_region(
            pool, tenant_id=tenant["id"], user_id=user["id"],
            region_code="E12000001", region_name="North East", notes="watching",
        )
        return await db.list_saved_regions(pool, tenant_id=tenant["id"])

    regions = asyncio.run(_run())
    assert len(regions) == 1
    assert regions[0]["region_name"] == "North East"


def test_saved_regions_scoped_to_tenant():
    async def _run():
        pool = await db.get_pool()
        user_a, tenant_a = await _make_user_and_tenant(pool, email="e@example.com")
        _, tenant_b = await _make_user_and_tenant(pool, email="f@example.com")
        await db.create_saved_region(
            pool, tenant_id=tenant_a["id"], user_id=user_a["id"],
            region_code="E12000001", region_name="A's region", notes=None,
        )
        return await db.list_saved_regions(pool, tenant_id=tenant_b["id"])

    assert asyncio.run(_run()) == []


def test_delete_saved_region():
    async def _run():
        pool = await db.get_pool()
        user, tenant = await _make_user_and_tenant(pool)
        row = await db.create_saved_region(
            pool, tenant_id=tenant["id"], user_id=user["id"],
            region_code="E12000001", region_name="To delete", notes=None,
        )
        await db.delete_saved_region(pool, tenant_id=tenant["id"], region_id=str(row["id"]))
        return await db.list_saved_regions(pool, tenant_id=tenant["id"])

    assert asyncio.run(_run()) == []
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/api/auth/test_db_saved_resources.py -v`
Expected: FAIL — functions don't exist yet

- [ ] **Step 3: Append query functions to `db.py`**

Append to `src/aequitas/api/auth/db.py`:

```python


async def list_saved_analyses(pool: asyncpg.Pool, *, tenant_id: str) -> list[dict]:
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT * FROM saved_analyses WHERE tenant_id = $1 ORDER BY created_at DESC",
            tenant_id,
        )
        return [dict(r) for r in rows]


async def create_saved_analysis(
    pool: asyncpg.Pool,
    *,
    tenant_id: str,
    user_id: str,
    title: str,
    content: str,
    section_id: str | None,
    dimension: str | None,
    tags: list[str],
) -> dict:
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            INSERT INTO saved_analyses (tenant_id, user_id, title, content, section_id, dimension, tags)
            VALUES ($1, $2, $3, $4, $5, $6, $7)
            RETURNING *
            """,
            tenant_id, user_id, title, content, section_id, dimension, tags,
        )
        return dict(row)


async def delete_saved_analysis(pool: asyncpg.Pool, *, tenant_id: str, analysis_id: str) -> None:
    async with pool.acquire() as conn:
        await conn.execute(
            "DELETE FROM saved_analyses WHERE id = $1 AND tenant_id = $2",
            analysis_id, tenant_id,
        )


async def list_policy_notes(pool: asyncpg.Pool, *, tenant_id: str) -> list[dict]:
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT * FROM policy_notes WHERE tenant_id = $1 ORDER BY created_at DESC",
            tenant_id,
        )
        return [dict(r) for r in rows]


async def create_policy_note(
    pool: asyncpg.Pool,
    *,
    tenant_id: str,
    user_id: str,
    dimension: str,
    region: str,
    stance: str,
    thesis: str,
) -> dict:
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            INSERT INTO policy_notes (tenant_id, user_id, dimension, region, stance, thesis)
            VALUES ($1, $2, $3, $4, $5, $6)
            RETURNING *
            """,
            tenant_id, user_id, dimension, region, stance, thesis,
        )
        return dict(row)


async def delete_policy_note(pool: asyncpg.Pool, *, tenant_id: str, note_id: str) -> None:
    async with pool.acquire() as conn:
        await conn.execute(
            "DELETE FROM policy_notes WHERE id = $1 AND tenant_id = $2",
            note_id, tenant_id,
        )


async def update_policy_note(
    pool: asyncpg.Pool,
    *,
    tenant_id: str,
    note_id: str,
    stance: str,
    thesis: str,
    critique: str | None,
) -> dict | None:
    """Update a policy note's stance/thesis/critique. Returns None if not found in this tenant."""
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            UPDATE policy_notes
            SET stance = $1, thesis = $2, critique = $3, updated_at = now()
            WHERE id = $4 AND tenant_id = $5
            RETURNING *
            """,
            stance, thesis, critique, note_id, tenant_id,
        )
        return dict(row) if row is not None else None


async def list_saved_regions(pool: asyncpg.Pool, *, tenant_id: str) -> list[dict]:
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT * FROM saved_regions WHERE tenant_id = $1 ORDER BY created_at DESC",
            tenant_id,
        )
        return [dict(r) for r in rows]


async def create_saved_region(
    pool: asyncpg.Pool,
    *,
    tenant_id: str,
    user_id: str,
    region_code: str,
    region_name: str,
    notes: str | None,
) -> dict:
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            INSERT INTO saved_regions (tenant_id, user_id, region_code, region_name, notes)
            VALUES ($1, $2, $3, $4, $5)
            RETURNING *
            """,
            tenant_id, user_id, region_code, region_name, notes,
        )
        return dict(row)


async def delete_saved_region(pool: asyncpg.Pool, *, tenant_id: str, region_id: str) -> None:
    async with pool.acquire() as conn:
        await conn.execute(
            "DELETE FROM saved_regions WHERE id = $1 AND tenant_id = $2",
            region_id, tenant_id,
        )
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/api/auth/test_db_saved_resources.py -v`
Expected: 11 passed (given `DATABASE_URL` set)

- [ ] **Step 5: Commit**

```bash
git add src/aequitas/api/auth/db.py tests/api/auth/test_db_saved_resources.py
git commit -m "Add tenant-scoped saved_analyses/policy_notes/saved_regions query functions to db.py"
```

---

### Task 5: New routers — `saved_analyses.py`, `policy_notes.py`, `saved_regions.py`

**Files:**
- Create: `src/aequitas/api/routers/saved_analyses.py`
- Create: `src/aequitas/api/routers/policy_notes.py`
- Create: `src/aequitas/api/routers/saved_regions.py`
- Modify: `src/aequitas/api/app.py`
- Test: `tests/api/test_saved_analyses.py`
- Test: `tests/api/test_policy_notes.py`
- Test: `tests/api/test_saved_regions.py`

**Interfaces:**
- Consumes: `require_session` (Plan 02), Task 4's `db.py` functions
- Produces: `GET/POST/DELETE /api/saved-analyses`, `GET/POST/PATCH/DELETE /api/policy-notes` (policy notes support update — a living document, unlike the other two which are list/create/delete only, per the spec), `GET/POST/DELETE /api/saved-regions` — mirroring `db.ts`'s field shapes exactly, consumed by Plan 05's frontend rewrite (`SavedAnalyses.tsx`, `PolicyNotes.tsx`, `SavedRegions.tsx`)

- [ ] **Step 1: Write the failing tests**

Create `tests/api/test_saved_analyses.py`:

```python
"""Tests for the saved_analyses router."""
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
            await conn.execute("TRUNCATE tenants, users, oauth_identities, memberships, saved_analyses CASCADE")

    asyncio.run(_truncate())
    yield


def test_create_and_list(api_client):
    create_resp = api_client.post(
        "/api/saved-analyses",
        json={"title": "Gini", "content": "0.5741", "section_id": "f1_gini", "dimension": "equity", "tags": ["priority"]},
    )
    assert create_resp.status_code == 201

    list_resp = api_client.get("/api/saved-analyses")
    assert len(list_resp.json()) == 1
    assert list_resp.json()[0]["title"] == "Gini"


def test_delete(api_client):
    create_resp = api_client.post(
        "/api/saved-analyses",
        json={"title": "To delete", "content": "x", "section_id": None, "dimension": None, "tags": []},
    )
    analysis_id = create_resp.json()["id"]

    delete_resp = api_client.delete(f"/api/saved-analyses/{analysis_id}")
    assert delete_resp.status_code == 204

    list_resp = api_client.get("/api/saved-analyses")
    assert list_resp.json() == []


def test_cross_tenant_isolation(api_client):
    import asyncio
    import uuid
    from aequitas.api.auth import db

    async def _seed_other_tenant():
        pool = await db.get_pool()
        other_user = await db.get_or_create_user(
            pool, email="other@example.com", display_name="Other",
            provider="google", provider_subject=f"sub-{uuid.uuid4().hex[:8]}",
        )
        other_tenant = await db.create_tenant(pool, name="Other", slug=f"other-{uuid.uuid4().hex[:8]}")
        await db.create_membership(pool, user_id=other_user["id"], tenant_id=other_tenant["id"], role="admin")
        await db.create_saved_analysis(
            pool, tenant_id=other_tenant["id"], user_id=other_user["id"], title="Other's secret",
            content="x", section_id=None, dimension=None, tags=[],
        )

    asyncio.run(_seed_other_tenant())

    resp = api_client.get("/api/saved-analyses")
    titles = [a["title"] for a in resp.json()]
    assert "Other's secret" not in titles
```

Create `tests/api/test_policy_notes.py`:

```python
"""Tests for the policy_notes router."""
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
            await conn.execute("TRUNCATE tenants, users, oauth_identities, memberships, policy_notes CASCADE")

    asyncio.run(_truncate())
    yield


def test_create_and_list(api_client):
    create_resp = api_client.post(
        "/api/policy-notes",
        json={"dimension": "equity", "region": "all", "stance": "priority", "thesis": "Gini is too high"},
    )
    assert create_resp.status_code == 201

    list_resp = api_client.get("/api/policy-notes")
    assert len(list_resp.json()) == 1
    assert list_resp.json()[0]["thesis"] == "Gini is too high"


def test_create_rejects_invalid_stance(api_client):
    resp = api_client.post(
        "/api/policy-notes",
        json={"dimension": "equity", "region": "all", "stance": "urgent", "thesis": "x"},
    )
    assert resp.status_code == 400


def test_update(api_client):
    create_resp = api_client.post(
        "/api/policy-notes",
        json={"dimension": "equity", "region": "all", "stance": "monitor", "thesis": "Initial"},
    )
    note_id = create_resp.json()["id"]

    update_resp = api_client.patch(
        f"/api/policy-notes/{note_id}",
        json={"stance": "priority", "thesis": "Revised thesis", "critique": "New evidence"},
    )
    assert update_resp.status_code == 200
    assert update_resp.json()["stance"] == "priority"
    assert update_resp.json()["thesis"] == "Revised thesis"
    assert update_resp.json()["critique"] == "New evidence"

    list_resp = api_client.get("/api/policy-notes")
    assert list_resp.json()[0]["thesis"] == "Revised thesis"


def test_update_rejects_invalid_stance(api_client):
    create_resp = api_client.post(
        "/api/policy-notes",
        json={"dimension": "equity", "region": "all", "stance": "monitor", "thesis": "x"},
    )
    note_id = create_resp.json()["id"]

    resp = api_client.patch(
        f"/api/policy-notes/{note_id}",
        json={"stance": "urgent", "thesis": "x", "critique": None},
    )
    assert resp.status_code == 400


def test_update_nonexistent_note_returns_404(api_client):
    import uuid

    resp = api_client.patch(
        f"/api/policy-notes/{uuid.uuid4()}",
        json={"stance": "priority", "thesis": "x", "critique": None},
    )
    assert resp.status_code == 404


def test_delete(api_client):
    create_resp = api_client.post(
        "/api/policy-notes",
        json={"dimension": "equity", "region": "all", "stance": "monitor", "thesis": "To delete"},
    )
    note_id = create_resp.json()["id"]

    delete_resp = api_client.delete(f"/api/policy-notes/{note_id}")
    assert delete_resp.status_code == 204
    assert api_client.get("/api/policy-notes").json() == []


def test_cross_tenant_isolation(api_client):
    import asyncio
    import uuid
    from aequitas.api.auth import db

    async def _seed_other_tenant():
        pool = await db.get_pool()
        other_user = await db.get_or_create_user(
            pool, email="other@example.com", display_name="Other",
            provider="google", provider_subject=f"sub-{uuid.uuid4().hex[:8]}",
        )
        other_tenant = await db.create_tenant(pool, name="Other", slug=f"other-{uuid.uuid4().hex[:8]}")
        await db.create_membership(pool, user_id=other_user["id"], tenant_id=other_tenant["id"], role="admin")
        await db.create_policy_note(
            pool, tenant_id=other_tenant["id"], user_id=other_user["id"],
            dimension="equity", region="all", stance="priority", thesis="Other's secret thesis",
        )

    asyncio.run(_seed_other_tenant())

    resp = api_client.get("/api/policy-notes")
    theses = [n["thesis"] for n in resp.json()]
    assert "Other's secret thesis" not in theses
```

Create `tests/api/test_saved_regions.py`:

```python
"""Tests for the saved_regions router."""
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
            await conn.execute("TRUNCATE tenants, users, oauth_identities, memberships, saved_regions CASCADE")

    asyncio.run(_truncate())
    yield


def test_create_and_list(api_client):
    create_resp = api_client.post(
        "/api/saved-regions",
        json={"region_code": "E12000001", "region_name": "North East", "notes": "watching closely"},
    )
    assert create_resp.status_code == 201

    list_resp = api_client.get("/api/saved-regions")
    assert len(list_resp.json()) == 1
    assert list_resp.json()[0]["region_name"] == "North East"


def test_delete(api_client):
    create_resp = api_client.post(
        "/api/saved-regions",
        json={"region_code": "E12000001", "region_name": "To delete", "notes": None},
    )
    region_id = create_resp.json()["id"]

    delete_resp = api_client.delete(f"/api/saved-regions/{region_id}")
    assert delete_resp.status_code == 204
    assert api_client.get("/api/saved-regions").json() == []


def test_cross_tenant_isolation(api_client):
    import asyncio
    import uuid
    from aequitas.api.auth import db

    async def _seed_other_tenant():
        pool = await db.get_pool()
        other_user = await db.get_or_create_user(
            pool, email="other@example.com", display_name="Other",
            provider="google", provider_subject=f"sub-{uuid.uuid4().hex[:8]}",
        )
        other_tenant = await db.create_tenant(pool, name="Other", slug=f"other-{uuid.uuid4().hex[:8]}")
        await db.create_membership(pool, user_id=other_user["id"], tenant_id=other_tenant["id"], role="admin")
        await db.create_saved_region(
            pool, tenant_id=other_tenant["id"], user_id=other_user["id"],
            region_code="E12000001", region_name="Other's secret region", notes=None,
        )

    asyncio.run(_seed_other_tenant())

    resp = api_client.get("/api/saved-regions")
    names = [r["region_name"] for r in resp.json()]
    assert "Other's secret region" not in names
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/api/test_saved_analyses.py tests/api/test_policy_notes.py tests/api/test_saved_regions.py -v`
Expected: FAIL — routers don't exist yet (404s)

- [ ] **Step 3: Write `saved_analyses.py`**

Create `src/aequitas/api/routers/saved_analyses.py`:

```python
"""Saved analyses router — tenant-scoped bookmarked narratives/chat responses."""
from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from aequitas.api.auth import db
from aequitas.api.auth.dependencies import require_session

router = APIRouter(tags=["saved-analyses"])


class SavedAnalysisCreate(BaseModel):
    title: str
    content: str
    section_id: str | None = None
    dimension: str | None = None
    tags: list[str] = []


@router.get("/saved-analyses")
async def list_saved_analyses(session: dict = Depends(require_session)) -> list[dict]:
    pool = await db.get_pool()
    rows = await db.list_saved_analyses(pool, tenant_id=session["tenant_id"])
    return [_serialize(r) for r in rows]


@router.post("/saved-analyses", status_code=201)
async def create_saved_analysis(
    body: SavedAnalysisCreate, session: dict = Depends(require_session)
) -> dict:
    pool = await db.get_pool()
    row = await db.create_saved_analysis(
        pool, tenant_id=session["tenant_id"], user_id=session["user_id"],
        title=body.title, content=body.content, section_id=body.section_id,
        dimension=body.dimension, tags=body.tags,
    )
    return _serialize(row)


@router.delete("/saved-analyses/{analysis_id}", status_code=204)
async def delete_saved_analysis(analysis_id: UUID, session: dict = Depends(require_session)) -> None:
    pool = await db.get_pool()
    await db.delete_saved_analysis(pool, tenant_id=session["tenant_id"], analysis_id=str(analysis_id))


def _serialize(row: dict) -> dict:
    return {
        "id": str(row["id"]),
        "user_id": str(row["user_id"]),
        "title": row["title"],
        "content": row["content"],
        "section_id": row["section_id"],
        "dimension": row["dimension"],
        "tags": list(row["tags"]) if row["tags"] else [],
        "created_at": row["created_at"].isoformat(),
    }
```

- [ ] **Step 4: Write `policy_notes.py`**

Create `src/aequitas/api/routers/policy_notes.py`:

```python
"""Policy notes router — tenant-scoped journal-style notes per dimension."""
from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from aequitas.api.auth import db
from aequitas.api.auth.dependencies import require_session

router = APIRouter(tags=["policy-notes"])

_VALID_STANCES = ("priority", "monitor", "adequate")


class PolicyNoteCreate(BaseModel):
    dimension: str
    region: str = "all"
    stance: str
    thesis: str


class PolicyNoteUpdate(BaseModel):
    stance: str
    thesis: str
    critique: str | None = None


@router.get("/policy-notes")
async def list_policy_notes(session: dict = Depends(require_session)) -> list[dict]:
    pool = await db.get_pool()
    rows = await db.list_policy_notes(pool, tenant_id=session["tenant_id"])
    return [_serialize(r) for r in rows]


@router.post("/policy-notes", status_code=201)
async def create_policy_note(
    body: PolicyNoteCreate, session: dict = Depends(require_session)
) -> dict:
    if body.stance not in _VALID_STANCES:
        raise HTTPException(400, f"stance must be one of {_VALID_STANCES}")

    pool = await db.get_pool()
    row = await db.create_policy_note(
        pool, tenant_id=session["tenant_id"], user_id=session["user_id"],
        dimension=body.dimension, region=body.region, stance=body.stance, thesis=body.thesis,
    )
    return _serialize(row)


@router.patch("/policy-notes/{note_id}")
async def update_policy_note(
    note_id: UUID, body: PolicyNoteUpdate, session: dict = Depends(require_session)
) -> dict:
    if body.stance not in _VALID_STANCES:
        raise HTTPException(400, f"stance must be one of {_VALID_STANCES}")

    pool = await db.get_pool()
    updated = await db.update_policy_note(
        pool, tenant_id=session["tenant_id"], note_id=str(note_id),
        stance=body.stance, thesis=body.thesis, critique=body.critique,
    )
    if updated is None:
        raise HTTPException(404, "Policy note not found")
    return _serialize(updated)


@router.delete("/policy-notes/{note_id}", status_code=204)
async def delete_policy_note(note_id: UUID, session: dict = Depends(require_session)) -> None:
    pool = await db.get_pool()
    await db.delete_policy_note(pool, tenant_id=session["tenant_id"], note_id=str(note_id))


def _serialize(row: dict) -> dict:
    return {
        "id": str(row["id"]),
        "user_id": str(row["user_id"]),
        "dimension": row["dimension"],
        "region": row["region"],
        "stance": row["stance"],
        "thesis": row["thesis"],
        "critique": row["critique"],
        "created_at": row["created_at"].isoformat(),
        "updated_at": row["updated_at"].isoformat(),
    }
```

- [ ] **Step 5: Write `saved_regions.py`**

Create `src/aequitas/api/routers/saved_regions.py`:

```python
"""Saved regions router — tenant-scoped tracked-regions watchlist."""
from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from aequitas.api.auth import db
from aequitas.api.auth.dependencies import require_session

router = APIRouter(tags=["saved-regions"])


class SavedRegionCreate(BaseModel):
    region_code: str
    region_name: str
    notes: str | None = None


@router.get("/saved-regions")
async def list_saved_regions(session: dict = Depends(require_session)) -> list[dict]:
    pool = await db.get_pool()
    rows = await db.list_saved_regions(pool, tenant_id=session["tenant_id"])
    return [_serialize(r) for r in rows]


@router.post("/saved-regions", status_code=201)
async def create_saved_region(
    body: SavedRegionCreate, session: dict = Depends(require_session)
) -> dict:
    pool = await db.get_pool()
    row = await db.create_saved_region(
        pool, tenant_id=session["tenant_id"], user_id=session["user_id"],
        region_code=body.region_code, region_name=body.region_name, notes=body.notes,
    )
    return _serialize(row)


@router.delete("/saved-regions/{region_id}", status_code=204)
async def delete_saved_region(region_id: UUID, session: dict = Depends(require_session)) -> None:
    pool = await db.get_pool()
    await db.delete_saved_region(pool, tenant_id=session["tenant_id"], region_id=str(region_id))


def _serialize(row: dict) -> dict:
    return {
        "id": str(row["id"]),
        "user_id": str(row["user_id"]),
        "region_code": row["region_code"],
        "region_name": row["region_name"],
        "notes": row["notes"],
        "created_at": row["created_at"].isoformat(),
    }
```

- [ ] **Step 6: Register the three new routers in `app.py`**

In `src/aequitas/api/app.py`, update the router import and registration block (this already includes `auth_router` from Plan 02):

```python
    from aequitas.api.routers import (
        overview, sections, lsoa, provenance, chat, conversations, metrics, export,
        auth as auth_router, saved_analyses, policy_notes, saved_regions,
    )
    app.include_router(overview.router, prefix="/api")
    app.include_router(sections.router, prefix="/api")
    app.include_router(lsoa.router, prefix="/api")
    app.include_router(provenance.router, prefix="/api")
    app.include_router(chat.router, prefix="/api")
    app.include_router(conversations.router, prefix="/api")
    app.include_router(metrics.router, prefix="/api")
    app.include_router(export.router, prefix="/api")
    app.include_router(auth_router.router, prefix="/api")
    app.include_router(saved_analyses.router, prefix="/api")
    app.include_router(policy_notes.router, prefix="/api")
    app.include_router(saved_regions.router, prefix="/api")
```

- [ ] **Step 7: Run tests to verify they pass**

Run: `uv run pytest tests/api/test_saved_analyses.py tests/api/test_policy_notes.py tests/api/test_saved_regions.py -v`
Expected: 13 passed (given `DATABASE_URL`/`SESSION_SECRET` set) — 3 for saved-analyses, 7 for policy-notes (create/list, invalid-stance, update, update-invalid-stance, update-404, delete, cross-tenant), 3 for saved-regions

- [ ] **Step 8: Commit**

```bash
git add src/aequitas/api/routers/saved_analyses.py src/aequitas/api/routers/policy_notes.py \
  src/aequitas/api/routers/saved_regions.py src/aequitas/api/app.py \
  tests/api/test_saved_analyses.py tests/api/test_policy_notes.py tests/api/test_saved_regions.py
git commit -m "Add tenant-scoped saved_analyses/policy_notes/saved_regions routers"
```

---

### Task 6: `profiles.py` router — user-scoped, policy_interests only

**Files:**
- Create: `src/aequitas/api/routers/profiles.py`
- Modify: `src/aequitas/api/auth/db.py`
- Modify: `src/aequitas/api/app.py`
- Test: `tests/api/test_profiles.py`

**Interfaces:**
- Consumes: `require_session` (Plan 02); `get_or_create_profile` (added in Plan 02 Task 5); new `get_profile`/`update_profile_policy_interests` in `db.py`
- Produces: `GET /api/profile`, `PATCH /api/profile` — user-scoped (filters by `user_id`, not `tenant_id`), consumed by Plan 05's `ProfilePage.tsx` rewrite

- [ ] **Step 1: Write the failing tests**

Create `tests/api/test_profiles.py`:

```python
"""Tests for the user-scoped profiles router."""
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
            await conn.execute("TRUNCATE tenants, users, oauth_identities, memberships, profiles CASCADE")

    asyncio.run(_truncate())
    yield


def test_get_profile_creates_empty_profile_if_absent(api_client):
    resp = api_client.get("/api/profile")
    assert resp.status_code == 200
    assert resp.json()["policy_interests"] == []


def test_update_policy_interests(api_client):
    resp = api_client.patch("/api/profile", json={"policy_interests": ["Equity & Deprivation", "Accessibility"]})
    assert resp.status_code == 200
    assert resp.json()["policy_interests"] == ["Equity & Deprivation", "Accessibility"]

    get_resp = api_client.get("/api/profile")
    assert get_resp.json()["policy_interests"] == ["Equity & Deprivation", "Accessibility"]


def test_profile_is_user_scoped_not_tenant_scoped(api_client):
    """Same dev user id across two different active tenants sees the same profile."""
    api_client.patch("/api/profile", json={"policy_interests": ["Route Network"]})
    resp = api_client.get("/api/profile")
    assert resp.json()["policy_interests"] == ["Route Network"]
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/api/test_profiles.py -v`
Expected: FAIL — route doesn't exist yet

- [ ] **Step 3: Add `get_profile`/`update_profile_policy_interests` to `db.py`**

Append to `src/aequitas/api/auth/db.py`:

```python


async def get_profile(pool: asyncpg.Pool, *, user_id: str) -> dict | None:
    async with pool.acquire() as conn:
        row = await conn.fetchrow("SELECT * FROM profiles WHERE user_id = $1", user_id)
        return dict(row) if row is not None else None


async def update_profile_policy_interests(
    pool: asyncpg.Pool, *, user_id: str, policy_interests: list[str]
) -> dict:
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            INSERT INTO profiles (user_id, policy_interests)
            VALUES ($1, $2)
            ON CONFLICT (user_id) DO UPDATE SET policy_interests = $2, updated_at = now()
            RETURNING *
            """,
            user_id, policy_interests,
        )
        return dict(row)
```

- [ ] **Step 4: Write `profiles.py`**

Create `src/aequitas/api/routers/profiles.py`:

```python
"""Profiles router — user-scoped (not tenant-scoped) profile data.

Only policy_interests is wired to the frontend today (see spec's Data model
section, "profiles is currently dead schema"); display_name/bio exist in the
schema but have no route needing them yet.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from aequitas.api.auth import db
from aequitas.api.auth.dependencies import require_session

router = APIRouter(tags=["profiles"])


class ProfileUpdate(BaseModel):
    policy_interests: list[str]


@router.get("/profile")
async def get_profile(session: dict = Depends(require_session)) -> dict:
    pool = await db.get_pool()
    profile = await db.get_profile(pool, user_id=session["user_id"])
    if profile is None:
        profile = await db.get_or_create_profile(pool, user_id=session["user_id"])
    return _serialize(profile)


@router.patch("/profile")
async def update_profile(body: ProfileUpdate, session: dict = Depends(require_session)) -> dict:
    pool = await db.get_pool()
    updated = await db.update_profile_policy_interests(
        pool, user_id=session["user_id"], policy_interests=body.policy_interests
    )
    return _serialize(updated)


def _serialize(row: dict) -> dict:
    return {
        "user_id": str(row["user_id"]),
        "display_name": row["display_name"],
        "bio": row["bio"],
        "policy_interests": list(row["policy_interests"]) if row["policy_interests"] else [],
    }
```

- [ ] **Step 5: Register the router in `app.py`**

In `src/aequitas/api/app.py`, add `profiles` to the import and registration block from Task 5, Step 6:

```python
    from aequitas.api.routers import (
        overview, sections, lsoa, provenance, chat, conversations, metrics, export,
        auth as auth_router, saved_analyses, policy_notes, saved_regions, profiles,
    )
    # ... (existing includes unchanged) ...
    app.include_router(profiles.router, prefix="/api")
```

- [ ] **Step 6: Run tests to verify they pass**

Run: `uv run pytest tests/api/test_profiles.py -v`
Expected: 3 passed (given `DATABASE_URL`/`SESSION_SECRET` set)

- [ ] **Step 7: Commit**

```bash
git add src/aequitas/api/routers/profiles.py src/aequitas/api/auth/db.py src/aequitas/api/app.py tests/api/test_profiles.py
git commit -m "Add user-scoped profiles router (policy_interests only)"
```

---

### Task 7: Confirm no router still imports the old Supabase auth

**Files:** none (verification only)

**Interfaces:**
- Consumes: everything from Tasks 1-6
- Produces: confirmation that Plan 07's later deletion of `src/aequitas/api/auth.py` will have no remaining call sites to break

- [ ] **Step 1: Grep for remaining imports of the old auth module**

Run: `grep -rln "from aequitas.api.auth import\|from aequitas\.api import auth\b" src/aequitas/api/routers/`

Expected: no output, or only matches for `from aequitas.api.auth import db` / `from aequitas.api.auth.dependencies import require_session` / `from aequitas.api.auth.oauth import ...` / `from aequitas.api.auth.email import ...` / `from aequitas.api.auth.sessions import ...` (all referring to the *new* `auth` package, not the old `auth.py` module) — if any router still imports `verify_supabase_jwt` specifically, stop and fix it before proceeding.

- [ ] **Step 2: Grep specifically for `verify_supabase_jwt` usage**

Run: `grep -rn "verify_supabase_jwt" src/aequitas/`

Expected: only the definition inside `src/aequitas/api/auth.py` itself remains — zero call sites in `src/aequitas/api/routers/`.

- [ ] **Step 3: Run the full backend suite**

Run: `uv run pytest tests/ -q`
Expected: all tests pass (given `DATABASE_URL`/`SESSION_SECRET`/`GOOGLE_CLIENT_ID`/`GOOGLE_CLIENT_SECRET` set in the environment) — this is the full regression check before moving to the frontend plans

---

## Handoff

At the end of this plan: every backend route the frontend needs — conversations, chat, export, saved-analyses, policy-notes, saved-regions, profile — is tenant-scoped (or user-scoped for profile) and authenticated via `require_session`, not Supabase JWTs. `src/aequitas/api/auth.py` (old Supabase JWT module) still exists on disk but has zero remaining call sites in `src/aequitas/api/routers/`. The frontend (`AuthContext`, `db.ts`, `ChatSidebar.tsx`, `api/client.ts`) still talks to Supabase — none of it has been touched yet.

Plan `05-frontend-auth-rewrite.md` begins here: it rewrites `AuthContext.tsx`, deletes `lib/db.ts` and `integrations/supabase/client.ts`, and repoints every consumer at the routes this plan built.
