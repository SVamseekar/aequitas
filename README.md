# Aequitas

[![GitHub Stars](https://img.shields.io/github/stars/SVamseekar/aequitas?style=flat-square&color=ffd700&label=Stars)](https://github.com/SVamseekar/aequitas/stargazers)
[![GitHub Forks](https://img.shields.io/github/forks/SVamseekar/aequitas?style=flat-square&color=87ceeb&label=Forks)](https://github.com/SVamseekar/aequitas/network/members)
[![Python Version](https://img.shields.io/badge/python-3.12+-blue.svg?style=flat-square&logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-009688?style=flat-square&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![React](https://img.shields.io/badge/React-20232A?style=flat-square&logo=react&logoColor=61DAFB)](https://react.dev/)
[![Gemini](https://img.shields.io/badge/Gemini%20AI-Flash-orange?style=flat-square&logo=google&logoColor=white)](https://deepmind.google/technologies/gemini/)
[![DuckDB](https://img.shields.io/badge/DuckDB-Analytics-yellowgreen?style=flat-square&logo=duckdb&logoColor=white)](https://duckdb.org/)
[![License](https://img.shields.io/github/license/SVamseekar/aequitas?style=flat-square&color=gray)](LICENSE)

**Open transport equity intelligence — evidence-graded analytics for transport authorities, ministries, and researchers.**

Aequitas answers the question every transport authority faces but rarely has the tools to answer cleanly: **which communities are underserved, by how much, and what would it cost to fix?**

It pre-computes equity, accessibility, and economic analytics over open transport and census data, then surfaces them through a fast, evidence-graded dashboard and a natural-language Q&A assistant. The reference implementation covers England — the data model and pipeline are designed from the ground up to port to any country with comparable open datasets (Australia, New Zealand, EU member states, United States).

![Aequitas landing page](docs/screenshots/landing-page.png)

---

## Who it's for

- **Transport authorities and local government** — build the evidence base for funding bids, route reviews, and franchising decisions
- **National ministries and regulators** — benchmark equity across regions, model policy scenarios before committing spend
- **Researchers and academics** — reproducible, open methodology; every metric traces back to its source formula and data
- **Civic technologists** — fork it, adapt the pipeline to your country's data sources, and deploy your own instance

---

## What it does

Most transport authorities sit on mountains of open data — stop locations, timetables, census deprivation indices, route geometries — spread across a dozen incompatible formats. Aequitas ingests, joins, and pre-computes all of it so the runtime API is a fast, read-only lookup — never running live analysis during a user session.

- **Equity & deprivation** — Gini, Lorenz, Palma ratio, concentration index, triple-deprivation flags
- **Accessibility** — 2SFCA catchments, 400m coverage, job/healthcare/education access gaps
- **Service quality** — headway, evening isolation, Sunday deserts, peak service ratios
- **Route network** — geometry, operator concentration (HHI), route clustering
- **Modal shift & carbon** — elasticity-based modal shift, national carbon factors
- **Economic appraisal** — benefit-cost ratios via standard transport appraisal methodology
- **Franchising readiness** — operator concentration and readiness tiers by region
- **Policy scenarios** — model frequency restoration, last-bus extension, demand-responsive transport, and see projected population impact and cost before writing a funding bid

Every chart and number ships with a plain-English narrative and a documented formula trace back to source data — built for people who need to defend a number in a board meeting, not just look at it.

---

## Architecture

```
Open data sources  →  Python pipeline (ingestion → processing → analytics)
                   →  Pre-computed results in DuckDB (read-only at runtime)
                   →  FastAPI backend
                   →  React dashboard + RAG chatbot (Gemini + FAISS)
```

**Design principles:**
- Analytics are pre-computed at build time — the runtime API is a read-only lookup, never running live analysis
- Narrative generation is deterministic (Jinja2 + evidence-gated rules) — no generative model in the analytics path
- The chatbot uses retrieval-augmented generation over the same pre-computed narratives, so answers are grounded in the warehouse data

### Stack

| Layer | Technology |
|---|---|
| Frontend | React, Vite, TypeScript, Tailwind, shadcn/ui |
| Backend | FastAPI (Python 3.12+) |
| Warehouse | DuckDB (single pre-built file) |
| Intermediate data | Parquet |
| LLM | Gemini Flash |
| Vector store | FAISS (in-memory) |
| Embeddings | all-MiniLM-L6-v2 |
| Auth & persistence | Supabase |

---

## Adapting to your country

The pipeline is structured around a common data model. To run Aequitas for a new country you need:

| Data type | England source | Equivalent elsewhere |
|---|---|---|
| Bus timetables | BODS (GTFS) | Any GTFS feed |
| Stop locations | NaPTAN | Any GTFS stops.txt |
| Deprivation index | IMD 2019/2025 | SEIFA (AU), NZDep (NZ), ACS (US), EU-SILC (EU) |
| Census boundaries | ONS LSOA | SA1 (AU), Meshblock (NZ), Census Tract (US), LAU (EU) |
| Population | Census | National census |

Swap the ingestion modules, keep the analytics and frontend unchanged.

---

## Getting started

### Backend

```bash
# from the repo root
uv sync
uv run aequitas build   # run the pipeline and build the warehouse
uv run uvicorn aequitas.api.app:app --reload
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

The dashboard expects the API at `http://localhost:8000` by default — see `frontend/src/api/client.ts` to point it elsewhere.

---

## Project status

Active development. Current reference implementation covers England (33,755 LSOAs, national bus network). The data model is intentionally generic — contributions adapting the pipeline to other countries are welcome.

This is a policy analysis tool, not official government guidance — see the in-app disclaimer for data limitations.

---

## Contact

Bug reports and feature requests: [open an issue](https://github.com/SVamseekar/aequitas/issues).
Research collaboration or institutional enquiries: martisoura@gmail.com
