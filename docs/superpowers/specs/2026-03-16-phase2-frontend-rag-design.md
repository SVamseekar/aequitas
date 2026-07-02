# Phase 2: Frontend + RAG — Design Spec

**Date:** 2026-03-16
**Status:** Draft
**Depends on:** Phase 1 pipeline + warehouse (complete), InsightEngine expansion (complete)

---

## Goal

Build a React dashboard and Gemini RAG chatbot that lets UK policy makers (DfT, LTA planners) explore pre-computed bus transport analytics across 8 policy dimensions and 9 English regions. Design inspired by Our World in Data — clean, chart-driven, narrative-supported, printable.

## Design Decisions (Locked)

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Page model | Hybrid — homepage cards + dimension pages with tab navigation | Gives both overview and depth |
| Content density | Balanced — headline + summary + chart + expandable narrative | Policy makers are time-poor; depth available when needed |
| Navigation | Top horizontal tab bar for 8 dimensions | 8 items fits comfortably; familiar pattern |
| Global filters | Dropdowns in header (region + urban/rural) | Compact, always visible, shareable via URL params |
| Chatbot access | Floating button + right-side slide-out drawer | Accessible from any page without losing context |
| Chart library | Observable Plot + D3 for charts; MapLibre GL JS for choropleths | OWID aesthetic; WebGL performance for 33K LSOA polygons |
| Colour theme | Light content + dark header | Printable/PDF-friendly; brand identity in header |
| Chart types (v1) | 7 core types: horizontal_bar, grouped_bar, stacked_bar, scatter_regression, lorenz_curve, shap_bar, choropleth | Covers all 51 sections; box_violin/heatmap/scatter_clusters degrade to DataTable |
| Unsupported charts | box_violin, heatmap, scatter_clusters → DataTable fallback | Add renderers only if GOV.UK feedback requests them |
| UI primitives | shadcn/ui (Button, Select, Sheet, Collapsible, Tooltip) | Accessible by default; avoids re-implementing ARIA patterns |
| Router | React Router v7 | Needed for `useSearchParams()` URL-based filter state |
| Accessibility | WCAG 2.1 AA, colourblind-safe palettes, data table fallbacks | Mandatory for government audience |

---

## Architecture

### System Layers

```
┌─────────────────────────────────────────────────────┐
│  DATA LAYER (exists)                                │
│  aequitas.duckdb: section_results (51 × 12 combos)  │
│  + 7 LSOA analytics tables + provenance             │
│  FAISS index: built at pipeline time, loaded on     │
│  startup (all-MiniLM-L6-v2 embeddings)              │
└──────────────────────┬──────────────────────────────┘
                       │ DuckDB reads
                       ▼
┌─────────────────────────────────────────────────────┐
│  API LAYER (new — FastAPI)                          │
│  GET  /api/overview         Homepage headline stats │
│  GET  /api/sections         Filtered section results│
│  GET  /api/lsoa/{table}     LSOA drill-down data    │
│  GET  /api/provenance/{id}  Metric audit trail      │
│  POST /api/chat             FAISS → Gemini RAG      │
└──────────────────────┬──────────────────────────────┘
                       │ JSON over HTTP
                       ▼
┌─────────────────────────────────────────────────────┐
│  FRONTEND (new — React + Vite + TS + Tailwind)      │
│  Homepage → Dimension pages (tab bar) → Chat drawer │
│  Observable Plot + D3 charts; MapLibre GL maps      │
└─────────────────────────────────────────────────────┘
```

### Data Flow

All analytics are pre-computed. The API is a thin read layer over DuckDB — zero runtime calculation.

1. **Homepage** — `GET /api/overview` returns 8 headline stats (one per dimension). Rendered as cards.
2. **Dimension page** — `GET /api/sections?dimension=equity&region=all&urban_rural=all` returns section results. Each result has `stats` (numbers), `chart_data` (plot-ready JSON), and `narrative` (Markdown).
3. **Chat** — `POST /api/chat` receives user query + current context (dimension, region). Backend embeds query (~5ms), retrieves top-5 FAISS chunks, constructs prompt, streams Gemini Flash response via SSE.
4. **Provenance** — Any metric on screen can be clicked to reveal `GET /api/provenance/{metric_id}` — formula, inputs, source files.

