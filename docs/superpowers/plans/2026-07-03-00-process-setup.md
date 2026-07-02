# Process Setup Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Commit the pending footer/contact-form work to `main`, add CI that runs the existing test suites on push, and create the feature branch that all subsequent enterprise-OAuth-tenancy plans will build on.

**Architecture:** No application code changes. This is repo hygiene: one commit for unrelated in-flight work, one new GitHub Actions workflow file, one new git branch.

**Tech Stack:** GitHub Actions, git, `uv` (Python), `npm` (frontend).

## Global Constraints

- This plan must complete and be merged/pushed to `main` before any task in later plans (01 onward) begins — every later plan assumes CI exists and work happens on `feature/enterprise-oauth-tenancy`.
- Per `docs/superpowers/specs/2026-07-03-enterprise-oauth-tenancy-design.md`'s Development Process section: no required PR reviews, no branch protection rules — this is a solo-developer project, keep process lightweight.
- Backend test commands must always be prefixed `uv run` (bare `python -m pytest` fails — `loguru` and other deps aren't on the bare interpreter's path).
- Frontend test commands run from the `frontend/` directory.

---

### Task 1: Commit the pending footer/contact-form work, and make the contact form actually functional

**Files:**
- Modify (already changed, uncommitted): `frontend/index.html`, `frontend/public/sitemap.xml`, `frontend/src/App.tsx`, `frontend/src/components/landing/LandingFooter.tsx`, `frontend/src/components/layout/Footer.tsx`, `frontend/src/lib/site.ts`, `frontend/src/pages/ContactPage.tsx`, `frontend/vercel.json`, `frontend/vite.config.ts`
- Create (already created, untracked): `frontend/about.html`, `frontend/api/contact.js`, `frontend/contact.html`, `frontend/disclaimer.html`, `frontend/privacy.html`, `frontend/refunds.html`, `frontend/src/pages/PrivacyPage.tsx`, `frontend/src/pages/RefundsPage.tsx`, `frontend/src/pages/TermsPage.tsx`, `frontend/terms.html`

