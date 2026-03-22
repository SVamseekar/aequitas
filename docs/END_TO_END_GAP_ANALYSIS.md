# Aequitas — End-to-End Gap Analysis

**Date:** 2026-03-18
**Phase:** Phase 2 (Frontend + RAG) — in progress
**Purpose:** Document every gap between "all the pieces exist" and "the app works end-to-end from login to chart rendering."

---

## Executive Summary

The Aequitas platform has a strong data foundation (Phase 0 audit: 19 notebooks, 103 checks, 0 FAIL) and well-architected code (72 Python files, 44 React components, 8 API routers). However, the system has never been tested end-to-end as a connected application. The warehouse is populated, the FAISS index is built, the frontend renders — but they've never all worked together with a real user logging in, browsing a dimension, and asking a question.

This document maps every gap, its severity, and the exact fix needed.

---

## 1. What Works Today

| Component | Status | Evidence |
|-----------|--------|----------|
| DuckDB Warehouse | **Populated** | 107 MB, 1,530 section_results (51 sections x 30 filter combos) |
| FAISS Vector Index | **Built** | 12 MB index + 3.7 MB metadata, ~3,700 text chunks |
| FastAPI Backend | **Implemented** | 8 routers, all endpoints defined, health check works |
| React Frontend | **7 pages, 44 components** | Landing, Auth, Dashboard, Dimension, Compare, Profile, About |
| InsightEngine | **Generates narratives** | Jinja2 + 15 evidence-gated rules, deterministic |
| Pipeline CLI | **Implemented** | `aequitas run` orchestrates 7 stages |
| Python Test Suite | **62 test files** | 2,275 lines, ~30% coverage by line count |
| Validation Gates | **All pass** | 6/6 ground truth checks confirmed |

---

## 2. Critical Gaps (Prevent Any Real Use)

### 2.1 Supabase Not Configured

**Impact:** Auth doesn't work. Conversation persistence returns 503. No user can sign in.

**What's needed:**
- Create a Supabase project
- Enable Google OAuth provider in Supabase Auth settings
- Create two PostgreSQL tables:

```sql
-- conversations
CREATE TABLE conversations (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id TEXT NOT NULL,
  title TEXT NOT NULL,
  created_at TIMESTAMPTZ DEFAULT now(),
  updated_at TIMESTAMPTZ DEFAULT now()
);
ALTER TABLE conversations ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Users see own conversations" ON conversations
  FOR ALL USING (auth.uid()::text = user_id);

-- messages
CREATE TABLE messages (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  conversation_id UUID REFERENCES conversations(id) ON DELETE CASCADE,
  user_id TEXT NOT NULL,
  role TEXT NOT NULL CHECK (role IN ('user', 'assistant')),
  content TEXT NOT NULL,
  created_at TIMESTAMPTZ DEFAULT now()
);
ALTER TABLE messages ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Users see own messages" ON messages
  FOR ALL USING (auth.uid()::text = user_id);
```

- Set environment variables:
  - `SUPABASE_JWT_SECRET` — from Supabase Settings > API > JWT Secret
  - `SUPABASE_URL` — project URL
  - `SUPABASE_SERVICE_ROLE_KEY` — service role key
  - `VITE_SUPABASE_URL` — same URL (for frontend)
  - `VITE_SUPABASE_PUBLISHABLE_KEY` — anon/public key (for frontend)

**Files involved:**
- `src/aequitas/api/auth.py` — JWT verification
- `src/aequitas/api/routers/conversations.py` — CRUD operations
- `frontend/src/integrations/supabase/client.ts` — frontend client
- `frontend/src/contexts/AuthContext.tsx` — auth state

---

### 2.2 Gemini API Key Not Set

**Impact:** Chat endpoint returns 503. The RAG chatbot — the flagship feature — doesn't work.

**What's needed:**
- Get a Google AI API key from https://aistudio.google.com/apikey
- Set `GEMINI_API_KEY` environment variable
- The app uses Gemini Flash (cost-effective) — no need for Pro tier

**Files involved:**
- `src/aequitas/api/config.py` — reads the key
- `src/aequitas/api/deps.py` — warns if missing at startup
- `src/aequitas/api/services/rag.py` — calls Gemini API

---

### 2.3 No .env.example Template

**Impact:** Any developer (including future you) doesn't know what environment variables to set.

**What's needed:** Create `.env.example` at project root:

