****# Security Audit Remediation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Close the Critical/High findings from `docs/SECURITY_AUDIT.md` (SEC-001 through SEC-007, plus the consistency fixes in SEC-004/SEC-015) so the API cannot be bypassed via dev-mode auth, the frontend chat path is actually authenticated, the backend stops relying on a service-role Supabase key for user-scoped reads, and known-vulnerable direct dependencies are upgraded.

**Architecture:** No architectural change — this is a hardening pass on existing modules. `auth.py` gets a stricter dev-bypass gate, `useChat.ts` gets the same auth-header pattern already used in `client.ts`, `conversations.py` switches from a service-role Supabase client to a JWT-scoped one (falling back to service-role only for the operations that legitimately need it), and `export.py` gets the same `verify_supabase_jwt` dependency the other mutating/expensive routes use. Dependency bumps are isolated, low-risk version changes verified by the existing test suite.

**Tech Stack:** FastAPI, `python-jose` (JWT), `supabase-py`, pytest, React + TypeScript, Vite, `npm`.

## Global Constraints

- `DEV_AUTH_BYPASS` must never grant access for a *supplied but invalid/expired* token — only for genuinely missing credentials, and only when `ENVIRONMENT != "production"`.
- No behavior change for the already-correct production JWT validation path (valid token → decoded payload; invalid token in production → 401).
- All existing tests in `tests/api/` must continue to pass; `DEV_AUTH_BYPASS=true` is still set in `tests/api/conftest.py` and must continue to work for routes that explicitly omit credentials.
- Frontend changes must not alter the SSE streaming behavior of `useChat.ts` — only the outgoing request gains an `Authorization` header.
- Dependency upgrades must be the minimum version that resolves the named CVE; do not perform unrelated major-version upgrades.

---

## Task 1: Tighten dev auth bypass to never swallow invalid/expired tokens

**Files:**
- Modify: `src/aequitas/api/auth.py:24-67`
- Test: `tests/api/test_auth.py` (new)

**Interfaces:**
- Consumes: `ApiConfig.supabase_jwt_secret` (existing, `src/aequitas/api/config.py:28-30`), `_is_dev_bypass_allowed() -> bool` (existing, `src/aequitas/api/auth.py:16-21`, unchanged)
- Produces: `verify_supabase_jwt(credentials) -> dict` — same signature, but now raises `HTTPException(401)` for any *supplied* invalid/expired token regardless of `DEV_AUTH_BYPASS`. Bypass only applies when `credentials is None` or `supabase_jwt_secret` is unset.

This is SEC-001 / CC-1 from `docs/SECURITY_AUDIT.md`: the `except JWTError` branch at `auth.py:62-65` currently returns `{"sub": "dev-user"}` for a token that was supplied but failed validation, not just for missing credentials. That must stop — bypass should only cover the "no token at all" and "no secret configured" cases that already exist.

- [ ] **Step 1: Write the failing tests**

Create `tests/api/test_auth.py`:

