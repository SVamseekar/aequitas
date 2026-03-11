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
Python pipeline ingests UK government open data → pre-computes 1,290 analytics results → stores in DuckDB → FastAPI serves to React frontend → Gemini RAG chatbot answers policy questions over pre-computed narratives.

## Non-Negotiable Decisions
1. No Streamlit — React frontend only
2. Gemini only for LLM — no other providers
3. Pre-compute everything — DuckDB is a read-only lookup store, zero runtime analytics
4. InsightEngine is deterministic — Jinja2 + evidence-gated rules, no LLM in narrative generation
5. Pydantic v2 at every data boundary — raw in, validated model out, always
6. Code quality over speed — single-purpose files, no monoliths, no quick hacks
7. Population denominator = total ONS regional population (~56.3M) — never pipeline-filtered

## Commit Messages
No co-author lines. Clean, descriptive messages only.

## Code Standards
- Python: type hints everywhere, loguru logging, no bare `except`, docstrings on public functions
- TypeScript: strict mode, no `any`, components ≤ 200 lines, no business logic in components
- Tests: pytest for pipeline/intelligence/warehouse; vitest for frontend
- Every metric on screen must trace to source data through a documented formula

## Current Phase
**Phase 0 — Data audit.** No pipeline code exists yet. Next: build `notebooks/01_data_audit.ipynb`, profile every raw source, lock ground truth counts.

## Reference Projects
@~/.claude/projects/-Users-souravamseekarmarti-Projects-aequitas/memory/MEMORY.md
