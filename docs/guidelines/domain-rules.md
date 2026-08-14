# Domain Coding Guidelines (Aequitas)

These guidelines define the coding conventions and architectural patterns expected when modifying specific parts of the Aequitas platform.

---

## 1. Python Backend & Data Pipeline
*Applies to: `src/aequitas/`*

- **Type Hints:** Strict type hinting is enforced. Functions **must** have return types and typed arguments.
- **Pydantic v2:** All request/response schemas and config entities **must** inherit from Pydantic v2 `BaseModel`.
- **Logging:** Use `loguru` (imported as `from loguru import logger`) for all logging. **NEVER** use standard print statements or default logging library.
- **Error Handling:** Avoid bare `except:` blocks. Always specify the exception class (e.g. `except ValueError:`) or use `except Exception as e:`.
- **Command Prefix:** All python execution/testing commands **must** be run through `uv run` to ensure dependency context matches the virtual environment.

---

## 2. Frontend Web App (React / TypeScript)
*Applies to: `frontend/src/`*

- **TypeScript Strictness:** Strict typing is enforced. **Never** use `any` or `// @ts-ignore` to silence type errors.
- **Component Complexity:** Keep components focused and small (preferably ≤200 lines). Extract heavy chart building or map rendering to utility files or helper components.
- **State & Routing:** Use React Router v8 for routing. Filter state (region, urban/rural status) **must** be stored and synced in URL search parameters to make views fully shareable.
- **Chart Rendering:** All charts **must** be built using Observable Plot (`@observablehq/plot`).
- **UI State Handling:** Every card or visualization component **must** handle: (1) loading state, (2) error state, (3) empty data fallback.

---

## 2.1 Multi-country schema
- Warehouse and filter URLs include `country` ∈ `{england, ireland, netherlands, france}`.
- Deprivation is **in-country rank only**. Never plot IMD vs Pobal HP vs SES-WOA vs F-EDI on one axis.
- App routes live under `/app/:country/...`. Legacy `/dashboard/*` redirects to `/app/england/...`.

## 3. Database & Storage Layers
- **DuckDB Warehouse:** The database `data/aequitas.duckdb` is served read-only at runtime. Access it using the DuckDB Python library or connection pool, making sure to close connections properly.
- **Supabase Integrations:** Supabase handles JWT verification (HS256) and conversation persistence. Ensure all database interactions go through RLS (Row Level Security) queries.
