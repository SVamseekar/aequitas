# Handoff: CV + Pitch Deck metrics (2026-07-19)

**Source of truth:** `frontend/src/lib/metricsCanon.ts`  
**Code status:** Aequitas app/landing use 55 sections, Gini 0.5741, Postgres session auth.  
**Hosting:** Local demo-ready (`./scripts/dev.sh`). Cloud API deferred (billing).

---

## Hard replacements (all surfaces)

| Wrong | Correct |
|---|---|
| 51 sections / 51 analytical | **55** |
| Gini 0.574 / 0.57 | **0.5741** |
| Palma 5.7 alone | **5.702×** |
| CI +0.14 / 0.1344 | **+0.1358** |
| Supabase auth (Aequitas) | **Postgres session auth + Google OAuth** |
| Always-on cloud production | **Local demo-ready; public analytics via local API** |

---

## Packet 1 — CV

**Files:**  
- `/Users/souravamseekarmarti/Documents/Marti_Soura_Vamseekar_CV.docx` (updated 2026-07-19: 55 sections)  
- Export PDF and replace portfolio `public/Marti_Soura_Vamseekar_CV.pdf`

### Aequitas bullets (canonical)

```
Aequitas — Public Transport Equity Intelligence · GitHub
M.Sc. Dissertation → production-grade platform · FastAPI · DuckDB · FAISS RAG · React/Vite · GTFS-portable

– Data Pipeline: 7-stage validated pipeline processing 1,752,443 GTFS trips, 13,099 routes, 274,719 stops, 33,755 LSOAs (56.5M population); 103 automated quality checks, 0 failures; spatial join accuracy 99.9993%.
– ML & Equity Analytics: Random Forest (R² 0.472), HDBSCAN, Isolation Forest; 2SFCA 400m catchment; findings — Gini 0.5741, Palma 5.702×, 4,245 zero-stop LSOAs, 612 triple-deprived communities.
– Product: FAISS RAG policy Q&A across 55 analytical sections and 8 policy dimensions; Bus Services Act 2025 franchising readiness; Google OAuth + multi-tenant Postgres sessions.
```

### Stack line (optional)
`Python · FastAPI · DuckDB · React/Vite · Postgres session auth · FAISS · Gemini · MapLibre · Observable Plot`

---

## Packet 2 — Portfolio (already applied in code)

**Repo:** `martisouravamseekar-portfolio`  
**File:** `src/data/projects.ts` — Aequitas metrics use **55** sections; stack uses **Postgres session auth** (not Supabase).  
Commit: `a00a650`

Still do: replace CV PDF under `public/` when PDF is regenerated.

---

## Packet 3 — Pitch deck (NVIDIA / general)

**File:** `/Users/souravamseekarmarti/Downloads/MSV_AI_Labs_Pitch_Deck.pdf`

### Aequitas slide — Key Metrics (replace cells)

| Cell | Copy |
|---|---|
| Scale 1 | **1.75M** trips · **13,099** routes |
| Scale 2 | **274,719** stops · **33,755** LSOAs |
| Equity | Gini **0.5741** · Palma **5.702×** |
| Quality / product | **103/0** quality · **55** sections |
| Optional line | 8 policy dimensions · 30 region×area filters |

### Body text (if present)

> Public transport equity analytics: 7-stage pipeline over England open data (NaPTAN, BODS, Census, IMD 2025). FAISS RAG + Gemini for policy Q&A. Multi-tenant Google OAuth (local). **Local demo-ready** — not marketed as always-on cloud production.

### Remove / avoid
- Gini **0.574** (use 0.5741)  
- **51** sections  
- Overclaiming always-on production API  

### Non-NVIDIA clones
Keep product slides; swap only “Why NVIDIA” closing slide.

---

## Verification checklist

- [ ] CV text: no “51 analytical”  
- [ ] CV Gini 0.5741  
- [ ] Pitch Aequitas metrics match table above  
- [ ] Portfolio live site after deploy shows 55  
- [ ] App landing: `metricsCanon` 55 / 0.5741  