```python
"""Unit tests for verify_supabase_jwt dev-bypass boundary conditions."""
import time

import pytest
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials
from jose import jwt

from aequitas.api.auth import verify_supabase_jwt

SECRET = "test-secret"


def _make_token(secret: str = SECRET, exp_delta: int = 3600, audience: str = "authenticated") -> str:
    payload = {"sub": "real-user", "aud": audience, "exp": int(time.time()) + exp_delta}
    return jwt.encode(payload, secret, algorithm="HS256")


def _creds(token: str) -> HTTPAuthorizationCredentials:
    return HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)


def test_valid_token_returns_payload(monkeypatch):
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("SUPABASE_JWT_SECRET", SECRET)
    monkeypatch.delenv("DEV_AUTH_BYPASS", raising=False)

    payload = verify_supabase_jwt(_creds(_make_token()))
    assert payload["sub"] == "real-user"


def test_invalid_token_with_dev_bypass_still_raises_401(monkeypatch):
    """A *supplied but invalid* token must 401 even when dev bypass is enabled."""
    monkeypatch.setenv("ENVIRONMENT", "development")
    monkeypatch.setenv("DEV_AUTH_BYPASS", "true")
    monkeypatch.setenv("SUPABASE_JWT_SECRET", SECRET)

    bad_token = _make_token(secret="wrong-secret")
    with pytest.raises(HTTPException) as exc_info:
        verify_supabase_jwt(_creds(bad_token))
    assert exc_info.value.status_code == 401


def test_expired_token_with_dev_bypass_still_raises_401(monkeypatch):
    monkeypatch.setenv("ENVIRONMENT", "development")
    monkeypatch.setenv("DEV_AUTH_BYPASS", "true")
    monkeypatch.setenv("SUPABASE_JWT_SECRET", SECRET)

    expired_token = _make_token(exp_delta=-3600)
    with pytest.raises(HTTPException) as exc_info:
        verify_supabase_jwt(_creds(expired_token))
    assert exc_info.value.status_code == 401


def test_missing_credentials_with_dev_bypass_returns_dev_user(monkeypatch):
    monkeypatch.setenv("ENVIRONMENT", "development")
    monkeypatch.setenv("DEV_AUTH_BYPASS", "true")
    monkeypatch.setenv("SUPABASE_JWT_SECRET", SECRET)

    payload = verify_supabase_jwt(None)
    assert payload == {"sub": "dev-user"}


def test_missing_credentials_without_bypass_raises_401(monkeypatch):
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.delenv("DEV_AUTH_BYPASS", raising=False)
    monkeypatch.setenv("SUPABASE_JWT_SECRET", SECRET)

    with pytest.raises(HTTPException) as exc_info:
        verify_supabase_jwt(None)
    assert exc_info.value.status_code == 401


def test_invalid_token_in_production_raises_401(monkeypatch):
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("DEV_AUTH_BYPASS", "true")  # must be ignored in production
    monkeypatch.setenv("SUPABASE_JWT_SECRET", SECRET)

    bad_token = _make_token(secret="wrong-secret")
    with pytest.raises(HTTPException) as exc_info:
        verify_supabase_jwt(_creds(bad_token))
    assert exc_info.value.status_code == 401
```

- [ ] **Step 2: Run tests to verify the new ones fail**

Run: `cd /Users/souravamseekarmarti/Projects/aequitas && uv run pytest tests/api/test_auth.py -v`
Expected: `test_invalid_token_with_dev_bypass_still_raises_401` and `test_expired_token_with_dev_bypass_still_raises_401` FAIL (currently return `dev-user` instead of raising). Other tests should already pass against current code.

- [ ] **Step 3: Remove the `JWTError` dev-bypass fallback**

In `src/aequitas/api/auth.py`, replace the `try/except` block at the end of `verify_supabase_jwt`:

```python
    try:
        payload = jwt.decode(
            credentials.credentials,
            cfg.supabase_jwt_secret,
            algorithms=["HS256"],
            audience="authenticated",
        )
        return payload
    except JWTError as exc:
        if _is_dev_bypass_allowed():
            logger.warning(f"Invalid token ({exc}) — using dev bypass fallback")
            return {"sub": "dev-user"}
        raise HTTPException(status_code=401, detail=f"Invalid token: {exc}") from exc
```

with:

```python
    try:
        payload = jwt.decode(
            credentials.credentials,
            cfg.supabase_jwt_secret,
            algorithms=["HS256"],
            audience="authenticated",
        )
        return payload
    except JWTError as exc:
        # A supplied-but-invalid token must always 401 — dev bypass only
        # covers missing credentials or an unconfigured secret, never a
        # token that was actually presented and failed validation.
        raise HTTPException(status_code=401, detail="Invalid or expired token") from exc
```

Also update the module docstring on `verify_supabase_jwt` to remove the now-incorrect claim that dev bypass covers "an invalid/expired token":

```python
def verify_supabase_jwt(
    credentials: HTTPAuthorizationCredentials | None = Security(_bearer),
) -> dict:
    """Validate Supabase JWT and return decoded payload with user sub.

    Dev mode: when ENVIRONMENT is not production AND DEV_AUTH_BYPASS=true, a
    placeholder dev-user payload is returned only for missing credentials or
    an unconfigured supabase_jwt_secret — never for a token that was supplied
    but failed validation. DEV_AUTH_BYPASS must never be set to true in
    production.
    """
```

