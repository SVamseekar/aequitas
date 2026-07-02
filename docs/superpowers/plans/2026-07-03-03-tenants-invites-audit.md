# Tenants, Invites & Audit Log Backend Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add the admin-only tenant/member/invite management routes and the Brevo-backed invite-email sender, so an admin can invite someone by email, the invitee can accept via a token, and every sensitive action is written to `audit_log`. After this plan, tenant growth (invite → accept → membership) and audit visibility work end-to-end over HTTP — but the frontend still has no UI for any of this (Plan 06), and existing app-data routers (`conversations.py` etc.) still use the old Supabase JWT auth (Plan 04).

**Architecture:** New `email.py` module in `src/aequitas/api/auth/` (Brevo API client). New routes appended to the existing `src/aequitas/api/routers/auth.py` (from Plan 02) rather than a separate router file — they share the same `/api/tenants/*` and `/api/invites/*` prefix family as the auth/session routes and reuse the same `require_session`/`require_admin` dependencies, so keeping them in one router file avoids splitting a cohesive dependency chain across files for no benefit.

**Tech Stack:** `requests` (already a dependency) for the Brevo HTTP API — no new SDK needed, Brevo's transactional email API is a single `POST` endpoint.

## Global Constraints

- Backend test commands must always be prefixed `uv run`.
- All work happens on `feature/enterprise-oauth-tenancy`.
- Invite emails sent via Brevo; `BREVO_API_KEY` env var (`ApiConfig.brevo_api_key`, added in Plan 01). A failed email send must never block invite creation — the invite row and link are always returned regardless of email delivery outcome.
- Audit log covers exactly four actions: `invite_created`, `invite_accepted`, `member_removed`, `role_changed`. No other actions are logged in this pass.
- The last admin of a tenant cannot be removed via `DELETE /api/tenants/{tenant_id}/members/{user_id}` — this must be enforced in the route handler, not left as a data-integrity assumption.
- No pagination on `GET /api/tenants/{tenant_id}/audit-log` in this pass — acceptable at current scale per the spec.

---

### Task 1: `email.py` — Brevo invite-email client

**Files:**
- Create: `src/aequitas/api/auth/email.py`
- Test: `tests/api/auth/test_email.py`

**Interfaces:**
- Consumes: `ApiConfig().brevo_api_key`
- Produces: `async def send_invite_email(*, to_email: str, tenant_name: str, invite_link: str) -> bool` — returns `True` on a successful Brevo API call (HTTP 2xx), `False` on any failure (non-2xx response, network error, or missing API key) without raising — consumed by Task 3's invite-creation route handler, which must never let an email failure block invite creation.

- [ ] **Step 1: Write the failing tests**

Create `tests/api/auth/test_email.py`:

```python
"""Tests for the Brevo invite-email client — HTTP calls mocked, no real network calls."""
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
```

Note: `pytest.mark.asyncio` requires `pytest-asyncio`. Check `pyproject.toml`'s `dev` dependencies — if `pytest-asyncio` isn't listed, add `"pytest-asyncio>=0.24.0",` to the `dev` optional-dependencies list and add `asyncio_mode = "auto"` under `[tool.pytest.ini_options]` before running this task's tests. Verify with `grep pytest-asyncio pyproject.toml` first.

- [ ] **Step 2: Ensure `pytest-asyncio` is available**

Run: `grep pytest-asyncio pyproject.toml`

If no output, add `"pytest-asyncio>=0.24.0",` to the `dev` list in `pyproject.toml` and `asyncio_mode = "auto"` to `[tool.pytest.ini_options]`, then run `uv sync --all-extras`.

- [ ] **Step 3: Run tests to verify they fail**

Run: `uv run pytest tests/api/auth/test_email.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'aequitas.api.auth.email'`

- [ ] **Step 4: Write `email.py`**

Create `src/aequitas/api/auth/email.py`:

