# Future Work

Deliberately deferred items — things we decided *not* to build now, with the reasoning, so they don't get lost or accidentally re-litigated later. Not a bug list; see `ISSUES.md` for that.

## Production hosting / cloud deploy (deferred 2026-07-19)

**Decision:** local-only until the full local E2E programme (Parts A–D) is complete. No Cloud Run, no Vercel-hosted API, no always-on production stack in this programme.

- **Why:** production site was broken / sleeping third parties; product shell (auth, LSOA, chat, empty filters) needs local reliability first. Human decision 2026-07-19.
- **In scope now:** `scripts/dev.sh`, Docker Compose Postgres, DuckDB on disk, Vite → local FastAPI proxy, smoke script.
- **Out of scope until local E2E done:** production Dockerfile / image, Vercel API rewrites to a hosted backend, Cloud Run / managed Postgres, production sleep mitigation, multi-region hosting.
- **Revisit when:** Parts A–D exit criteria met and a deliberate deploy decision is made. Track under a future plan; do not block product quality (Part E) or metrics handoffs (Part C) on hosting.

## Metrics canon handoffs (Part C, 2026-07-19)

Code surfaces (landing, about, auth, README, ticker fallback, equity card packing) use `frontend/src/lib/metricsCanon.ts` — **55 sections**, Gini **0.5741**, full scale pack. Non-code surfaces (CV `.docx`, portfolio `projects.ts`, pitch PDF) are **not** edited in this repo; apply the packets below in separate sessions. Do **not** claim always-on cloud production (local-only programme).

### Canonical pack

```
Aequitas — Public transport equity intelligence (England)
Scale: 1,752,443 GTFS trips · 13,099 routes · 274,719 active bus stops · 33,755 LSOAs · 56.5M population
Quality: 103 automated checks · 0 failures · spatial join 99.9993%
Equity: Gini 0.5741 · Palma 5.702× · CI +0.1358 pro-rich · 4,245 zero-stop LSOAs · 612 triple-deprived
Service: evening isolation 15.4% of LSOAs (5,189) · Sunday deserts 20.0% (6,745)
ML: Random Forest R² 0.472 · HDBSCAN · Isolation Forest · 2SFCA (400m)
Product: 55 analytical sections · 8 policy dimensions · 30 filter combos · FAISS RAG + Gemini 2.5 Flash
Stack (public): Python · FastAPI · DuckDB · React/Vite · Postgres session auth · FAISS · sentence-transformers · MapLibre · Observable Plot
Hosting: local demo / research platform — not marketed as always-on cloud production
```

| Wrong / stale | Correct |
|---|---|
| 51 analytical sections | **55** analytical sections |
| Gini 0.574 / 0.57 | Gini **0.5741** |
| Palma 5.7 alone | Palma **5.702×** |
| CI +0.14 / 0.1344 | CI **+0.1358** |
| Supabase-backed auth | Postgres session auth + Google OAuth (local) |
| Always-on production API | Soften: local demo-ready; cloud deferred |

### Packet 1 — CV

**File:** `/Users/souravamseekarmarti/Documents/Marti_Soura_Vamseekar_CV.docx`  
Export PDF; replace portfolio `public/*.pdf` CV copies.

```
• Built Aequitas — England bus transport equity intelligence: 1,752,443 GTFS trips · 13,099 routes · 274,719 stops · 33,755 LSOAs (56.5M population)
• Pre-computed warehouse with 103 quality checks (0 failures); spatial join accuracy 99.9993%
• Equity metrics: Gini 0.5741 · Palma 5.702× · CI +0.1358 pro-rich · 4,245 zero-stop LSOAs · 612 triple-deprived communities
• ML & product: Random Forest (R² 0.472), HDBSCAN, Isolation Forest, 2SFCA; FAISS RAG chatbot across 55 analytical sections and 8 policy dimensions
• Stack: Python · FastAPI · DuckDB · React/Vite · Postgres session auth · FAISS · Gemini
```

### Packet 2 — Portfolio

**Repo:** `/Users/souravamseekarmarti/Projects/Portfolio/martisouravamseekar-portfolio`  
**File:** `src/data/projects.ts` (Aequitas entry)

```ts
metrics: [
  "1.75M GTFS trips · 13,099 routes · 274,719 stops · 33,755 LSOAs (56.5M population)",
  "103 quality checks · 0 failures · spatial join at 99.9993% accuracy",
  "Gini 0.5741 · Palma 5.702 · 4,245 zero-stop LSOAs · 612 triple-deprived communities",
  "ML: Random Forest (R² 0.472), HDBSCAN, Isolation Forest, 2SFCA accessibility scoring",
  "FAISS RAG chatbot across 55 analytical sections and 8 policy dimensions",
],
```

Also: drop Supabase from stack if listed; mark `UK_Bus_Analytics_Research_Portfolio.md` historical; refresh CV PDFs.

### Packet 3 — Pitch deck

**File:** `/Users/souravamseekarmarti/Downloads/MSV_AI_Labs_Pitch_Deck.pdf`

| Line | Copy |
|---|---|
| Scale 1 | 1.75M trips · 13,099 routes |
| Scale 2 | 274,719 stops · 33,755 LSOAs |
| Equity | Gini 0.5741 · Palma 5.702× |
| Quality / product | 103/0 quality · 55 sections |
| Optional | 8 policy dimensions · 30 region×area filters |

Remove truncated Gini **0.574**; no overclaim of cloud production.

## Empty `stops` / `routes` warehouse tables (documented 2026-07-19, Part E)

**Fact:** Live DuckDB (`data/aequitas.duckdb`) has schema for `stops` and `routes` but **0 rows**. Map / network features that would join these tables are **degraded** — do not present choropleth or route-network maps as complete until tables are reloaded from audit/pipeline Parquet (NaPTAN + BODS geometry).

- **Why empty:** warehouse build focused on `section_results` + LSOA analytics; stop/route raw load was skipped or not copied into this DB revision.
- **What still works:** dimension sections, overview, ticker (from `section_results` / provenance), LSOA tables that *are* populated (`lsoa_demographics`, `anomalies`, `coverage_prediction`, `lsoa_clusters`, …).
- **Do not:** invent map completeness in marketing copy while row counts are zero.
- **Fix path:** pipeline/warehouse reload of NaPTAN stops + BODS routes into DuckDB; then re-enable map layers with a row-count guard in the API.

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
