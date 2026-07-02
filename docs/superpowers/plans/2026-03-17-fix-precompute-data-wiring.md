# Fix Precompute Data Wiring — Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix all 25 broken section builders in `precompute.py` so every section produces stats, chart_data, and narratives — and region/urban_rural filters work for all dimensions.

**Architecture:** The root cause is data wiring: builders reference column names that don't exist in the parquets they query. Fix by (1) loading `master_lsoa_table` + `shap_summary.csv` as additional data sources, (2) enriching sparse parquets with region/urban_rural/population via left joins to `policy`, and (3) fixing column name mismatches in each builder. No new chart types or frontend changes needed.

**Tech Stack:** Python, pandas, DuckDB, existing `chart_data_builder.py` functions

---

## Chunk 1: Data Loading & Enrichment Layer

### Problem Summary

25 of 51 sections produce empty `chart_data` (`{}`). Root causes:

| Root Cause | Sections Affected | Fix |
|---|---|---|
| `shap_importance.parquet` missing — only `shap_summary.csv` exists | a8, d8, g3, g4 | Load CSV instead |
| Correlation columns (`unemployment_rate`, `nocar_pct`, `elderly_pct`, `income_score`) are in `master_lsoa_table` not `policy` | d2, d3, d4, d5 | Load master, merge into policy |
| `accessibility` has only 3 cols (`LSOA21CD`, `sfca_score`, `sfca_score_norm`) — no `region`, `population`, `urban_rural` | a3, a4, f4 | Join with policy on lsoa_cd |
| `service_quality` uses `LSOA21CD` (not `lsoa_cd`) and has no `region` | b2, b3 (stats but no chart) | Rename col, join with policy for region |
| `routes` has `length_km` not `route_length_km`, `stop_count` not `num_stops`, `primary_region` not `region` | c1, c2, c5, c7 | Rename columns |
| `equity` has no `gini`/`palma_ratio`/`concentration_index` — those are computed values, not stored columns | f1, a4 | Compute at precompute time from policy |
| `policy` has no `nonwhite_pct` | f3 | Merge from master |
| `economic` has `bcr` not `bcr_central`, no `annual_benefit_gbp` or `trips_per_day` | j1, j2 | Use correct column names |
| `anomalies` has no `x`/`y` for scatter — but does have `imd_score`/`service_quality_index` | g2 | Already works (uses those cols) |
| `clusters` has no `region` for D6 transport poverty | d6 | Join with policy |
| `routes` has no `trips_per_day` for c5 correlation | c5 | Skip — data doesn't exist |
| `master_lsoa_table` has `region = 'Unknown'` for all rows | — | Use `policy.region` as region source |

### Task 1: Enrich `_load_all_data` — add master table, shap CSV, and join sparse parquets

**Files:**
- Modify: `src/aequitas/warehouse/precompute.py:172-203` (`_load_all_data`)

- [ ] **Step 1: Add `master` and `shap` to source loading**

In `_load_all_data`, after the existing `sources` dict (line 182), add:

```python
# Load master_lsoa_table for socio-economic factors
master_path = _p("master_lsoa_table.parquet")
master = _load_parquet_safe(master_path)

# Load SHAP from CSV (no parquet exists)
shap_csv = cfg.audit_dir / "shap_summary.csv"
if shap_csv.exists():
    import csv
    shap_df = pd.read_csv(shap_csv)
    # Rename to match chart_data_builder expectation
    if "mean_abs_shap" in shap_df.columns:
        shap_df = shap_df.rename(columns={"mean_abs_shap": "importance"})
    data["shap"] = shap_df
```

And remove the existing `"shap": cfg.audit_dir / "shap_importance.parquet"` line from the sources dict since that file doesn't exist.

- [ ] **Step 2: Enrich `accessibility` with region/population/urban_rural**

After loading all sources, add enrichment joins. The join source is `policy` (has `lsoa_cd`, `region`, `urban_rural`, `population` for 33,755 LSOAs with real region names). `master` has `region = 'Unknown'` so don't use it for region.

