# Cleanup & Cutover Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Final plan in the migration. Delete every remaining Supabase code path (`src/aequitas/api/auth.py`, the `supabase` Python dependency, `@supabase/supabase-js`, `supabase/migrations/001_initial.sql`, `supabase/config.toml`), fix `PrivacyPage.tsx`'s now-false claims about Supabase, run the full verification pass (both test suites + manual OAuth round-trip), and merge `feature/enterprise-oauth-tenancy` back to `main`.

**Architecture:** Pure deletion and one content fix — no new application code. This plan assumes Plans 01-06 are fully merged into the feature branch and their tests pass; its job is removing what they made obsolete and closing out the branch per the spec's Rollout and Development Process sections.

**Tech Stack:** No new dependencies — this plan only removes dependencies (`supabase`, `@supabase/supabase-js`) and files.

## Global Constraints

- Backend test commands must always be prefixed `uv run`.
- Frontend test commands run from the `frontend/` directory.
- This is a single cutover, no feature flag — per the spec's Rollout section, once the new auth stack passes its tests, the old paths are removed in the same change, not left running in parallel.
- Per the spec's Development Process section: merge to `main` only once the full test suite passes and the OAuth flow is manually verified working on localhost. No required PR review, no branch protection — solo-developer project.
- Existing local Supabase data is discarded (confirmed no real users to preserve, per spec Context).

---

### Task 1: Delete `src/aequitas/api/auth.py`, its test, and the now-dead `ApiConfig.supabase_jwt_secret` field

**Files:**
- Delete: `src/aequitas/api/auth.py`
- Delete: `tests/api/test_auth.py` (its entire subject, `verify_supabase_jwt`, no longer exists — a `require_session` dev-bypass equivalent was already added as part of Plan 02's `test_dependencies.py`, so this file is removed, not replaced)
- Modify: `src/aequitas/api/config.py` — remove the `supabase_jwt_secret` field, which Plan 01's Task 6 deliberately kept until this point (see that plan's note on why deleting it earlier would break `conversations.py`/`chat.py`/`export.py` before Plan 04 rewrote them)
- Modify: `tests/api/test_config.py` — remove `test_supabase_jwt_secret_still_present` (its assertion — that the field exists — is now the opposite of correct) and add its replacement

**Interfaces:**
- Consumes: Plan 04 Task 7's confirmation that no router imports `verify_supabase_jwt` anymore
- Produces: a codebase where `aequitas.api.auth` (the package, from Plan 01) is the only thing named `auth` under `src/aequitas/api/` — the old `auth.py` module and its `ApiConfig` field are both gone

- [ ] **Step 1: Re-confirm zero remaining call sites (in case anything changed since Plan 04 Task 7)**

Run: `grep -rn "verify_supabase_jwt\|supabase_jwt_secret" src/aequitas/ tests/`
Expected: only matches inside `src/aequitas/api/auth.py`, `src/aequitas/api/config.py` (the field definition), and `tests/api/test_auth.py`/`tests/api/test_config.py` — no matches in any router or other test file

If any other file still references `verify_supabase_jwt` or `supabase_jwt_secret`, stop and fix that call site before proceeding (it should have been migrated in Plan 04).

- [ ] **Step 2: Update the failing test first — replace the "still present" assertion**

In `tests/api/test_config.py`, replace:

```python
def test_supabase_jwt_secret_still_present():
    """Must stay until Plan 04 removes verify_supabase_jwt's last call site."""
    cfg = ApiConfig()
    assert hasattr(cfg, "supabase_jwt_secret")
```

with:

```python
def test_supabase_jwt_secret_field_removed():
    """The old Supabase JWT config is fully retired as of this cutover."""
    cfg = ApiConfig()
    assert not hasattr(cfg, "supabase_jwt_secret")
```

- [ ] **Step 3: Run test to verify it fails**

