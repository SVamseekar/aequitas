# Enterprise OAuth + Multi-Tenancy — Design

**Status**: Approved for planning
**Date**: 2026-07-03

## Context

Aequitas currently uses Supabase Auth (email/password) with a single-tenant model — every row in `conversations`, `messages`, `saved_analyses`, etc. is scoped to a Supabase `auth.users` id, enforced via Postgres RLS policies keyed on `auth.uid()`. The FastAPI backend validates Supabase JWTs directly (`src/aequitas/api/auth.py`) and one router (`conversations.py`) opens a per-request Supabase client scoped by the user's raw token to lean on RLS for isolation.

**Today there are two independent, inconsistent data-access paths, not one.** `conversations.py` is a tested FastAPI REST router (`tests/api/test_conversations.py`), but no frontend code calls it — the actual conversation list/CRUD UI (`frontend/src/components/chat/ChatSidebar.tsx`) instead calls `frontend/src/lib/db.ts`, which talks to Supabase **directly from the browser** via `@supabase/supabase-js`, bypassing FastAPI entirely. `db.ts` also owns `saved_analyses`, `policy_notes`, and `saved_regions` the same way — direct browser-to-Supabase, relying on RLS as the only access-control boundary — and **none of those three tables have a FastAPI router today** (confirmed: `src/aequitas/api/routers/` contains only `metrics`, `sections`, `export`, `overview`, `chat`, `lsoa`, `provenance`, `conversations`). This migration must consolidate everything onto one path (FastAPI + asyncpg, tenant-scoped) since a browser can no longer safely hold direct Postgres credentials once Supabase's client-side auth/RLS safety net is removed — see Backend and Rollout sections below.

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
| `/api/auth/me` | GET | Returns `{user, active_tenant, role, memberships: [...]}` (snake_case JSON keys, matching the rest of the API's response convention) — 401 if no valid session |
| `/api/session/switch-tenant` | POST | Body `{tenant_id}`; verifies caller has a membership in that tenant; updates `sessions.tenant_id` |
| `/api/tenants/{tenant_id}/invites` | POST | Admin-only; body `{email, role}`; creates `invites` row, returns `{token, link}` |
| `/api/invites/{token}` | GET | Public; returns `{tenant_name, role}` for the accept-invite screen, 404/410 if invalid/expired/already accepted |
| `/api/invites/{token}/accept` | POST | Requires session; creates `memberships` row for the caller in the invite's tenant, marks `accepted_at` |
| `/api/tenants/{tenant_id}/members` | GET | Lists memberships (admin-only) |
| `/api/tenants/{tenant_id}/members/{user_id}` | DELETE | Admin-only; removes the membership (cannot remove the last admin) |

Existing routers updated:
- `conversations.py` — drop the per-request Supabase client (`_get_supabase`) entirely, including its raw `os.environ.get("SUPABASE_URL"/"SUPABASE_ANON_KEY"/"SUPABASE_SERVICE_ROLE_KEY")` reads (these bypass `ApiConfig` today and are deleted, not migrated). Replace with asyncpg queries filtered by `tenant_id` from `require_session`. All five endpoints (list/create/get/update/delete) rewritten. This becomes the single source of truth for conversations — see "Consolidating the dual conversations path" below.
- `chat.py` — swap `user["sub"]` (Supabase JWT subject) for `user["user_id"]` from `require_session`; rate-limit key unchanged in shape.
- `export.py` — swap `verify_supabase_jwt` dependency for `require_session`; no other logic change.

New routers (none of these exist today — `db.ts` was the only implementation):
- `src/aequitas/api/routers/saved_analyses.py` — list/create/delete, tenant-scoped, mirroring the shape of the deleted `db.ts` functions (`listSavedAnalyses`, `saveAnalysis`, `deleteSavedAnalysis`).
- `src/aequitas/api/routers/policy_notes.py` — list/create/update/delete, tenant-scoped.
- `src/aequitas/api/routers/saved_regions.py` — list/create/delete, tenant-scoped.

**Consolidating the dual conversations path**: `ChatSidebar.tsx` currently reads/writes conversations via `db.ts` → Supabase directly; `conversations.py` is a parallel, currently-unused-by-the-frontend REST implementation of the same feature. This migration deletes `db.ts` entirely (see Frontend section) and points `ChatSidebar.tsx` at the rewritten `conversations.py` endpoints instead — one implementation, not two.

`src/aequitas/api/config.py`'s `ApiConfig` gains new fields for the replacement auth stack: `database_url`, `session_secret`, `google_client_id`, `google_client_secret` (env var names matching WorkforceGuard's `.env.example`: `DATABASE_URL`, `SESSION_SECRET`, `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`). The existing `supabase_jwt_secret` field, and `SUPABASE_URL`/`SUPABASE_ANON_KEY`/`SUPABASE_SERVICE_ROLE_KEY`/`SUPABASE_JWT_SECRET` env vars, are removed.