---

## Dimension-to-Section Mapping

The InsightEngine section registry uses category prefixes (a, b, c, d, f, g, j, bsa, ps). The frontend maps these to 8 user-facing dimensions. The API resolves `?dimension=X` to the corresponding section_id prefixes.

| Frontend Dimension | Route | Registry Categories | Section IDs | Headline Section |
|---|---|---|---|---|
| Equity & Deprivation | `/equity` | F (Equity & Social Inclusion) | f1–f6 | f1_gini |
| Accessibility | `/accessibility` | A (Coverage & Accessibility) | a1–a8 | a5_service_deserts |
| Service Quality | `/service-quality` | B (Service Quality) | b1–b5 | b1_frequency |
| Route Network | `/route-network` | C (Route Characteristics) | c1–c7 | c3_operator_hhi |
| Socio-Economic & ML | `/correlations` | D (Socio-Economic Correlations) + G (ML Insights) | d1–d8, g1–g5 | d8_feature_importance |
| Economic Appraisal | `/economic` | J (Economic Impact & BCR) | j1–j4 | j2_bcr |
| Bus Services Act 2025 | `/bus-services-act` | BSA | bsa1–bsa3 | bsa1_franchising_readiness |
| Policy Scenarios | `/scenarios` | PS (Policy Scenario Modelling) | ps1–ps5 | ps5_scenario_comparison |

**Notes:**
- Categories D and G are merged into one "Socio-Economic & ML" dimension (13 sections). This is the largest dimension — the frontend may need sub-grouping (e.g., collapsible "Correlations" and "ML Insights" headers within the page).
- The "Headline Section" column defines which section's lead stat populates the homepage card for that dimension.
- This mapping is defined as a frontend constant in `lib/constants.ts` — no `/api/dimensions` endpoint needed (static data).

### Filter Combinations

Precompute produces 12 filter combos (not 30 — single-region × single-area-type combos are skipped):
- "all" × {all, urban, rural} = 3
- 9 ONS regions × "all" = 9
- **Total: 12 combos × 51 sections = 612 rows in section_results**

---

## API Design

### `GET /api/overview`

Returns homepage headline stats. The API reads the "headline section" (per mapping above) for each dimension and extracts the lead stat from its `stats` JSON.

```
Query params: region (default "all"), urban_rural (default "all")

Response: {
  dimensions: [
    {
      id: "equity",
      name: "Equity & Deprivation",
      headline_stat: { value: 0.5741, label: "Gini coefficient", severity: "high" },
      summary: "Bus service inequality exceeds UK income inequality",
      route: "/equity"
    },
    ...
  ]
}
```

**Implementation:** For each dimension, query `section_results WHERE section_id = {headline_section} AND region = {region} AND urban_rural = {urban_rural}`, extract the lead stat from `stats` JSON. The headline_section→stat_key mapping is a backend constant.

### `GET /api/sections`

Returns pre-computed section results for a dimension.

```
Query params:
  dimension (required): one of 8 dimension IDs
  region (default "all"): "all" or ONS code E12000001–E12000009
  urban_rural (default "all"): "all", "urban", "rural"

Response: {
  dimension: "equity",
  sections: [
    {
      section_id: "f1_gini",
      dimension: "equity",
      stats: { gini: 0.5741, income_gini: 0.36, ratio: 1.59, ... },
      chart_data: {
        type: "lorenz_curve",
        title: "Lorenz curve — bus service distribution",
        gini: 0.5741,
        reference_gini: 0.36,
        reference_label: "UK income Gini",
        curve_points: [{ cum_pop: 0.0, cum_service: 0.0 }, ...]
      },
      narrative: "**Bus service in England is distributed more unequally...**",
      suppressed: false
    },
    ...
  ]
}
```

**Implementation:** Query `section_results WHERE section_id LIKE '{prefix}%' AND region = {region} AND urban_rural = {urban_rural}`. The `chart_data` field is a JSON object matching one of the 10 chart_data_builder schemas.