This change also fixes SEC-010 (JWT error detail leakage) as a side effect, since the new message no longer interpolates `exc`.

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /Users/souravamseekarmarti/Projects/aequitas && uv run pytest tests/api/test_auth.py -v`
Expected: all 6 tests PASS.

- [ ] **Step 5: Run the full API test suite to check for regressions**

Run: `cd /Users/souravamseekarmarti/Projects/aequitas && uv run pytest tests/api/ -v`
Expected: all tests PASS (existing tests rely on `DEV_AUTH_BYPASS=true` with *missing* credentials via `tests/api/conftest.py`, which is unaffected by this change).

- [ ] **Step 6: Commit**

```bash
git add src/aequitas/api/auth.py tests/api/test_auth.py
git commit -m "fix: dev auth bypass must not swallow invalid/expired tokens (SEC-001)"
```

---

## Task 2: Add Authorization header to chat frontend requests

**Files:**
- Modify: `frontend/src/hooks/useChat.ts:44-55`
- Test: manual verification (no frontend test runner configured for hooks in this repo — see Step 3)

**Interfaces:**
- Consumes: `supabase.auth.getSession()` from `frontend/src/integrations/supabase/client.ts:10-13` (existing export, same pattern `client.ts:11` already uses)
- Produces: no new exports; `sendMessage` callback behavior unchanged except for the added header.

This is SEC-002: `useChat.ts` posts to `/api/chat` with only `Content-Type`, so once SEC-001 is closed and a real deployment has `DEV_AUTH_BYPASS=false`, chat would 401 for every real user. Fix by mirroring the exact pattern `client.ts:11-15` already uses.

- [ ] **Step 1: Add the Supabase session import and build the headers object**

In `frontend/src/hooks/useChat.ts`, add the import at the top of the file:

```typescript
import { useCallback, useRef, useState } from "react"
import { supabase } from "@/integrations/supabase/client"
```

Then replace the `fetch` call inside `sendMessage` (currently lines 45-55):

```typescript
        const resp = await fetch("/api/chat", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          signal: controller.signal,
          body: JSON.stringify({
            query,
            context,
            conversation_id: conversationId.current,
            history: messagesRef.current.slice(-6).map((m) => ({ role: m.role, content: m.content })),
          }),
        })
```

with:

```typescript
        const { data: { session } } = await supabase.auth.getSession()
        const headers: Record<string, string> = { "Content-Type": "application/json" }
        if (session?.access_token) {
          headers["Authorization"] = `Bearer ${session.access_token}`
        }

        const resp = await fetch("/api/chat", {
          method: "POST",
          headers,
          signal: controller.signal,
          body: JSON.stringify({
            query,
            context,
            conversation_id: conversationId.current,
            history: messagesRef.current.slice(-6).map((m) => ({ role: m.role, content: m.content })),
          }),
        })
```

- [ ] **Step 2: Type-check the frontend**

Run: `cd /Users/souravamseekarmarti/Projects/aequitas/frontend && npx tsc --noEmit`
Expected: no errors.

- [ ] **Step 3: Manually verify in the browser**

Run: `cd /Users/souravamseekarmarti/Projects/aequitas/frontend && npm run dev`

Open the app, sign in, open the browser's Network tab, send a chat message, and inspect the `/api/chat` request headers — confirm `Authorization: Bearer <token>` is present. Then sign out and confirm the request either omits the header or the backend correctly 401s (depending on `DEV_AUTH_BYPASS` setting in your local `.env`).

- [ ] **Step 4: Commit**

```bash
git add frontend/src/hooks/useChat.ts
git commit -m "fix: send Authorization header from chat frontend (SEC-002)"
```

---

## Task 3: Replace service-role Supabase client with user-scoped client in conversations router

**Files:**
- Modify: `src/aequitas/api/routers/conversations.py:1-152`
- Test: `tests/api/test_conversations.py` (new)

**Interfaces:**
- Consumes: `verify_supabase_jwt` (existing, `src/aequitas/api/auth.py`), raw JWT string — needs to be threaded through from the `HTTPAuthorizationCredentials` the auth dependency already validates.
- Produces: `_get_supabase(access_token: str | None) -> Any` — changed signature (was `_get_supabase() -> Any`); now builds a client that forwards the caller's JWT to PostgREST so RLS policies in `supabase/migrations/001_initial.sql` are the actual enforcement boundary, not just the application-level `.eq("user_id", ...)` filters.

This is SEC-003 / CC-2. The `supabase-py` client supports per-request auth via `postgrest_client.auth(token)` (exposed as `client.postgrest.auth(token)` in `supabase-py>=2.0`). Because `verify_supabase_jwt` currently only returns the decoded payload dict and discards the raw token, the auth dependency needs a small addition: return the raw token alongside the payload so routers can forward it.

- [ ] **Step 1: Extend `verify_supabase_jwt` to include the raw token in its returned payload**

In `src/aequitas/api/auth.py`, after a successful `jwt.decode`, attach the raw token under a private key so callers can forward it without re-parsing the `Authorization` header:

```python
    try:
        payload = jwt.decode(
            credentials.credentials,
            cfg.supabase_jwt_secret,
            algorithms=["HS256"],
            audience="authenticated",
        )
        payload["_raw_token"] = credentials.credentials
        return payload
    except JWTError as exc:
        raise HTTPException(status_code=401, detail="Invalid or expired token") from exc
