---
name: aequitas-context
description: Load full Aequitas project context — architecture, data sources, design decisions, current phase. Use when starting a new task on this project or when context about the project is needed.
user-invocable: false
---

Read and internalize the following files in order:

1. `/Users/souravamseekarmarti/Projects/aequitas/CLAUDE.md` — core project rules and stack
2. `/Users/souravamseekarmarti/.claude/projects/-Users-souravamseekarmarti-Projects-aequitas/memory/MEMORY.md` — project memory and decisions
3. `/Users/souravamseekarmarti/.claude/projects/-Users-souravamseekarmarti-Projects-aequitas/memory/architecture.md` — architecture details

After reading, confirm you have understood:
- The full stack (React + FastAPI + DuckDB + Gemini + FAISS)
- The pre-compute architecture (no runtime analytics)
- The 8 socio-economic factors being correlated
- The critical data traps (NaPTAN filtering, BODS deduplication, population denominator)
- The current build phase
- Code quality standards

Do not summarize back to the user unless asked. Just confirm context is loaded.