```python
# Build a lookup from policy for region/population/urban_rural
policy_df = data.get("policy")
if policy_df is not None:
    lookup_cols = ["lsoa_cd", "region", "urban_rural", "population"]
    # Add socio-economic factors from master if available
    if master is not None:
        extra_cols = ["unemployment_rate", "nocar_pct", "elderly_pct",
                      "income_score", "nonwhite_pct", "disability_pct"]
        available = [c for c in extra_cols if c in master.columns]
        if available:
            policy_df = policy_df.merge(
                master[["lsoa_cd"] + available],
                on="lsoa_cd", how="left", suffixes=("", "_master"),
            )
            # Use master values where policy doesn't have them
            for col in available:
                master_col = f"{col}_master"
                if master_col in policy_df.columns:
                    policy_df[col] = policy_df[col].fillna(policy_df[master_col])
                    policy_df = policy_df.drop(columns=[master_col])
    data["policy"] = policy_df
    lookup = policy_df[lookup_cols].drop_duplicates(subset=["lsoa_cd"])

    # Enrich accessibility (has LSOA21CD, no region/population/urban_rural)
    if "accessibility" in data:
        acc = data["accessibility"]
        acc = acc.rename(columns={"LSOA21CD": "lsoa_cd"})
        acc = acc.merge(lookup, on="lsoa_cd", how="left")
        data["accessibility"] = acc

    # Enrich service_quality (has LSOA21CD, no region)
    if "service_quality" in data:
        sq = data["service_quality"]
        sq = sq.rename(columns={"LSOA21CD": "lsoa_cd"})
        sq = sq.merge(
            lookup[["lsoa_cd", "region"]], on="lsoa_cd", how="left",
        )
        data["service_quality"] = sq

    # Enrich clusters with region for D6
    if "clusters" in data:
        cl = data["clusters"]
        cl = cl.merge(lookup, on="lsoa_cd", how="left")
        data["clusters"] = cl

    # Enrich anomalies with region
    if "anomalies" in data:
        an = data["anomalies"]
        if "lsoa_cd" in an.columns and "region" not in an.columns:
            an = an.merge(
                lookup[["lsoa_cd", "region"]], on="lsoa_cd", how="left",
            )
            data["anomalies"] = an

    # Enrich coverage_prediction with region
    if "coverage_pred" in data:
        cp = data["coverage_pred"]
        if "lsoa_cd" in cp.columns and "region" not in cp.columns:
            cp = cp.merge(lookup, on="lsoa_cd", how="left")
            data["coverage_pred"] = cp
```

- [ ] **Step 3: Fix route column names**

```python
# Fix routes column naming
if "routes" in data:
    r = data["routes"]
    renames = {}
    if "length_km" in r.columns and "route_length_km" not in r.columns:
        renames["length_km"] = "route_length_km"
    if "primary_region" in r.columns and "region" not in r.columns:
        renames["primary_region"] = "region"
    if "cross_la" in r.columns and "cross_la_flag" not in r.columns:
        renames["cross_la"] = "cross_la_flag"
    if renames:
        data["routes"] = r.rename(columns=renames)
```

- [ ] **Step 4: Run precompute and verify section count improvement**

```bash
cd /Users/souravamseekarmarti/Projects/aequitas/.worktrees/phase2-frontend-rag
source .venv/bin/activate
python3 -c "
from aequitas.core.config import PipelineConfig
from aequitas.warehouse.precompute import precompute_all_sections
cfg = PipelineConfig()
results = precompute_all_sections(cfg)
national = [r for r in results if r['region'] == 'all' and r['urban_rural'] == 'all']
with_chart = [r for r in national if r['chart_data'] and len(r['chart_data']) > 0]
with_stats = [r for r in national if r['stats'] and len(r['stats']) > 0]
print(f'Total sections: {len(national)}')
print(f'With chart_data: {len(with_chart)}')
print(f'With stats: {len(with_stats)}')
empty = [r['section_id'] for r in national if not r['chart_data'] or len(r['chart_data']) == 0]
print(f'Still empty: {empty}')
"
```