```env
# Backend
GEMINI_API_KEY=
SUPABASE_URL=https://xxx.supabase.co
SUPABASE_SERVICE_ROLE_KEY=
SUPABASE_JWT_SECRET=
AEQUITAS_DB_PATH=data/aequitas.duckdb
AEQUITAS_FAISS_INDEX=data/faiss_index.bin
AEQUITAS_FAISS_METADATA=data/faiss_metadata.json
AEQUITAS_CORS_ORIGINS=http://localhost:5173
ENVIRONMENT=development
DEV_AUTH_BYPASS=true

# Frontend (prefix with VITE_ for Vite exposure)
VITE_SUPABASE_URL=https://xxx.supabase.co
VITE_SUPABASE_PUBLISHABLE_KEY=
```

---

## 3. High-Priority Gaps (Restrict Feature Use)

### 3.1 Raw Data Not Present

**Impact:** Cannot re-run the pipeline from scratch. If the warehouse needs rebuilding, there's no source data.

**Current state:**
- `data/raw/` is **empty** (0 files)
- All raw data was consumed during Phase 0 audit notebooks
- The pipeline builder falls back to `data/audit/` parquets (Phase 0 outputs), so the warehouse builds successfully without raw data
- This works for now, but is fragile

**What's needed:**
- Document the data download process (partially done in `docs/data-downloads.md`)
- Either: (a) store download scripts that re-fetch from UK gov APIs, or (b) keep `data/audit/` parquets as the canonical source
- Decision: if `data/audit/` is the source of truth, rename it to something clearer and update pipeline config

**Risk level:** LOW in short term (audit parquets work fine), HIGH if data needs refreshing with newer BODS/NaPTAN releases.

---

### 3.2 `stops` and `routes` DuckDB Tables Empty

**Impact:** Any future endpoint that queries individual stops or routes will return empty results.

**Current state:**
- Schema defined in `src/aequitas/warehouse/schema.py`
- Builder creates the tables but never populates them because pipeline stages 1-2 (ingest, process) haven't run
- No current frontend feature queries these tables directly — all analytics use `section_results`

**What's needed:**
- Either populate from audit parquets, or remove the empty table definitions to avoid confusion
- If populated: `naptan_stops.parquet` → `stops` table, `route_geometries.parquet` → `routes` table

**Risk level:** LOW — no feature depends on these tables yet.

---

### 3.3 Frontend Test Coverage ~5%

**Current state:**
- 2 vitest files across 44 components and 7 pages
- No component rendering tests, no integration tests, no snapshot tests

**What's needed:**
- Priority test targets (highest risk of breaking):
  1. `DimensionPage` — complex data fetching + rendering
  2. `SectionCard` — handles many data shapes with formatValue()
  3. `ChatDrawer` — SSE streaming + focus trap
  4. `FilterDropdowns` — URL search param state
  5. `AuthPage` — Supabase integration

**Risk level:** MEDIUM — any refactor could silently break rendering.

---

### 3.4 No CI/CD Pipeline

**Impact:** Every deploy is manual. No automated test runs on PR. No build verification.

**What's needed:**
- GitHub Actions workflow:
  - `pytest` on Python changes
  - `npx tsc --noEmit` + `vitest run` on frontend changes
  - Build the frontend (`npm run build`)
  - Lint checks (optional)

**Risk level:** MEDIUM — acceptable for solo development, problematic if anyone else contributes.

---

## 4. Medium-Priority Gaps (Quality / Polish)

### 4.1 Chat UI Integration Not Tested End-to-End

**Current state:**
- `ChatDrawer` component exists with SSE streaming
- Backend `POST /api/chat` endpoint implemented with FAISS retrieval + Gemini streaming
- But nobody has ever: opened the drawer → typed a question → seen Gemini respond with grounded analytics

**What's needed:**
- Set `GEMINI_API_KEY`
- Open the app, open chat drawer, send a question like "What's the Gini coefficient for bus service?"
- Verify: FAISS retrieves relevant chunks → prompt built correctly → Gemini streams response → frontend renders markdown

---

### 4.2 PDF Export Partially Implemented

**Current state:**
- `GET /api/export/{dimension}` exists in `src/aequitas/api/routers/export.py`
- Uses ReportLab to generate PDFs
- Frontend has an "Export PDF" button on each dimension page

**Gap:** Not tested with real data. May produce empty or malformatted PDFs.

---

### 4.3 No Error Monitoring

