# Aequitas

**Policy intelligence for bus transport equity — evidence-graded analytics for transport authorities, ministries, and researchers.**

Aequitas pre-computes equity, accessibility, and economic analytics over national open transport and census data, then surfaces them through a fast, evidence-graded dashboard and a natural-language Q&A assistant. Built first for the UK, designed to generalise to any country with comparable open data (EU, US, AUS, NZ).

![Aequitas landing page](docs/screenshots/landing-page.png)

---

## What it does

Most transport authorities sit on mountains of open data — stop locations, timetables, census deprivation indices, route geometries — spread across a dozen incompatible formats. Aequitas turns that data into a single, navigable answer to the question that matters: **which communities are underserved, by how much, and what would it cost to fix?**

- **Equity & deprivation** — Gini, Lorenz, Palma ratio, concentration index, triple-deprivation flags
- **Accessibility** — 2SFCA catchments, 400m coverage, job/healthcare/education gaps
- **Service quality** — headway, evening isolation, Sunday deserts, peak service ratios
- **Route network** — geometry, operator concentration (HHI), route clustering
- **Modal shift & carbon** — elasticity-based modal shift, national carbon factors
- **Economic appraisal** — benefit-cost ratios via standard transport appraisal methodology
- **Franchising readiness** — operator concentration and readiness tiers
- **Policy scenarios** — model frequency restoration, last-bus extension, demand-responsive transport, and see the projected population impact and cost before writing a funding bid

Every chart and number ships with a plain-English narrative explanation and a documented formula trace back to source data — built for people who need to defend a number in a board meeting, not just look at it.

---

## Architecture

```
Raw open data  →  Python pipeline (ingestion → processing → analytics)
               →  Pre-computed results in DuckDB (read-only at runtime)
               →  FastAPI backend
               →  React dashboard + RAG chatbot (Gemini + FAISS)
```

**Design principles:**
- Analytics are pre-computed at build time — the runtime API is a read-only lookup, never running live analysis
- Narrative generation is deterministic (Jinja2 + evidence-gated rules) — no LLM in the analytics path
- The chatbot uses retrieval-augmented generation over the same pre-computed narratives, so it can't hallucinate numbers that aren't in the warehouse

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

Aequitas is under active development. Current focus: building out the pipeline and warehouse for England, with the data model designed to extend to other countries with comparable open transport/census datasets.

This is a policy analysis tool, not official government guidance — see the in-app disclaimer for data limitations.

---

## Contact

Bug reports and feature requests: [open an issue](https://github.com/SVamseekar/aequitas/issues).
Research collaboration or institutional enquiries: martisoura@gmail.com