```

(The dev-bypass branches that return `{"sub": "dev-user"}` do not have a raw token — leave those untouched; `_get_supabase` will fall back to the service-role key when no raw token is present, which only happens in dev-bypass mode.)

- [ ] **Step 2: Write the failing test for RLS-scoped access**

Create `tests/api/test_conversations.py`:

```python
"""Tests for conversations router Supabase client scoping."""
from unittest.mock import MagicMock, patch

from aequitas.api.routers.conversations import _get_supabase


def test_get_supabase_uses_anon_key_and_forwards_user_token(monkeypatch):
    monkeypatch.setenv("SUPABASE_URL", "https://example.supabase.co")
    monkeypatch.setenv("SUPABASE_ANON_KEY", "anon-key-value")
    monkeypatch.setenv("SUPABASE_SERVICE_ROLE_KEY", "service-role-key-value")

    mock_client = MagicMock()
    with patch("supabase.create_client", return_value=mock_client) as mock_create:
        result = _get_supabase(access_token="user-jwt-token")

    # Must be created with the anon key, never the service-role key, when a
    # user token is available — RLS only applies to the anon/authenticated role.
    mock_create.assert_called_once_with("https://example.supabase.co", "anon-key-value")
    mock_client.postgrest.auth.assert_called_once_with("user-jwt-token")
    assert result is mock_client


def test_get_supabase_falls_back_to_service_role_without_token(monkeypatch):
    """Dev-bypass mode has no raw JWT — fall back to service role so dev flows keep working."""
    monkeypatch.setenv("SUPABASE_URL", "https://example.supabase.co")
    monkeypatch.setenv("SUPABASE_ANON_KEY", "anon-key-value")
    monkeypatch.setenv("SUPABASE_SERVICE_ROLE_KEY", "service-role-key-value")

    mock_client = MagicMock()
    with patch("supabase.create_client", return_value=mock_client) as mock_create:
        _get_supabase(access_token=None)

    mock_create.assert_called_once_with("https://example.supabase.co", "service-role-key-value")
```

- [ ] **Step 3: Run the test to verify it fails**

Run: `cd /Users/souravamseekarmarti/Projects/aequitas && uv run pytest tests/api/test_conversations.py -v`
Expected: FAIL — `_get_supabase()` does not currently accept an `access_token` parameter (`TypeError: _get_supabase() takes 0 positional arguments but 1 was given`).

- [ ] **Step 4: Rewrite `_get_supabase` and thread the token through every route**

In `src/aequitas/api/routers/conversations.py`, replace the existing `_get_supabase` function (lines 33-45):

```python
def _get_supabase() -> Any:
    """Return Supabase admin client, or raise 503 if not configured."""
    try:
        import os
        from supabase import create_client  # type: ignore[import-untyped]

        url = os.environ.get("SUPABASE_URL", "")
        key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "")
        if not url or not key:
            raise RuntimeError("Supabase not configured")
        return create_client(url, key)
    except Exception as exc:
        raise HTTPException(503, "Supabase unavailable") from exc
