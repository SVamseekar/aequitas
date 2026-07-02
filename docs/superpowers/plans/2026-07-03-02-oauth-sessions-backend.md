# OAuth + Sessions Backend Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the Google OAuth login flow, signed session cookies, and the `require_session`/`require_admin` FastAPI dependencies, plus the `/api/auth/*` and `/api/session/switch-tenant` routes. After this plan, a browser can sign in with Google and get a working session cookie — but no tenant/invite/audit-log management routes exist yet (that's Plan 03), and no existing router (`conversations.py`, `chat.py`, `export.py`) is switched over yet (that's Plan 04).

**Architecture:** New modules in `src/aequitas/api/auth/` (the package Plan 01 scaffolded): `oauth.py` (authlib Google client), `sessions.py` (cookie signing/verification), `dependencies.py` (`require_session`/`require_admin` FastAPI dependencies). New router `src/aequitas/api/routers/auth.py` wires these into HTTP routes, registered in `app.py` alongside the existing routers (additively — nothing is removed from `app.py` in this plan).

**Tech Stack:** `authlib` (new dependency, `starlette_client.OAuth` for Google OIDC discovery), `itsdangerous` (new dependency, `URLSafeTimedSerializer` for cookie signing), the `db.py` functions from Plan 01.

## Global Constraints