Expected: chart_data count should go from ~26 to ~45+ (c5 will remain empty since route frequency data doesn't exist).

- [ ] **Step 5: Commit**

```bash
git add src/aequitas/warehouse/precompute.py
git commit -m "fix(precompute): enrich parquets with region/socio-economic cols, load SHAP CSV"
```

---

## Chunk 2: Fix Individual Builder Column Mismatches

### Task 2: Fix `_build_correlation` — use correct column names for d2-d5

**Files:**
- Modify: `src/aequitas/warehouse/precompute.py:618-665` (`_build_correlation`)

The correlation builder already maps d2→`unemployment_rate`, d3→`nocar_pct`, d4→`elderly_pct`, d5→`income_score`. After Task 1's enrichment, these columns will exist in `policy`. No code change needed here — the enrichment in Task 1 fixes this.

- [ ] **Step 1: Verify d2-d5 now produce charts**

```bash
python3 -c "
from aequitas.core.config import PipelineConfig
from aequitas.warehouse.precompute import precompute_all_sections
cfg = PipelineConfig()
results = precompute_all_sections(cfg)
national = [r for r in results if r['region'] == 'all' and r['urban_rural'] == 'all']
for sid in ['d1_coverage_deprivation','d2_coverage_unemployment','d3_coverage_car','d4_coverage_elderly','d5_coverage_income']:
    r = next((x for x in national if x['section_id'] == sid), None)
    has_chart = bool(r and r['chart_data'] and len(r['chart_data']) > 0)
    has_stats = bool(r and r['stats'] and len(r['stats']) > 0)
    chart_type = r['chart_data'].get('type','') if has_chart else ''
    print(f'{sid}: chart={has_chart} ({chart_type}) stats={has_stats}')
"
```

Expected: All 5 should show `chart=True (scatter_regression) stats=True`.

### Task 3: Fix `_build_equity` — compute Gini/Palma from policy data

**Files:**
- Modify: `src/aequitas/warehouse/precompute.py:366-392` (`_build_equity`)

The builder checks for `gini`, `palma_ratio`, `concentration_index` columns in the `equity` parquet, but these are computed values (single numbers), not columns. Fix: compute them from `policy.trips_per_capita` + `policy.population`.

- [ ] **Step 1: Rewrite `_build_equity` to compute metrics**

Replace the existing function:

```python
def _build_equity(
    section_id: str, data: dict, region: str, urban_rural: str,
) -> tuple[dict, dict]:
    """Build equity metrics (A4, F1)."""
    policy = data.get("policy")
    if policy is None:
        return {}, {}
    filtered = _filter_data(policy, region, urban_rural)
    if "trips_per_capita" not in filtered.columns or "population" not in filtered.columns:
        return {}, {}
    if not GiniEquityRule().should_fire(n_lsoas=len(filtered)):
        return {}, {}

    import numpy as np
    from scipy import stats as scipy_stats

    values = filtered["trips_per_capita"].fillna(0).values
    weights = filtered["population"].fillna(1).values

    # Gini coefficient
    sorted_idx = values.argsort()
    sv = values[sorted_idx]
    sw = weights[sorted_idx]
    cum_pop = np.cumsum(sw) / sw.sum()
    weighted_vals = sv * sw
    cum_service = np.cumsum(weighted_vals) / weighted_vals.sum()
    cum_pop = np.concatenate([[0], cum_pop])
    cum_service = np.concatenate([[0], cum_service])
    trapezoid = np.trapezoid if hasattr(np, "trapezoid") else np.trapz
    area_under = float(trapezoid(cum_service, cum_pop))
    gini = round(1 - 2 * area_under, 4)

    # Palma ratio (top 10% / bottom 40% by population-weighted service)
    n = len(sv)
    bottom_40_idx = int(n * 0.4)
    top_10_idx = int(n * 0.9)
    bottom_40_service = float(weighted_vals[:bottom_40_idx].sum())
    top_10_service = float(weighted_vals[top_10_idx:].sum())
    palma = round(top_10_service / bottom_40_service, 3) if bottom_40_service > 0 else 0.0

    # Concentration index
    if "imd_score" in filtered.columns:
        imd = filtered["imd_score"].fillna(0).values
        tpc = filtered["trips_per_capita"].fillna(0).values
        pop = filtered["population"].fillna(1).values
        imd_rank = scipy_stats.rankdata(imd) / len(imd)
        mean_tpc = float((tpc * pop).sum() / pop.sum())
        ci = float(2 * ((tpc * pop * imd_rank).sum() / (pop.sum() * mean_tpc)) - 1) if mean_tpc > 0 else 0.0
        ci = round(ci, 4)
    else:
        ci = 0.0

    stats: dict[str, Any] = {
        "gini": gini,
        "palma": palma,
        "concentration_index": ci,
    }

    chart = build_lorenz_curve(
        values=filtered["trips_per_capita"].fillna(0),
        weights=filtered["population"].fillna(1),
        title=SECTION_REGISTRY[section_id].title,
    )
    return stats, chart
```

- [ ] **Step 2: Verify f1 and a4 now produce Lorenz curves**

```bash
python3 -c "
from aequitas.core.config import PipelineConfig
from aequitas.warehouse.precompute import precompute_all_sections
cfg = PipelineConfig()
results = precompute_all_sections(cfg)
national = [r for r in results if r['region'] == 'all' and r['urban_rural'] == 'all']
for sid in ['f1_gini', 'a4_coverage_equity']:
    r = next((x for x in national if x['section_id'] == sid), None)
    print(f'{sid}: chart_type={r[\"chart_data\"].get(\"type\",\"EMPTY\") if r[\"chart_data\"] else \"EMPTY\"} gini={r[\"stats\"].get(\"gini\",\"?\")}')
"
```

Expected: Both show `lorenz_curve` type and `gini=0.5741`.

- [ ] **Step 3: Commit**

```bash
git add src/aequitas/warehouse/precompute.py
git commit -m "fix(precompute): compute Gini/Palma/CI from policy data, not equity parquet"
```

### Task 4: Fix `_build_economic_value` and `_build_bcr` — correct column names

**Files:**
- Modify: `src/aequitas/warehouse/precompute.py:1054-1113` (`_build_economic_value`, `_build_bcr`)

The economic parquet has:
- `annual_total_benefit` not `annual_benefit_gbp`
- `annual_additional_trips` not `trips_per_day`
- `bcr` not `bcr_central`

- [ ] **Step 1: Fix `_build_economic_value`**

Replace references:
- `annual_benefit_gbp` → `annual_total_benefit` (3 occurrences)
- `trips_per_day` → `annual_additional_trips` (1 occurrence)

```python
def _build_economic_value(
    section_id: str, data: dict, region: str, urban_rural: str,
) -> tuple[dict, dict]:
    """Build economic value (J1)."""
    econ = data.get("economic")
    if econ is None:
        return {}, {}
    filtered = _filter_data(econ, region, urban_rural)
    if not MinLsoaRule().should_fire(n_lsoas=len(filtered)):
        return {}, {}

    benefit_col = "annual_total_benefit" if "annual_total_benefit" in filtered.columns else "annual_benefit_gbp"
    trips_col = "annual_additional_trips" if "annual_additional_trips" in filtered.columns else "trips_per_day"

    stats: dict[str, Any] = {
        "annual_benefit": float(filtered[benefit_col].sum()) if benefit_col in filtered.columns else 0,
        "region_name": "England" if region == "all" else region,
        "n_trips": int(filtered[trips_col].sum()) if trips_col in filtered.columns else 0,
        "vot": 8.49,
    }

    chart: dict = {}
    if "region" in filtered.columns and benefit_col in filtered.columns:
        by_region = filtered.groupby("region")[benefit_col].sum().reset_index()
        by_region.columns = ["label", "value"]
        by_region["value"] = (by_region["value"] / 1e6).round(1)
        chart = build_horizontal_bar(
            data=by_region, title=SECTION_REGISTRY[section_id].title,
            x_label="Annual benefit (£m)", y_label="Region",
        )
    return stats, chart
```

- [ ] **Step 2: Fix `_build_bcr`**

Replace `bcr_central` → `bcr`:

```python
def _build_bcr(
    section_id: str, data: dict, region: str, urban_rural: str,
) -> tuple[dict, dict]:
    """Build BCR analysis (J2)."""
    econ = data.get("economic")
    if econ is None:
        return {}, {}
    filtered = _filter_data(econ, region, urban_rural)
    bcr_col = "bcr" if "bcr" in filtered.columns else "bcr_central"
    if bcr_col not in filtered.columns or len(filtered) == 0:
        return {}, {}

    mean_bcr = float(filtered[bcr_col].mean())
    stats: dict[str, Any] = {
        "bcr": round(mean_bcr, 2),
        "area_name": "England" if region == "all" else region,
        "vfm_band": "Very High" if mean_bcr > 4 else ("High" if mean_bcr > 2 else ("Medium" if mean_bcr > 1.5 else ("Low" if mean_bcr > 1 else "Poor"))),
        "investment_m": round(float(filtered["investment_gap_annual_cost"].sum()) / 1e6, 1) if "investment_gap_annual_cost" in filtered.columns else 0,
        "appraisal_years": 60,
    }

    chart: dict = {}
    if "region" in filtered.columns:
        by_region = filtered.groupby("region")[bcr_col].mean().reset_index()
        by_region.columns = ["label", "value"]
        by_region["value"] = by_region["value"].round(2)
        chart = build_horizontal_bar(
            data=by_region, title=SECTION_REGISTRY[section_id].title,
            x_label="BCR", y_label="Region",
        )
    return stats, chart
```

- [ ] **Step 3: Commit**

```bash
git add src/aequitas/warehouse/precompute.py
git commit -m "fix(precompute): use correct economic column names (bcr, annual_total_benefit)"
```

### Task 5: Fix `_build_demographic` — use `nonwhite_pct` from enriched policy

**Files:**
- Modify: `src/aequitas/warehouse/precompute.py:906-939` (`_build_demographic`)

After Task 1's enrichment, `policy` will have `nonwhite_pct` merged from master. No code change needed — verify only.

- [ ] **Step 1: Verify f3 now produces chart**

```bash
python3 -c "
from aequitas.core.config import PipelineConfig
from aequitas.warehouse.precompute import precompute_all_sections
cfg = PipelineConfig()
results = precompute_all_sections(cfg)
r = next((x for x in results if x['section_id'] == 'f3_ethnic_access' and x['region'] == 'all' and x['urban_rural'] == 'all'), None)
print(f'f3: chart={bool(r[\"chart_data\"])} stats={bool(r[\"stats\"])}')
if r['chart_data']: print(f'  type={r[\"chart_data\"].get(\"type\",\"?\")}')
"
```

Expected: `chart=True` with `grouped_bar` type.

### Task 6: Fix `_build_distribution` — routes column `stop_count` not `num_stops`

**Files:**
- Modify: `src/aequitas/warehouse/precompute.py:668-713` (`_build_distribution`)

After Task 1's route column renames, `length_km` → `route_length_km` is fixed. But the metric_map for c2 references `num_stops` — the actual column is `stop_count`.

- [ ] **Step 1: Fix c2 metric name**

Change line in `metric_map`:
```python
"c2": ("stop_count", "Stops per Route", "stops"),
```

- [ ] **Step 2: Commit**

```bash
git add src/aequitas/warehouse/precompute.py
git commit -m "fix(precompute): c2 uses stop_count not num_stops"
```

### Task 7: Handle `_build_network` — fix `cross_la_flag` and `route_length_km`

**Files:**
- Modify: `src/aequitas/warehouse/precompute.py:789-816` (`_build_network`)

After Task 1's renames, `cross_la` → `cross_la_flag` and `length_km` → `route_length_km` are handled. But `cross_la_flag` is boolean/string (`True`/`False`), not int. Fix the `.sum()` call.

- [ ] **Step 1: Fix cross_la_flag type handling**

```python
cross_col = "cross_la_flag" if "cross_la_flag" in routes.columns else "cross_la"
if cross_col in routes.columns:
    n_cross = int(routes[cross_col].astype(bool).sum())
else:
    n_cross = 0
```

- [ ] **Step 2: Commit**

```bash
git add src/aequitas/warehouse/precompute.py
git commit -m "fix(precompute): handle cross_la boolean type in c7 network"
```

### Task 8: Mark c5 as data-unavailable gracefully

**Files:**
- Modify: `src/aequitas/warehouse/precompute.py:618-665` (`_build_correlation`)

The `c5` section wants `route_length_km` vs `trips_per_day` from `policy`, but `trips_per_day` doesn't exist in any parquet. The routes parquet has `route_length_km` (after rename) but no frequency data per route. This is genuinely missing data.

- [ ] **Step 1: Add c5 to use routes data with a stats-only fallback**

Instead of trying to correlate, produce a stats-only section with route length distribution info:

In the `col_map` dict in `_build_correlation`, change c5 to use columns that actually exist in routes:

```python
# c5 cannot do correlation (no trips_per_day in routes), handled by _build_distribution fallback
```

Actually, c5 is already handled: the col_map lookup for `c5` references `policy` columns that don't exist, so it returns `{}`. This is acceptable — the section just won't have a chart. No change needed.

---

## Chunk 3: Rebuild Warehouse & Verify

### Task 9: Rebuild the DuckDB warehouse

**Files:**
- No file changes — execution only

- [ ] **Step 1: Kill any processes holding the DuckDB lock**

```bash
lsof data/aequitas.duckdb 2>/dev/null | grep -v COMMAND | awk '{print $2}' | xargs -r kill
```

- [ ] **Step 2: Rebuild warehouse**

```bash
cd /Users/souravamseekarmarti/Projects/aequitas/.worktrees/phase2-frontend-rag
source .venv/bin/activate
python3 -c "
from aequitas.core.config import PipelineConfig
from aequitas.warehouse.precompute import precompute_all_sections
from aequitas.warehouse.schema import create_warehouse
import json

cfg = PipelineConfig()
results = precompute_all_sections(cfg)

# Stats before write
national = [r for r in results if r['region'] == 'all' and r['urban_rural'] == 'all']
with_chart = [r for r in national if r.get('chart_data') and len(r['chart_data']) > 0]
with_stats = [r for r in national if r.get('stats') and len(r['stats']) > 0]
with_narrative = [r for r in national if r.get('narrative','').strip()]
print(f'Total national sections: {len(national)}')
print(f'With chart_data: {len(with_chart)}')
print(f'With stats: {len(with_stats)}')
print(f'With narrative: {len(with_narrative)}')
empty_charts = [r['section_id'] for r in national if not r.get('chart_data') or len(r['chart_data']) == 0]
print(f'Empty chart sections: {empty_charts}')

# Chart type breakdown
from collections import Counter
types = Counter(r['chart_data'].get('type','none') for r in national if r.get('chart_data'))
print(f'Chart type distribution: {dict(types)}')

# Write to warehouse
create_warehouse(cfg, results)
print('Warehouse rebuilt.')
"
```

Expected:
- With chart_data: 45+ (was 26)
- Empty charts: only c5 and possibly a few others with genuinely missing data
- Chart types: mix of horizontal_bar, scatter_regression, lorenz_curve, grouped_bar, stacked_bar, box_violin, scatter_clusters, choropleth, heatmap, shap_bar

- [ ] **Step 3: Verify region filter works**

```bash
python3 -c "
import duckdb, json
db = duckdb.connect('data/aequitas.duckdb', read_only=True)
# Check London sections
london = db.execute(\"SELECT section_id, chart_data FROM section_results WHERE region = 'London' AND urban_rural = 'all'\").fetchall()
with_data = [(sid, json.loads(cd).get('type','none') if cd else 'empty') for sid, cd in london if cd and json.loads(cd)]
print(f'London sections with charts: {len(with_data)} / {len(london)}')
for sid, t in with_data[:10]:
    print(f'  {sid}: {t}')

# Check urban filter
urban = db.execute(\"SELECT section_id, chart_data FROM section_results WHERE region = 'all' AND urban_rural = 'urban'\").fetchall()
with_data_u = [(sid, json.loads(cd).get('type','none') if cd else 'empty') for sid, cd in urban if cd and json.loads(cd)]
print(f'\nUrban sections with charts: {len(with_data_u)} / {len(urban)}')
"
```

Expected: Both London and Urban should have similar chart counts to national.

- [ ] **Step 4: Restart API server and verify in browser**

```bash
# Kill existing uvicorn
pkill -f "uvicorn.*aequitas" 2>/dev/null
sleep 2
# Restart
cd /Users/souravamseekarmarti/Projects/aequitas/.worktrees/phase2-frontend-rag
source .venv/bin/activate
uvicorn src.aequitas.api.main:app --reload --port 8000 &
```

Check frontend at `http://localhost:5173` — each dimension page should show diverse chart types, not just horizontal bars and data tables.

- [ ] **Step 5: Commit**

```bash
git add -A
git commit -m "fix(warehouse): rebuild with all 51 sections producing charts and stats"
```

---

## Sections That Will Remain Empty (Acceptable)

| Section | Reason | Resolution |
|---|---|---|
| `c5_length_vs_frequency` | No per-route frequency data exists in any parquet | Future data enhancement |
| `a6_urban_rural_gap` | May fail if `_filter_data` comparison produces NaN | Debug if still empty after rebuild |
| `d6_transport_poverty` | HDBSCAN has only 2 clusters + noise (87.7%) — ClusterRule may not fire | Acceptable — low signal |

---

## Verification Checklist

After all tasks complete:

- [ ] `python3 -c "..."` precompute shows 45+ sections with chart_data (was 26)
- [ ] Region filter (e.g. London) returns non-empty results for all dimensions
- [ ] Urban/rural filter returns non-empty results
- [ ] Chart type distribution shows 8+ different types (not just horizontal_bar)
- [ ] Frontend renders charts for correlations (d1-d5), equity (f1), service quality (b2, b3), routes (c1, c2), economic (j1, j2), ML (a8, d8, g4)
- [ ] No Python errors in uvicorn logs
