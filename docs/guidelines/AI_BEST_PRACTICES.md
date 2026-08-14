# AI Context Management & Best Practices

This document outlines the design strategy behind the AI-native configuration files in the Aequitas repository, addressing concerns about documentation staleness, token efficiency, and maintenance overhead.

---

## 1. The Problem with Monolithic Reference Files

In complex, data-heavy repositories (Python pipelines, FastAPI backend, React frontend), a single monolithic reference file or `CLAUDE.md` creates three primary bottlenecks:

1. **High Maintenance Friction (Staleness):** When coding styles, API endpoints, or database structures change, developers must remember to update a large, single file. Because it contains both low-level commands and high-level logic, it is frequently forgotten, making it go stale.
2. **Context & Token Bloat:** The full text of the reference is loaded into the AI’s prompt context on every command or edit. A large file wastes tokens and dilutes the AI's attention, causing it to ignore critical rules.
3. **No Domain Separation:** An AI developer working purely on the React frontend should not have its context window flooded with Python pipeline KDTree bugs or pandas chunking rules.

---

## 2. The Solution: Modular Context Architecture

Inspired by best practices from mature, AI-native repositories like [pocketshell](https://github.com/alexeygrigorev/pocketshell), Aequitas has migrated to a **Modular Context Directory**:

```
aequitas/
├── AGENTS.md                       # The Index & Command Runbook (Durable & Static)
└── docs/guidelines/
    ├── domain-rules.md             # Code patterns by language (Python, React/TS, SQL)
    ├── decisions.md                # Locked architectural rules & constraints
    ├── gotchas.md                  # Python quirks, DuckDB traps, and Vite v6 settings
    ├── git-branching.md            # Commit formats, local AI ignores, and worktrees
    ├── testing.md                  # Testing guidelines (Vitest, Pytest, Validation gates)
    └── deployment.md               # Pre-computation analytics packaging and Vercel
```

### File Breakdown & Purpose:

*   **[AGENTS.md](file:///Users/souravamseekarmarti/Projects/aequitas/AGENTS.md):** 
    *   *Purpose:* Acts as the entry runbook. It maps hardware environments and standard compile/test/run commands.
    *   *Staleness Prevention:* This file contains only durable command lines that change only when switching build tools (e.g. poetry to uv). It stays static.
*   **[docs/guidelines/domain-rules.md](file:///Users/souravamseekarmarti/Projects/aequitas/docs/guidelines/domain-rules.md):**
    *   *Purpose:* Enforces coding practices specific to directories. The AI reads this only when editing code in those specific subfolders (e.g., checking controller/service rules when editing Python files).
*   **[docs/guidelines/decisions.md](file:///Users/souravamseekarmarti/Projects/aequitas/docs/guidelines/decisions.md):**
    *   *Purpose:* Declares architectural restrictions (like no live compute at runtime, Jinja2 templates for InsightEngine).
    *   *Staleness Prevention:* Tracks history chronologically (like Architecture Decision Records). Instead of editing existing rules, you append new decisions, keeping history intact.
*   **[docs/guidelines/gotchas.md](file:///Users/souravamseekarmarti/Projects/aequitas/docs/guidelines/gotchas.md):**
    *   *Purpose:* Documents tricky traps (DuckDB read-only concurrency, ONS vintage naming, sentence-transformers token count).
*   **[docs/guidelines/git-branching.md](file:///Users/souravamseekarmarti/Projects/aequitas/docs/guidelines/git-branching.md):**
    *   *Purpose:* Keeps commit style rules, platform line endings, and local superpower/AI ignore guidelines.

---

## 3. Best Practices for Writing AI Context Rules

When editing or creating rules in `docs/guidelines/`, follow these principles to keep them effective:

### Rule 1: Prioritize Durable Invariants over Dynamic Logic
- **Do NOT Document:** Changing route path listings (e.g. `GET /api/overview`). Let the AI read this from the code routers.
- **Do Document:** Architectural constraints (e.g. "InsightEngine must remain deterministic; never call Gemini inside narrative builders").

### Rule 2: Enforce Negative Constraints
LLMs are highly responsive to absolute negative directives. Vague guidelines (e.g. *"Try to use Pydantic"*) are ignored. Use strong, capitalized negative qualifiers:
- *Bad:* "It is better to calculate route length via Haversine since shape_dist_traveled can be null."
- *Good:* "**NEVER** use BODS `shape_dist_traveled` to compute route lengths. You **MUST** compute route lengths using Haversine formulas."

### Rule 3: Leverage the `/learn` Command
When you teach an AI assistant a new convention (e.g. fixing a recurring compile issue or styling pattern), suggest using the `/learn` slash command to capture the context automatically in local configurations without manually rewriting documentation files.
