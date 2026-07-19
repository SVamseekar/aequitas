# Aequitas — Current State (2026-07-19)

Authoritative product snapshot for humans and agents. Prefer this over older gap analyses.

---

## 1. What works where

| Surface | What you get | Needs local backend? |
|---|---|---|
| **Vercel / aequitas.souravamseekar.com** | Marketing site: landing, about, contact, legal, methodology, accessibility, SEO stubs | **No** for static pages |
| **Explore / dashboard on Vercel alone** | Charts/API **do not work** until API is proxied or you run locally | **Yes** (local API) |
| **Local full stack** | Full analytics + filters + (optional) Google OAuth + chat | `./scripts/dev.sh` |

**Answer to “is the landing enough?”**  
Landing is updated and live after Vercel deploy. **Functional analytics (dashboard, filters, chat, export)** require the **local API** (or a future Cloud Run API — currently deferred for billing).

```bash
./scripts/dev.sh
# Frontend http://localhost:5173  (proxies /api → :8000)
# API     http://127.0.0.1:8000/api/health
uv run python scripts/smoke_local.py
```

---

## 2. Canonical metrics (do not drift)

From `frontend/src/lib/metricsCanon.ts` / `data/audit/ground_truth.json`:

| Metric | Value |
|---|---|
| Trips | 1,752,443 (1.75M) |
| Routes | 13,099 |
| Stops | 274,719 |
| LSOAs | 33,755 |
| Population | 56,490,056 (56.5M) |
| Quality | 103 checks · 0 fails · 14 warns |
| Spatial join | 99.9993% |
| Gini | **0.5741** |
| Palma | **5.702×** |
| CI | **+0.1358** |
| Zero-stop LSOAs | 4,245 |
| Triple-deprived | 612 |
| Evening isolated | 15.4% (5,189) |
| Sunday deserts | 20.0% (6,745) |
| RF R² | 0.472 |
| Sections | **55** |
| Dimensions | 8 |
| Filter combos | 30 |

---

## 3. Architecture (current)

```
Browser (Vite / Vercel static)
  ├─ Public marketing pages (no API)
  ├─ /dashboard/* → needs /api/overview, /api/sections, … (DuckDB)
  └─ Auth (Google OAuth) → /api/auth/* → Postgres sessions/tenants
Chat → FAISS + Gemini (optional GEMINI_API_KEY)
```

- **Auth:** Google OAuth + signed cookies + multi-tenant Postgres (Part A). Not Supabase.  
- **Warehouse:** DuckDB `data/aequitas.duckdb` (gitignored; must exist locally).  
- **Cloud API:** Deferred (billing). No Aequitas Cloud Run service; image deleted.

---

## 4. Programme status

| Part | Status |
|---|---|
| A OAuth tenancy | Done (local) |
| B Local boot / smoke | Done |
| E Product quality | Done |
| C Metrics canon | Done |
| D Landing / SEO / footer | Done |
| Cloud production API | Deferred |
| CV / pitch PDF | Handoffs in `docs/HANDOFF_CV_AND_PITCH.md` |

---

## 5. OAuth (local complete checklist)

Required in `.env`:

```env
ENVIRONMENT=development
DATABASE_URL=postgresql://localhost/aequitas   # or docker compose
SESSION_SECRET=<long random>
GOOGLE_CLIENT_ID=...
GOOGLE_CLIENT_SECRET=...
FRONTEND_URL=http://localhost:5173
API_PUBLIC_URL=http://localhost:8000
AEQUITAS_CORS_ORIGINS=http://localhost:5173
```

Google Cloud Console → OAuth client → redirect URI:  
`http://localhost:8000/api/auth/callback/google`

Optional demos without Google:

```env
DEV_AUTH_BYPASS=true   # never in production
```

Apply schema: `src/aequitas/api/auth/schema.sql` via app migration on startup / Plan A scripts.

---

## 6. Accessibility & SEO

- Accessibility statement: `/accessibility`  
- Methodology: `/methodology`  
- Sitemap: `frontend/public/sitemap.xml`  
- robots.txt disallows private app routes  
- Search Console: add property `https://aequitas.souravamseekar.com` → submit sitemap (owner action)  
- WCAG: target 2.2 AA; run automated checks after deploy (see `docs/A11Y_REPORT.md` when generated)

---

## 7. Superseded documents

Do **not** treat as current product truth without checking this file:

- `docs/END_TO_END_GAP_ANALYSIS.md` (2026-03)  
- `ISSUES.md` June “5 of 51 precompute” narrative  
- `docs/AEQUITAS_MASTER_REFERENCE.md` historical 51-section notes  
- Portfolio `UK_Bus_Analytics_Research_Portfolio.md` (Streamlit era)

---

## 8. Contact

Support: `aequitas@souravamseekar.com`  
Site: `https://aequitas.souravamseekar.com`  
Local: `http://localhost:5173`
