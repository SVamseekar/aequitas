# Aequitas

<div align="center">

**See where the bus fails people — England, Ireland, the Netherlands, and France.**

*Open timetables × official deprivation. Same method, four countries. No licence fee.*

[![Stars](https://img.shields.io/github/stars/SVamseekar/aequitas?style=flat-square&color=ffd700&label=Stars)](https://github.com/SVamseekar/aequitas/stargazers)
[![Forks](https://img.shields.io/github/forks/SVamseekar/aequitas?style=flat-square&color=87ceeb&label=Forks)](https://github.com/SVamseekar/aequitas/network/members)
[![Python](https://img.shields.io/badge/python-3.12+-blue.svg?style=flat-square&logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-009688?style=flat-square&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![React](https://img.shields.io/badge/React-20232A?style=flat-square&logo=react&logoColor=61DAFB)](https://react.dev/)
[![DuckDB](https://img.shields.io/badge/DuckDB-Analytics-yellowgreen?style=flat-square&logo=duckdb&logoColor=white)](https://duckdb.org/)
[![License](https://img.shields.io/github/license/SVamseekar/aequitas?style=flat-square&color=gray)](LICENSE)

![Aequitas dashboard](docs/screenshots/landing-page.png)

</div>

---

## Current status (read this first)

See **[docs/CURRENT_STATE.md](docs/CURRENT_STATE.md)** for wave status. **Waves 1–5:** England map-first briefing + Ireland pack (`/app/ireland`) on the same score formula (HP decile, not IMD). Studio walk-to-stop is live when centroids exist. 15/30/45 stays honest-empty without r5py. NL / FR packs are **not** live (waves 7, 9). Waves 6–9 are not done.

**Quick start (full analytics):**

```bash
cp .env.example .env   # set DATABASE_URL / Google OAuth as needed
./scripts/dev.sh
# open http://localhost:5173
```

**Marketing site only** is on Vercel (`aequitas.souravamseekar.com`). Dashboard data needs the local API.


## Countries (same method)

| Country | Timetables | Deprivation | Small areas | Wave |
|---|---|---|---|---|
| England | BODS GTFS + NaPTAN | IMD 2025 (in-country) | LSOA 2021 | 1 live |
| Ireland | TFI GTFS_All.zip (free) | Pobal HP 2022 relative index / decile (not IMD) | CSO SA 2022, Republic only | 5 live |
| Netherlands | gtfs.ovapi.nl | CBS SES-WOA | wijk/buurt | 7 |
| France | NAP GTFS harvest | F-EDI or Filosofi proxy | IRIS | 9 |

Never plot those deprivation indices on one axis.

## The problem

Transport authorities everywhere have the same problem: mountains of open data — stop locations, timetables, deprivation indices, route geometries — spread across incompatible formats, and no fast path from raw data to the question that actually matters: **which communities are underserved, and by how much?**

That question still gets answered with spreadsheets and gut feel in most cities and regions around the world. Aequitas gives you a rigorous, auditable answer — complete with formula traces, plain-English narratives, and a policy scenario sandbox — in a dashboard anyone can use without a data science team.

> **Want to use or adapt this for your region?** Reach out first — martisoura@gmail.com

---

## What it produces

| Module | Output |
|---|---|
| **Equity** | Gini coefficient, Lorenz curve, Palma ratio, concentration index, triple-deprivation flags |
| **Accessibility** | 2SFCA catchments, 400m stop coverage, job/healthcare/education access gaps |
| **Service quality** | Headway, evening isolation, Sunday deserts, peak ratios, weekend penalty |
| **Route network** | Geometry, HHI operator concentration, route clustering by archetype |
| **Economic appraisal** | Benefit-cost ratios via standard transport appraisal methodology |
| **Carbon & modal shift** | Elasticity-based modal shift scenarios, national carbon reduction factors |
| **Policy scenarios** | Frequency restoration, last-bus extension, DRT — projected population impact and cost |
| **Market structure** | Franchising readiness and operator concentration tiers by region |

Every metric ships with a plain-English narrative and a documented formula trace back to the source data.

---

## What the data shows — England reference implementation

> Canonical pack (2026-07-19) from the pre-computed warehouse (`data/aequitas.duckdb`, built 2026-06-14). Single source of truth in code: `frontend/src/lib/metricsCanon.ts`.

**Scale:** 1.75M GTFS trips · 13,099 routes · 274,719 stops · 33,755 LSOAs (56.5M population)

**Quality:** 103 automated checks · 0 failures · spatial join 99.9993%

**Equity & service:**
- **Gini 0.5741** — bus service is more unequally distributed than household income (income Gini: 0.36)
- **Palma 5.702×** — the best-served 10% of areas receive 5.7× more service than the bottom 40%
- **Concentration index +0.1358** — service provision is systematically pro-rich
- **4,245 zero-stop LSOAs** · **612 triple-deprived** communities
- **Evening isolation 15.4%** of LSOAs · **Sunday deserts 20.0%**
- **55 analytical sections** · **8 policy dimensions** · **30 filter combos**
- **ML:** Random Forest R² 0.472 · HDBSCAN · Isolation Forest · 2SFCA

> Hosting posture: **local-only** for the current programme. Do not claim always-on cloud production until deliberately deployed.

The same methodology applies anywhere. The numbers change; the analytical framework does not.

---

## Architecture

```
Open data sources
    └──► Ingestion       GTFS · census boundaries · deprivation index · points of interest
         └──► Processing  Deduplication · spatial joins · service quality aggregation
              └──► Analytics  Equity · accessibility · ML clustering · economic appraisal
                   └──► DuckDB warehouse  ◄── read-only at runtime
                        └──► FastAPI backend
                             ├──► React dashboard
                             └──► RAG chatbot  (FAISS retrieval + Gemini Flash)
```

**Design principles**
- All analytics are pre-computed at build time — the runtime API is a read-only lookup, zero live computation during a user session
- Narratives are generated by deterministic, evidence-gated rules — suppressed when evidence is weak, never fabricated
- The chatbot is grounded in the warehouse; it cannot return a number that isn't in the pre-computed data

### Stack

| Layer | Technology |
|---|---|
| Frontend | React 19, Vite, TypeScript, Tailwind CSS, MapLibre + free OSM/CARTO tiles |
| Backend | FastAPI (Python 3.12+) |
| Warehouse | DuckDB (single pre-built binary, served read-only) |
| Intermediate data | Parquet |
| Chatbot | Gemini Flash + FAISS + all-MiniLM-L6-v2 embeddings |
| Auth & persistence | Local Postgres + Google OAuth (session cookies); multi-tenant workspaces |

---

## Who it's for

**Transport authorities and local government** — build the evidence base for funding bids, route reviews, and franchising decisions without needing an in-house data science team.

**National ministries and regulators** — benchmark equity performance across regions, run what-if policy scenarios, and produce audit-ready outputs for committees and consultations.

**Researchers and academics** — fully reproducible, open methodology; every metric is documented to formula level with source data citations and a ground-truth validation suite.

**Civic technologists and open data practitioners** — fork the repo, swap the ingestion layer for your country's data sources, and keep the analytics pipeline and dashboard unchanged.

---

## Running it for your country

The pipeline is built around a country-agnostic data model. The only layer that changes between countries is ingestion.

| Data type | England source | Standard equivalent |
|---|---|---|
| Transit timetables | BODS | Any GTFS feed |
| Stop locations | NaPTAN | GTFS `stops.txt` |
| Deprivation index | IMD | SEIFA (AU) · NZDep (NZ) · ACS (US) · EU-SILC (EU) · national equivalents |
| Small-area boundaries | ONS LSOA | SA1 (AU) · Meshblock (NZ) · Census Tract (US) · LAU (EU) |
| Points of interest | GIAS / NHS ODS | National open datasets |
| Population | ONS Census | Any national census |

Write a new ingestion module. The processing, analytics, warehouse schema, and frontend need no changes.

---

## Getting started

**Prerequisites:** Python 3.12+, Node 18+, [`uv`](https://docs.astral.sh/uv/). Optional: Docker (Postgres for auth), Google OAuth credentials, `GEMINI_API_KEY` (chat). **r5py reach:** JDK **17** (`brew install openjdk@17`) and `uv pip install r5py` — not required for the rest of the dashboard.

**Local only** for the current programme — production hosting is deferred (see `docs/FUTURE_WORK.md`).

### Quick start (one command)

```bash
git clone https://github.com/SVamseekar/aequitas.git
cd aequitas
uv sync
cp .env.example .env   # edit as needed
# If you already have a built warehouse at data/aequitas.duckdb, skip the pipeline.
# Otherwise: uv run aequitas run
chmod +x scripts/dev.sh
./scripts/dev.sh
```

- API: `http://127.0.0.1:8000` — `GET /api/health` → `{"status":"ok","warehouse":"connected"}`
- Frontend: `http://localhost:5173` — Vite proxies `/api` → `:8000`
- Smoke: `uv run python scripts/smoke_local.py`
- App: `http://localhost:5173/app/england` (map home + score)
- Reach (optional, hours for full England): place Geofabrik England PBF in `data/raw/osm/` (gitignored) and BODS GTFS in `data/raw/bods/`, destination points as `data/processed/destinations_{jobs,gp,school}.parquet`, then:

```bash
uv run aequitas reach --region E12000005   # West Midlands batch; add --force to recompute
```

Skip is automatic when the reach cache is newer than GTFS+PBF. Access UI names ITL1s that are not in the parquet.

`scripts/dev.sh` starts Postgres when nothing is listening on `:5432` (via `docker compose`), then uvicorn and Vite. It defaults `ENVIRONMENT=development` and `DEV_AUTH_BYPASS=true` so the dashboard works without Google for local analytics demos.

### Backend only

```bash
uv sync
uv run uvicorn aequitas.api.app:app --reload --host 127.0.0.1 --port 8000
```

The ASGI target is the module-level `app` (`app = create_app()` in `src/aequitas/api/app.py`). Factory form: `uvicorn aequitas.api.app:create_app --factory`.

### Frontend only

```bash
cd frontend
npm install
npm run dev
```

### Local environment variables

See `.env.example` and `AGENTS.md`. Summary:

| Area | Variables |
|---|---|
| Analytics warehouse | `AEQUITAS_DB_PATH`, FAISS paths |
| Auth / tenancy | `DATABASE_URL`, `SESSION_SECRET`, `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET` |
| Local demos | `ENVIRONMENT=development`, `DEV_AUTH_BYPASS=true` (never in production) |
| Chat (optional) | `GEMINI_API_KEY` |
| URLs | `AEQUITAS_CORS_ORIGINS`, `FRONTEND_URL`, `API_PUBLIC_URL` |

**Postgres:** `docker compose up -d` → `DATABASE_URL=postgresql://aequitas:aequitas@localhost:5432/aequitas`, or Homebrew Postgres → `postgresql://localhost/aequitas`. Schema migrations run on API startup.

**Auth notes:** Overview and dimension sections are public. Dashboard shell, chat, export, and saved items require a session. With `DEV_AUTH_BYPASS=true` the API returns a synthetic dev user from `/api/auth/me` so ProtectedRoute works without Google. For real OAuth, set Google credentials and `DEV_AUTH_BYPASS=false`.

---

## Get in touch

If you're a transport authority, ministry, research institution, or civic tech organisation and want to deploy or adapt Aequitas — **reach out before you start**. I can help assess data availability for your country, scope the adaptation work, and flag the gotchas from the England build.

**Marti Soura Vamseekar** · martisoura@gmail.com

Good reasons to reach out:
- Adapting Aequitas to a new country or transit network
- Research collaboration or co-authorship
- Institutional partnerships or grant-funded deployments
- Custom analytics modules, additional policy scenarios, or bespoke appraisal methodologies

Bug reports and feature requests: [open an issue](https://github.com/SVamseekar/aequitas/issues)