**Interfaces:**
- Consumes: nothing (this is a commit of already-written code from an earlier session); `frontend/api/contact.js` already reads `DISCORD_CONTACT_WEBHOOK_URL` from the environment (Discord webhook, not email — no SMTP/nodemailer involved, per the decision to avoid personal-Gmail automated-sending risk)
- Produces: a clean `main` with no uncommitted changes (which Task 3's branch creation depends on) **and** a contact form that actually delivers submissions, not just code that compiles

- [ ] **Step 1: Verify the frontend build succeeds with the pending changes**

Run: `cd frontend && npm run build`
Expected: build completes with no errors (warnings about chunk size are pre-existing and fine)

- [ ] **Step 2: Verify the frontend typecheck succeeds**

Run: `cd frontend && npx tsc --noEmit -p tsconfig.json`
Expected: no output (clean pass)

- [ ] **Step 3: Review the diff one more time before committing**

Run: `git status --short && git diff --stat`
Expected: only the files listed above appear; nothing under `src/aequitas/` or `docs/superpowers/specs/` is staged by accident

- [ ] **Step 4: Stage and commit**

```bash
git add frontend/index.html frontend/public/sitemap.xml frontend/src/App.tsx \
  frontend/src/components/landing/LandingFooter.tsx frontend/src/components/layout/Footer.tsx \
  frontend/src/lib/site.ts frontend/src/pages/ContactPage.tsx frontend/vercel.json \
  frontend/vite.config.ts frontend/about.html frontend/api/contact.js frontend/contact.html \
  frontend/disclaimer.html frontend/privacy.html frontend/refunds.html \
  frontend/src/pages/PrivacyPage.tsx frontend/src/pages/RefundsPage.tsx \
  frontend/src/pages/TermsPage.tsx frontend/terms.html

git commit -m "$(cat <<'EOF'
Add Privacy, Terms, Refunds pages and working contact form

New legal/footer pages (Privacy, Terms, Refunds) follow the existing
About/Contact/Disclaimer pattern: React page component + static SEO
stub HTML + sitemap entry + footer links. Contact form now actually
sends (via a Vercel serverless function) instead of a mailto link.
EOF
)"
```

- [ ] **Step 5: Set the required Vercel environment variable (manual — cannot be automated)**

`frontend/api/contact.js` reads `process.env.DISCORD_CONTACT_WEBHOOK_URL` and throws if it's unset (`if (!webhookUrl) { throw new Error('DISCORD_CONTACT_WEBHOOK_URL is required') }`), which the handler catches and turns into a 503 — so without this variable, the deployed contact form silently fails for every visitor with "Unable to send your message right now."

The webhook is a Discord Incoming Webhook URL (`https://discord.com/api/webhooks/{id}/{token}`) for a channel you control, created via Discord's Server Settings → Integrations → Webhooks → New Webhook. This is a secret and must never be committed to the repo or pasted into any file this plan creates.

Set it in Vercel: Project → Settings → Environment Variables → add `DISCORD_CONTACT_WEBHOOK_URL` with the webhook URL as the value (or `vercel env add DISCORD_CONTACT_WEBHOOK_URL` from the CLI). Apply it to whichever environments you deploy to (Production and/or Preview).

If this webhook URL has ever been pasted into a chat, commit message, or any non-secret-storage location, treat it as compromised and regenerate it in Discord (same Webhooks screen → "New Webhook URL" resets the token without deleting the channel or message history) before or after setting it in Vercel — the old token stops working the moment it's regenerated, so update Vercel with the new one if you rotate it.

- [ ] **Step 6: Verify the contact form actually delivers to Discord**

Once the env var is set and the site is deployed (or via `vercel dev` locally with the same variable set in `frontend/.env.local`, which is gitignored), submit the `/contact` page's form and confirm a message embed appears in the target Discord channel with the submitted Name/Email/Organisation/Message fields. This closes the loop on Task 1 — the code was committed in Step 4, but isn't actually functional in production until this step passes.

Expected: commit succeeds, `git status --short` now shows a clean working tree

- [ ] **Step 5: Verify clean working tree**

Run: `git status --short`
Expected: no output

---

### Task 2: Add GitHub Actions CI workflow

**Files:**
- Create: `.github/workflows/test.yml`

**Interfaces:**
- Consumes: `uv run pytest` (backend test entrypoint, already works — confirmed 509 tests pass), `cd frontend && npx vitest run` (frontend test entrypoint, already works — confirmed 16 tests pass)
- Produces: a CI check that runs on every push and PR, giving later plans (01–07) a safety net while they touch auth end-to-end

- [ ] **Step 1: Check for an existing `.github` directory**

Run: `ls -la .github 2>/dev/null || echo "no .github directory"`
Expected: either shows nothing relevant, or confirms no workflows exist yet — this repo has no CI today per the spec's Development Process section

- [ ] **Step 2: Create the workflow file**

Create `.github/workflows/test.yml`:

```yaml
name: Tests

on:
  push:
  pull_request:

jobs:
  backend:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Install uv
        uses: astral-sh/setup-uv@v3
      - name: Set up Python
        run: uv python install 3.12
      - name: Install dependencies
        run: uv sync --all-extras
      - name: Run backend tests
        run: uv run pytest tests/ -q

  frontend:
    runs-on: ubuntu-latest
    defaults:
      run:
        working-directory: frontend
    steps:
      - uses: actions/checkout@v4
      - name: Set up Node
        uses: actions/setup-node@v4
        with:
          node-version: "20"
          cache: "npm"
          cache-dependency-path: frontend/package-lock.json
      - name: Install dependencies
        run: npm ci
      - name: Run frontend tests
        run: npx vitest run
```

- [ ] **Step 2: Commit the workflow**

```bash
git add .github/workflows/test.yml
git commit -m "Add CI workflow to run backend and frontend test suites on push"
```

Expected: commit succeeds

- [ ] **Step 3: Push to origin and verify the workflow runs**

Run: `git push origin main`

Then check the Actions tab on GitHub (or `gh run list --limit 1` if `gh` CLI is available) to confirm the workflow triggered and both jobs (`backend`, `frontend`) pass.

Expected: both jobs show green/success within a few minutes. If either fails, stop and fix before proceeding to Task 3 — later plans depend on this CI actually working, not just existing.

---

### Task 3: Create the feature branch for the auth migration

**Files:** none (git operation only)

**Interfaces:**
- Consumes: clean `main` from Task 1, working CI from Task 2
- Produces: `feature/enterprise-oauth-tenancy` branch, which every task in plans 01–07 commits to

- [ ] **Step 1: Confirm `main` is clean and up to date**

Run: `git status --short && git log --oneline -3`
Expected: clean working tree; the CI workflow commit from Task 2 is the most recent commit

- [ ] **Step 2: Create and switch to the feature branch**

```bash
git checkout -b feature/enterprise-oauth-tenancy
```

Expected: `git branch --show-current` prints `feature/enterprise-oauth-tenancy`

- [ ] **Step 3: Push the branch to origin so CI runs on it too**

```bash
git push -u origin feature/enterprise-oauth-tenancy
```

Expected: push succeeds; the CI workflow from Task 2 triggers on this branch (via the `push:` trigger with no branch filter) and passes, confirming the branch starts from a known-good state

---

## Handoff

Once all three tasks are complete: `main` has the footer/contact work and a working CI workflow, and `feature/enterprise-oauth-tenancy` exists and is checked out. Plan `01-postgres-foundation.md` begins here.