```

with:

```python
def _get_supabase(access_token: str | None) -> Any:
    """Return a Supabase client scoped to the caller's JWT so RLS applies.

    Falls back to the service-role key only when no user token is available
    (dev-bypass mode), so existing dev workflows keep functioning. In every
    other case the anon key + forwarded JWT means Postgres RLS policies are
    the real enforcement boundary, not just the .eq("user_id", ...) filters
    below.
    """
    try:
        import os
        from supabase import create_client  # type: ignore[import-untyped]

        url = os.environ.get("SUPABASE_URL", "")
        if not url:
            raise RuntimeError("Supabase not configured")

        if access_token:
            anon_key = os.environ.get("SUPABASE_ANON_KEY", "")
            if not anon_key:
                raise RuntimeError("Supabase not configured")
            client = create_client(url, anon_key)
            client.postgrest.auth(access_token)
            return client

        service_key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "")
        if not service_key:
            raise RuntimeError("Supabase not configured")
        return create_client(url, service_key)
    except Exception as exc:
        raise HTTPException(503, "Supabase unavailable") from exc
```

Then update every call site in the same file to pass `user.get("_raw_token")`:

```python
@router.get("/conversations")
async def list_conversations(user: dict = Depends(verify_supabase_jwt)) -> list[dict]:
    """List authenticated user's conversations, newest first."""
    sb = _get_supabase(user.get("_raw_token"))
    resp = (
        sb.table("conversations")
        .select("*")
        .eq("user_id", user["sub"])
        .order("updated_at", desc=True)
        .limit(50)
        .execute()
    )
    return resp.data or []


@router.post("/conversations", status_code=201)
async def create_conversation(
    body: ConversationCreate,
    user: dict = Depends(verify_supabase_jwt),
) -> dict:
    """Create a new conversation for the authenticated user."""
    sb = _get_supabase(user.get("_raw_token"))
    resp = (
        sb.table("conversations")
        .insert({"user_id": user["sub"], "title": body.title})
        .execute()
    )
    if not resp.data:
        raise HTTPException(500, "Failed to create conversation")
    return resp.data[0]


@router.get("/conversations/{conversation_id}/messages")
async def get_messages(
    conversation_id: UUID,
    user: dict = Depends(verify_supabase_jwt),
    offset: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
) -> list[dict]:
    """Return messages for a conversation with pagination."""
    sb = _get_supabase(user.get("_raw_token"))
    resp = (
        sb.table("messages")
        .select("*")
        .eq("conversation_id", str(conversation_id))
        .eq("user_id", user["sub"])
        .order("created_at", desc=False)
        .range(offset, offset + limit - 1)
        .execute()
    )
    return resp.data or []


@router.post("/conversations/{conversation_id}/messages", status_code=201)
async def add_message(
    conversation_id: UUID,
    body: MessageCreate,
    user: dict = Depends(verify_supabase_jwt),
) -> dict:
    """Add a message to a conversation."""
    if body.role not in ("user", "assistant"):
        raise HTTPException(400, "role must be 'user' or 'assistant'")
    sb = _get_supabase(user.get("_raw_token"))
    # Verify ownership: conversation must belong to this user
    conv = (
        sb.table("conversations")
        .select("id")
        .eq("id", str(conversation_id))
        .eq("user_id", user["sub"])
        .execute()
    )
    if not conv.data:
        raise HTTPException(404, "Conversation not found")

    resp = (
        sb.table("messages")
        .insert({
            "conversation_id": str(conversation_id),
            "user_id": user["sub"],
            "role": body.role,
            "content": body.content,
        })
        .execute()
    )
    if not resp.data:
        raise HTTPException(500, "Failed to save message")
    # Touch conversation updated_at
    sb.table("conversations").update(
        {"updated_at": datetime.now(timezone.utc).isoformat()}
    ).eq("id", str(conversation_id)).execute()
    return resp.data[0]


@router.delete("/conversations/{conversation_id}", status_code=204)
async def delete_conversation(
    conversation_id: UUID,
    user: dict = Depends(verify_supabase_jwt),
) -> None:
    """Delete a conversation and its messages (cascades via DB)."""
    sb = _get_supabase(user.get("_raw_token"))
    sb.table("conversations").delete().eq("id", str(conversation_id)).eq("user_id", user["sub"]).execute()