- Backend test commands must always be prefixed `uv run`.
- All work happens on `feature/enterprise-oauth-tenancy`.
- Session cookie: httponly, secure, samesite=lax, 7-day expiry (matches WorkforceGuard AI's pattern at `/Users/souravamseekarmarti/Projects/WorkforceGuard-AI/dashboard/backend`).
- `require_session`'s dev-bypass must activate only when `DEV_AUTH_BYPASS=true` AND `ENVIRONMENT` is not `"production"` — matching the existing guard in `src/aequitas/api/auth.py`'s `_is_dev_bypass_allowed()`. This bypass must never fire when `ENVIRONMENT=production`, even if `DEV_AUTH_BYPASS=true` is (incorrectly) set.
- This plan does **not** delete or modify `src/aequitas/api/auth.py` (the old Supabase JWT module) or any existing router — those are updated in Plan 04. Both auth systems coexist during Plans 02-03.
- New `pyproject.toml` dependencies: `"authlib>=1.3.0"`, `"itsdangerous>=2.2.0"`.

---

### Task 1: Add `authlib` and `itsdangerous` dependencies

**Files:**
- Modify: `pyproject.toml`

**Interfaces:**
- Consumes: nothing
- Produces: `authlib` and `itsdangerous` importable in the environment for Tasks 2-3

- [ ] **Step 1: Add dependencies to `pyproject.toml`**

Add `"authlib>=1.3.0",` and `"itsdangerous>=2.2.0",` to the `dependencies` list, alongside `"asyncpg>=0.29.0",` added in Plan 01.

- [ ] **Step 2: Sync**

Run: `uv sync --all-extras`
Expected: completes with both packages installed

- [ ] **Step 3: Verify imports**

Run: `uv run python -c "from authlib.integrations.starlette_client import OAuth; from itsdangerous import URLSafeTimedSerializer; print('ok')"`
Expected: prints `ok`

- [ ] **Step 4: Commit**

```bash
git add pyproject.toml uv.lock
git commit -m "Add authlib and itsdangerous dependencies for OAuth and session signing"
```

---

### Task 2: `sessions.py` — cookie signing and verification

**Files:**
- Create: `src/aequitas/api/auth/sessions.py`
- Test: `tests/api/auth/test_sessions.py`

**Interfaces:**
- Consumes: `ApiConfig().session_secret` (from Plan 01, Task 6)
- Produces: `sign_session_id(session_id: str) -> str` (returns a signed token embedding the session id), `unsign_session_id(token: str, max_age_seconds: int = 604800) -> str | None` (returns the session id, or `None` if the signature is invalid or the token has expired past `max_age_seconds`) — consumed by Task 4's `require_session` and Task 5's login/callback/logout routes. `COOKIE_NAME = "aequitas_session"` and `COOKIE_MAX_AGE_SECONDS = 604800` (7 days) module-level constants — consumed by Task 5's route handlers when setting/clearing the cookie.

- [ ] **Step 1: Write the failing tests**

Create `tests/api/auth/test_sessions.py`:

```python
"""Tests for session cookie signing/verification — no live Postgres required."""
import time

from aequitas.api.auth import sessions


def test_sign_and_unsign_roundtrip(monkeypatch):
    monkeypatch.setenv("SESSION_SECRET", "test-secret")
    token = sessions.sign_session_id("session-id-123")
    result = sessions.unsign_session_id(token)
    assert result == "session-id-123"


def test_unsign_rejects_tampered_token(monkeypatch):
    monkeypatch.setenv("SESSION_SECRET", "test-secret")
    token = sessions.sign_session_id("session-id-123")
    tampered = token[:-1] + ("a" if token[-1] != "a" else "b")
    assert sessions.unsign_session_id(tampered) is None


def test_unsign_rejects_expired_token(monkeypatch):
    monkeypatch.setenv("SESSION_SECRET", "test-secret")
    token = sessions.sign_session_id("session-id-123")
    assert sessions.unsign_session_id(token, max_age_seconds=0) is None


def test_unsign_rejects_garbage_input(monkeypatch):
    monkeypatch.setenv("SESSION_SECRET", "test-secret")
    assert sessions.unsign_session_id("not-a-valid-token") is None


def test_different_secrets_cannot_cross_verify(monkeypatch):
    monkeypatch.setenv("SESSION_SECRET", "secret-a")
    token = sessions.sign_session_id("session-id-123")
    monkeypatch.setenv("SESSION_SECRET", "secret-b")
    assert sessions.unsign_session_id(token) is None


def test_cookie_constants():
    assert sessions.COOKIE_NAME == "aequitas_session"
    assert sessions.COOKIE_MAX_AGE_SECONDS == 604800
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/api/auth/test_sessions.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'aequitas.api.auth.sessions'`

- [ ] **Step 3: Write `sessions.py`**

Create `src/aequitas/api/auth/sessions.py`:

```python
"""Session cookie signing and verification via itsdangerous."""
from __future__ import annotations

from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer

from aequitas.api.config import ApiConfig

COOKIE_NAME = "aequitas_session"
COOKIE_MAX_AGE_SECONDS = 604800  # 7 days, matches WorkforceGuard's pattern


def _serializer() -> URLSafeTimedSerializer:
    cfg = ApiConfig()
    return URLSafeTimedSerializer(cfg.session_secret, salt="aequitas-session-cookie")


def sign_session_id(session_id: str) -> str:
    """Produce a signed, timestamped token embedding the session id."""
    return _serializer().dumps(session_id)


def unsign_session_id(token: str, max_age_seconds: int = COOKIE_MAX_AGE_SECONDS) -> str | None:
    """Recover the session id from a signed token, or None if invalid/expired/tampered."""
    try:
        return _serializer().loads(token, max_age=max_age_seconds)
    except (BadSignature, SignatureExpired):
        return None
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/api/auth/test_sessions.py -v`
Expected: 6 passed

- [ ] **Step 5: Commit**

```bash
git add src/aequitas/api/auth/sessions.py tests/api/auth/test_sessions.py
git commit -m "Add session cookie signing and verification"
```

---

### Task 3: `oauth.py` — Google OAuth client

**Files:**
- Create: `src/aequitas/api/auth/oauth.py`
- Test: `tests/api/auth/test_oauth.py`

**Interfaces:**
- Consumes: `ApiConfig().google_client_id`, `ApiConfig().google_client_secret`
- Produces: `get_google_oauth_client() -> authlib.integrations.starlette_client.OAuth` — a module-level-cached `OAuth` instance with a `google` client registered against Google's OIDC discovery document (`https://accounts.google.com/.well-known/openid-configuration`), consumed by Task 5's login/callback route handlers via `oauth_client.google.authorize_redirect(...)` and `oauth_client.google.authorize_access_token(...)`.

- [ ] **Step 1: Write the failing test**

Create `tests/api/auth/test_oauth.py`:

```python
"""Tests for the Google OAuth client registration."""
from aequitas.api.auth.oauth import get_google_oauth_client


def test_get_google_oauth_client_registers_google(monkeypatch):
    monkeypatch.setenv("GOOGLE_CLIENT_ID", "test-client-id")
    monkeypatch.setenv("GOOGLE_CLIENT_SECRET", "test-client-secret")

    client = get_google_oauth_client()

    assert client.google is not None
    assert client.google.client_id == "test-client-id"


def test_get_google_oauth_client_is_cached(monkeypatch):
    monkeypatch.setenv("GOOGLE_CLIENT_ID", "test-client-id")
    monkeypatch.setenv("GOOGLE_CLIENT_SECRET", "test-client-secret")

    first = get_google_oauth_client()
    second = get_google_oauth_client()

    assert first is second
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/api/auth/test_oauth.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'aequitas.api.auth.oauth'`

- [ ] **Step 3: Write `oauth.py`**

Create `src/aequitas/api/auth/oauth.py`:

```python
"""Google OAuth client via authlib, OIDC discovery against Google's well-known config."""
from __future__ import annotations

from authlib.integrations.starlette_client import OAuth

from aequitas.api.config import ApiConfig

_oauth_client: OAuth | None = None


def get_google_oauth_client() -> OAuth:
    """Return a process-wide OAuth client with Google registered as a provider."""
    global _oauth_client
    if _oauth_client is None:
        cfg = ApiConfig()
        oauth = OAuth()
        oauth.register(
            name="google",
            client_id=cfg.google_client_id,
            client_secret=cfg.google_client_secret,
            server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
            client_kwargs={"scope": "openid email profile"},
        )
        _oauth_client = oauth
    return _oauth_client
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/api/auth/test_oauth.py -v`
Expected: 2 passed

Note: `test_get_google_oauth_client_is_cached` will only pass across the two calls within one test process if `GOOGLE_CLIENT_ID`/`GOOGLE_CLIENT_SECRET` env vars are set identically for both — if this test is flaky because a prior test in the same session already populated `_oauth_client` with different creds, that's expected caching behavior (this module intentionally caches for the life of the process, matching how `authlib`'s `OAuth.register` is meant to be called once at startup) — not a bug to fix.