**Current state:**
- Loguru logging throughout backend
- No log aggregation, no error tracking (Sentry, etc.)
- Frontend has no error reporting

**What's needed for production:**
- At minimum: structured logging to stdout for container environments
- Ideally: Sentry free tier for error tracking

---

### 4.4 Map Component Not Implemented

**Current state:**
- `ChartRenderer` dispatches chart types (bar, scatter, histogram, etc.)
- Choropleth maps referenced in design docs but no MapLibre GL integration

**What's needed:**
- MapLibre GL JS component for LSOA-level choropleth visualization
- GeoJSON boundaries for LSOAs (large file, ~50MB)

---

## 5. What Does NOT Need Fixing

These were flagged in code reviews but are actually fine:

| Item | Why It's Fine |
|------|---------------|
| Filter state persistence | Already uses URL search params — survives navigation |
| Compare page empty state | Has default region selections (North West vs London) |
| Loading skeletons | Already implemented on all data-fetching pages |
| Analytics docstrings | All public functions already documented |
| Ground truth constants | Single source in `metrics.py` with CLAUDE.md reference |
| FAISS index loading | Already cached in memory at startup, not rebuilt per request |

---

## 6. Verification Checklist

Run these checks to confirm end-to-end readiness:

```
SETUP
[ ] .env file created from .env.example with all keys populated
[ ] Supabase project created with conversations + messages tables
[ ] Google OAuth configured in Supabase Auth > Providers
[ ] GEMINI_API_KEY valid and working

BACKEND
[ ] `python -m uvicorn aequitas.api.app:create_app --factory --port 8000` starts without errors
[ ] GET http://localhost:8000/api/health returns {"status": "ok", "warehouse": "connected"}
[ ] GET http://localhost:8000/api/overview returns 8 dimensions with headline stats
[ ] GET http://localhost:8000/api/sections?dimension=equity&region=all&urban_rural=all returns sections
[ ] GET http://localhost:8000/api/metrics/ticker returns 6 headline metrics

FRONTEND
[ ] `npm run dev` starts on http://localhost:5173
[ ] Landing page loads at /
[ ] "Get Started" navigates to /auth
[ ] Google sign-in redirects to Supabase OAuth flow
[ ] After auth, redirected to /dashboard
[ ] Dashboard shows 8 dimension cards with headline stats
[ ] Clicking a dimension loads section cards with charts and narratives
[ ] Filter dropdowns (region, area type) update section content
[ ] Compare page loads two regions side by side
[ ] Export PDF button downloads a file

CHAT
[ ] Chat drawer opens from any page
[ ] Typing a question and pressing Send triggers SSE stream
[ ] Response renders with markdown formatting
[ ] Suggested questions work
[ ] Conversation persists in Supabase after page reload

PIPELINE
[ ] `aequitas validate` passes all 6 ground truth checks
[ ] `aequitas rag` rebuilds FAISS index without errors
[ ] `aequitas warehouse` rebuilds DuckDB from audit parquets
```

---

## 7. Recommended Sprint Order

| Sprint | Focus | Effort | Unblocks |
|--------|-------|--------|----------|
| **Day 1** | Supabase setup + .env.example + test auth flow | 2-3 hours | Auth, conversations |
| **Day 2** | Set Gemini key + test chat end-to-end | 1-2 hours | Chat feature |
| **Day 3** | Run verification checklist above, fix any failures | 3-4 hours | Confidence |
| **Week 2** | Frontend tests (top 5 components) + GitHub Actions CI | 1-2 days | Regression safety |
| **Week 3** | Map component (MapLibre GL + LSOA GeoJSON) | 2-3 days | Visual analytics |
| **Week 4** | Production deploy (hosting, HTTPS, monitoring) | 2-3 days | Public access |

---

## 8. Architecture Confidence

Despite the integration gaps, the core architecture is sound:

- **Pre-compute pattern works.** 1,530 section_results serve the entire dashboard with zero runtime computation. Response times will be <50ms.
- **FAISS + Gemini RAG is built correctly.** Chunks are paragraph-level, embeddings are cached, retrieval uses cosine similarity. The only missing piece is the API key.
- **InsightEngine is deterministic.** No LLM hallucination risk in narratives. Every number traces to source data.
- **DuckDB as read-only store is the right call.** No schema migrations, no connection pooling complexity, no write contention.

The gaps are configuration and integration, not architectural. The hardest engineering work is done.