**Narrative type fix required:** The `narrative` field is a Markdown string from Jinja2, but the DuckDB schema currently stores it as `JSON` and the Pydantic `SectionResult` model types it as `dict`. Both must be fixed to `VARCHAR`/`str` before API implementation. This is a prerequisite task.

### `GET /api/lsoa/{table}`

Returns LSOA-level data for maps and drill-downs.

```
Path param: table — one of:
  lsoa_service_quality, lsoa_equity_metrics, lsoa_accessibility,
  lsoa_economic, lsoa_policy, route_details, lta_readiness

Query params:
  region (optional): filter to one region
  fields (optional): comma-separated field names to return (reduces payload)
  limit (optional): max rows (default: all)

Response: {
  rows: [ { lsoa_code: "E01000001", ... }, ... ],
  total: 33755
}
```

**Note:** Table names match DuckDB exactly (include `lsoa_` prefix). `route_details` and `lta_readiness` are included for route_network and bus_services_act dimensions.

### `GET /api/provenance/{metric_id}`

Returns audit trail for a metric. Provenance is currently populated for key metrics only (Gini, Palma, Concentration Index). The frontend shows the tooltip only when provenance exists; otherwise the metric displays without audit trail.

```
Response: {
  metric_id: "gini_national",
  value: 0.5741,
  formula: "1 - 2 * AUC(lorenz_curve)",
  inputs: { "lorenz_x": "cumulative population share", "lorenz_y": "cumulative trips share" },
  source_files: ["lsoa_equity_metrics.parquet"]
}
```

### `POST /api/chat`

RAG chatbot endpoint. Streams Gemini Flash response via SSE.

```
Request: {
  query: "Why is bus inequality higher than income inequality?",
  context: { dimension: "equity", region: "all", urban_rural: "all" },
  conversation_id: "uuid-optional",
  history: [ { role: "user", content: "..." }, { role: "assistant", content: "..." } ]
}

Response: SSE stream
  event: chunk
  data: {"text": "Bus service inequality"}

  event: chunk
  data: {"text": " in England exceeds income"}

  event: done
  data: {"conversation_id": "uuid", "sources": ["f1_gini", "f2_disparity_ratio"]}

  event: error
  data: {"message": "Gemini API rate limit exceeded", "code": "rate_limit"}
```

**Notes:**
- `event: chunk` matches Gemini's `generate_content(stream=True)` behaviour (multi-token chunks, not single tokens).
- `conversation_id` is returned for future persistence (Phase 3 Supabase). Generated server-side if not provided.
- `event: error` handles mid-stream failures (Gemini timeout, rate limit, invalid response).

---

## Frontend Structure

### File Structure