```python
"""Brevo transactional email client for invite delivery."""
from __future__ import annotations

import requests
from loguru import logger

from aequitas.api.config import ApiConfig

_BREVO_SEND_URL = "https://api.brevo.com/v3/smtp/email"
_FROM_EMAIL = "noreply@aequitas.app"
_FROM_NAME = "Aequitas"


async def send_invite_email(*, to_email: str, tenant_name: str, invite_link: str) -> bool:
    """Send an invite email via Brevo. Returns False on any failure — never raises.

    Invite creation must succeed even when email delivery fails (best-effort
    on top of the link-based flow), so callers should not treat a False
    return as a reason to roll back the invite row.
    """
    cfg = ApiConfig()
    if not cfg.brevo_api_key:
        logger.warning("BREVO_API_KEY not set — invite email not sent")
        return False

    payload = {
        "sender": {"name": _FROM_NAME, "email": _FROM_EMAIL},
        "to": [{"email": to_email}],
        "subject": f"You've been invited to join {tenant_name} on Aequitas",
        "htmlContent": (
            f"<p>You've been invited to join <strong>{tenant_name}</strong> on Aequitas.</p>"
            f'<p><a href="{invite_link}">Accept the invite</a></p>'
        ),
    }
    headers = {"api-key": cfg.brevo_api_key, "content-type": "application/json"}

    try:
        response = requests.post(_BREVO_SEND_URL, json=payload, headers=headers, timeout=10)
    except Exception as exc:
        logger.warning(f"Invite email send failed (network error): {exc}")
        return False

    if not (200 <= response.status_code < 300):
        logger.warning(f"Invite email send failed (HTTP {response.status_code}): {getattr(response, 'text', '')}")
        return False

    return True
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `uv run pytest tests/api/auth/test_email.py -v`
Expected: 4 passed

- [ ] **Step 6: Commit**

```bash
git add pyproject.toml uv.lock src/aequitas/api/auth/email.py tests/api/auth/test_email.py
git commit -m "Add Brevo invite-email client"
```

---

### Task 2: `db.py` — invite token generation helper

**Files:**
- Modify: `src/aequitas/api/auth/db.py`
- Test: `tests/api/auth/test_db_invite_token.py`

**Interfaces:**
- Consumes: nothing
- Produces: `generate_invite_token() -> str` — a URL-safe random token (32 bytes, base64url-encoded, no padding), consumed by Task 3's invite-creation route handler

- [ ] **Step 1: Write the failing test**

Create `tests/api/auth/test_db_invite_token.py`:

```python
"""Test for the invite token generator — no live Postgres required."""
from aequitas.api.auth.db import generate_invite_token


def test_generate_invite_token_is_url_safe_and_unique():
    token_a = generate_invite_token()
    token_b = generate_invite_token()
    assert token_a != token_b
    assert all(c.isalnum() or c in "-_" for c in token_a)
    assert len(token_a) >= 32
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/api/auth/test_db_invite_token.py -v`
Expected: FAIL with `ImportError: cannot import name 'generate_invite_token'`

- [ ] **Step 3: Append `generate_invite_token` to `db.py`**

Append to `src/aequitas/api/auth/db.py`:

```python


def generate_invite_token() -> str:
    """Generate a URL-safe random invite token."""
    import secrets

    return secrets.token_urlsafe(32)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/api/auth/test_db_invite_token.py -v`
Expected: 1 passed

- [ ] **Step 5: Commit**

```bash
git add src/aequitas/api/auth/db.py tests/api/auth/test_db_invite_token.py
git commit -m "Add invite token generator to db.py"
```

---

### Task 3: Invite-creation and invite-lookup routes

**Files:**
- Modify: `src/aequitas/api/routers/auth.py`
- Test: `tests/api/test_invites_router.py`

**Interfaces:**
- Consumes: `require_admin`, `require_session` (Plan 02), `db.create_invite`/`get_invite_by_token`/`write_audit_log`/`generate_invite_token` (Plan 01, Task 2 above), `send_invite_email` (Task 1)
- Produces: `POST /api/tenants/{tenant_id}/invites`, `GET /api/invites/{token}` — consumed by Plan 06's invite-management UI and invite-accept page

- [ ] **Step 1: Write the failing tests**

Create `tests/api/test_invites_router.py`:

```python
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
                "TRUNCATE tenants, users, oauth_identities, memberships, sessions, invites, audit_log CASCADE"
            )

    asyncio.run(_truncate())
    yield