- [ ] **Step 5: Commit**

```bash
git add src/aequitas/api/auth/oauth.py tests/api/auth/test_oauth.py
git commit -m "Add Google OAuth client registration via authlib"
```

---

### Task 4: `dependencies.py` — `require_session` and `require_admin`

**Files:**
- Create: `src/aequitas/api/auth/dependencies.py`
- Test: `tests/api/auth/test_dependencies.py`

**Interfaces:**
- Consumes: `sessions.unsign_session_id`, `sessions.COOKIE_NAME` (Task 2), `db.get_session`, `db.get_membership`, `db.get_pool` (Plan 01)
- Produces:
  - `async def require_session(request: Request) -> dict` — a FastAPI dependency returning `{"user_id": str, "tenant_id": str, "role": str, "session_id": str}`; raises `HTTPException(401)` if the cookie is missing/invalid/expired, or if the session row itself has expired (`sessions.expires_at < now()`) or no longer has a corresponding `memberships` row for its `tenant_id` (e.g. membership was removed after the session was created). In dev-bypass mode (`DEV_AUTH_BYPASS=true` and `ENVIRONMENT != "production"`) with no cookie present, returns a synthesized `{"user_id": "00000000-0000-0000-0000-000000000001", "tenant_id": "00000000-0000-0000-0000-000000000002", "role": "admin", "session_id": "dev-session"}` instead of 401ing.
  - `async def require_admin(session: dict = Depends(require_session)) -> dict` — re-raises the same dict if `session["role"] == "admin"`, else raises `HTTPException(403)`.

- [ ] **Step 1: Write the failing tests**

Create `tests/api/auth/test_dependencies.py`:

```python
"""Tests for require_session / require_admin dependencies."""
import asyncio
import os
import uuid
from datetime import datetime, timedelta, timezone

import pytest
from fastapi import HTTPException, Request

from aequitas.api.auth import db, dependencies


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
                "TRUNCATE tenants, users, oauth_identities, memberships, sessions CASCADE"
            )

    asyncio.run(_truncate())
    yield


def _make_request(cookie_value: str | None) -> Request:
    headers = []
    if cookie_value is not None:
        headers.append((b"cookie", f"aequitas_session={cookie_value}".encode()))
    scope = {
        "type": "http",
        "headers": headers,
        "method": "GET",
        "path": "/",
        "query_string": b"",
    }
    return Request(scope)


async def _make_session():
    pool = await db.get_pool()
    user = await db.get_or_create_user(
        pool, email="test@example.com", display_name="Test",
        provider="google", provider_subject=f"sub-{uuid.uuid4().hex[:8]}",
    )
    tenant = await db.create_tenant(pool, name="Test Tenant", slug=f"tenant-{uuid.uuid4().hex[:8]}")
    await db.create_membership(pool, user_id=user["id"], tenant_id=tenant["id"], role="admin")
    expires_at = datetime.now(timezone.utc) + timedelta(days=7)
    session = await db.create_session(pool, user_id=user["id"], tenant_id=tenant["id"], expires_at=expires_at)
    return user, tenant, session


def test_require_session_valid_cookie_passes(monkeypatch):
    monkeypatch.setenv("SESSION_SECRET", "test-secret")
    monkeypatch.delenv("DEV_AUTH_BYPASS", raising=False)

    async def _run():
        user, tenant, session = await _make_session()
        from aequitas.api.auth.sessions import sign_session_id
        token = sign_session_id(str(session["id"]))
        request = _make_request(token)
        result = await dependencies.require_session(request)
        return result, user, tenant

    result, user, tenant = asyncio.run(_run())
    assert result["user_id"] == str(user["id"])
    assert result["tenant_id"] == str(tenant["id"])
    assert result["role"] == "admin"


def test_require_session_missing_cookie_raises_401(monkeypatch):
    monkeypatch.setenv("SESSION_SECRET", "test-secret")
    monkeypatch.delenv("DEV_AUTH_BYPASS", raising=False)
    monkeypatch.setenv("ENVIRONMENT", "production")

    async def _run():
        request = _make_request(None)
        await dependencies.require_session(request)

    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(_run())
    assert exc_info.value.status_code == 401


def test_require_session_invalid_cookie_raises_401(monkeypatch):
    monkeypatch.setenv("SESSION_SECRET", "test-secret")
    monkeypatch.delenv("DEV_AUTH_BYPASS", raising=False)
    monkeypatch.setenv("ENVIRONMENT", "production")

    async def _run():
        request = _make_request("garbage-token")
        await dependencies.require_session(request)

    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(_run())
    assert exc_info.value.status_code == 401


def test_require_session_expired_session_row_raises_401(monkeypatch):
    monkeypatch.setenv("SESSION_SECRET", "test-secret")
    monkeypatch.delenv("DEV_AUTH_BYPASS", raising=False)
    monkeypatch.setenv("ENVIRONMENT", "production")

    async def _run():
        pool = await db.get_pool()
        user = await db.get_or_create_user(
            pool, email="expired@example.com", display_name="Expired",
            provider="google", provider_subject=f"sub-{uuid.uuid4().hex[:8]}",
        )
        tenant = await db.create_tenant(pool, name="Expired Tenant", slug=f"tenant-{uuid.uuid4().hex[:8]}")
        await db.create_membership(pool, user_id=user["id"], tenant_id=tenant["id"], role="admin")
        expires_at = datetime.now(timezone.utc) - timedelta(days=1)
        session = await db.create_session(pool, user_id=user["id"], tenant_id=tenant["id"], expires_at=expires_at)

        from aequitas.api.auth.sessions import sign_session_id
        token = sign_session_id(str(session["id"]))
        request = _make_request(token)
        await dependencies.require_session(request)

    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(_run())
    assert exc_info.value.status_code == 401


def test_require_session_dev_bypass_without_cookie(monkeypatch):
    monkeypatch.setenv("SESSION_SECRET", "test-secret")
    monkeypatch.setenv("ENVIRONMENT", "development")
    monkeypatch.setenv("DEV_AUTH_BYPASS", "true")

    async def _run():
        request = _make_request(None)
        return await dependencies.require_session(request)

    result = asyncio.run(_run())
    assert result["role"] == "admin"
    assert result["session_id"] == "dev-session"


def test_require_session_dev_bypass_never_fires_in_production(monkeypatch):
    monkeypatch.setenv("SESSION_SECRET", "test-secret")
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("DEV_AUTH_BYPASS", "true")  # must be ignored

    async def _run():
        request = _make_request(None)
        await dependencies.require_session(request)

    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(_run())
    assert exc_info.value.status_code == 401


def test_require_admin_passes_for_admin_role(monkeypatch):
    monkeypatch.setenv("SESSION_SECRET", "test-secret")

    async def _run():
        user, tenant, session = await _make_session()
        session_dict = {
            "user_id": str(user["id"]), "tenant_id": str(tenant["id"]),
            "role": "admin", "session_id": str(session["id"]),
        }
        return await dependencies.require_admin(session_dict)

    result = asyncio.run(_run())
    assert result["role"] == "admin"


def test_require_admin_raises_403_for_member_role():
    session_dict = {
        "user_id": str(uuid.uuid4()), "tenant_id": str(uuid.uuid4()),
        "role": "member", "session_id": "some-session",
    }

    async def _run():
        await dependencies.require_admin(session_dict)

    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(_run())
    assert exc_info.value.status_code == 403
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/api/auth/test_dependencies.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'aequitas.api.auth.dependencies'` (or SKIPPED for DB-dependent tests if `DATABASE_URL` unset — but the module-not-found failure happens at collection time regardless, since Python imports the module before running individual tests)