Run: `uv run pytest tests/api/test_config.py -v`
Expected: FAIL — `test_supabase_jwt_secret_field_removed` fails (field is still present; `ApiConfig` hasn't been changed yet)

- [ ] **Step 4: Remove the field from `ApiConfig`**

In `src/aequitas/api/config.py`, delete the `supabase_jwt_secret` field (and its trailing dev-mode comment) entirely.

- [ ] **Step 5: Run test to verify it passes**

Run: `uv run pytest tests/api/test_config.py -v`
Expected: 6 passed

- [ ] **Step 6: Delete the old auth module and its test**

```bash
git rm src/aequitas/api/auth.py tests/api/test_auth.py
```

- [ ] **Step 7: Run the full backend suite**

Run: `uv run pytest tests/ -q`
Expected: all tests pass (given `DATABASE_URL`/`SESSION_SECRET`/`GOOGLE_CLIENT_ID`/`GOOGLE_CLIENT_SECRET` set) — no import errors from the deleted module, no leftover references to the deleted config field

- [ ] **Step 8: Commit**

```bash
git add src/aequitas/api/config.py tests/api/test_config.py
git rm src/aequitas/api/auth.py tests/api/test_auth.py 2>/dev/null || true
git commit -m "Delete old Supabase JWT auth module and supabase_jwt_secret config field"
```

---

### Task 2: Remove `supabase` Python dependency

**Files:**
- Modify: `pyproject.toml`

**Interfaces:**
- Consumes: Task 1's confirmation that nothing imports `supabase` anymore (the old `conversations.py`'s `_get_supabase` was already deleted in Plan 04 Task 2)
- Produces: `supabase` no longer listed in `pyproject.toml`'s dependencies

- [ ] **Step 1: Confirm nothing still imports `supabase`**

Run: `grep -rn "^import supabase\|from supabase import\|import supabase$" src/ tests/`
Expected: no output

- [ ] **Step 2: Remove the dependency**

In `pyproject.toml`, delete the line `"supabase>=2.0.0",` from the `dependencies` list.

- [ ] **Step 3: Sync and verify the app still starts**

Run: `uv sync --all-extras`
Run: `uv run python -c "from aequitas.api.app import create_app; create_app(); print('ok')"`
Expected: prints `ok` with no import errors

- [ ] **Step 4: Run the full backend suite**

Run: `uv run pytest tests/ -q`
Expected: all tests pass

- [ ] **Step 5: Commit**

```bash
git add pyproject.toml uv.lock
git commit -m "Remove supabase Python dependency, fully replaced by asyncpg"
```

---

### Task 3: Delete Supabase migration/config files

**Files:**
- Delete: `supabase/migrations/001_initial.sql`
- Delete: `supabase/config.toml`

**Interfaces:**
- Consumes: nothing — this is the schema Plan 01's `schema.sql` fully superseded
- Produces: no remaining Supabase project files in the repo

- [ ] **Step 1: Confirm nothing references the old migration file**

Run: `grep -rln "001_initial.sql\|supabase/migrations" src/ tests/ frontend/src/ --include="*.py" --include="*.ts" --include="*.tsx" 2>/dev/null`
Expected: no output

- [ ] **Step 2: Delete the Supabase project directory contents**

```bash
git rm supabase/migrations/001_initial.sql supabase/config.toml
```

Check if `supabase/` is now empty:

