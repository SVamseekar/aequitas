# Aequitas

<div align="center">

**Open transport equity intelligence for governments, researchers, and civic technologists.**

*Which communities are underserved — by how much — and what would it cost to fix?*

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

## The problem

Transport authorities have the data. They rarely have the tools to turn it into defensible, audit-ready evidence. Stop locations, timetables, deprivation indices, and route geometries sit across a dozen incompatible formats — and the question *"which communities are underserved, and by how much?"* still gets answered with spreadsheets and gut feel.

Aequitas changes that. It ingests open transport and census data, runs a rigorous analytics pipeline, and serves the results through a fast evidence-graded dashboard and a natural-language Q&A assistant — so a policy analyst can find an answer, trace it to its source formula, and defend it in a board meeting.

> **Want to use this for your country or region?** Get in touch before you start — martisoura@gmail.com

---

## What's inside

| Module | What it produces |
|---|---|
| **Equity** | Gini coefficient, Lorenz curve, Palma ratio, concentration index, triple-deprivation flags |
| **Accessibility** | 2SFCA catchments, 400m stop coverage, job/healthcare/education access gaps |
| **Service quality** | Headway, evening isolation, Sunday deserts, peak ratios, weekend penalty |
| **Route network** | Geometry, HHI operator concentration, route clustering by archetype |
| **Economic appraisal** | Benefit-cost ratios via standard transport appraisal methodology |
| **Carbon & modal shift** | Elasticity-based modal shift scenarios, national carbon reduction factors |
| **Policy scenarios** | Frequency restoration, last-bus extension, DRT — with projected population impact and cost |
| **Franchising readiness** | Operator concentration and readiness tiers by region |

Every metric ships with a plain-English narrative and a formula trace back to the source data.

---

## Key findings — England reference implementation

> These numbers come from the pre-computed warehouse over all 33,755 LSOAs in England.

- **Gini 0.57** — bus service is more unequally distributed than UK household income (Gini 0.36)
- **Palma 5.7** — the top 10% of areas receive 5.7× more service than the bottom 40%
- **Concentration index +0.14** — service provision is pro-rich; deprived communities are systematically under-served
- **6,776 LSOAs** have zero accessibility to key services within a 400m walk of any bus stop
- **53–72% of service variance** is explained by policy choices, not demographics — the gap is fixable

---

## Architecture

```
Open data  ──►  Ingestion          NaPTAN · BODS/GTFS · Census · IMD · GIAS · OS
               └──► Processing     Deduplication · spatial joins · service quality
                    └──► Analytics Equity · accessibility · ML · economic appraisal
                         └──► DuckDB warehouse  (read-only at runtime)
                              └──► FastAPI  ──►  React dashboard
                                             └──►  RAG chatbot (FAISS + Gemini Flash)
```

**Design principles**
- Pre-computed at build time — the runtime API is a read-only lookup, zero live analysis during user sessions
- Narratives are deterministic (Jinja2 + evidence-gated rules) — suppressed when evidence is absent, never fabricated
- The chatbot is grounded in the warehouse; it cannot return numbers that aren't in the pre-computed data

### Stack

| Layer | Technology |
|---|---|
| Frontend | React 18, Vite, TypeScript, Tailwind CSS, shadcn/ui, Mapbox GL |
| Backend | FastAPI (Python 3.12+) |
| Warehouse | DuckDB (single pre-built file, served read-only) |
| Intermediate data | Parquet |
| Chatbot | Gemini Flash + FAISS + all-MiniLM-L6-v2 embeddings |
| Auth & persistence | Supabase |

---

## Who it's for

**Transport authorities and local government** — build the evidence base for funding bids, route reviews, and franchising decisions without a data science team.

**National ministries and regulators** — benchmark equity across regions, run what-if policy scenarios, and produce audit-ready outputs.

**Researchers and academics** — reproducible, open methodology; every metric is documented to formula level with source data citations.

**Civic technologists** — fork it, adapt the ingestion pipeline to your country's data sources, keep the analytics and frontend.

---

## Adapting to your country

The pipeline is built around a common data model. To run Aequitas for a new country:

| Data type | England source | Equivalent |
|---|---|---|
| Bus timetables | BODS (GTFS) | Any national GTFS feed |
| Stop locations | NaPTAN | GTFS `stops.txt` |
| Deprivation index | IMD 2019/2025 | SEIFA (AU) · NZDep (NZ) · ACS (US) · EU-SILC (EU) |
| Small-area boundaries | ONS LSOA | SA1 (AU) · Meshblock (NZ) · Census Tract (US) · LAU (EU) |
| Points of interest | GIAS / NHS ODS | National equivalents |

Swap the ingestion modules. The analytics, warehouse, and frontend need no changes.

Contributions adapting the pipeline to Australia, New Zealand, EU member states, or the United States are very welcome — open an issue to discuss.

---

## Getting started

### Prerequisites

- Python 3.12+
- Node 18+
- [`uv`](https://docs.astral.sh/uv/) (Python package manager)
- A Supabase project (for auth)
- A Gemini API key (for the chatbot)

### Backend

```bash
git clone https://github.com/SVamseekar/aequitas.git
cd aequitas

uv sync
uv run aequitas build        # ingest data, run analytics, build the DuckDB warehouse
uv run uvicorn aequitas.api.app:app --reload
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

The dashboard connects to `http://localhost:8000` by default. See `frontend/src/api/client.ts` to point it at a different API host.

---

## Project status

The England implementation is complete — 33,755 LSOAs, the full national bus network, all eight analytics modules, pre-computed warehouse, dashboard, and RAG chatbot.

The data model is country-agnostic by design. If you're working on a port to another country or want to discuss methodology, open an issue or reach out directly.

This is a policy analysis tool, not official government guidance. See the in-app disclaimer for data limitations.

---

## Get in touch

If you're a transport authority, ministry, research institution, or civic tech team and want to use or adapt Aequitas — **reach out before you start**. I can help you assess data availability for your country, scope the adaptation work, and avoid the traps we hit building the England implementation.

**Marti Soura Vamseekar** — martisoura@gmail.com

Relevant conversations:
- Deploying Aequitas for a new country or region
- Research collaboration or methodology questions
- Institutional partnerships or funding
- Custom analytics modules or policy scenarios

Bug reports and feature requests: [open an issue](https://github.com/SVamseekar/aequitas/issues)