- [ ] **Step 3: Write `dependencies.py`**

Create `src/aequitas/api/auth/dependencies.py`:

```python
"""FastAPI dependencies for session and admin-role enforcement."""
from __future__ import annotations

import os
from datetime import datetime, timezone

from fastapi import Depends, HTTPException, Request

from aequitas.api.auth import db
from aequitas.api.auth.sessions import COOKIE_NAME, unsign_session_id

_DEV_USER_ID = "00000000-0000-0000-0000-000000000001"
_DEV_TENANT_ID = "00000000-0000-0000-0000-000000000002"


def _is_dev_bypass_allowed() -> bool:
    env = os.getenv("ENVIRONMENT", "development")
    if env == "production":
        return False
    return os.getenv("DEV_AUTH_BYPASS", "").lower() in ("1", "true", "yes")


async def require_session(request: Request) -> dict:
    """Load and validate the session from the signed cookie.

    Raises 401 if the cookie is missing/invalid/expired, the session row
    has expired, or the session's tenant no longer has a membership for
    this user (e.g. they were removed after the session was issued).
    """
    cookie_value = request.cookies.get(COOKIE_NAME)

    if cookie_value is None:
        if _is_dev_bypass_allowed():
            return {
                "user_id": _DEV_USER_ID,
                "tenant_id": _DEV_TENANT_ID,
                "role": "admin",
                "session_id": "dev-session",
            }
        raise HTTPException(status_code=401, detail="Missing session cookie")

    session_id = unsign_session_id(cookie_value)
    if session_id is None:
        raise HTTPException(status_code=401, detail="Invalid or expired session cookie")

    pool = await db.get_pool()
    session_row = await db.get_session(pool, session_id=session_id)
    if session_row is None:
        raise HTTPException(status_code=401, detail="Session not found")

    if session_row["expires_at"] < datetime.now(timezone.utc):
        raise HTTPException(status_code=401, detail="Session expired")

    membership = await db.get_membership(
        pool, user_id=str(session_row["user_id"]), tenant_id=str(session_row["tenant_id"])
    )
    if membership is None:
        raise HTTPException(status_code=401, detail="No active membership for this session's tenant")

    return {
        "user_id": str(session_row["user_id"]),
        "tenant_id": str(session_row["tenant_id"]),
        "role": membership["role"],
        "session_id": str(session_row["id"]),
    }


async def require_admin(session: dict = Depends(require_session)) -> dict:
    """Wrap require_session, raising 403 if the caller isn't admin in the active tenant."""
    if session["role"] != "admin":
        raise HTTPException(status_code=403, detail="Admin role required")
    return session
```

- [ ] **Step 4: Run tests to verify they pass (if `DATABASE_URL` set) or skip cleanly for DB-dependent cases**

Run: `uv run pytest tests/api/auth/test_dependencies.py -v`
Expected: DB-independent tests (`test_require_admin_raises_403_for_member_role`, `test_require_session_dev_bypass_without_cookie`, `test_require_session_dev_bypass_never_fires_in_production`) always pass; DB-dependent tests pass if `DATABASE_URL` is set to a live Postgres, else skip

- [ ] **Step 5: Commit**

```bash
git add src/aequitas/api/auth/dependencies.py tests/api/auth/test_dependencies.py
git commit -m "Add require_session and require_admin FastAPI dependencies"
```

---

### Task 5: `routers/auth.py` — login, callback, logout, me, switch-tenant

**Files:**
- Create: `src/aequitas/api/routers/auth.py`
- Modify: `src/aequitas/api/app.py`
- Test: `tests/api/test_auth_router.py`

