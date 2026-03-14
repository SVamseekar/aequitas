# Aequitas — Claude Context

## Project
UK bus transport policy intelligence platform. Policy makers (DfT, LTA planners) get evidence-graded analytics correlating bus coverage with socio-economic deprivation, plus a Gemini RAG chatbot for natural language Q&A.

## Stack
- **Frontend:** React + Vite + TypeScript + Tailwind + shadcn/ui
- **Backend:** FastAPI (Python 3.12+)
- **Warehouse:** DuckDB (single pre-built file — all analytics pre-computed at build time)
- **Intermediate data:** Parquet
- **LLM:** Gemini Flash (Google AI Pro) — upgrade to Pro only if Flash underperforms
- **Vector store:** FAISS (faiss-cpu, in-memory)
- **Embeddings:** all-MiniLM-L6-v2 (CPU)
- **Auth/persistence:** Supabase (reuse bharat-alpha patterns)
- **CI/CD:** GitHub Actions

## Architecture in One Sentence
Python pipeline ingests UK government open data → pre-computes all analytics results at build time (covering 8 policy dimensions, exact section count TBD after EDA completes) → stores everything in DuckDB → FastAPI serves pre-built results to React frontend → Gemini RAG chatbot answers policy questions over pre-computed narratives.

## Policy Dimensions (EDA must cover all 8 before pipeline build)
1. Equity & deprivation (Gini/Lorenz/Palma, vulnerability index, triple deprivation)
2. Accessibility (2SFCA, 400m buffer coverage, job/healthcare/education gaps)
3. Service quality (headway, evening isolation, Sunday deserts, peak ratios)
4. Route network (geometry, operator HHI, route clustering)
5. Modal shift & carbon (DfT elasticities, car dependency reduction, DESNZ 2025 factors)
6. Economic appraisal (BCR/Green Book/TAG v2.03fc, investment gap, GDP multipliers)
7. Bus Services Act 2025 (LTA franchising readiness, operator concentration)
8. Policy scenario modelling (parameterised: frequency restoration, last bus extension, DRT)

## Non-Negotiable Decisions
1. No Streamlit — React frontend only
2. Gemini only for LLM — no other providers
3. Pre-compute everything — DuckDB is a read-only lookup store, zero runtime analytics
4. InsightEngine is deterministic — Jinja2 + evidence-gated rules, no LLM in narrative generation
5. Pydantic v2 at every data boundary — raw in, validated model out, always
6. Code quality over speed — single-purpose files, no monoliths, no quick hacks
7. Population denominator = total ONS regional population (56,490,056) — never pipeline-filtered

## Commit Messages
No co-author lines. Clean, descriptive messages only.

## Code Standards
- Python: type hints everywhere, loguru logging, no bare `except`, docstrings on public functions
- TypeScript: strict mode, no `any`, components ≤ 200 lines, no business logic in components
- Tests: pytest for pipeline/intelligence/warehouse; vitest for frontend
- Every metric on screen must trace to source data through a documented formula

## Current Phase
**Phase 0 — Data audit + EDA COMPLETE (2026-03-14).** 19 notebooks total (01, 02–02i, 03a–03h, 04a–04f). 103 checks, 0 FAIL, ground truth locked. All 8 policy dimensions covered, all 9 socio-economic factors confirmed. → **Phase 1 (pipeline build) begins next.**

## Ground Truth (Locked — do not change without re-running audit)
| Entity | Count | Source |
|--------|-------|--------|
| England active bus stops | 274,719 | NaPTAN (BCT/BCS/BCE, Status=active, ATCO 0xx-4xx) |
| BODS unique routes | 13,099 | BODS GTFS (9 feeds, deduplicated) |
| BODS total trips | 1,752,443 | BODS GTFS |
| Census 2021 England LSOAs | 33,755 | ONS Census |
| Census population (England) | 56,490,056 | ONS TS001 |
| IMD 2025 LSOAs | 33,755 | MHCLG (zero mismatch) |
| LSOAs with zero bus stops | 4,245 | Spatial join |
| IMD–stop Pearson correlation | -0.0644 | Weak negative |
| LSOA archetypes (KMeans k=4) | 4 | 02e_multivariate_clustering.ipynb |
| GIAS open schools (England) | 27,183 | 03d (EstablishmentStatus=1) |
| Secondary + all-through schools (geocoded) | 3,336 | 03d (England bounding box filtered) |
| BRES England MSOAs | 6,791 | 03e (NOMIS BRES 2023) |
| England employees (BRES 2023) | 27,343,200 | 03e |
| Code-Point Open England postcodes | 1,492,016 | 03h |
| NHS hospitals (geocoded) | 3,714 | 03b |
| NHS GP practices (geocoded) | 12,059 | 03c |
| Bus CO2 (avg local, DESNZ 2025) | 0.10385 kg/pax-km | 03g (cell D81) |
| Car CO2 (avg diesel, DESNZ 2025) | 0.17304 kg/veh-km | 03g (cell D53) |
| Routes with geometry (shapes.txt) | 7,241 (53.1%) | 04a — shape_dist_traveled 100% null; Haversine computed |
| Mean route length | 23.0 km (median 18.7 km) | 04a |
| Cross-LA routes | 5,143 (37.7%) | 04a |
| Evening isolated LSOAs | 5,189 (15.4%) | 04b |
| Sunday desert LSOAs | 6,745 (20.0%) | 04b |
| Mean service quality index | 65.4/100 | 04b |
| Gini coefficient (bus service, pop-weighted) | 0.5741 | 04c — exceeds UK income Gini 0.36 |
| Palma ratio | 5.702 | 04c — top 10% gets 5.7× more than bottom 40% |
| Concentration Index (trips vs IMD) | +0.1358 PRO-RICH | 04c — key policy finding |
| Triple-deprived LSOAs | 612 (1.8%) | 04c |
| RF coverage prediction R² | 0.472 | 04d — 53-72% policy-driven variance |
| Top SHAP feature | nocar_pct | 04d |

## Reference Projects
@~/.claude/projects/-Users-souravamseekarmarti-Projects-aequitas/memory/MEMORY.md