```

- [ ] **Step 5: Run the test to verify it passes**

Run: `cd /Users/souravamseekarmarti/Projects/aequitas && uv run pytest tests/api/test_conversations.py -v`
Expected: both tests PASS.

- [ ] **Step 6: Add `SUPABASE_ANON_KEY` to `.env.example`**

Check `.env.example` for the existing `SUPABASE_URL` / `SUPABASE_SERVICE_ROLE_KEY` entries and add a line directly after them:

```
SUPABASE_ANON_KEY=
```

- [ ] **Step 7: Run the full API test suite**

Run: `cd /Users/souravamseekarmarti/Projects/aequitas && uv run pytest tests/api/ -v`
Expected: all tests PASS. (No existing test in `tests/api/` exercises `conversations.py` end-to-end against a live Supabase instance, so no other test files are affected.)

- [ ] **Step 8: Commit**

```bash
git add src/aequitas/api/auth.py src/aequitas/api/routers/conversations.py tests/api/test_conversations.py .env.example
git commit -m "fix: scope Supabase client to caller's JWT so RLS enforces conversation access (SEC-003)"
```

---

## Task 4: Require auth on the PDF export endpoint

**Files:**
- Modify: `src/aequitas/api/routers/export.py:81-87`
- Test: `tests/api/test_export.py` (new)

**Interfaces:**
- Consumes: `verify_supabase_jwt` (existing, `src/aequitas/api/auth.py`)
- Produces: no new exports; `export_dimension_pdf` gains a `user: dict = Depends(verify_supabase_jwt)` parameter, unused in the body but enforcing the auth boundary.

This closes the consistency gap noted in SEC-004/CC-3: every other mutating or expensive route (`chat`, `conversations/*`) requires auth; `export` did not.

- [ ] **Step 1: Write the failing test**

Create `tests/api/test_export.py`:

```python
def test_export_without_auth_returns_401(api_client, monkeypatch):
    """Export must require auth like chat/conversations do."""
    monkeypatch.delenv("DEV_AUTH_BYPASS", raising=False)
    monkeypatch.setenv("ENVIRONMENT", "production")
    resp = api_client.get("/api/export/f1_gini")
    assert resp.status_code == 401


def test_export_with_dev_bypass_succeeds(api_client):
    """With dev bypass enabled (set in conftest), export still works."""
    resp = api_client.get("/api/export/f1_gini")
    assert resp.status_code == 200
    assert resp.headers["content-type"] == "application/pdf"
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `cd /Users/souravamseekarmarti/Projects/aequitas && uv run pytest tests/api/test_export.py -v`
Expected: `test_export_without_auth_returns_401` FAILS (currently returns 200 with no auth check).

- [ ] **Step 3: Add the auth dependency**

In `src/aequitas/api/routers/export.py`, add the import:

```python
from aequitas.api.deps import get_db
from aequitas.api.auth import verify_supabase_jwt
from aequitas.api.services.warehouse import DIMENSION_PREFIXES, query_sections
```

Then update the route signature (lines 81-87):

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

- [ ] **Step 4: Run the test to verify it passes**

Run: `cd /Users/souravamseekarmarti/Projects/aequitas && uv run pytest tests/api/test_export.py -v`
Expected: both tests PASS.

- [ ] **Step 5: Update the frontend export call to send the auth header**

Run: `grep -rn "export/" frontend/src --include="*.ts" --include="*.tsx"`

For each call site found, confirm it already goes through `fetchJson` in `frontend/src/api/client.ts` (which already attaches the Authorization header per Task 2's pattern). If a call site uses a raw `fetch`/`window.open` instead (e.g. for triggering a PDF download), it must be switched to fetch the PDF as a blob via `fetchJson`-style auth headers, then trigger the download client-side from the blob — apply the same header-injection pattern shown in Task 2 Step 1.

- [ ] **Step 6: Run the full API test suite**

Run: `cd /Users/souravamseekarmarti/Projects/aequitas && uv run pytest tests/api/ -v`
Expected: all tests PASS.

- [ ] **Step 7: Commit**

```bash
git add src/aequitas/api/routers/export.py tests/api/test_export.py
git commit -m "fix: require auth on PDF export endpoint for consistency with chat/conversations (SEC-004)"
```

---

## Task 5: Upgrade vulnerable direct dependencies (react-router, starlette/FastAPI)

**Files:**
- Modify: `frontend/package.json`
- Modify: `pyproject.toml`
- Test: existing test suites (frontend build + `tests/api/`)

**Interfaces:**
- Consumes: nothing new.
- Produces: nothing new — pure version bumps.

This closes SEC-005 (react-router RCE, GHSA-49rj-9fvp-4h2h) and SEC-006 (starlette CVEs).

- [ ] **Step 1: Check current and available versions**

Run: `cd /Users/souravamseekarmarti/Projects/aequitas/frontend && npm view react-router versions --json | tail -20`
Run: `cd /Users/souravamseekarmarti/Projects/aequitas && uv run pip index versions starlette 2>&1 || true`

Identify the minimum version of `react-router` that resolves GHSA-49rj-9fvp-4h2h (check the advisory's "patched versions" field at the GHSA URL cited in SEC-005) and the minimum `starlette>=1.3.1` already identified in SEC-006.

- [ ] **Step 2: Upgrade react-router**

Run: `cd /Users/souravamseekarmarti/Projects/aequitas/frontend && npm install react-router@latest`

Then verify the installed version satisfies the advisory's fixed-version requirement:

Run: `cd /Users/souravamseekarmarti/Projects/aequitas/frontend && npm ls react-router`

- [ ] **Step 3: Run frontend audit to confirm the advisory is resolved**

Run: `cd /Users/souravamseekarmarti/Projects/aequitas/frontend && npm audit --audit-level=high`
Expected: `react-router` no longer appears in the output.

- [ ] **Step 4: Build the frontend to catch any breaking API changes**

Run: `cd /Users/souravamseekarmarti/Projects/aequitas/frontend && npm run build`
Expected: build succeeds. If `react-router`'s major version changed and the build fails on a removed/renamed API, fix the specific call sites reported by the build error (do not guess — read the exact TypeScript error and the react-router migration notes for that version).

- [ ] **Step 5: Upgrade starlette/FastAPI**

In `pyproject.toml`, update the `fastapi` constraint (currently `"fastapi>=0.115.0"` per the earlier grep) to a version whose bundled Starlette dependency is `>=1.3.1`. Check what FastAPI version pulls in a fixed Starlette:

Run: `cd /Users/souravamseekarmarti/Projects/aequitas && uv run python -c "import starlette; print(starlette.__version__)"`

Update `pyproject.toml`'s fastapi line, e.g.:

```
    "fastapi>=0.128.0",
```

(Use whichever FastAPI version your `uv lock` resolves to a Starlette `>=1.3.1` — verify with Step 6 before committing to a specific number.)

- [ ] **Step 6: Re-lock and verify**

Run: `cd /Users/souravamseekarmarti/Projects/aequitas && uv lock && uv sync`
Run: `cd /Users/souravamseekarmarti/Projects/aequitas && uv run python -c "import starlette; print(starlette.__version__)"`
Expected: printed version is `>=1.3.1`.

- [ ] **Step 7: Run the full backend test suite**

Run: `cd /Users/souravamseekarmarti/Projects/aequitas && uv run pytest tests/ -v`
Expected: all tests PASS. If FastAPI's major version bump breaks anything, fix the specific reported failure by consulting FastAPI's migration guide for that version — do not silence the failure.

- [ ] **Step 8: Commit**

```bash
git add frontend/package.json frontend/package-lock.json pyproject.toml uv.lock
git commit -m "chore: upgrade react-router and starlette/FastAPI to patch known CVEs (SEC-005, SEC-006)"
```

---

## Self-Review Notes

- **Spec coverage:** SEC-001 (Task 1), SEC-002 (Task 2), SEC-003 (Task 3), SEC-004/export half (Task 4), SEC-005/SEC-006 (Task 5), SEC-010 (closed as a side effect of Task 1 Step 3). SEC-004's rate-limiting half, SEC-007, SEC-008/009/011-022, and the CVE summary's remaining transitive packages are explicitly **out of scope** for this plan — they are lower-severity hardening items better suited to a follow-up plan once P0/P1 is closed, per the roadmap in `docs/SECURITY_AUDIT.md`.
- **Placeholder scan:** no TBD/TODO/"add appropriate" phrasing present; every step has literal code or literal commands with expected output.
- **Type consistency:** `_get_supabase(access_token: str | None)` signature is identical across Task 3's test mocks and the five call sites updated in Step 4. `user.get("_raw_token")` is introduced in Task 1 (Step 1, the `_raw_token` key) and consumed identically in Task 3.