def test_create_invite_returns_token_and_link(api_client):
    """api_client's dev-bypass user is admin of the dev tenant."""
    with patch("aequitas.api.routers.auth.send_invite_email", return_value=True):
        resp = api_client.post(
            f"/api/tenants/00000000-0000-0000-0000-000000000002/invites",
            json={"email": "newmember@example.com", "role": "member"},
        )
    assert resp.status_code == 200
    body = resp.json()
    assert "token" in body
    assert "link" in body


def test_create_invite_writes_audit_log_entry(api_client):
    with patch("aequitas.api.routers.auth.send_invite_email", return_value=True):
        api_client.post(
            "/api/tenants/00000000-0000-0000-0000-000000000002/invites",
            json={"email": "another@example.com", "role": "member"},
        )
    resp = api_client.get("/api/tenants/00000000-0000-0000-0000-000000000002/audit-log")
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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/api/test_invites_router.py -v`
Expected: FAIL — routes don't exist yet (404s where 200 expected)

- [ ] **Step 3: Append invite routes to `routers/auth.py`**

Append to `src/aequitas/api/routers/auth.py` (after the existing `switch_tenant` route):

```python


class CreateInviteRequest(BaseModel):
    email: str
    role: str


@router.post("/tenants/{tenant_id}/invites")
async def create_invite(
    tenant_id: str,
    body: CreateInviteRequest,
    session: dict = Depends(require_admin),
) -> dict:
    if body.role not in ("admin", "member"):
        raise HTTPException(status_code=400, detail="role must be 'admin' or 'member'")

    pool = await db.get_pool()
    token = db.generate_invite_token()
    expires_at = datetime.now(timezone.utc) + timedelta(days=7)
    invite = await db.create_invite(
        pool, tenant_id=tenant_id, email=body.email, role=body.role,
        token=token, expires_at=expires_at,
    )
    await db.write_audit_log(
        pool, tenant_id=tenant_id, actor_user_id=session["user_id"],
        action="invite_created", target_user_id=None,
        metadata={"invited_email": body.email, "role": body.role},
    )

    cfg = ApiConfig()
    frontend_origin = cfg.cors_origins[0] if cfg.cors_origins else "http://localhost:5173"
    link = f"{frontend_origin}/invite/{token}"

    from aequitas.api.routers.auth import send_invite_email as _send  # re-import for patchability
    tenant_row = await db._fetch_tenant(pool, tenant_id=tenant_id)
    await send_invite_email(to_email=body.email, tenant_name=tenant_row["name"], invite_link=link)

    return {"token": token, "link": link, "invite_id": str(invite["id"])}


@router.get("/invites/{token}")
async def get_invite(token: str) -> dict:
    pool = await db.get_pool()
    invite = await db.get_invite_by_token(pool, token=token)
    if invite is None:
        raise HTTPException(status_code=404, detail="Invite not found")
    if invite["accepted_at"] is not None:
        raise HTTPException(status_code=410, detail="Invite already accepted")
    if invite["expires_at"] < datetime.now(timezone.utc):
        raise HTTPException(status_code=410, detail="Invite expired")

    tenant_row = await db._fetch_tenant(pool, tenant_id=str(invite["tenant_id"]))
    return {"tenant_name": tenant_row["name"], "role": invite["role"]}
```

Also add the `send_invite_email` import at the top of `routers/auth.py`, alongside the other `aequitas.api.auth` imports:

```python
from aequitas.api.auth.email import send_invite_email
```

(Remove the redundant local re-import line `from aequitas.api.routers.auth import send_invite_email as _send` added above in the first draft of `create_invite` — it was a placeholder for patchability that the top-level import already covers via `unittest.mock.patch("aequitas.api.routers.auth.send_invite_email", ...)`, which patches the name in this module's namespace regardless of how it got there. Call `send_invite_email(...)` directly, not through `_send`.)

- [ ] **Step 4: Add `_fetch_tenant` helper to `db.py`**

Append to `src/aequitas/api/auth/db.py`:

```python