```
frontend/
├── index.html
├── vite.config.ts
├── tsconfig.json
├── tailwind.config.ts
├── package.json
├── public/
│   └── boundaries/              — LSOA/region GeoJSON for MapLibre
│       ├── regions.geojson
│       └── lsoa_simplified.geojson
├── src/
│   ├── main.tsx
│   ├── App.tsx                  — AppShell + router
│   ├── api/
│   │   ├── client.ts            — Fetch wrapper, base URL config
│   │   ├── types.ts             — API response TypeScript types
│   │   └── hooks.ts             — useOverview, useSections, useLsoa, useProvenance
│   ├── components/
│   │   ├── layout/
│   │   │   ├── AppShell.tsx     — Header + filters + tab bar + content + chat FAB
│   │   │   ├── Header.tsx       — Dark header: logo, region Select, urban/rural Select (shadcn)
│   │   │   ├── TabBar.tsx       — 8 dimension tabs, horizontal
│   │   │   └── FilterDropdowns.tsx — Region + urban/rural shadcn Select components
│   │   ├── home/
│   │   │   ├── HomePage.tsx     — Grid of DimensionCards
│   │   │   └── DimensionCard.tsx — Headline stat + summary + link
│   │   ├── dimension/
│   │   │   ├── DimensionPage.tsx — Fetches sections, renders SectionCards
│   │   │   └── SectionCard.tsx  — Headline + summary + chart + Collapsible narrative (shadcn)
│   │   ├── charts/
│   │   │   ├── ChartRenderer.tsx — Dispatcher: chart_data.type → component (fallback: DataTable)
│   │   │   ├── HorizontalBarChart.tsx — Observable Plot horizontal bar (+ grouped_bar, stacked_bar variants)
│   │   │   ├── ScatterRegressionChart.tsx — Observable Plot scatter with regression line
│   │   │   ├── LorenzCurveChart.tsx — Observable Plot Lorenz curve with equality line + reference Gini
│   │   │   ├── ShapBarChart.tsx — Observable Plot horizontal bar for SHAP feature importance
│   │   │   ├── ChoroplethMap.tsx — MapLibre GL JS (WebGL, vector tiles for 33K LSOAs)
│   │   │   └── DataTable.tsx    — Accessible HTML table fallback for unsupported chart types
│   │   ├── chat/
│   │   │   ├── ChatDrawer.tsx   — shadcn Sheet (right side), focus trap, Escape to close
│   │   │   ├── ChatMessage.tsx  — Single message bubble (user/assistant)
│   │   │   └── ChatFAB.tsx      — shadcn Button, floating bottom-right
│   │   └── shared/
│   │       ├── Markdown.tsx     — react-markdown wrapper for narratives
│   │       ├── ProvenanceTooltip.tsx — shadcn Tooltip: click metric → show formula + sources
│   │       └── Severity.tsx     — Colour-coded severity badge (high/medium/low)
│   ├── hooks/
│   │   └── useChat.ts           — Chat state, SSE streaming, context injection
│   ├── lib/
│   │   ├── constants.ts         — Dimension metadata, route paths, colour scales
│   │   └── colours.ts           — Colourblind-safe palettes (viridis, categorical)
│   └── styles/
│       └── globals.css          — Tailwind base + OWID-inspired typography overrides
```

### Pages & Routes

| Route | Component | Data Source |
|-------|-----------|-------------|
| `/` | `HomePage` | `GET /api/overview` |
| `/equity` | `DimensionPage` | `GET /api/sections?dimension=equity` (f1–f6) |
| `/accessibility` | `DimensionPage` | `GET /api/sections?dimension=accessibility` (a1–a8) |
| `/service-quality` | `DimensionPage` | `GET /api/sections?dimension=service_quality` (b1–b5) |
| `/route-network` | `DimensionPage` | `GET /api/sections?dimension=route_network` (c1–c7) |
| `/correlations` | `DimensionPage` | `GET /api/sections?dimension=correlations` (d1–d8, g1–g5) |
| `/economic` | `DimensionPage` | `GET /api/sections?dimension=economic` (j1–j4) |
| `/bus-services-act` | `DimensionPage` | `GET /api/sections?dimension=bus_services_act` (bsa1–bsa3) |
| `/scenarios` | `DimensionPage` | `GET /api/sections?dimension=scenarios` (ps1–ps5) |

### Component Design

**SectionCard** (the core repeating unit):
```
┌──────────────────────────────────────────────┐
│ Key Finding Headline (bold, 1 line)          │
│ 2-3 sentence summary text                    │
│                                              │
│ ┌──────────────────────────────────────────┐ │
│ │              Chart                       │ │
│ │        (Observable Plot / MapLibre)      │ │
│ │                                          │ │
│ └──────────────────────────────────────────┘ │
│ Source: BODS GTFS 2025, NaPTAN  [View table] │
│                                              │
│ ▶ Read more (expandable → full narrative)    │
└──────────────────────────────────────────────┘
```

**ChartRenderer** — reads `chart_data.type` and dispatches:
- `"horizontal_bar"` / `"grouped_bar"` / `"stacked_bar"` → `HorizontalBarChart` (variant prop)
- `"scatter_regression"` → `ScatterRegressionChart`
- `"lorenz_curve"` → `LorenzCurveChart`
- `"shap_bar"` → `ShapBarChart`
- `"choropleth"` → `ChoroplethMap`
- `"box_violin"` / `"heatmap"` / `"scatter_clusters"` → `DataTable` (v1 fallback — add renderers later if needed)
- Unknown type → `DataTable`

### State Management

