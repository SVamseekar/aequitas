# Enterprise OAuth + Multi-Tenancy — Design

**Status**: Approved for planning
**Date**: 2026-07-03

## Context

Aequitas currently uses Supabase Auth (email/password) with a single-tenant model — every row in `conversations`, `messages`, `saved_analyses`, etc. is scoped to a Supabase `auth.users` id, enforced via Postgres RLS policies keyed on `auth.uid()`. The FastAPI backend validates Supabase JWTs directly (`src/aequitas/api/auth.py`) and one router (`conversations.py`) opens a per-request Supabase client scoped by the user's raw token to lean on RLS for isolation.

Aequitas is moving toward an enterprise model: Local Transport Authorities (and other organisations, or individuals) as tenants, with staff sharing saved research within their organisation. This mirrors the architecture already built in a reference project, WorkforceGuard AI (`/Users/souravamseekarmarti/Projects/WorkforceGuard-AI`) — FastAPI + self-hosted Postgres, OAuth-only sign-in (no passwords), signed session cookies, and a `tenants`/`memberships`/`sessions` schema with tenant-scoped data access enforced in application code rather than RLS.

This is a full replacement of Supabase Auth, not an addition alongside it. There are no real external users on Aequitas today (confirmed: existing accounts are test/personal), so no data migration path is needed — this is a clean cutover.

## Goals