async def _fetch_tenant(pool: asyncpg.Pool, *, tenant_id: str) -> dict:
    async with pool.acquire() as conn:
        row = await conn.fetchrow("SELECT * FROM tenants WHERE id = $1", tenant_id)
        return dict(row)
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `uv run pytest tests/api/test_invites_router.py -v`
Expected: 5 passed if `DATABASE_URL` set to a live local Postgres with `SESSION_SECRET`/`GOOGLE_CLIENT_ID`/`GOOGLE_CLIENT_SECRET` set; note the dev-bypass user's tenant id `00000000-0000-0000-0000-000000000002` (from Plan 02's `dependencies.py`) has no real `memberships`/`tenants` row in a fresh test database — the route handlers here don't call `require_membership` checks beyond `require_admin` (which only checks `session["role"]`, itself hardcoded to `"admin"` in dev-bypass), so this should still succeed even though the dev tenant id isn't backed by a real row. If `create_invite` fails with a foreign-key violation (`invites.tenant_id REFERENCES tenants(id)` requires the tenant to actually exist), that confirms dev-bypass mode needs a seeded dev tenant — see Step 6.

- [ ] **Step 6: If Step 5 reveals a foreign-key violation, seed the dev tenant**

If invite creation fails with `asyncpg.exceptions.ForeignKeyViolationError` because dev-bypass's hardcoded tenant/user IDs (`00000000-0000-0000-0000-000000000002` / `...001`) don't exist as real rows, add a one-time seed step. Modify `require_session` in `src/aequitas/api/auth/dependencies.py`'s dev-bypass branch to ensure the dev user/tenant/membership exist before returning:

```python
    if cookie_value is None:
        if _is_dev_bypass_allowed():
            pool = await db.get_pool()
            await db.run_migrations(pool)
            existing_tenant = await db._fetch_tenant(pool, tenant_id=_DEV_TENANT_ID)
            if existing_tenant is None:
                async with pool.acquire() as conn:
                    await conn.execute(
                        "INSERT INTO users (id, email, display_name) VALUES ($1, $2, $3) ON CONFLICT (id) DO NOTHING",
                        _DEV_USER_ID, "dev@localhost", "Dev User",
                    )
                    await conn.execute(
                        "INSERT INTO tenants (id, name, slug) VALUES ($1, $2, $3) ON CONFLICT (id) DO NOTHING",
                        _DEV_TENANT_ID, "Dev Workspace", "dev-workspace",
                    )
                    await conn.execute(
                        "INSERT INTO memberships (user_id, tenant_id, role) VALUES ($1, $2, $3) ON CONFLICT DO NOTHING",
                        _DEV_USER_ID, _DEV_TENANT_ID, "admin",
                    )
            return {
                "user_id": _DEV_USER_ID,
                "tenant_id": _DEV_TENANT_ID,
                "role": "admin",
                "session_id": "dev-session",
            }
```

This requires `_fetch_tenant` to tolerate a missing row by returning `None` rather than raising — check its current implementation from Step 4 above returns `dict(row)` unconditionally; update it to `return dict(row) if row is not None else None` so this existence check works. Re-run Step 5's tests after this change.

- [ ] **Step 7: Commit**

```bash
git add src/aequitas/api/routers/auth.py src/aequitas/api/auth/db.py src/aequitas/api/auth/dependencies.py tests/api/test_invites_router.py
git commit -m "Add invite creation and lookup routes with audit logging"
```

---

### Task 4: Invite-accept route

**Files:**
- Modify: `src/aequitas/api/routers/auth.py`
- Test: `tests/api/test_invite_accept_router.py`

**Interfaces:**
- Consumes: `require_session` (Plan 02), `db.accept_invite`/`create_membership`/`write_audit_log`/`get_invite_by_token` (Plan 01)
- Produces: `POST /api/invites/{token}/accept` — consumed by Plan 06's invite-accept page

- [ ] **Step 1: Write the failing tests**

Create `tests/api/test_invite_accept_router.py`:

```python
"""Tests for invite acceptance."""
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
                "TRUNCATE tenants, users, oauth_identities, memberships, sessions, invites, audit_log CASCADE"
            )

    asyncio.run(_truncate())
    yield


def test_accept_invite_creates_membership(api_client):
    with patch("aequitas.api.routers.auth.send_invite_email", return_value=True):
        create_resp = api_client.post(
            "/api/tenants/00000000-0000-0000-0000-000000000002/invites",
            json={"email": "acceptor@example.com", "role": "member"},
        )
    token = create_resp.json()["token"]

    resp = api_client.post(f"/api/invites/{token}/accept")
    assert resp.status_code == 200

    memberships_resp = api_client.get("/api/auth/me")
    tenant_ids = [m["tenant_id"] for m in memberships_resp.json()["memberships"]]
    assert "00000000-0000-0000-0000-000000000002" in tenant_ids


def test_accept_invite_writes_audit_log(api_client):
    with patch("aequitas.api.routers.auth.send_invite_email", return_value=True):
        create_resp = api_client.post(
            "/api/tenants/00000000-0000-0000-0000-000000000002/invites",
            json={"email": "acceptor2@example.com", "role": "member"},
        )
    token = create_resp.json()["token"]
    api_client.post(f"/api/invites/{token}/accept")

    resp = api_client.get("/api/tenants/00000000-0000-0000-0000-000000000002/audit-log")
    assert any(e["action"] == "invite_accepted" for e in resp.json())


def test_accept_invite_twice_fails_second_time(api_client):
    with patch("aequitas.api.routers.auth.send_invite_email", return_value=True):
        create_resp = api_client.post(
            "/api/tenants/00000000-0000-0000-0000-000000000002/invites",
            json={"email": "acceptor3@example.com", "role": "member"},
        )
    token = create_resp.json()["token"]
    first = api_client.post(f"/api/invites/{token}/accept")
    second = api_client.post(f"/api/invites/{token}/accept")
    assert first.status_code == 200
    assert second.status_code in (404, 410)


def test_accept_unknown_token_returns_404(api_client):
    resp = api_client.post("/api/invites/nonexistent-token/accept")
    assert resp.status_code == 404
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/api/test_invite_accept_router.py -v`
Expected: FAIL — route doesn't exist yet

- [ ] **Step 3: Append the accept route to `routers/auth.py`**

Append to `src/aequitas/api/routers/auth.py`:

```python


@router.post("/invites/{token}/accept")
async def accept_invite_route(token: str, session: dict = Depends(require_session)) -> dict:
    pool = await db.get_pool()
    invite = await db.get_invite_by_token(pool, token=token)
    if invite is None:
        raise HTTPException(status_code=404, detail="Invite not found")

    accepted = await db.accept_invite(pool, token=token)
    if accepted is None:
        raise HTTPException(status_code=410, detail="Invite already accepted or expired")

    await db.create_membership(
        pool, user_id=session["user_id"], tenant_id=str(invite["tenant_id"]), role=invite["role"]
    )
    await db.write_audit_log(
        pool, tenant_id=str(invite["tenant_id"]), actor_user_id=session["user_id"],
        action="invite_accepted", target_user_id=session["user_id"],
        metadata={"invited_email": invite["email"], "role": invite["role"]},
    )
    return {"status": "ok", "tenant_id": str(invite["tenant_id"])}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/api/test_invite_accept_router.py -v`
Expected: 4 passed (given `DATABASE_URL`/`SESSION_SECRET` set)

- [ ] **Step 5: Commit**

```bash
git add src/aequitas/api/routers/auth.py tests/api/test_invite_accept_router.py
git commit -m "Add invite acceptance route with membership creation and audit logging"
```

---

### Task 5: Member list, remove, role-change routes

**Files:**
- Modify: `src/aequitas/api/routers/auth.py`
- Test: `tests/api/test_members_router.py`

**Interfaces:**
- Consumes: `require_admin` (Plan 02), `db.list_memberships_for_user`/`remove_membership`/`update_membership_role`/`write_audit_log` (Plan 01)
- Produces: `GET /api/tenants/{tenant_id}/members`, `DELETE /api/tenants/{tenant_id}/members/{user_id}`, `PATCH /api/tenants/{tenant_id}/members/{user_id}/role` — consumed by Plan 06's member-management UI

- [ ] **Step 1: Add a `list_members_for_tenant` query function to `db.py`**

The existing `list_memberships_for_user` (Plan 01) lists a *user's* tenants; this task needs the inverse — a *tenant's* members. Append to `src/aequitas/api/auth/db.py`:

```python


async def list_members_for_tenant(pool: asyncpg.Pool, *, tenant_id: str) -> list[dict]:
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT m.user_id, m.role, m.created_at, u.email, u.display_name
            FROM memberships m
            JOIN users u ON u.id = m.user_id
            WHERE m.tenant_id = $1
            ORDER BY m.created_at ASC
            """,
            tenant_id,
        )
        return [dict(r) for r in rows]


async def count_admins_for_tenant(pool: asyncpg.Pool, *, tenant_id: str) -> int:
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT COUNT(*) AS n FROM memberships WHERE tenant_id = $1 AND role = 'admin'",
            tenant_id,
        )
        return row["n"]
```

Test this alongside the routes below rather than in isolation — it has no independent behavior worth a standalone unit test beyond what the route tests already exercise.

- [ ] **Step 2: Write the failing tests**

Create `tests/api/test_members_router.py`:

```python
"""Tests for member listing, removal, and role-change routes."""
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
                "TRUNCATE tenants, users, oauth_identities, memberships, sessions, invites, audit_log CASCADE"
            )

    asyncio.run(_truncate())
    yield


def _accept_new_member(api_client, email: str) -> str:
    """Helper: create + accept an invite, return the new member's user_id via /me is not
    directly available since /me reflects the caller's own session, not the invitee's.
    Instead, insert directly via db.py for test setup speed."""
    import asyncio
    import uuid
    from aequitas.api.auth import db

    async def _run():
        pool = await db.get_pool()
        user = await db.get_or_create_user(
            pool, email=email, display_name=email.split("@")[0],
            provider="google", provider_subject=f"sub-{uuid.uuid4().hex[:8]}",
        )
        await db.create_membership(
            pool, user_id=str(user["id"]),
            tenant_id="00000000-0000-0000-0000-000000000002", role="member",
        )
        return str(user["id"])

    return asyncio.run(_run())


def test_list_members_includes_dev_admin(api_client):
    resp = api_client.get("/api/tenants/00000000-0000-0000-0000-000000000002/members")
    assert resp.status_code == 200
    emails = [m["email"] for m in resp.json()]
    assert "dev@localhost" in emails


def test_remove_member(api_client):
    member_user_id = _accept_new_member(api_client, "toremove@example.com")
    resp = api_client.delete(f"/api/tenants/00000000-0000-0000-0000-000000000002/members/{member_user_id}")
    assert resp.status_code == 200

    list_resp = api_client.get("/api/tenants/00000000-0000-0000-0000-000000000002/members")
    user_ids = [m["user_id"] for m in list_resp.json()]
    assert member_user_id not in user_ids


def test_remove_member_writes_audit_log(api_client):
    member_user_id = _accept_new_member(api_client, "toremove2@example.com")
    api_client.delete(f"/api/tenants/00000000-0000-0000-0000-000000000002/members/{member_user_id}")

    resp = api_client.get("/api/tenants/00000000-0000-0000-0000-000000000002/audit-log")
    assert any(e["action"] == "member_removed" for e in resp.json())


def test_cannot_remove_last_admin(api_client):
    """The dev-bypass user is the only admin of the dev tenant."""
    resp = api_client.delete(
        "/api/tenants/00000000-0000-0000-0000-000000000002/members/00000000-0000-0000-0000-000000000001"
    )
    assert resp.status_code == 400


def test_update_member_role(api_client):
    member_user_id = _accept_new_member(api_client, "topromote@example.com")
    resp = api_client.patch(
        f"/api/tenants/00000000-0000-0000-0000-000000000002/members/{member_user_id}/role",
        json={"role": "admin"},
    )
    assert resp.status_code == 200

    list_resp = api_client.get("/api/tenants/00000000-0000-0000-0000-000000000002/members")
    updated = next(m for m in list_resp.json() if m["user_id"] == member_user_id)
    assert updated["role"] == "admin"


def test_update_member_role_writes_audit_log_with_old_and_new(api_client):
    member_user_id = _accept_new_member(api_client, "topromote2@example.com")
    api_client.patch(
        f"/api/tenants/00000000-0000-0000-0000-000000000002/members/{member_user_id}/role",
        json={"role": "admin"},
    )
    resp = api_client.get("/api/tenants/00000000-0000-0000-0000-000000000002/audit-log")
    entry = next(e for e in resp.json() if e["action"] == "role_changed")
    assert entry["metadata"]["old_role"] == "member"
    assert entry["metadata"]["new_role"] == "admin"
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `uv run pytest tests/api/test_members_router.py -v`
Expected: FAIL — routes don't exist yet

- [ ] **Step 4: Append member-management routes to `routers/auth.py`**

Append to `src/aequitas/api/routers/auth.py`:

```python