`src/aequitas/api/auth.py` (the old Supabase JWT module) is deleted once all call sites are migrated. Its `tests/api/test_auth.py` (6 passing tests) covers a **dev-bypass mode** (`ENVIRONMENT`/`DEV_AUTH_BYPASS` env vars, letting local development skip real token validation) that has no equivalent in the spec as written. The new `require_session` dependency needs the same dev-bypass affordance — when `DEV_AUTH_BYPASS=true` and no session cookie is present, synthesize a placeholder dev user/tenant rather than 401ing — so local development isn't blocked on a real Google OAuth round-trip for every route. This bypass must never activate when `ENVIRONMENT=production`, matching the existing guard.

## Frontend

- **`AuthContext.tsx`** — no Supabase client. On mount, `fetch('/api/auth/me', {credentials: 'include'})`. React state shape: `{user, activeTenant, role, memberships, loading, signOut}` (camelCase, per existing frontend convention — `activeTenant` in JS state is populated from the API's `active_tenant` JSON field; this is a normal snake_case→camelCase mapping at the fetch boundary, not a naming inconsistency to resolve). **`signOut` must be preserved in the exported shape** (not dropped, and not silently renamed to `logout`), because `UserMenu.tsx` and `ProfilePage.tsx` both destructure `signOut` directly from `useAuth()` today; keeping the name avoids touching those two call sites. Internally `signOut` posts to `/api/auth/logout` then clears state. `login()` navigates to `/api/auth/login/google`.
- **`AuthPage.tsx`** — single "Continue with Google" button, full-page redirect (not a popup), following WorkforceGuard's `fetch(..., {redirect: 'manual'})` pre-check pattern to surface config errors before navigating away from the SPA.
- **Tenant switcher** — small dropdown in the app shell header (only rendered when `memberships.length > 1`); posts to `/api/session/switch-tenant`, then reloads `/api/auth/me`.
- **Invite management** — new admin-only panel (likely on `ProfilePage.tsx` or a new `OrgSettingsPage.tsx`) — email + role input, submits to `/api/tenants/{id}/invites`, displays the returned link in a copyable field. Also lists current members with a remove button (admin-only).
- **`/invite/:token`** — new public route. Fetches `/api/invites/{token}` to show tenant name; if the visitor isn't signed in, prompts Google sign-in first (preserving the token through the OAuth redirect via a query param or session-stored return-to path); once signed in, posts to `/api/invites/{token}/accept` and redirects into the app with that tenant active.
- **Deleted**: `integrations/supabase/client.ts`, `lib/db.ts` (including its `saved_analyses`/`policy_notes`/`saved_regions`/`conversations` functions — replaced by the new/rewritten routers above).
- **`ChatSidebar.tsx`** — repointed from `db.ts`'s Supabase calls to `conversations.py`'s REST endpoints via `api/client.ts`.
- **`api/client.ts`** — all requests add `credentials: 'include'` so the session cookie rides automatically; a 401 interceptor clears auth state (matches WorkforceGuard's pattern). This is not the only place manually attaching auth today — `hooks/useChat.ts` and `components/dimension/DimensionPage.tsx` (PDF export) both call `supabase.auth.getSession()` directly to attach a bearer token; both are updated to rely on the cookie (`credentials: 'include'`) instead, removing their manual token-attachment code.
- **`useAuth()` consumers** — 12 files call this hook and need reviewing against the new context shape (most only read `user`, which is unaffected): `ProtectedRoute.tsx`, `AuthPage.tsx`, `UserMenu.tsx`, `ProfilePage.tsx`, `ChatSidebar.tsx`, `PolicyNotes.tsx`, `SavedAnalyses.tsx`, `SavedRegions.tsx`, `LandingNav.tsx`, `LandingHero.tsx`, `LandingDimensions.tsx`, `LandingCta.tsx`.

### Also affected: PrivacyPage.tsx

`frontend/src/pages/PrivacyPage.tsx` (built in an earlier, unrelated session for the site's legal/footer pages) makes factual claims that become false once this migration ships: it states data is stored "via Supabase Auth," that "Aequitas uses Supabase (authentication and database, EU-hosted)," and that essential cookies are used "for authentication (via Supabase)." This page must be updated in the same change to describe Google OAuth + self-hosted Postgres instead — Terms, Refunds, Contact, and Disclaimer pages have no Supabase-specific claims and don't need changes.

## Testing

Tests are written alongside each piece as it's implemented, not as a separate pass.

**Backend (pytest, against a test Postgres database)**:
- `db.py` query functions: user/tenant/membership/session/invite CRUD, including edge cases (duplicate OAuth identity, expired invite, expired session).
- OAuth callback: new user creates tenant+membership+session; returning user reuses existing tenant; malformed/failed token exchange returns an error, not a crash.
- `require_session` / `require_admin`: valid session passes, missing/expired cookie 401s, non-admin hitting an admin route 403s.
- Invite lifecycle: create → fetch by token → accept → membership exists → re-accepting the same token fails (already accepted or expired).
- **Cross-tenant isolation** (highest priority): a user in tenant A can never read/write tenant B's data via any router — `conversations`, `messages`, `saved_analyses`, `policy_notes`, `saved_regions` each get an explicit cross-tenant-isolation test, not just incidental happy-path coverage.
- New routers (`saved_analyses.py`, `policy_notes.py`, `saved_regions.py`): full CRUD test coverage — these have zero existing backend tests today since they were previously implemented only in `db.ts`.
- Rewritten routers (`conversations.py`, `chat.py`, `export.py`): existing test coverage updated to use the new session fixture instead of a mocked Supabase JWT.

**Frontend (vitest)**:
- `AuthContext`: 200 from `/auth/me` populates state; 401 leaves user null; `logout()` clears state.
- `ProtectedRoute`: redirects to `/auth` when unauthenticated, renders children when authenticated.
- Tenant switcher: only renders with >1 membership; posts the right tenant_id.
- Invite accept page: shows tenant name from a mocked fetch; posts accept and redirects.

**Manual verification**: the actual Google OAuth redirect round-trip is verified by hand on localhost (a live OAuth consent screen isn't practical to fully automate) — this is the one piece confirmed via the demo, not an automated test.

**Existing test inventory — what's replaced vs. carried forward** (confirmed by running the full suite: 509 backend tests collect cleanly, all pass, via `uv run pytest`; run bare `python -m pytest` does NOT work in this repo — dependencies like `loguru` aren't on the bare interpreter's path, so every backend test command in the implementation plan must be prefixed `uv run`):
- `tests/api/test_auth.py` (6 passing tests, all against `verify_supabase_jwt`'s dev-bypass logic) — fully replaced by an equivalent `require_session` dev-bypass test file, not modified in place, since the underlying function is deleted.
- `tests/api/test_conversations.py` (2 passing tests, both specifically exercising `_get_supabase`'s anon-key-vs-service-role-key fallback) — fully replaced; this test's entire subject (the Supabase client factory) no longer exists.
- `tests/api/test_export.py` (2 passing tests: 401 without auth, success with dev bypass) — carried forward with minor updates to use the new dependency/fixture.
- `tests/api/test_chat.py` (1 passing test, doesn't exercise auth) — unaffected, no changes needed.
- `frontend/src/components/auth/__tests__/ProtectedRoute.test.tsx` (3 passing tests, mocks `useAuth()` returning today's shape `{user, session, loading, signOut}`) — updated to mock the new shape (`{user, activeTenant, role, memberships, loading, signOut}`); confirmed compatible once `signOut` is preserved per the Frontend section above. Frontend suite currently: 16/16 passing via `npx vitest run`.

## Rollout

Single cutover, no feature flag: once the new auth stack passes its tests, the old Supabase Auth code paths are removed in the same change, not left running in parallel:
- Backend: `src/aequitas/api/auth.py`, the `_get_supabase` client factory in `conversations.py`, `supabase>=2.0.0` from `pyproject.toml`.
- Frontend: `integrations/supabase/client.ts`, `lib/db.ts` (all of it — conversations, saved_analyses, policy_notes, saved_regions), `@supabase/supabase-js` from `frontend/package.json`, the manual `supabase.auth.getSession()` token-attachment code in `hooks/useChat.ts` and `components/dimension/DimensionPage.tsx`.
- Database: all Supabase RLS policies, `supabase/migrations/001_initial.sql`'s auth-dependent tables (`auth.users`-referencing FKs on `conversations`, `messages`, `saved_analyses`, `policy_notes`, `saved_regions`, `profiles`), and the `handle_new_user` trigger.

Existing local Supabase data is discarded (confirmed: no real users to preserve). `frontend/src/pages/PrivacyPage.tsx` is updated in the same change (see Frontend section) so the legal copy doesn't misdescribe the new auth stack.
