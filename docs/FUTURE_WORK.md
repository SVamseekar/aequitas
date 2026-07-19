# Future Work

Deliberately deferred items — things we decided *not* to build now, with the reasoning, so they don't get lost or accidentally re-litigated later. Not a bug list; see `ISSUES.md` for that.

## Production hosting / cloud deploy (deferred 2026-07-19)

**Decision:** local-only until the full local E2E programme (Parts A–D) is complete. No Cloud Run, no Vercel-hosted API, no always-on production stack in this programme.

- **Why:** production site was broken / sleeping third parties; product shell (auth, LSOA, chat, empty filters) needs local reliability first. Human decision 2026-07-19.
- **In scope now:** `scripts/dev.sh`, Docker Compose Postgres, DuckDB on disk, Vite → local FastAPI proxy, smoke script.
- **Out of scope until local E2E done:** production Dockerfile / image, Vercel API rewrites to a hosted backend, Cloud Run / managed Postgres, production sleep mitigation, multi-region hosting.
- **Revisit when:** Parts A–D exit criteria met and a deliberate deploy decision is made. Track under a future plan; do not block product quality (Part E) or metrics handoffs (Part C) on hosting.

## From the enterprise OAuth + multi-tenancy migration (2026-07-03)

Spec: `docs/superpowers/specs/2026-07-03-enterprise-oauth-tenancy-design.md`

- **Audit log viewer UI** — the backend already writes every entry (invite created/accepted, member removed, role changed) and `GET /api/tenants/{id}/audit-log` returns them, but no frontend page displays the list. Deferred because nobody has actually needed to read this yet — building a viewer (sorting, filtering, pagination) before there's a real usage pattern to design against would be guesswork. The data isn't lost, just not surfaced.
- **Microsoft OAuth** — launched with Google only. Reasoning: most of the target audience (UK public sector, transport researchers) has Google accounts readily; a second provider means a second app registration, a second consent screen, and doubled OAuth testing surface for unvalidated demand. Revisit if users actually ask for Microsoft sign-in.
- **Cross-provider account linking** — e.g. someone signs in with Google today, later wants to add Microsoft and have it merge into the same account. Only becomes a real problem once there's a second provider to link to — solving it now would be solving a problem that can't happen yet.
- **Billing / seat limits** — no paid tier exists yet (subscriptions are planned, not shipped). Enforcing seat limits against a billing system that doesn't exist would be speculative.
- **Migrating existing Supabase accounts** — not needed for this migration; confirmed no real external users existed at cutover time, only test/personal accounts.
- **EU data residency / region-aware hosting** — Aequitas may extend its analytics to EU countries in the future (a data/product decision), but that doesn't imply an EU-region hosting requirement today. Revisit once there's an actual EU deployment target, not before.
- **Production hosting** — this migration runs entirely on localhost by design; no production environment has been configured yet.

## Open UI gap found during plan review (2026-07-03)

- **Policy notes editing** — was missing entirely from the original 7-plan set (no `db.py` function, no route, no tests, no frontend UI existed anywhere) despite the spec calling for it. Found during plan review and fixed into Plan 04 (backend) and Plan 06 (frontend edit UI) — not deferred, already addressed. Listed here only as a record of what almost shipped incomplete.
