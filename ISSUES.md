# Aequitas — Complete Issue Register

> Full codebase audit conducted June 2026. Every issue is traced to a specific file and line.
> Severity: 🔴 Critical (broken/misleading right now) · 🟡 Medium (degraded experience) · 🟢 Low (polish / improvement)

---

## Table of Contents

1. [Architecture Quick Reference](#1-architecture-quick-reference)
2. [Critical — Data Pipeline & Precompute](#2-critical--data-pipeline--precompute)
3. [Critical — Authentication](#3-critical--authentication)
4. [Critical — Filter Combinations](#4-critical--filter-combinations)
5. [Critical — Overview Page Returns All Zeros](#5-critical--overview-page-returns-all-zeros)
6. [Critical — FAISS / RAG Quality](#6-critical--faiss--rag-quality)
7. [Medium — Chart & Visualization Mismatches](#7-medium--chart--visualization-mismatches)
8. [Medium — Specific Section Data Problems](#8-medium--specific-section-data-problems)
9. [Medium — Frontend Product Issues](#9-medium--frontend-product-issues)
10. [Medium — API Issues](#10-medium--api-issues)
11. [Low — Polish & Improvements](#11-low--polish--improvements)
12. [What Is Genuinely Good](#12-what-is-genuinely-good)
13. [Recommended Fix Order](#13-recommended-fix-order)

---

## 1. Architecture Quick Reference

| Layer | Technology | Status |
|---|---|---|
| Pipeline | Python 3.12, 7 stages | Partial — 3 of 51 sections produce real data |
| Warehouse | DuckDB 107MB, 1,530 rows in `section_results` | Populated but mostly empty stats |
| API | FastAPI, 8 routers | Running, but auth calls fail |
| Vector store | FAISS + all-MiniLM-L6-v2 | Built but low-quality content |
| Frontend | React + Vite + TypeScript | Renders, but auth-gated and filter-broken |
| Auth | Supabase | **Not configured — completely broken** |

**Ground truth locked in `CLAUDE.md`:**
- 33,755 LSOAs · 274,719 bus stops · 13,099 routes · 1,752,443 trips
- Gini 0.5741 · Palma 5.702 · Concentration Index +0.1358 pro-rich
- Population denominator: 56,490,056 (never filter this)

---

## 2. Critical — Data Pipeline & Precompute

### 2.1 🔴 5-vs-51 Section Gap — The Root Cause of Everything

**File:** `src/aequitas/warehouse/precompute.py`, lines 1–25

```python
_SECTIONS = [
    "coverage_density",
    "equity",
    "correlation",
    "gap_to_target",
    "policy_scenario",
]
```

**Problem:** `SECTION_REGISTRY` in `src/aequitas/intelligence/section_registry.py` defines **51 new-style section IDs** (`a1_route_density`, `b2_operating_hours`, `f1_gini`, etc.). `precompute.py` was never updated to use them. It still loops over 5 old-style IDs that no longer exist anywhere else in the system.

**Consequence:** The DuckDB warehouse has 1,530 rows in `section_results` (51 × 30), but 48 of those 51 section slots have `stats = {}`, `chart_data = {}`, and `narrative = ""`. InsightEngine suppresses empty stats, so 48 sections render nothing despite appearing registered.

**Fix:**
```python
# Replace _SECTIONS with:
from aequitas.intelligence.section_registry import SECTION_REGISTRY
_SECTIONS = list(SECTION_REGISTRY.keys())
```
Then write `_build_stats` cases for all 51 sections.

---

### 2.2 🔴 `_build_stats` Only Has Real Implementations for 3 Sections

**File:** `src/aequitas/warehouse/precompute.py`, `_build_stats()` function

The function has `if/elif` branches only for:
- `coverage_density` → produces real stats
- `equity` → produces real stats (but see §4.2 for filter bug)
- `gap_to_target` → produces real stats

For `correlation` and `policy_scenario` it returns `{}`. For all 46 new-style section IDs it falls through to `return {}`.

**Consequence:** Only 3 sections have content. The other 48 are shells.

**Data available for all 51 sections** (confirmed by reading audit parquets):
- `data/audit/lsoa_policy_synthesis.parquet` — 33,755 rows, columns: `lsoa_code`, `region`, `urban_rural`, `imd_decile`, `trips_per_capita`, `stops_per_1000`, `sqi`, `nocar_pct`, `elderly_pct`, `unemployment_rate`, `income_score`
- `data/audit/lsoa_equity_metrics.parquet` — Gini components, Lorenz arrays, concentration index
- `data/audit/route_analytics.parquet` — route lengths, stops per route, HHI, operator data
- `data/audit/lsoa_accessibility.parquet` — 400m coverage, 2SFCA scores, desert flags
- `data/audit/equity_summary.json` — pre-aggregated Gini, Palma, Lorenz curve points (national only)
- `data/audit/shap_values.parquet` — SHAP feature importances from RF model
- `data/audit/ml_clusters.parquet` — HDBSCAN cluster assignments
- `data/audit/anomaly_results.parquet` — Isolation Forest anomaly labels
- `data/audit/economic_summary.parquet` — BCR, CO₂, economic value per region

48 of 51 sections have all required data. The 3 incomplete sections are:
- `f3_ethnic_access` — needs `ts021` (ethnicity × LSOA) joined with service data; source file exists but join not done
- `f4_gender_accessibility` — **no source data exists** for gender-disaggregated travel demand in England at LSOA level
- `c4_urban_rural_routes` — needs route geometry joined to urban/rural classification

---

### 2.3 🔴 `equity` Section Always Returns National Data Regardless of Region Filter

**File:** `src/aequitas/warehouse/precompute.py`, `_build_stats()`, equity branch

```python
elif section_id == "equity":
    stats["gini"] = equity_summary.get("gini_population_weighted", 0.5741)
    stats["palma"] = equity_summary.get("palma_ratio", 5.702)
    # Lorenz curve also from national equity_summary
    lorenz_x = equity_summary.get("lorenz_x", [])
    lorenz_y = equity_summary.get("lorenz_y", [])
```

`equity_summary.json` is a **flat national aggregate** — confirmed by inspection, no regional breakdown in its top-level keys. However, the file **does** contain a `regional_equity` key with per-region Gini values that `_build_stats` never reads.

**Consequence:** Selecting "North East" region shows Gini = 0.5741 (England average). The Lorenz curve for every regional filter is identical. The narrative says "the Gini coefficient is 0.57" with no caveat, making it appear region-specific.

**Fix:**
```python
elif section_id == "equity":
    if region != "all" and "regional_equity" in equity_summary:
        regional = equity_summary["regional_equity"].get(region, {})
        stats["gini"] = regional.get("gini", equity_summary.get("gini_population_weighted"))
        stats["palma"] = regional.get("palma", equity_summary.get("palma_ratio"))
        # Regional Lorenz arrays if available, else fall back to national
    else:
        stats["gini"] = equity_summary.get("gini_population_weighted", 0.5741)
        ...
```

---

### 2.4 🔴 `coverage_density` `_build_stats` Silently Returns Empty for Single-Region Views

**File:** `src/aequitas/warehouse/precompute.py`, `_build_stats()`, coverage_density branch

```python
by_region = filtered.groupby("region")["trips_per_capita"].mean()
if len(by_region) > 1:   # <-- fails when filtered to one region
    best_region = by_region.idxmax()
    ...
```

When `region = "E12000001"`, `by_region` has 1 row, the condition is `False`, `stats` stays `{}`, and InsightEngine suppresses the section. "Route density by region" shows nothing for any single-region view — precisely the context where a user most wants regional data.

**Fix:** When `len(by_region) == 1`, switch to `single_region.j2` template context:
```python
else:
    # Single region view
    val = float(by_region.iloc[0])
    nat_mean = float(policy_df["trips_per_capita"].mean())  # unfiltered
    stats["region_name"] = region
    stats["value"] = round(val, 2)
    stats["national_avg"] = round(nat_mean, 2)
    stats["vs_national_pct"] = round((val - nat_mean) / nat_mean * 100, 1)
    stats["unit"] = "trips/capita"
```
Note: `single_region.j2` already exists and is correctly written for this purpose — it just needs to be wired up (see §8.1).

---

## 3. Critical — Authentication

### 3.1 🔴 API Client Sends No Authorization Header — Every Call Is Unauthenticated

**File:** `frontend/src/api/client.ts`

```typescript
export async function fetchJson<T>(path: string, params?: Record<string, string>): Promise<T> {
  const url = new URL(`${BASE}${path}`, window.location.origin)
  if (params) {
    Object.entries(params).forEach(([k, v]) => url.searchParams.set(k, v))
  }
  const res = await fetch(url.toString())   // <-- no Authorization header
  if (!res.ok) throw new Error(`API ${res.status}: ${await res.text()}`)
  return res.json() as Promise<T>
}
```

The Supabase session token is never attached. Any JWT-protected endpoints (chat, conversations, saved analyses) will respond with 401 for all users.

**Fix:**
```typescript
import { supabase } from "@/lib/supabase"

export async function fetchJson<T>(path: string, params?: Record<string, string>): Promise<T> {
  const { data: { session } } = await supabase.auth.getSession()
  const headers: Record<string, string> = {}
  if (session?.access_token) {
    headers["Authorization"] = `Bearer ${session.access_token}`
  }
  const url = new URL(`${BASE}${path}`, window.location.origin)
  if (params) {
    Object.entries(params).forEach(([k, v]) => url.searchParams.set(k, v))
  }
  const res = await fetch(url.toString(), { headers })
  if (!res.ok) throw new Error(`API ${res.status}: ${await res.text()}`)
  return res.json() as Promise<T>
}
```

---

### 3.2 🔴 Supabase Environment Variables Not Configured

**File:** `supabase/migrations/001_initial.sql` (migration exists), but `.env` / `.env.local` has no Supabase credentials.

The migration defines 6 tables with RLS: `profiles`, `conversations`, `messages`, `saved_analyses`, `policy_notes`, `saved_regions`. All 6 tables have "users can CRUD own rows" RLS policies. A `handle_new_user()` trigger auto-creates a profile on signup.

**Consequence:** Everything behind `ProtectedRoute` is completely inaccessible: `/dashboard`, `/compare`, `/profile`, `/saved`, `/notes`, `/regions`. The app functions as a login page with nothing behind it.

**Required environment variables:**
```
VITE_SUPABASE_URL=https://<project>.supabase.co
VITE_SUPABASE_ANON_KEY=<anon-key>
SUPABASE_SERVICE_ROLE_KEY=<service-role-key>   # backend only
```

---

### 3.3 🟡 Chat Rate Limiter Is In-Memory — Resets on Restart, Won't Work Across Workers

**File:** `src/aequitas/api/routers/chat.py`

```python
from collections import defaultdict
_rate_store: dict[str, list[float]] = defaultdict(list)
```

Rate limit: 10 requests / 60 seconds per user. The `_rate_store` is a module-level dict, which means:
- Every process restart resets all limits (users can bypass by triggering a restart)
- Multi-worker deployments (Gunicorn with 4 workers) each have independent stores — effective limit becomes 40 req/60s

**Fix:** Replace with Redis or Supabase-backed rate limiting. Short term: use a single-worker deployment with `--workers 1` and document the limitation.

---

## 4. Critical — Filter Combinations

The frontend's two dropdowns offer 10 regions × 3 area types = **30 filter combinations**. The actual state of each:

### 4.1 🔴 18 of 30 Filter Combos Return a Blank Dashboard

**File:** `src/aequitas/warehouse/precompute.py`, line ~70

```python
if region != "all" and urban_rural != "all":
    continue  # skips 9 regions × 2 area types = 18 combos
```

**Precomputed combos (12 total):**
- `all` × `all`, `all` × `urban`, `all` × `rural` (3 combos)
- `E12000001`–`E12000009` × `all` (9 combos)

**Dead combos (18 total):** Any single region + `urban` or `rural` (e.g., "East Midlands + Urban", "London + Rural").

**User experience:** The `FilterDropdowns` component has no knowledge of which combos have data. Both dropdowns are fully interactive for all 30 combinations. Selecting a dead combo silently waits for the API, which returns 0 rows, and `DimensionPage` shows:

> "No data available for East Midlands (Urban). Try selecting 'All England' and 'All Areas'."

The user finds out after the round-trip, not before. 60% of the filter space is a dead end.

**Fix options:**
1. **Short term:** Gray out area-type dropdown when a specific region is selected. Add a tooltip: "Urban/rural breakdown only available for All England."
2. **Preferred:** Precompute all 30 combos. The skip was a performance optimisation during development — at 51 sections × 18 combos = 918 additional rows, this adds negligible time and ~5MB to the warehouse.

---

### 4.2 🔴 Urban-Rural Gap Sections Are Self-Contradictory Under Area-Type Filter

**Sections affected:** `a6_urban_rural_gap`, `c4_urban_rural_routes`, `f5_rural_penalty`
**Template:** `src/aequitas/intelligence/templates/urban_rural_gap.j2`

These sections show "Urban areas receive X compared to Y in rural areas" — a comparison between area types. But they are served for `urban_rural = "urban"` (the "All England + Urban" filter combo). When the user has already filtered to urban-only areas, showing an urban-vs-rural comparison chart uses mixed data:

- `urban_value` is computed from the urban-filtered DataFrame ✓
- `rural_value` must come from the unfiltered DataFrame, but `_build_stats` applies the same filter to both — so `rural_value` is computed from 0 rural LSOAs in the urban-only subset

If `rural_value` resolves to `0`, the template gate `{% if urban_value is defined and rural_value is not none %}` passes (0 is not None), and the narrative renders: "Urban areas receive X compared to **0** in rural areas — an urban premium of **∞%**."

**Fix:** When `urban_rural != "all"`, `_build_stats` for urban-rural sections should either:
- Load the unfiltered DataFrame separately to compute the other side, or
- Suppress and show a message: "Urban/rural comparison requires 'All Areas' filter."

---

### 4.3 🟡 SHAP / ML Sections Show National Model Results for Every Regional Filter

**Sections:** `a8_coverage_prediction`, `d8_feature_importance`, `g4_shap`

The Random Forest model was trained on all 33,755 LSOAs. SHAP values are computed once on the full model. The same SHAP importances (`nocar_pct` is top feature, R² = 0.472) are stored for every filter combo — regional filter makes no difference to the output.

**Consequence:** A user comparing "North East" vs "South West" SHAP charts sees identical charts. Nothing in the UI or narrative indicates this.

**Fix:** Either:
1. Add a caveat in the narrative: "Feature importances are from a model trained on all England — regional sub-selection does not affect these values."
2. Re-run SHAP on regional subsets at precompute time (computationally heavier but analytically correct).

---

### 4.4 🟡 Correlation Scatter Sections Have Evidence Gates Calibrated for n=33,755 but Serve Regional Subsets of ~3,750

**Sections:** `d1_coverage_deprivation` through `d5_coverage_income`, `b5_frequency_deprivation`, `c5_length_vs_frequency`

Evidence gates in `correlation.j2` check for significance thresholds calibrated on the full national dataset. When filtered to a single region (~3,750 LSOAs), correlations that were nationally significant (p < 0.001 at n=33,755) may not be significant at smaller n. The template fires anyway, producing a narrative that overstates the confidence of the regional correlation.

**Fix:** Pass `n_observations` in stats and adjust the evidence gate threshold:
```jinja
{% if r is not none and p_value is not none and p_value < (0.001 if n_observations > 10000 else 0.05) %}
```

---

## 5. Critical — Overview Page Returns All Zeros

**File:** `src/aequitas/api/services/warehouse.py`, `HEADLINE_SECTIONS` dict

```python
HEADLINE_SECTIONS: dict[str, tuple[str, str]] = {
    "equity": ("f1_gini", "gini"),
    "accessibility": ("a3_walking_distance", "pct_covered"),
    "service_quality": ("b1_frequency", "national_avg"),
    ...
}
```

`query_overview()` looks up these new-style section IDs in `section_results`. But the warehouse was built with old-style IDs (`coverage_density`, `equity`, `gap_to_target`). The new-style IDs (`f1_gini`, `a3_walking_distance`) return zero rows from:

```sql
SELECT stats, narrative FROM section_results
WHERE section_id = 'f1_gini' AND region = 'all' AND urban_rural = 'all'
```

Every dimension defaults to `value = 0.0`. `_severity()` classifies 0.0 as `"low"` for every dimension. The first screen after login shows **eight dimensions, all showing 0.0, all green severity** — completely wrong and immediately destroys trust in the tool.

**Fix (short term):** Update `HEADLINE_SECTIONS` to use old-style IDs that actually exist:
```python
HEADLINE_SECTIONS = {
    "equity": ("equity", "gini"),
    "accessibility": ("coverage_density", "national_avg"),
    ...
}
```

**Fix (correct):** Fix issue §2.1 first (5→51 precompute gap), then the new-style IDs will exist and `HEADLINE_SECTIONS` will work as written.

---

## 6. Critical — FAISS / RAG Quality

**Files:** `src/aequitas/api/services/rag.py`, `data/faiss_index.bin`, `data/faiss_metadata.json`

The FAISS index was built from pre-computed narratives stored in the warehouse. Since `_build_stats` only produces real content for 3 sections, 48 sections produce empty narratives (`""`), which InsightEngine suppresses. The FAISS index of ~3,700 chunks was built from mostly empty strings.

**Consequence:** The RAG chatbot (`POST /api/chat`) retrieves chunks almost exclusively from `coverage_density`, `equity`, and `gap_to_target` section narratives, regardless of what the user asks. A question about operator market concentration (Category C) or BCR analysis (Category J) retrieves irrelevant coverage/equity chunks, and Gemini generates an answer with no grounding in the actual data.

**Fix:** Fix §2.1 and §2.2 first (all 51 sections produce real narratives), then rebuild the FAISS index:
```bash
aequitas run --stage rag_index
```

The index rebuild is fast (~2 min) and must happen after every precompute run.

---

## 7. Medium — Chart & Visualization Mismatches

### 7.1 🟡 `g2_anomalies` Uses `scatter_regression` — Wrong Chart Type

**File:** `src/aequitas/intelligence/section_registry.py`, line for `g2_anomalies`

```python
"g2_anomalies": SectionDef("anomaly_spotlight.j2", "scatter_regression", "G", "Anomaly detection"),
```

`anomaly_spotlight.j2` receives: `n_anomalies`, `pct_anomalies`, `n_positive`, `n_inefficiency`, `n_policy_failure` — **aggregate counts by anomaly type**.

`ScatterRegressionChart` (`frontend/src/components/charts/ScatterRegressionChart.tsx`) expects:
- `data: [{x, y, id}]` — scatter coordinates
- `r`, `p_value` — correlation stats
- `regression_line: {slope, intercept}` — regression parameters

These fields will never exist in anomaly stats. The chart will receive `data = []` and render a blank Plot output.

**Fix:** Change chart_type to `scatter_clusters` and emit per-LSOA coordinates with anomaly type as cluster label:
```python
"g2_anomalies": SectionDef("anomaly_spotlight.j2", "scatter_clusters", "G", "Anomaly detection"),
```
`_build_stats` for `g2_anomalies` should emit:
```python
{
  "data": [{"x": imd_decile, "y": sqi, "cluster": anomaly_type, "id": lsoa_code}, ...],
  "clusters": [{"label": "Deprived well-served", "n": n_positive}, ...],
  "x_label": "IMD Decile",
  "y_label": "Service Quality Index"
}
```

---

### 7.2 🟡 `g3_coverage_model` Uses `ml_prediction.j2` but `scatter_regression` Chart Type

**File:** `src/aequitas/intelligence/section_registry.py`

```python
"g3_coverage_model": SectionDef("ml_prediction.j2", "scatter_regression", "G", "Coverage prediction"),
```

`ml_prediction.j2` is shared with `a8_coverage_prediction`, `d8_feature_importance`, `g4_shap` — all of which use `shap_bar` chart type. The template generates SHAP-style narrative (feature importance framing), while `scatter_regression` expects actual-vs-predicted scatter coordinates.

This creates a narrative/chart mismatch: the text reads "feature X contributes most to coverage prediction" while the chart below it (if data is provided) would show actual vs predicted values on two axes.

**Fix:** Create a dedicated `coverage_model_fit.j2` template for `g3_coverage_model` that describes model accuracy (R², RMSE, actual-vs-predicted framing), and keep the chart_type as `scatter_regression`.

---

### 7.3 🟡 `ps1`–`ps4` Use `horizontal_bar` With `policy_scenario.j2` — Bar Semantics Undefined

**File:** `src/aequitas/intelligence/section_registry.py`

```python
"ps1_freq_restoration": SectionDef("policy_scenario.j2", "horizontal_bar", "PS", ...),
"ps2_evening_extension": SectionDef("policy_scenario.j2", "horizontal_bar", "PS", ...),
"ps3_drt_rural":         SectionDef("policy_scenario.j2", "horizontal_bar", "PS", ...),
"ps4_franchise":         SectionDef("policy_scenario.j2", "horizontal_bar", "PS", ...),
```

`policy_scenario.j2` receives a single `scenario` object (one scenario per section). `horizontal_bar` expects `{data: [{label, value}]}` — a ranked list. What should the bars represent? Population affected per region? Cost per region? This is not defined anywhere, meaning whoever writes `_build_stats` for these sections must guess.

**Fix:** Add an explicit comment in `section_registry.py` and a corresponding note in `precompute.py`:
```
# ps1-ps4: horizontal_bar shows regions ranked by population that would
# benefit from this intervention, using DfT elasticity-based scenario params.
# Stats dict must include: {data: [{label: region_name, value: population_affected}]}
```

---

### 7.4 🟢 `stacked_bar` and `grouped_bar` Both Route to `HorizontalBarChart`

**File:** `frontend/src/components/charts/ChartRenderer.tsx`

```tsx
case "grouped_bar":
case "stacked_bar":
case "horizontal_bar":
  return <HorizontalBarChart chartData={chartData} />
```

`HorizontalBarChart` handles the variant internally via `Plot.stackX` vs `Plot.groupY` based on `chartData.type`. This works, but means the chart_type field in the registry serves as both a chart-type discriminator and a layout variant. If a new chart type is added that maps to a different component, this pattern breaks.

**No immediate fix needed** — just be aware when adding new chart types.

---

### 7.5 🟡 Several Visualizations Are Too Technical for the Target Audience

**Affected sections and components:**

| Section | Chart | Issue |
|---|---|---|
| `f1_gini`, `a4_coverage_equity` | `lorenz_curve` | Requires understanding of the equality diagonal; Palma ratio (already computed) is more intuitive |
| `a8`, `d8`, `g4` | `shap_bar` | SHAP is ML-researcher vocabulary; the finding ("car ownership predicts coverage most strongly") needs plain-language framing |
| `d1`–`d5`, `b5`, `c5` | `scatter_regression` | r and p-value annotations on scatter plots are meaningless to most policy analysts |

**Not bugs, but product decisions** that should be revisited for the target audience of transport consultants and LTA analysts.

---

## 8. Medium — Specific Section Data Problems

### 8.1 🟡 `single_region.j2` Template Exists But Is Never Used

**File:** `src/aequitas/intelligence/templates/single_region.j2`

```jinja
{% if region_name and value is not none -%}
**{{ region_name }}** records **{{ value|round(2) }} {{ unit }}**, {{ vs_national_pct|round(1) }}%
{{ "above" if vs_national_pct >= 0 else "below" }} the national average of {{ national_avg|round(2) }} {{ unit }}.
{%- endif %}
```

This template is exactly what ranking sections (`a1`, `a2`, `b1`, `b4`, `f6`, `j1`–`j4`, `bsa1`, `bsa2`) need when `region != "all"`. It already handles the `vs_national_pct` comparison to national average. It is defined in `_SECTION_TEMPLATES` in `engine.py` as `"single_region": "single_region.j2"` but **no section in `SECTION_REGISTRY` maps to it**.

**Fix:** In `_build_stats`, detect single-region context for ranking sections and set the template override key, or modify `engine.py` to select `single_region.j2` when region context is single and stats contain `region_name`:
```python
# In _build_stats for ranking sections:
if region != "all":
    stats["region_name"] = REGION_NAMES.get(region, region)
    stats["value"] = float(by_region.iloc[0])
    stats["national_avg"] = round(nat_mean, 2)
    stats["vs_national_pct"] = round(...)
    stats["unit"] = "trips/capita"
    # Engine will need to select single_region.j2 for these stats
```

---

### 8.2 🔴 `f4_gender_accessibility` — No Source Data Exists

**File:** `src/aequitas/intelligence/section_registry.py`

```python
"f4_gender_accessibility": SectionDef("accessibility_gap.j2", "horizontal_bar", "F", "Gender-adjusted accessibility"),
```

No gender-disaggregated travel demand data exists for England at LSOA level. DfT's National Travel Survey is not LSOA-level. Census 2021 has gender data but not travel-mode-specific. The section will always return empty stats and suppress.

**Consequence:** The section appears in the registry, gets a row in `section_results`, renders nothing, and a user who notices it in the registry has no way to know it's permanently empty vs temporarily broken.

**Fix:** Either remove `f4_gender_accessibility` from `SECTION_REGISTRY` entirely, or add a status field:
```python
"f4_gender_accessibility": SectionDef(..., status="planned", status_note="Awaiting DfT travel survey microdata at LSOA resolution"),
```

---

### 8.3 🟡 `f3_ethnic_access` — Data Join Missing

**File:** `src/aequitas/intelligence/section_registry.py`

`f3_ethnic_access` requires joining `ts021` (Census 2021 ethnicity by LSOA) with service quality data. The `ts021` CSV file exists in `data/audit/` but the join has never been performed. The section will produce empty stats until this join is implemented in the analytics stage.

---

### 8.4 🟡 `c4_urban_rural_routes` — Route Geometry–to–Classification Join Missing

Requires joining route geometry (from `data/audit/route_analytics.parquet`) with ONS Urban-Rural Classification boundaries. The geometry join was not completed in the analytics stage. Section produces empty stats.

---

### 8.5 🟡 `gap_to_target` Uses Filtered Median as Target — Shifts With Every Filter

**File:** `src/aequitas/warehouse/precompute.py`, `_build_stats`, gap_to_target branch

```python
median = float(filtered["trips_per_capita"].median())
below = filtered[filtered["trips_per_capita"] < median]
```

When filtered to "North West", `median` is the North West median, not the national median. The "gap to target" becomes "gap to the North West median" — a moving target. This makes cross-region comparison meaningless: every region has ~50% of its LSOAs below its own median by definition.

**Fix:** Always compute the target against the unfiltered national median, applying the filter only to identify which LSOAs are below it:
```python
national_median = float(policy_df["trips_per_capita"].median())  # unfiltered
below = filtered[filtered["trips_per_capita"] < national_median]
stats["target"] = round(national_median, 2)
stats["target_description"] = "national median"
```

---

## 9. Medium — Frontend Product Issues

### 9.1 🔴 Everything Is Behind Auth — No Public Landing Page

**File:** `frontend/src/App.tsx`

```tsx
<Route path="/dashboard" element={<ProtectedRoute><AppShell /></ProtectedRoute>} />
```

Every meaningful route is behind `ProtectedRoute`. The public routes are `/`, `/about`, `/disclaimer`, `/contact`, `/auth`. The root `/` likely renders a marketing page with no data. A transport analyst or researcher who lands on the site sees a login form before a single data point.

The three numbers that would hook any transport policy professional — Gini 0.5741 (exceeds UK income inequality at 0.36), 4,245 zero-stop LSOAs, Concentration Index +0.1358 pro-rich — are invisible until after account creation.

**Fix:** Add a public `/explore` or `/insights` page that shows national headline figures with no auth required. Gate only saving, chat, and notes behind auth.

---

### 9.2 🟡 Overview Page Is the First Screen but Shows Zero Information

See §5 for technical cause. The product consequence: after a user successfully logs in, the first thing they see is eight dimension cards all showing `0.0` value and green severity. This looks like either a broken state or completely uniform data. There is no indication that Supabase needs to be configured or that the warehouse needs to be rebuilt.

---

### 9.3 🟡 ComparePage Always Locks to `urban_rural = "all"` and Slices to 8 Sections

**File:** `frontend/src/pages/ComparePage.tsx`

```tsx
queryFn: () => fetchJson<SectionsResponse>("/sections", { dimension, region, urban_rural: "all" }),
```

The compare page compares two regions but always compares their `all`-area-type data. There is no option to compare Region A (urban) vs Region B (urban), which is a meaningful policy comparison.

The component also has:
```tsx
sections.slice(0, 8)
```
The first 8 sections in alphabetical order by section_id are shown. This is arbitrary and never explained to the user. For the "equity" dimension, alphabetical order gives `f1_gini`, `f2_disparity_ratio`, `f3_ethnic_access`... which is coincidentally correct, but for other dimensions it may cut off important sections.

---

### 9.4 🟡 ScenarioBuilder Uses Hardcoded Coefficients — Violates Pre-Compute Principle

**File:** `frontend/src/components/dimension/ScenarioBuilder.tsx`

```tsx
const COEFFICIENTS = {
  freq_pct: { lsoas_affected: 0.42, co2_saving_kt: 0.18, bcr: 1.8 },
  last_bus_min: { lsoas_affected: 0.31, co2_saving_kt: 0.09, bcr: 1.4 },
  drt_coverage_pct: { lsoas_affected: 0.15, co2_saving_kt: 0.04, bcr: 1.1 },
}
const FRANCHISE_MULTIPLIERS: Record<string, number> = {
  none: 1.0, partial: 1.3, full: 1.7,
}
```

These are hardcoded multipliers with no data provenance. `CLAUDE.md` states: "Pre-compute everything — DuckDB is a read-only lookup store, zero runtime analytics." The ScenarioBuilder is runtime analytics in the frontend, which is the exact pattern the architecture was designed to avoid.

The output (LSOAs affected, CO₂ saving, BCR) is computed entirely in the browser with no API call. The displayed disclaimer says "not DfT-validated" but the coefficients appear to be approximate estimates.

**Fix:** Precompute scenario impact data per region in `ps1`–`ps4` section stats. Read from the warehouse via the sections API. The sliders interpolate between pre-computed anchor points rather than computing from scratch.

---

### 9.5 🟡 PDF Export Has No Charts — Silently Truncates Narratives

**File:** `src/aequitas/api/routers/export.py`

The PDF export endpoint is already implemented (a Phase 3 item you thought was ahead of you). It uses ReportLab to produce an A4 document. What it includes:
- Cover heading with dimension and filter
- Stats table per section (key/value, plain numbers)
- Narrative text per section

What it **does not include:**
- Any Observable Plot charts (client-side only, unreachable by server-side ReportLab)
- Map visualizations (MapLibre GL is browser-only)

Narratives are silently truncated:
```python
story.append(Paragraph(narrative[:2000], styles["Normal"]))
```
No ellipsis, no indicator that the text was cut.

**Consequence:** The "Export PDF" button on `DimensionPage` produces a plain-text document. A policy analyst who wants to put this in a briefing pack gets something that looks like a data dump, not a professional report.

**Fix options:**
1. Add `[truncated]` indicator when narrative exceeds 2000 chars.
2. Server-side chart rendering: use `@observablehq/plot` via a Node.js subprocess to render charts as PNG, embed in ReportLab PDF.
3. Client-side PDF: use `html2canvas` + `jsPDF` in the frontend to screenshot the rendered section cards including charts.

---

### 9.6 🟢 Filter Dropdowns Have No Validation Against Available Data

**File:** `frontend/src/components/layout/FilterDropdowns.tsx`

Both dropdowns are fully interactive for all 30 combinations regardless of which have precomputed data. There is no visual indicator, tooltip, or disabled state for the 18 dead combinations.

**Fix:** Export a `PRECOMPUTED_COMBOS` constant from a shared module and use it to disable or visually flag combos with no data:
```tsx
const isAvailable = (region: string, urbanRural: string) =>
  region === "all" || urbanRural === "all"
```

---

### 9.7 🟢 Section Titles Don't Adapt to Filter Context

**File:** `frontend/src/lib/constants.ts`, `SECTION_TITLES`

"Route density **by region**" is the title for `a1_route_density` regardless of filter. When a single region is selected, there is no "by region" comparison — the title becomes misleading. The section is also suppressed (empty stats), so the title is never actually shown, but it should be fixed when §2.4 is fixed.

**Fix:** In `SectionCard.tsx`, derive title suffix from current filter:
```tsx
const contextSuffix = region !== "all" ? ` — ${regionName}` : " by region"
```

---

## 10. Medium — API Issues

### 10.1 🟡 No Input Validation on Region / Urban-Rural Parameters

**File:** `src/aequitas/api/routers/sections.py`

```python
region: str = Query("all", description="'all' or ONS region code"),
urban_rural: str = Query("all", description="'all', 'urban', or 'rural'"),
```

FastAPI accepts any string without validation. `?region=scotland&urban_rural=INVALID` returns an empty `SectionsResponse` rather than a 400 error. Downstream, the DuckDB query executes with invalid parameters and returns 0 rows.

**Fix:**
```python
from enum import Enum

class RegionParam(str, Enum):
    all = "all"
    north_east = "E12000001"
    ...

class UrbanRuralParam(str, Enum):
    all = "all"
    urban = "urban"
    rural = "rural"
```

---

### 10.2 🟡 `query_lsoa` Allowed Tables Don't All Exist in the Warehouse

**File:** `src/aequitas/api/services/warehouse.py`

```python
ALLOWED_TABLES = {
    "lsoa_service_quality",
    "lsoa_equity_metrics",
    "lsoa_accessibility",     # may not exist
    "lsoa_economic",          # may not exist
    "lsoa_policy",            # may not exist
    "route_details",          # may not exist
    "lta_readiness",          # may not exist
}
```

`builder.py`'s `load_core_tables()` only loads `lsoa_demographics`, `lsoa_service_quality`, and `lsoa_equity_metrics` from parquets. The other 5 tables in `ALLOWED_TABLES` may not exist, causing a DuckDB `CatalogException` on the LSOA endpoint.

---

### 10.3 🟡 `dimension` Parameter Not Validated in Sections Router

**File:** `src/aequitas/api/routers/sections.py`

```python
dimension: str = Query(..., description="One of 8 dimension IDs"),
```

`DIMENSION_PREFIXES` has 8 valid keys. An invalid dimension string silently returns an empty response. The `...` (required) is correct but validation against allowed values is missing.

---

### 10.4 🟢 Fresh DuckDB Connection Per Request Has Overhead

**File:** `src/aequitas/api/deps.py`

```python
def get_db() -> Generator[duckdb.DuckDBPyConnection | None, None, None]:
    conn = duckdb.connect(str(db_path), read_only=True)
    try:
        yield conn
    finally:
        conn.close()
```

A new DuckDB connection is opened and closed on every API request. For a pre-built read-only warehouse this is safe, but adds ~5–10ms overhead per request. Under moderate load (multiple analysts using simultaneously) this accumulates.

**Fix:** Use a connection pool or a single shared read-only connection with thread-local copies. DuckDB supports multiple readers on the same file.

---

## 11. Low — Polish & Improvements

### 11.1 🟢 No Data Freshness Timestamp Anywhere in the UI

The warehouse is built from BODS data captured at a specific pipeline run date. There is no `metadata` table in the warehouse, no `GET /api/metadata` endpoint, and no UI element showing "Data as of: March 2026." For transport analysts, data currency is critical — BODS feeds update frequently, NaPTAN changes quarterly, and using data that is 6+ months stale can produce materially wrong BCR calculations.

**Fix:** Add a `metadata` table in `builder.py`:
```python
db.execute("""
    CREATE OR REPLACE TABLE metadata AS
    SELECT
        CURRENT_TIMESTAMP AS built_at,
        '1.0.0' AS version,
        33755 AS lsoa_count,
        274719 AS stop_count,
        13099 AS route_count
""")
```
Expose at `GET /api/metadata` and show in the page header.

---

### 11.2 🟢 Test Suite Likely Fails Against Current Code

The project has 40+ test files including:
- `tests/warehouse/test_precompute_30.py` — presumably asserts all 30 combos produce results for all sections
- `tests/intelligence/test_section_registry.py` — tests section registry coverage
- `tests/api/test_overview.py` — tests overview endpoint

Given issue §2.1 (5-vs-51 gap), `test_precompute_30.py` will fail (precompute only produces 12 × 5 = 60 rows, not 30 × 51 = 1,530). The test suite is currently a liability rather than a safety net. Fix §2.1 first, then run `pytest` to identify remaining failures.

---

### 11.3 🟢 `equity` Section `gini_after_bottom_decile_uplift` Not Used

`equity_summary.json` contains `gini_after_bottom_decile_uplift` — the Gini after a modelled policy intervention uplifting the bottom decile. This is a compelling "what if" number for policy scenarios. It is never read by `_build_stats` or rendered in any template.

---

### 11.4 🟢 FAISS Embedding Model Loads at Startup — No Readiness Check

**File:** `src/aequitas/api/deps.py`, `lifespan()`

`SentenceTransformer("all-MiniLM-L6-v2")` is loaded synchronously at startup. Cold start (first load, model not cached) takes 30–60 seconds. The FastAPI lifespan is blocked during this period. `GET /api/health` may return 200 before the model is actually ready because the health endpoint doesn't check model state.

**Fix:** Add `"embedding_model_ready": bool(_state.get("embedding_model") is not None)` to the health endpoint response.

---

### 11.5 🟢 PDF Filename Sanitisation Is Over-Aggressive

**File:** `src/aequitas/api/routers/export.py`

```python
safe = re.sub(r"[^a-zA-Z0-9_-]", "_", f"aequitas_{dimension}_{region}_{urban_rural}")
```

Region codes like `E12000001` contain no special characters, but this still produces `aequitas_equity_E12000001_all.pdf` which is fine. However the regex replaces `.` with `_`, which would corrupt any extension accidentally included in the dimension string. Minor, but worth noting.

---

## 12. What Is Genuinely Good

These decisions are correct and should be kept:

| Decision | Why It's Right |
|---|---|
| Pre-compute everything into DuckDB | Zero runtime analytics = predictable latency, auditable outputs |
| Evidence-gated Jinja2 templates | Suppresses rather than misleads when data is absent |
| Fresh read-only DuckDB connection per request | Safe, no shared mutable state |
| `staleTime: Infinity` in TanStack Query | Correct for a pre-built warehouse — data doesn't change |
| URL-based filter state (`useSearchParams`) | Deep linking and shareability work out of the box |
| `ChartErrorBoundary` on every chart component | Prevents chart crashes from killing the whole page |
| ReportLab PDF infrastructure already in place | The skeleton is there — just needs charts added |
| BCR using Green Book / TAG v2.03fc methodology | Defensible to DfT scrutiny |
| IMD 2025 (not 2019) | Current data |
| Pydantic v2 at every data boundary | Enforces validation, no silent coercions |
| ScenarioBuilder slider UI concept | Right interaction pattern for the audience — just use warehouse data |
| ComparePage region side-by-side concept | Strong feature for LTA analysts — fix the `urban_rural` lock and slice |
| 40+ test files covering pipeline, intelligence, API, warehouse | Correct coverage structure — just needs to be run and fixed |

---

## 13. Recommended Fix Order

### Tier 1 — Fix These First (Everything Else Depends On Them)

1. **§2.1 + §2.2:** Update `_SECTIONS` to use `SECTION_REGISTRY.keys()` and write `_build_stats` for all 48 remaining sections using confirmed available parquet columns
2. **§5:** Fix `HEADLINE_SECTIONS` to use existing section IDs (or fix §2.1 first, then this resolves itself)
3. **§3.2:** Configure Supabase environment variables — nothing behind auth works without this
4. **§3.1:** Add Authorization header to `fetchJson` in `client.ts`

### Tier 2 — Fix Before Any User Testing

5. **§6:** Rebuild FAISS index after Tier 1 fixes
6. **§4.1:** Gray out dead filter combos in `FilterDropdowns.tsx`
7. **§4.2:** Fix urban-rural sections to suppress or use unfiltered data for the other-side computation
8. **§2.3:** Read `regional_equity` from `equity_summary.json` for regional Gini
9. **§2.4 + §8.1:** Switch ranking sections to `single_region.j2` context when `region != "all"`
10. **§2.5:** Fix `gap_to_target` to use national median as target, not filtered median

### Tier 3 — Before Public Launch

11. **§9.1:** Add public landing page with headline statistics (no auth required)
12. **§9.4:** Replace ScenarioBuilder hardcoded coefficients with warehouse lookup
13. **§9.5:** Add charts to PDF export (or client-side PDF generation)
14. **§11.1:** Add `metadata` table and data freshness indicator
15. **§7.1:** Change `g2_anomalies` chart_type to `scatter_clusters`
16. **§7.3:** Document ps1–ps4 bar semantics and implement in `_build_stats`
17. **§10.1:** Add enum validation on `region` and `urban_rural` API params
18. **§8.2:** Remove or stub `f4_gender_accessibility` with status note

### Tier 4 — Quality of Life

19. **§3.3:** Move rate limiter to Redis/Supabase
20. **§7.2:** Create dedicated `coverage_model_fit.j2` for `g3_coverage_model`
21. **§9.3:** Fix ComparePage `urban_rural` lock and arbitrary section slice
22. **§11.2:** Run test suite, fix failures against current code
23. **§10.4:** Connection pooling for DuckDB
24. **§11.3:** Expose `gini_after_bottom_decile_uplift` in equity narrative

---

*Document generated from full codebase audit, June 2026.*
*Files inspected: 60+ source files across pipeline, warehouse, API, frontend, templates, tests.*