**Interfaces:**
- Consumes: `get_google_oauth_client` (Task 3), `sign_session_id`/`unsign_session_id`/`COOKIE_NAME`/`COOKIE_MAX_AGE_SECONDS` (Task 2), `require_session` (Task 4), `db.get_or_create_user`/`create_tenant`/`create_membership`/`create_session`/`delete_session`/`list_memberships_for_user` (Plan 01)
- Produces: HTTP routes `GET /api/auth/login/google`, `GET /api/auth/callback/google`, `POST /api/auth/logout`, `GET /api/auth/me`, `POST /api/session/switch-tenant` — consumed by Plan 05's `AuthContext.tsx`

- [ ] **Step 1: Write the failing tests**

Create `tests/api/test_auth_router.py`:

```python
"""Tests for the new /api/auth/* and /api/session/* routes."""
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
                "TRUNCATE tenants, users, oauth_identities, memberships, sessions CASCADE"
            )

    asyncio.run(_truncate())
    yield


def test_me_without_session_returns_401(api_client, monkeypatch):
    monkeypatch.delenv("DEV_AUTH_BYPASS", raising=False)
    monkeypatch.setenv("ENVIRONMENT", "production")
    resp = api_client.get("/api/auth/me")
    assert resp.status_code == 401


def test_me_with_dev_bypass_returns_dev_user(api_client):
    """api_client fixture sets DEV_AUTH_BYPASS=true by default."""
    resp = api_client.get("/api/auth/me")
    assert resp.status_code == 200
    body = resp.json()
    assert "user" in body
    assert "active_tenant" in body
    assert "memberships" in body


def test_login_google_redirects(api_client, monkeypatch):
    monkeypatch.setenv("GOOGLE_CLIENT_ID", "test-client-id")
    monkeypatch.setenv("GOOGLE_CLIENT_SECRET", "test-client-secret")
    resp = api_client.get("/api/auth/login/google", follow_redirects=False)
    assert resp.status_code in (302, 307)


def test_callback_google_with_failed_token_exchange_returns_400(api_client, monkeypatch):
    """A malformed/failed OAuth code exchange must return a clean 400, not crash the request."""
    monkeypatch.setenv("GOOGLE_CLIENT_ID", "test-client-id")
    monkeypatch.setenv("GOOGLE_CLIENT_SECRET", "test-client-secret")

    from aequitas.api.auth import oauth as oauth_module

    class _FailingGoogleClient:
        async def authorize_access_token(self, request):
            raise Exception("invalid_grant: malformed authorization code")

    class _FailingOAuth:
        google = _FailingGoogleClient()

    monkeypatch.setattr(oauth_module, "get_google_oauth_client", lambda: _FailingOAuth())

    resp = api_client.get("/api/auth/callback/google", follow_redirects=False)
    assert resp.status_code == 400
    assert "Google OAuth exchange failed" in resp.json()["detail"]


def test_logout_clears_session(api_client):
    resp = api_client.post("/api/auth/logout")
    assert resp.status_code == 200


def test_switch_tenant_without_session_returns_401(api_client, monkeypatch):
    monkeypatch.delenv("DEV_AUTH_BYPASS", raising=False)
    monkeypatch.setenv("ENVIRONMENT", "production")
    resp = api_client.post("/api/session/switch-tenant", json={"tenant_id": "00000000-0000-0000-0000-000000000000"})
    assert resp.status_code == 401


def test_switch_tenant_rejects_tenant_without_membership(api_client):
    """dev-bypass user has no real membership row for an arbitrary tenant id."""
    resp = api_client.post(
        "/api/session/switch-tenant",
        json={"tenant_id": "11111111-1111-1111-1111-111111111111"},
    )
    assert resp.status_code == 403
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/api/test_auth_router.py -v`
Expected: FAIL — route `/api/auth/me` etc. don't exist yet (404s instead of the expected status codes)

- [ ] **Step 3: Write `routers/auth.py`**

Create `src/aequitas/api/routers/auth.py`:

```python
"""Google OAuth login/callback/logout and session-tenant-switch routes."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse
from pydantic import BaseModel

from aequitas.api.auth import db
from aequitas.api.auth.dependencies import require_session
from aequitas.api.auth.oauth import get_google_oauth_client
from aequitas.api.auth.sessions import (
    COOKIE_MAX_AGE_SECONDS,
    COOKIE_NAME,
    sign_session_id,
)
from aequitas.api.config import ApiConfig

router = APIRouter(tags=["auth"])


class SwitchTenantRequest(BaseModel):
    tenant_id: str


@router.get("/auth/login/google")
async def login_google(request: Request):
    oauth = get_google_oauth_client()
    redirect_uri = request.url_for("auth_callback_google")
    return await oauth.google.authorize_redirect(request, redirect_uri)


@router.get("/auth/callback/google", name="auth_callback_google")
async def auth_callback_google(request: Request):
    oauth = get_google_oauth_client()
    try:
        token = await oauth.google.authorize_access_token(request)
    except Exception as exc:
        raise HTTPException(status_code=400, detail="Google OAuth exchange failed") from exc

    userinfo = token.get("userinfo") or {}
    email = userinfo.get("email")
    if not email:
        raise HTTPException(status_code=400, detail="Google account has no email")
    display_name = userinfo.get("name")
    provider_subject = userinfo.get("sub")

    pool = await db.get_pool()
    user = await db.get_or_create_user(
        pool, email=email, display_name=display_name,
        provider="google", provider_subject=provider_subject,
    )

    memberships = await db.list_memberships_for_user(pool, user_id=str(user["id"]))
    if not memberships:
        slug_base = email.split("@")[0].lower().replace(".", "-")
        tenant = await db.create_tenant(pool, name=f"{display_name or email}'s Workspace", slug=f"{slug_base}-{str(user['id'])[:8]}")
        await db.create_membership(pool, user_id=str(user["id"]), tenant_id=str(tenant["id"]), role="admin")
        active_tenant_id = str(tenant["id"])
        await db.get_or_create_profile(pool, user_id=str(user["id"]))
    else:
        active_tenant_id = str(memberships[0]["tenant_id"])

    expires_at = datetime.now(timezone.utc) + timedelta(seconds=COOKIE_MAX_AGE_SECONDS)
    session = await db.create_session(
        pool, user_id=str(user["id"]), tenant_id=active_tenant_id, expires_at=expires_at
    )

    cfg = ApiConfig()
    frontend_origin = cfg.cors_origins[0] if cfg.cors_origins else "http://localhost:5173"
    response = RedirectResponse(url=f"{frontend_origin}/dashboard")
    response.set_cookie(
        COOKIE_NAME,
        sign_session_id(str(session["id"])),
        httponly=True,
        secure=True,
        samesite="lax",
        max_age=COOKIE_MAX_AGE_SECONDS,
    )
    return response


@router.post("/auth/logout")
async def logout(request: Request):
    cookie_value = request.cookies.get(COOKIE_NAME)
    if cookie_value is not None:
        from aequitas.api.auth.sessions import unsign_session_id

        session_id = unsign_session_id(cookie_value)
        if session_id is not None:
            pool = await db.get_pool()
            await db.delete_session(pool, session_id=session_id)

    from fastapi.responses import JSONResponse

    response = JSONResponse({"status": "ok"})
    response.delete_cookie(COOKIE_NAME)
    return response


@router.get("/auth/me")
async def me(session: dict = Depends(require_session)) -> dict:
    pool = await db.get_pool()
    memberships = await db.list_memberships_for_user(pool, user_id=session["user_id"])
    user_row = await db._fetch_user(pool, user_id=session["user_id"])
    active = next((m for m in memberships if str(m["tenant_id"]) == session["tenant_id"]), None)
    return {
        "user": {
            "id": session["user_id"],
            "email": user_row["email"],
            "display_name": user_row["display_name"],
        },
        "active_tenant": {
            "id": session["tenant_id"],
            "name": active["tenant_name"] if active else None,
            "slug": active["tenant_slug"] if active else None,
        },
        "role": session["role"],
        "memberships": [
            {
                "tenant_id": str(m["tenant_id"]),
                "tenant_name": m["tenant_name"],
                "tenant_slug": m["tenant_slug"],
                "role": m["role"],
            }
            for m in memberships
        ],
    }


@router.post("/session/switch-tenant")
async def switch_tenant(
    body: SwitchTenantRequest, session: dict = Depends(require_session)
) -> dict:
    pool = await db.get_pool()
    membership = await db.get_membership(pool, user_id=session["user_id"], tenant_id=body.tenant_id)
    if membership is None:
        raise HTTPException(status_code=403, detail="Not a member of this tenant")
    await db.update_session_tenant(pool, session_id=session["session_id"], tenant_id=body.tenant_id)
    return {"status": "ok", "active_tenant_id": body.tenant_id}
```