- **Global filters** (region, urban_rural) — URL search params via `useSearchParams()`. Changing a filter updates the URL, which triggers re-fetch via React Query. Bookmarkable and shareable.
- **Server state** — React Query (`@tanstack/react-query`). Section results are small (612 rows total), cache indefinitely (`staleTime: Infinity`). LSOA data cached per region.
- **Chat state** — `useChat` hook manages message history, streaming state, and context. Local state only (not URL).
- **No client-side global store** (no Redux/Zustand). URL + React Query is sufficient.

---

## RAG Chatbot Pipeline

### Build-Time (Pipeline Stage — `src/aequitas/rag/index_builder.py`)

1. Load all section_result narratives from DuckDB (612 rows: 51 sections × 12 filter combos)
2. Chunk long narratives at paragraph boundaries (~500 tokens each)
3. Embed chunks with `all-MiniLM-L6-v2` (CPU, ~5 seconds total)
4. Build FAISS index (IndexFlatL2) and save to disk (`data/faiss_index.bin` + `data/faiss_metadata.json`)

**Code location:** Build-time index construction lives in `src/aequitas/rag/index_builder.py`, added as a pipeline stage in `_stages.py`. Runtime query logic lives in `src/aequitas/api/services/rag.py`. This matches the existing pattern of separating build-time and serve-time code.

### Runtime (Per Query)

1. User sends message. Frontend includes current context (dimension, region, urban_rural).
2. FastAPI embeds query with same MiniLM model (~5ms).
3. FAISS retrieves top-5 nearest narrative chunks.
4. Construct prompt:
   ```
   System: You are a UK bus transport policy analyst. Answer based only on the provided evidence.
   Context: User is viewing {dimension} for {region} ({urban_rural}).
   Evidence:
   [chunk 1]
   [chunk 2]
   ...
   User: {query}
   ```
5. Stream Gemini Flash response via SSE to frontend.
6. Final SSE message includes `sources` array (section_ids) for attribution.

### FAISS Index Details

- **Model:** all-MiniLM-L6-v2 (384-dim, CPU-only, ~80MB)
- **Index type:** IndexFlatIP on L2-normalized vectors (cosine similarity — standard for sentence-transformers; dataset is tiny, no need for approximate)
- **Loaded on startup:** FastAPI loads index + metadata into memory once. No rebuilds.
- **Index size:** ~612 narratives → ~800 chunks × 384 dims × 4 bytes ≈ 1.2MB

---

## Visual Design

### Theme

