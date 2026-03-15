---
name: aequitas-context
description: Load full Aequitas project context — architecture, data sources, design decisions, current phase. Use when starting a new task on this project or when context about the project is needed.
user-invocable: false
---

Read and internalize the following files in order:

1. `/Users/souravamseekarmarti/Projects/aequitas/CLAUDE.md` — core project rules, stack, and locked ground truth numbers
2. `/Users/souravamseekarmarti/.claude/projects/-Users-souravamseekarmarti-Projects-aequitas/memory/MEMORY.md` — project memory and decisions
3. `/Users/souravamseekarmarti/.claude/projects/-Users-souravamseekarmarti-Projects-aequitas/memory/architecture.md` — architecture details
4. `/Users/souravamseekarmarti/Projects/aequitas/docs/SESSION_REPORT_2026-03-11.md` — Phase 0 completion summary: what was built, gap analysis, next steps
5. `/Users/souravamseekarmarti/Projects/aequitas/docs/data-downloads.md` — dataset download status (all ✅), download methods, API details, and processing notes
6. `/Users/souravamseekarmarti/Projects/aequitas/docs/figures-registry.md` — every figure in the project with status (✅ Confirmed / ⚠️ Stale / ❌ Unverified). Check before using any number.

After reading, confirm you have understood:
- The full stack (React + FastAPI + DuckDB + Gemini + FAISS)
- The pre-compute architecture (no runtime analytics)
- The 9 socio-economic factors being correlated
- The critical data traps (NaPTAN filtering, BODS deduplication, population denominator)
- **Current phase: Phase 1 — Pipeline + Warehouse (started 2026-03-15).** Phase 0 COMPLETE (2026-03-14): 19 notebooks, 103 checks, 0 FAIL, ground truth locked, all 8 policy dimensions covered. Phase 1 builds `src/aequitas/` — raw data → Parquet → analytics → InsightEngine → DuckDB. Plan: `docs/superpowers/plans/2026-03-15-phase1-pipeline-warehouse.md`
- Build phases consolidated to 3 (was 7): Phase 1 Pipeline+Warehouse, Phase 2 Frontend+RAG, Phase 3 Deploy+CI/CD
- Which figures are ✅ Confirmed vs ⚠️ Stale vs ❌ Unverified (from figures-registry.md)
- Code quality standards

Do not summarize back to the user unless asked. Just confirm context is loaded.