- Google OAuth sign-in (no email/password), matching WorkforceGuard's pattern.
- Every user gets a personal tenant ("workspace") automatically on first sign-in — no forced choice between "create org" / "join org" at signup.
- Tenants can grow into real organisations via admin-issued invite links.
- Data shared within a tenant: `conversations`, `messages`, `saved_analyses`, `policy_notes`, `saved_regions` are all tenant-scoped, not just user-scoped — any member of a tenant sees everything the tenant has saved. `profiles` stays per-person (not shared).
- Admins (first member of a tenant) can invite and remove members. No other role-gated behavior yet.
- A user can belong to multiple tenants (their personal workspace plus any org they've joined) and switch the active tenant for their session.
- Runs entirely on localhost for now — no production hosting decision is part of this work.

## Non-goals (explicitly out of scope)

- Microsoft OAuth or any other identity provider.
- Production hosting/deployment configuration for the new Postgres or backend.
- Transactional email — invites are shareable links the admin copies and sends manually through their own channel (email, Slack, Teams).
- Seat limits, plans, or billing enforcement.
- Audit logging of tenant/membership actions.
- Cross-provider account linking (e.g. same person signing in with Google vs. a future Microsoft option).
- Migrating existing Supabase-authenticated accounts or their data.

## Data model

New Postgres database (local dev: `postgresql://localhost/aequitas`), owned entirely by the application — no Supabase involvement.

```sql
tenants
  id UUID PK
  name TEXT NOT NULL
  slug TEXT UNIQUE NOT NULL
  created_at TIMESTAMPTZ

users
  id UUID PK
  email TEXT UNIQUE NOT NULL
  display_name TEXT
  created_at TIMESTAMPTZ

oauth_identities
  id UUID PK
  user_id UUID FK -> users
  provider TEXT NOT NULL  -- 'google'
  provider_subject TEXT NOT NULL
  created_at TIMESTAMPTZ
  UNIQUE (provider, provider_subject)

memberships
  user_id UUID FK -> users
  tenant_id UUID FK -> tenants
  role TEXT NOT NULL CHECK (role IN ('admin', 'member'))
  created_at TIMESTAMPTZ
  PRIMARY KEY (user_id, tenant_id)

sessions
  id UUID PK
  user_id UUID FK -> users
  tenant_id UUID FK -> tenants  -- the active tenant for this session
  created_at TIMESTAMPTZ
  expires_at TIMESTAMPTZ NOT NULL

invites
  id UUID PK
  tenant_id UUID FK -> tenants
  email TEXT NOT NULL
  role TEXT NOT NULL CHECK (role IN ('admin', 'member'))
  token TEXT UNIQUE NOT NULL
  created_at TIMESTAMPTZ
  expires_at TIMESTAMPTZ NOT NULL
  accepted_at TIMESTAMPTZ  -- null until accepted
```

Existing application tables — `conversations`, `messages`, `saved_analyses`, `policy_notes`, `saved_regions` (all currently `user_id`-scoped, per `supabase/migrations/001_initial.sql`) — are recreated in this same database with a `tenant_id UUID NOT NULL REFERENCES tenants(id)` column replacing `user_id UUID REFERENCES auth.users(id)` as the scoping key. `user_id` is retained on each row (who created it) for display purposes, but access control filters on `tenant_id`, not `user_id`. RLS is not used; every query in the FastAPI layer filters by the session's active `tenant_id` explicitly.

`profiles` (`display_name`, `bio`, `policy_interests`) stays `user_id`-scoped, not tenant-scoped — it's per-person identity data, not shared research, so it doesn't fit the "shared within a tenant" model. It's recreated in the new Postgres keyed on the new `users.id`, and its Supabase auto-create trigger (`handle_new_user`) is replaced by an explicit insert in the OAuth callback when a user is first created.

## Backend (`src/aequitas/api/auth/`)

New package, replacing `src/aequitas/api/auth.py`:

- **`oauth.py`** — Google OAuth client via `authlib`'s `starlette_client.OAuth`, OIDC discovery against Google's `.well-known/openid-configuration`.
- **`sessions.py`** — session token signing via `itsdangerous.URLSafeTimedSerializer`; cookie is httponly, secure, samesite=lax, 7-day expiry (matches WorkforceGuard).
- **`db.py`** — asyncpg connection pool and query functions for all six tables above (`get_or_create_user`, `create_tenant`, `create_membership`, `create_session`, `get_session`, `create_invite`, `accept_invite`, `list_memberships_for_user`, `remove_membership`).
- **`dependencies.py`** — `require_session` (reads cookie, loads session + membership, raises 401 if missing/expired) and `require_admin` (wraps `require_session`, raises 403 if role != 'admin' for the active tenant).

Routes (new router, `src/aequitas/api/routers/auth.py`):

| Route | Method | Behavior |
|---|---|---|
| `/api/auth/login/google` | GET | Redirect to Google's OAuth consent screen |
| `/api/auth/callback/google` | GET | Exchange code, upsert `users`/`oauth_identities`; on first login, create a personal `tenants` row + `admin` `memberships` row; create `sessions` row (active tenant = personal tenant); set cookie; redirect to frontend |
| `/api/auth/logout` | POST | Delete session row, clear cookie |
| `/api/auth/me` | GET | Returns `{user, active_tenant, role, memberships: [...]}` — 401 if no valid session |
| `/api/session/switch-tenant` | POST | Body `{tenant_id}`; verifies caller has a membership in that tenant; updates `sessions.tenant_id` |
| `/api/tenants/{tenant_id}/invites` | POST | Admin-only; body `{email, role}`; creates `invites` row, returns `{token, link}` |
| `/api/invites/{token}` | GET | Public; returns `{tenant_name, role}` for the accept-invite screen, 404/410 if invalid/expired/already accepted |
| `/api/invites/{token}/accept` | POST | Requires session; creates `memberships` row for the caller in the invite's tenant, marks `accepted_at` |
| `/api/tenants/{tenant_id}/members` | GET | Lists memberships (admin-only) |
| `/api/tenants/{tenant_id}/members/{user_id}` | DELETE | Admin-only; removes the membership (cannot remove the last admin) |

Existing routers updated:
- `conversations.py` — drop the per-request Supabase client (`_get_supabase`) entirely; replace with asyncpg queries filtered by `tenant_id` from `require_session`. All five endpoints (list/create/get/update/delete) rewritten.
- `chat.py` — swap `user["sub"]` (Supabase JWT subject) for `user["user_id"]` from `require_session`; rate-limit key unchanged in shape.
- `export.py` — swap `verify_supabase_jwt` dependency for `require_session`; no other logic change.

`src/aequitas/api/auth.py` (the old Supabase JWT module) is deleted once all call sites are migrated.

## Frontend

- **`AuthContext.tsx`** — no Supabase client. On mount, `fetch('/api/auth/me', {credentials: 'include'})`. State shape: `{user, activeTenant, role, memberships, loading}`. `login()` navigates to `/api/auth/login/google`. `logout()` posts to `/api/auth/logout` then clears state.
- **`AuthPage.tsx`** — single "Continue with Google" button, full-page redirect (not a popup), following WorkforceGuard's `fetch(..., {redirect: 'manual'})` pre-check pattern to surface config errors before navigating away from the SPA.
- **Tenant switcher** — small dropdown in the app shell header (only rendered when `memberships.length > 1`); posts to `/api/session/switch-tenant`, then reloads `/api/auth/me`.
- **Invite management** — new admin-only panel (likely on `ProfilePage.tsx` or a new `OrgSettingsPage.tsx`) — email + role input, submits to `/api/tenants/{id}/invites`, displays the returned link in a copyable field. Also lists current members with a remove button (admin-only).
- **`/invite/:token`** — new public route. Fetches `/api/invites/{token}` to show tenant name; if the visitor isn't signed in, prompts Google sign-in first (preserving the token through the OAuth redirect via a query param or session-stored return-to path); once signed in, posts to `/api/invites/{token}/accept` and redirects into the app with that tenant active.
- **Deleted**: `integrations/supabase/client.ts`, `lib/db.ts`.
- **`api/client.ts`** — all requests add `credentials: 'include'` so the session cookie rides automatically; a 401 interceptor clears auth state (matches WorkforceGuard's pattern).

## Testing

Tests are written alongside each piece as it's implemented, not as a separate pass.

**Backend (pytest, against a test Postgres database)**:
- `db.py` query functions: user/tenant/membership/session/invite CRUD, including edge cases (duplicate OAuth identity, expired invite, expired session).
- OAuth callback: new user creates tenant+membership+session; returning user reuses existing tenant; malformed/failed token exchange returns an error, not a crash.
- `require_session` / `require_admin`: valid session passes, missing/expired cookie 401s, non-admin hitting an admin route 403s.
- Invite lifecycle: create → fetch by token → accept → membership exists → re-accepting the same token fails (already accepted or expired).
- **Cross-tenant isolation** (highest priority): a user in tenant A can never read/write tenant B's `conversations`/`saved_analyses`/etc. via any rewritten router — tested explicitly, not just incidentally covered by happy-path tests.
- Rewritten routers (`conversations.py`, `chat.py`, `export.py`): existing test coverage updated to use the new session fixture instead of a mocked Supabase JWT.

**Frontend (vitest)**:
- `AuthContext`: 200 from `/auth/me` populates state; 401 leaves user null; `logout()` clears state.
- `ProtectedRoute`: redirects to `/auth` when unauthenticated, renders children when authenticated.
- Tenant switcher: only renders with >1 membership; posts the right tenant_id.
- Invite accept page: shows tenant name from a mocked fetch; posts accept and redirects.

**Manual verification**: the actual Google OAuth redirect round-trip is verified by hand on localhost (a live OAuth consent screen isn't practical to fully automate) — this is the one piece confirmed via the demo, not an automated test.

## Rollout

Single cutover, no feature flag: once the new auth stack passes its tests, the old Supabase Auth code paths (`api/auth.py`, `integrations/supabase/client.ts`, `lib/db.ts`, all Supabase RLS policies, `supabase/migrations/001_initial.sql`'s auth-dependent tables) are removed in the same change, not left running in parallel. Existing local Supabase data is discarded (confirmed: no real users to preserve).