- [ ] **Step 4: Add `_fetch_user` and `get_or_create_profile` helpers to `db.py`**

`routers/auth.py` above calls two `db.py` functions that don't exist yet from Plan 01. Append to `src/aequitas/api/auth/db.py`:

```python


async def _fetch_user(pool: asyncpg.Pool, *, user_id: str) -> dict:
    async with pool.acquire() as conn:
        row = await conn.fetchrow("SELECT * FROM users WHERE id = $1", user_id)
        return dict(row)


async def get_or_create_profile(pool: asyncpg.Pool, *, user_id: str) -> dict:
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            INSERT INTO profiles (user_id)
            VALUES ($1)
            ON CONFLICT (user_id) DO UPDATE SET user_id = EXCLUDED.user_id
            RETURNING *
            """,
            user_id,
        )
        return dict(row)
```

- [ ] **Step 5: Register the router in `app.py`**

In `src/aequitas/api/app.py`, update the router import and registration block:

```python
    from aequitas.api.routers import overview, sections, lsoa, provenance, chat, conversations, metrics, export, auth as auth_router
    app.include_router(overview.router, prefix="/api")
    app.include_router(sections.router, prefix="/api")
    app.include_router(lsoa.router, prefix="/api")
    app.include_router(provenance.router, prefix="/api")
    app.include_router(chat.router, prefix="/api")
    app.include_router(conversations.router, prefix="/api")
    app.include_router(metrics.router, prefix="/api")
    app.include_router(export.router, prefix="/api")
    app.include_router(auth_router.router, prefix="/api")
```

Also add `session_secret`-based `SessionMiddleware` registration required by `authlib`'s `authorize_redirect`/`authorize_access_token` (they store OAuth state in `request.session`). Add to `create_app()`, after the existing `CORSMiddleware` registration:

```python
    from starlette.middleware.sessions import SessionMiddleware
    app.add_middleware(SessionMiddleware, secret_key=cfg.session_secret or "dev-insecure-secret-change-me")
```

- [ ] **Step 6: Run tests to verify they pass**

Run: `uv run pytest tests/api/test_auth_router.py -v`
Expected: 7 passed if `DATABASE_URL` is set to a live local Postgres and `SESSION_SECRET` is set in the environment; if `DATABASE_URL` is unset, the DB-touching tests (`test_me_with_dev_bypass_returns_dev_user`, `test_switch_tenant_rejects_tenant_without_membership`) will fail rather than skip (they don't call `_requires_database_url()` directly — they rely on `api_client`'s dev-bypass short-circuit, which itself calls `db.get_pool()` inside `require_session`). If those two fail with a `KeyError: 'DATABASE_URL'` when no Postgres is configured, that's expected in an environment with no local Postgres — set `DATABASE_URL` before running this step. This is the first plan where dev-bypass mode itself depends on a live database (because `require_session`'s dev-bypass path returns synthetic IDs but `/me` and `/switch-tenant` still call `db.py` functions with those IDs) — note this dependency for later manual verification in Plan 07.

- [ ] **Step 7: Run the full existing backend suite to confirm no regressions**

Run: `uv run pytest tests/ -q`
Expected: all previously-passing tests (509 at spec time) still pass, plus this plan's new tests

- [ ] **Step 8: Commit**

```bash
git add src/aequitas/api/routers/auth.py src/aequitas/api/app.py src/aequitas/api/auth/db.py tests/api/test_auth_router.py
git commit -m "Add Google OAuth login/callback/logout/me and tenant-switch routes"
```

---

## Handoff

At the end of this plan: a browser can hit `/api/auth/login/google`, complete the Google consent screen, land back at `/api/auth/callback/google`, and receive a signed session cookie. `/api/auth/me` and `/api/session/switch-tenant` work against that cookie. The old Supabase JWT auth (`src/aequitas/api/auth.py`) and all existing routers are untouched and still functioning in parallel — nothing has been cut over yet.

Plan `03-tenants-invites-audit.md` begins here: it adds the admin-only tenant/invite/member-management/audit-log routes on top of `require_admin` from this plan.