Run: `find supabase -type f 2>/dev/null`
Expected: no output — if the directory is now empty, it will be implicitly removed from git tracking once these are the last tracked files in it (git doesn't track empty directories, so no explicit `rmdir` is needed).

- [ ] **Step 3: Commit**

```bash
git commit -m "Delete Supabase migration and config files, schema fully replaced by src/aequitas/api/auth/schema.sql"
```

---

### Task 4: Remove `@supabase/supabase-js` frontend dependency

**Files:**
- Modify: `frontend/package.json`

**Interfaces:**
- Consumes: Plan 05's confirmation (Task 6, Step 4) that zero frontend source files import `supabase` anymore
- Produces: `@supabase/supabase-js` no longer in `frontend/package.json`

- [ ] **Step 1: Re-confirm zero remaining imports**

Run: `grep -rln "supabase" frontend/src/ --include="*.ts" --include="*.tsx" -i`
Expected: no output

- [ ] **Step 2: Remove the dependency**

Run: `cd frontend && npm uninstall @supabase/supabase-js`
Expected: `package.json` and `package-lock.json` updated, dependency removed

- [ ] **Step 3: Verify the frontend still builds**

Run: `cd frontend && npm run build`
Expected: build completes with no errors

- [ ] **Step 4: Run the full frontend suite**

Run: `cd frontend && npx vitest run`
Expected: all tests pass

- [ ] **Step 5: Commit**

```bash
git add frontend/package.json frontend/package-lock.json
git commit -m "Remove @supabase/supabase-js frontend dependency"
```

---

### Task 5: Fix `PrivacyPage.tsx`'s Supabase claims

**Files:**
- Modify: `frontend/src/pages/PrivacyPage.tsx`

**Interfaces:**
- Consumes: nothing — this is a content-only fix
- Produces: privacy copy that accurately describes Google OAuth + self-hosted Postgres instead of Supabase

- [ ] **Step 1: Update the three Supabase-referencing paragraphs**

In `frontend/src/pages/PrivacyPage.tsx`, the three `body` strings currently read (confirmed at lines 9, 21, 29):

Line 9 (data collected):
```
"Account details (email address, password hash) via Supabase Auth when you sign up. Saved views, notes, and comparisons you create while using the platform. Aggregated usage analytics via Google Analytics (GA4) on public pages. We do not collect payroll, financial, or personal data about third parties — Aequitas analyses publicly available government transport and demographic datasets, not data you upload about individuals."
```

Replace with:
```
"Account details (email address, display name) via Google Sign-In when you sign up — Aequitas never sees or stores your Google password. Saved views, notes, and comparisons you create while using the platform. Aggregated usage analytics via Google Analytics (GA4) on public pages. We do not collect payroll, financial, or personal data about third parties — Aequitas analyses publicly available government transport and demographic datasets, not data you upload about individuals."
```

Line 21 (third-party services):
```
"Aequitas uses Supabase (authentication and database, EU-hosted), Google Analytics (usage analytics), and Google Gemini (chatbot responses — your questions to the chatbot are sent to Google's API to generate answers grounded in pre-computed narratives). No underlying government source data we analyse contains personal information about individuals."
```

Replace with:
```
"Aequitas uses Google Sign-In (authentication), a self-hosted Postgres database (account and saved-data storage), Google Analytics (usage analytics), and Google Gemini (chatbot responses — your questions to the chatbot are sent to Google's API to generate answers grounded in pre-computed narratives). No underlying government source data we analyse contains personal information about individuals."
```

Line 29 (cookies):
```
"We use essential cookies for authentication (via Supabase) and analytics cookies (Google Analytics) to understand site usage. You can control cookies through your browser settings; disabling them may affect sign-in functionality."
```

Replace with:
```
"We use an essential session cookie for authentication (set after Google Sign-In) and analytics cookies (Google Analytics) to understand site usage. You can control cookies through your browser settings; disabling them may affect sign-in functionality."
```

- [ ] **Step 2: Confirm no remaining mention of Supabase anywhere in the legal pages**

Run: `grep -rln "Supabase" frontend/src/pages/`
Expected: no output

- [ ] **Step 3: Verify the frontend builds**

Run: `cd frontend && npm run build`
Expected: no errors

- [ ] **Step 4: Commit**

```bash
git add frontend/src/pages/PrivacyPage.tsx
git commit -m "Fix PrivacyPage copy to describe Google OAuth + self-hosted Postgres, not Supabase"
```

---

### Task 6: Full verification pass

**Files:** none (verification only)

**Interfaces:**
- Consumes: everything from Plans 01-07
- Produces: confirmation the branch is ready to merge, per the spec's Development Process and Testing sections

- [ ] **Step 1: Run the full backend suite**

Run: `uv run pytest tests/ -q`
Expected: all tests pass (given `DATABASE_URL` pointing at a live local Postgres, and `SESSION_SECRET`/`GOOGLE_CLIENT_ID`/`GOOGLE_CLIENT_SECRET`/`BREVO_API_KEY` set in the environment) — note the exact count for comparison against the spec's baseline (509 backend tests at spec time, plus everything added across Plans 01-07)

- [ ] **Step 2: Run the full frontend suite**

Run: `cd frontend && npx vitest run`
Expected: all tests pass (16 pre-existing at spec time, plus everything added across Plans 05-06)

- [ ] **Step 3: Confirm zero remaining Supabase references anywhere in the repo**

Run: `grep -rln "supabase" --include="*.py" --include="*.ts" --include="*.tsx" --include="*.toml" --include="*.sql" src/ tests/ frontend/src/ frontend/package.json pyproject.toml -i 2>/dev/null`
Expected: no output

- [ ] **Step 4: Manual end-to-end OAuth verification on localhost**

This is the one piece confirmed by hand, not by automated test (per the spec's Testing section — a live Google OAuth consent screen isn't practical to fully automate):

1. Set real `GOOGLE_CLIENT_ID`/`GOOGLE_CLIENT_SECRET` (from a Google Cloud OAuth client configured for `http://localhost:8000/api/auth/callback/google`), a real `SESSION_SECRET`, and `DATABASE_URL` pointing at a running local Postgres.
2. Start the backend without `DEV_AUTH_BYPASS` set.
3. Start the frontend dev server.
4. Navigate to `/auth`, click "Continue with Google," complete the real Google consent screen.
5. Confirm redirect lands on `/dashboard` with a working session (user menu shows your real Google name/email).
6. Create a conversation, send a chat message, refresh the page, confirm both persisted.
7. Go to `/org-settings`, send an invite to a second real or test Google account's email.
8. Open the invite link in an incognito window, sign in with the second account, confirm it lands in the shared tenant and the shared conversation is visible.
9. Confirm the tenant switcher now appears for the second account (member of >1 tenant: their personal workspace + the invited one) — actually, per the spec, the *inviter's* tenant is what's shared; confirm the specific behavior matches what Plans 02/03 implemented, and note any discrepancy from this expected flow rather than assuming it's correct.
10. From `/org-settings` as the original admin, remove the second member, confirm they lose access to the shared tenant's conversations on their next request.
11. Check `GET /api/tenants/{id}/audit-log` (via browser dev tools or a raw fetch in the console) and confirm all four action types recorded so far (`invite_created`, `invite_accepted`, `member_removed`) appear with correct `actor_user_id`/`target_user_id`.

Document the outcome of each step. If any step fails, stop and fix the underlying issue in the relevant earlier plan's code before merging — do not patch around it in this plan.

- [ ] **Step 5: Confirm CI passes on the feature branch**

Run: `gh run list --branch feature/enterprise-oauth-tenancy --limit 1` (or check the GitHub Actions tab)
Expected: the CI workflow from Plan 00 shows green for both `backend` and `frontend` jobs on the latest commit

---

### Task 7: Merge to `main`

**Files:** none (git operation only)

**Interfaces:**
- Consumes: Task 6's full verification pass
- Produces: `feature/enterprise-oauth-tenancy` merged into `main`

- [ ] **Step 1: Confirm the feature branch is up to date and clean**

Run: `git status --short && git log --oneline main..feature/enterprise-oauth-tenancy | wc -l`
Expected: clean working tree; a nonzero commit count confirming the branch has the full migration's history

- [ ] **Step 2: Merge into `main`**

Per the spec's Development Process section (no required PR review at this project's current scale), merge directly:

```bash
git checkout main
git pull origin main
git merge --no-ff feature/enterprise-oauth-tenancy -m "Merge enterprise-oauth-tenancy: replace Supabase Auth with Google OAuth + multi-tenant orgs"
```

- [ ] **Step 3: Run the full verification pass once more on `main`**

Run: `uv run pytest tests/ -q && cd frontend && npx vitest run`
Expected: all tests pass on `main` post-merge

- [ ] **Step 4: Push to origin**

```bash
git push origin main
```

Confirm the CI workflow triggers and passes on `main` (per Plan 00's CI setup).

- [ ] **Step 5: Delete the now-merged feature branch (local and remote)**

```bash
git branch -d feature/enterprise-oauth-tenancy
git push origin --delete feature/enterprise-oauth-tenancy
```

---

## Handoff

The enterprise OAuth + multi-tenancy migration is complete. `main` now runs Google OAuth sign-in, self-hosted Postgres, tenant-scoped shared data, admin-issued invites with Brevo email delivery, and a four-action audit log — with zero remaining Supabase code, dependencies, or database schema anywhere in the repo. `frontend/src/pages/PrivacyPage.tsx` accurately describes the new auth stack. The `feature/enterprise-oauth-tenancy` branch has been merged and deleted.