- **Header:** Dark (#1a1a2e), white text, indigo accents (#6366f1)
- **Content background:** White (#ffffff) with subtle grey section separators (#f8f9fa)
- **Typography:** System font stack (Inter if available). Headings: 600 weight. Body: 400 weight, #1a1a1a.
- **Charts:** OWID-inspired — minimal chrome, clear axis labels, annotation lines for benchmarks
- **Colour palettes:**
  - Sequential (choropleths): viridis or cividis (colourblind-safe)
  - Categorical (bar/line): 6-colour palette tested against WCAG contrast + deuteranopia/protanopia
  - Severity: red (#dc2626) = high concern, amber (#d97706) = moderate, green (#059669) = good

### OWID-Inspired Design Principles

1. **Charts are the content** — not decorations. Every chart answers a specific policy question.
2. **Source attribution on every chart** — dataset name, date, methodology link.
3. **Minimal chrome** — no gratuitous borders, shadows, or gradients. White space does the work.
4. **Annotations over legends** — label data directly on charts when possible (Observable Plot excels at this).
5. **Print-friendly** — white backgrounds, high-contrast text, charts render cleanly in PDF.

---

## Accessibility (WCAG 2.1 AA)

| Requirement | Implementation |
|-------------|---------------|
| Keyboard navigation | Tab bar, dropdowns, expandable sections all keyboard-accessible |
| Focus trapping | Chat drawer traps focus when open; Escape to close |
| ARIA labels | All interactive elements labelled; chart containers have `aria-label` with title |
| Data table fallback | Every chart has "View data table" toggle → accessible HTML table |
| Colour contrast | All text meets 4.5:1 ratio; chart colours meet 3:1 against background |
| Colourblind safety | Viridis/cividis for sequential; tested categorical palette |
| Screen reader | Narratives are plain Markdown (accessible by default); chart descriptions via aria-label |
| Reduced motion | Respect `prefers-reduced-motion` — disable chart transitions |

---

## Backend Structure

### File Structure

```
src/aequitas/rag/
├── __init__.py
└── index_builder.py      — Build-time: embed narratives → FAISS index (pipeline stage)

src/aequitas/api/
├── __init__.py
├── app.py                — FastAPI app factory, CORS, lifespan (load DuckDB + FAISS)
├── deps.py               — Dependency injection (db connection, faiss index, gemini client)
├── routers/
│   ├── __init__.py
│   ├── overview.py       — GET /api/overview
│   ├── sections.py       — GET /api/sections
│   ├── lsoa.py           — GET /api/lsoa/{table}
│   ├── provenance.py     — GET /api/provenance/{metric_id}
│   └── chat.py           — POST /api/chat (SSE streaming)
├── models/
│   ├── __init__.py
│   ├── requests.py       — Pydantic v2 request models
│   └── responses.py      — Pydantic v2 response models
├── services/
│   ├── __init__.py
│   ├── warehouse.py      — DuckDB query helpers (read-only)
│   └── rag.py            — Runtime: FAISS query + Gemini prompt construction + streaming
└── config.py             — API config (CORS origins, DuckDB path, FAISS path, Gemini API key)
```

**Note:** `/api/dimensions` endpoint removed — dimension metadata is static and lives in `frontend/src/lib/constants.ts` instead.

### Key Implementation Details

- **DuckDB connection:** Single read-only connection, opened at startup via FastAPI lifespan.
- **FAISS loading:** Index loaded into memory at startup. ~2.3MB, instant.
- **Gemini client:** `google-generativeai` SDK. Streaming via `generate_content(stream=True)`. Wrapped in SSE for the frontend.
- **CORS:** Allow frontend dev server (localhost:5173) + production origin.
- **Pydantic v2 everywhere:** Request validation + response serialisation. Consistent with Phase 1 patterns.
- **No authentication in v1.** Supabase auth deferred to Phase 3.

---

## Loading, Error, and Empty States

- **Loading:** Skeleton placeholders for SectionCards (grey shimmer blocks matching headline + chart layout). Homepage cards show skeleton during `/api/overview` fetch.
- **Error:** React Error Boundary wraps each DimensionPage. On API failure, show "Unable to load data — try refreshing" with retry button. Individual chart failures degrade to DataTable if chart_data is available, or a "Chart unavailable" placeholder if not.
- **Empty (suppressed):** When all sections in a dimension are `suppressed: true` (insufficient data for the selected filter), show: "No data available for [region] ([urban/rural]). Try selecting 'All England' for national-level analysis."
- **LSOA data timeout:** LSOA tables (33K rows) may be 5-10MB. Show a loading spinner on the map; fetch only when a choropleth section scrolls into view (intersection observer).

## Map Boundary Strategy

LSOA boundaries (33,755 polygons) are too large for static GeoJSON download on page load.

**Approach:** Generate Mapbox Vector Tiles (MVT) at build time using `tippecanoe`. Serve the `.mbtiles` file via the API (`GET /api/tiles/{z}/{x}/{y}.pbf`) or host as static tiles. MapLibre consumes vector tiles natively — only visible polygons are loaded, enabling smooth zoom/pan.

- **Build-time:** `tippecanoe` converts LSOA GeoJSON → `.mbtiles` (stored in `data/tiles/`)
- **Region boundaries:** Small enough for static GeoJSON (`public/boundaries/regions.geojson`, ~200KB)
- **Fallback:** If `tippecanoe` is unavailable, serve simplified LSOA GeoJSON via API with region filtering (`GET /api/lsoa/boundaries?region=E12000007`)

---

## What's Out of Scope (Phase 2)

- Authentication / user accounts (Phase 3)
- PDF export (Phase 3)
- LAD-level profiles (deferred from InsightEngine expansion)
- Box plot, violin, heatmap, scatter_clusters chart renderers (degrade to DataTable in v1)
- Mobile-first responsive design (desktop-first, basic mobile support only)
- Internationalisation