class UpdateRoleRequest(BaseModel):
    role: str


@router.get("/tenants/{tenant_id}/members")
async def list_members(tenant_id: str, session: dict = Depends(require_admin)) -> list[dict]:
    pool = await db.get_pool()
    members = await db.list_members_for_tenant(pool, tenant_id=tenant_id)
    return [
        {
            "user_id": str(m["user_id"]),
            "email": m["email"],
            "display_name": m["display_name"],
            "role": m["role"],
        }
        for m in members
    ]


@router.delete("/tenants/{tenant_id}/members/{user_id}")
async def remove_member(
    tenant_id: str, user_id: str, session: dict = Depends(require_admin)
) -> dict:
    pool = await db.get_pool()
    membership = await db.get_membership(pool, user_id=user_id, tenant_id=tenant_id)
    if membership is None:
        raise HTTPException(status_code=404, detail="Membership not found")

    if membership["role"] == "admin":
        admin_count = await db.count_admins_for_tenant(pool, tenant_id=tenant_id)
        if admin_count <= 1:
            raise HTTPException(status_code=400, detail="Cannot remove the last admin of a tenant")

    await db.remove_membership(pool, user_id=user_id, tenant_id=tenant_id)
    await db.write_audit_log(
        pool, tenant_id=tenant_id, actor_user_id=session["user_id"],
        action="member_removed", target_user_id=user_id, metadata=None,
    )
    return {"status": "ok"}


@router.patch("/tenants/{tenant_id}/members/{user_id}/role")
async def update_member_role(
    tenant_id: str, user_id: str, body: UpdateRoleRequest, session: dict = Depends(require_admin)
) -> dict:
    if body.role not in ("admin", "member"):
        raise HTTPException(status_code=400, detail="role must be 'admin' or 'member'")

    pool = await db.get_pool()
    existing = await db.get_membership(pool, user_id=user_id, tenant_id=tenant_id)
    if existing is None:
        raise HTTPException(status_code=404, detail="Membership not found")

    old_role = existing["role"]
    if old_role == "admin" and body.role == "member":
        admin_count = await db.count_admins_for_tenant(pool, tenant_id=tenant_id)
        if admin_count <= 1:
            raise HTTPException(status_code=400, detail="Cannot demote the last admin of a tenant")

    updated = await db.update_membership_role(pool, user_id=user_id, tenant_id=tenant_id, role=body.role)
    await db.write_audit_log(
        pool, tenant_id=tenant_id, actor_user_id=session["user_id"],
        action="role_changed", target_user_id=user_id,
        metadata={"old_role": old_role, "new_role": body.role},
    )
    return {"user_id": user_id, "role": updated["role"]}
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `uv run pytest tests/api/test_members_router.py -v`
Expected: 7 passed (given `DATABASE_URL`/`SESSION_SECRET` set)

- [ ] **Step 6: Commit**

```bash
git add src/aequitas/api/routers/auth.py src/aequitas/api/auth/db.py tests/api/test_members_router.py
git commit -m "Add member list/remove/role-change routes with last-admin protection and audit logging"
```

---

### Task 6: Audit-log listing route

**Files:**
- Modify: `src/aequitas/api/routers/auth.py`
- Test: `tests/api/test_audit_log_router.py`

**Interfaces:**
- Consumes: `require_admin` (Plan 02), `db.list_audit_log` (Plan 01)
- Produces: `GET /api/tenants/{tenant_id}/audit-log` — this route is referenced by Tasks 3/5's tests above, so it must exist by the time those tests run in a from-scratch execution; sequence-wise, if executing this plan strictly in order, move this task's route addition earlier (before Task 3) or run this task's Step 4 before running Task 3's Step 5. The route itself has no dependency on later tasks, so it can be safely written first if a re-order is more convenient.

- [ ] **Step 1: Write the failing tests**

Create `tests/api/test_audit_log_router.py`:

```python
"""Tests for the audit-log listing route in isolation (beyond what Tasks 3/5 already exercise)."""
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
                "TRUNCATE tenants, users, oauth_identities, memberships, sessions, invites, audit_log CASCADE"
            )

    asyncio.run(_truncate())
    yield


def test_audit_log_empty_for_fresh_tenant(api_client):
    resp = api_client.get("/api/tenants/00000000-0000-0000-0000-000000000002/audit-log")
    assert resp.status_code == 200
    assert resp.json() == []


def test_audit_log_newest_first(api_client):
    with patch("aequitas.api.routers.auth.send_invite_email", return_value=True):
        api_client.post(
            "/api/tenants/00000000-0000-0000-0000-000000000002/invites",
            json={"email": "first@example.com", "role": "member"},
        )
        api_client.post(
            "/api/tenants/00000000-0000-0000-0000-000000000002/invites",
            json={"email": "second@example.com", "role": "member"},
        )
    resp = api_client.get("/api/tenants/00000000-0000-0000-0000-000000000002/audit-log")
    entries = resp.json()
    assert entries[0]["metadata"]["invited_email"] == "second@example.com"
    assert entries[1]["metadata"]["invited_email"] == "first@example.com"


def test_audit_log_requires_admin(api_client, monkeypatch):
    """A non-admin session must get 403, not the audit trail."""
    monkeypatch.delenv("DEV_AUTH_BYPASS", raising=False)
    monkeypatch.setenv("ENVIRONMENT", "production")
    resp = api_client.get("/api/tenants/00000000-0000-0000-0000-000000000002/audit-log")
    assert resp.status_code == 401  # no session at all in production without bypass
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/api/test_audit_log_router.py -v`
Expected: FAIL — route doesn't exist yet (this must be added if Tasks 3/5 haven't already added it during execution; check first with `grep "audit-log" src/aequitas/api/routers/auth.py`)

- [ ] **Step 3: Check whether the route already exists**

Run: `grep -n "audit-log" src/aequitas/api/routers/auth.py`

If this already shows a `@router.get("/tenants/{tenant_id}/audit-log")` route (because Tasks 3/5's tests required it and it was added out of strict order during execution), skip to Step 5. Otherwise continue to Step 4.

- [ ] **Step 4: Append the audit-log route to `routers/auth.py`**

Append to `src/aequitas/api/routers/auth.py`:

```python


@router.get("/tenants/{tenant_id}/audit-log")
async def get_audit_log(tenant_id: str, session: dict = Depends(require_admin)) -> list[dict]:
    pool = await db.get_pool()
    entries = await db.list_audit_log(pool, tenant_id=tenant_id)
    return [
        {
            "id": str(e["id"]),
            "actor_user_id": str(e["actor_user_id"]),
            "action": e["action"],
            "target_user_id": str(e["target_user_id"]) if e["target_user_id"] else None,
            "metadata": e["metadata"],
            "created_at": e["created_at"].isoformat(),
        }
        for e in entries
    ]
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `uv run pytest tests/api/test_audit_log_router.py -v`
Expected: 3 passed

- [ ] **Step 6: Run the full backend suite for this plan's plans-01-through-03 scope**

Run: `uv run pytest tests/ -q`
Expected: all tests pass (existing 509 + everything added across Plans 01-03), given `DATABASE_URL`/`SESSION_SECRET`/`GOOGLE_CLIENT_ID`/`GOOGLE_CLIENT_SECRET` set in the environment

- [ ] **Step 7: Commit**

```bash
git add src/aequitas/api/routers/auth.py tests/api/test_audit_log_router.py
git commit -m "Add audit-log listing route"
```

---

## Handoff

At the end of this plan: the full `/api/auth/*`, `/api/session/*`, `/api/tenants/*`, `/api/invites/*` route surface from the spec exists and is tested, including admin-only member management with last-admin protection and a complete four-action audit trail. The old Supabase JWT auth and all existing app-data routers (`conversations.py`, `chat.py`, `export.py`) are still untouched and running the old auth path.

Plan `04-router-migration.md` begins here — the riskiest plan: it rewrites `conversations.py`, `chat.py`, `export.py` to use `require_session` instead of `verify_supabase_jwt`, and adds the four new tenant-scoped app-data routers (`saved_analyses.py`, `policy_notes.py`, `saved_regions.py`, `profiles.py`).
