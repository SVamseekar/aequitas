# Plan: Fix warehouse staleness + region/urban_rural filter bugs across all 8 dimensions

## Context

A full visual audit (240 screenshots: 8 dimensions × 10 regions × 3 area types) plus
warehouse/code cross-checks found two classes of problem:

1. **Warehouse staleness** — `data/aequitas.duckdb` was last built 2026-05-22, but
   `chart_dispatch.py`, `stats_builders/*.py`, and `intelligence/templates/*.j2` have
   commits through 2026-06-10 (the "wire all 51 sections through stats builders" work
   and chart_dispatch wiring). Most empty-narrative and schema-mismatch issues are
   downstream of this — **a warehouse rebuild alone fixes them**, once the underlying
   code is correct.

2. **Genuine code bugs** — independent of staleness, several stats builders/chart
   builders don't filter by `region` and/or `urban_rural` correctly, have signature
   mismatches, or produce template/builder schema drift. **A rebuild will NOT fix
   these** — they must be fixed in code first, otherwise the rebuild bakes in the
   same bugs.

Order of operations: **fix code bugs first → then rebuild the warehouse → then
re-screenshot to verify.**

## Part A — Code bugs to fix (rebuild won't help until these are done)

### A1. bsa3_tier_distribution — ignores urban_rural (RESOLVED: region-only by design)
- **Confirmed**: `data/audit/lta_franchising_readiness.parquet` (298 LAD rows) has
  columns `lad_cd, lad_nm, region, n_lsoas, population, mean_imd_score, mean_sqi,
  mean_trips_per_cap, ..., franchising_readiness, readiness_tier` — **no
  urban_rural column at LAD grain**. LADs mix urban and rural LSOAs, so an
  urban/rural split of LAD-level tiers isn't meaningful without re-aggregating
  from LSOA grain (out of scope here).
- Fix: (1) `src/aequitas/warehouse/stats_builders/misc.py` `_build_tier_distribution`
  (~lines 190-200) and `chart_dispatch.py` `_build_tier_distribution_chart`
  (~lines 755-778) should still filter `lta_df` by `region` (currently
  `_build_tier_distribution_chart` does this for chart but `_build_tier_distribution`
  doesn't filter at all — fix the stats builder to match).
  (2) For `urban_rural != "all"`, return the same region-filtered result
  (LAD-grain, can't subdivide) — but the frontend/template should note
  "LAD-level metric — not subdivided by urban/rural" so it's not presented as if
  it were filtered when it isn't.

### A2. bsa1_franchising_readiness — ignores urban_rural (RESOLVED: region-only by design)
- Same root data (`lta_franchising_readiness.parquet`, LAD-grain, no urban_rural
  column) — same fix as A1: ensure region filtering works correctly, document/label
  as LAD-level (not subdividable by urban_rural) rather than silently ignoring the
  filter.

### A3. bsa2_operator_concentration — single global HHI, ignores all filters
- HHI=829 / "Low concentration" identical across every region and filter combo,
  including "all". `data/audit/bods_operator_summary.csv` (`agency_name, n_routes,
  total_trips, mean_trips_per_route, max_trips`) has **no region/LAD column** —
  computing region-aware HHI requires joining routes to `route_geometries.primary_region`
  (and agency) first, then computing per-region operator route-share HHI.
- Locate the operator concentration stats builder, build the
  route→operator→region join (via `route_geometries.agency_name` +
  `.primary_region`), and make HHI computation region-aware. urban_rural split
  possible if A8's route urban/rural classification is reused (route counts as
  urban/rural/mixed). Consistent with c3_operator_hhi (see A7 — likely shares
  this same join/helper).

### A4. b2_operating_hours / b3_weekend_penalty — signature mismatch + non-responsive
- `chart_dispatch.py` calls a region-aware signature
  `_build_operating_hours(section_id, region, filtered, sources, lsoa_cds)` /
  `_build_weekend_penalty(...)` (returns `{}` if `region != "all"` per current
  code, ~lines 134-138, 671-680, 709-718).
- `stats_builders/misc.py` still calls the OLD signature
  `_build_operating_hours(service_quality_df)` / `_build_weekend_penalty(service_quality_df)`
  (~lines 259-262) — dataframe-only, not filter-aware.
- Fix: align `misc.py` to call the same region/urban_rural-aware path as
  `chart_dispatch.py` (or vice versa — pick one canonical implementation and have
  both call sites use it). Both currently produce identical stats across
  urban/rural within a region — must vary after fix.
- Both also have **0 narrative for every row including region='all'** — confirm
  `b2_operating_hours.j2`/`b3_weekend_penalty.j2` (or whichever templates) exist and
  are wired in `intelligence/engine.py`'s section→template map.

### A5. b4_route_frequency — documented stub duplicating b1 (NOW BUILDABLE)
- `ranking.py` comment says "there is no per-route frequency join in the
  warehouse" — b4 currently returns byte-identical stats to b1_frequency.
- **This data exists.** `data/audit/route_stop_sequences.parquet` has
  `route_id` + `trip_id` for all 13,640 routes (452,322 rows). Per-route daily
  trip count = `df.groupby('route_id')['trip_id'].nunique()`.
- Implementation: build a `route_trip_frequency` intermediate (route_id →
  n_trips/day, joined to `route_geometries` for route_short_name/agency_name/
  primary_region). b4_route_frequency stats = top-5/bottom-5 individual routes
  by trip count (filtered by region/urban_rural via `primary_region` and the
  route's LSOA urban/rural mix from A8's join, once that exists). Genuinely
  distinct from b1 (region-level mean headway) — operates at route grain.
- New chart: horizontal bar of top/bottom routes by trips/day, labeled with
  route_short_name + agency_name.

### A6. c1_route_length / c2_stops_per_route — ignore urban_rural
- `_build_distribution_section` in `misc.py` (~lines 134-147) filters by
  `primary_region` only; signature doesn't accept `urban_rural`.
- Also: stats schema is `{mean, median, p25, p75, max, n_routes}` but
  `distribution.j2` needs `{mean, median, std, cv, iqr, p10, p90, n_outliers,
  metric_name, unit, skew_label}` — schema must be extended (this part is also a
  staleness symptom but the schema itself needs the new fields computed in code
  before any rebuild produces them).
- Fix: (1) add urban_rural filtering, (2) compute the additional distribution
  stats fields the template requires.

### A7. c3_operator_hhi — non-responsive + blank narrative substitution (LIKELY SAME TASK AS A3)
- HHI/market_structure/n_operators_national identical across all regions/filters.
  `market_concentration.py::_build_from_routes` now takes `region_name` as a
  required param per current code, but the narrative renders with a literal blank
  where the region name should be — confirm the param is actually being passed
  and the template placeholder matches the stats key name.
- **Implementation note**: A3 (bsa2_operator_concentration) and A7 (c3_operator_hhi)
  almost certainly share the same route→operator→region join and
  `market_concentration.py` helper. Implement as ONE task: build the join once,
  fix `_build_from_routes` to be region/urban_rural-aware, and wire both bsa2 and
  c3 stats builders + their narratives through it. Do not dispatch as two
  independent subagent tasks — the second would likely redo or conflict with the
  first's join.

### A8. c4_urban_rural_routes — stub vs warehouse mismatch (NOW BUILDABLE)
- `urban_rural_gap.py` documents this as a stub returning `{}`/different schema
  (no route-geometry × urban/rural join exists). Warehouse still has old
  `{n_routes, n_cross_la, pct_cross_la}` data.
- **This is buildable.** `route_stop_sequences.parquet` has `stop_lat`/`stop_lon`
  for every stop on all 13,640 routes (not gated on the 53% with shape
  geometry). Spatial-join each stop to its LSOA (point-in-polygon against LSOA
  boundaries already used for choropleth sections), pull
  `lsoa_service_quality.urban_rural` per stop, then classify each route by the
  urban/rural mix of its stops (e.g., "urban" if >80% urban stops, "rural" if
  >80% rural, else "mixed").
- Implementation: build a `route_urban_rural` intermediate (route_id →
  urban/rural/mixed classification + primary_region). c4_urban_rural_routes
  stats = % of routes per region that are urban/rural/mixed, plus the existing
  `n_cross_la`/`pct_cross_la` (already correct, from `route_geometries.cross_la`).
  Filterable by region (via `primary_region`) and by urban_rural (a route counts
  toward "urban" view if classified urban, etc.).
- New chart: stacked bar of urban/rural/mixed route share per region.
- Note: this spatial join (stop → LSOA) may already exist in
  `src/aequitas/processing/demographics.py` (grep hit during investigation) —
  check for a reusable function before writing a new point-in-polygon join.

### A9. c5_length_vs_frequency — defined but never computed
- `correlation.py::build_correlation_stats` defines a `c5_length_vs_frequency`
  config but the warehouse has never had it computed (`stats={}` for all combos).
  Confirm the config is correctly wired into whatever orchestrates
  `build_correlation_stats` calls during precompute — likely just a missing
  registration, not a missing implementation.

### A10. c6_route_archetypes — cluster labels never populated
- Stats correctly show `n_clusters/n_routes/largest_cluster_size` (national,
  acceptable since clustering is inherently non-regional), but the chart legend
  shows "Cluster -1: undefined | Cluster 0: undefined ..." for every cluster.
- Find where cluster labels should be derived (likely from
  `lsoa_archetypes`/route clustering ML output — HDBSCAN labels per
  CLAUDE.md ML decisions) and populate human-readable names instead of
  "undefined".

### A11. c7_network_topology — total schema mismatch
- Warehouse stats `{n_lads, mean_sqi}` vs current code's
  `_build_network_topology` (precompute.py ~line 437) which produces
  `{n_cross_la, pct_cross_la, mean_length, median_length, densest_corridor,
  densest_count}` for `network_topology.j2`, and chart builder
  `_build_network_topology_choropleth` (chart_dispatch.py ~line 811) expects
  `lta_df` columns `lad_cd/lad_nm/mean_trips_per_cap`.
- Confirm current `_build_network_topology` + choropleth builder are mutually
  consistent and produce real per-region/urban_rural variation (this is a fresh
  schema, not present at all in the stale warehouse — needs end-to-end check
  after rebuild, but verify the code path is internally consistent first).

### A12. d1-d8 narrative template/builder contract drift (SPLIT INTO 3 SEPARATE TASKS — different builders)

**A12a — correlation.j2 `n` vs `n_observations`** (`correlation.py`)
- `correlation.j2` requires `n_observations`; `correlation.py`'s
  `build_correlation_stats` only writes `{r, p, n}`. Fix: either rename `n` →
  `n_observations` in the stats output, or update the template to use `n` —
  pick one and make consistent across all correlation sections (d1-d5, b5,
  f3 once A16 is built, whichever else uses `correlation.j2`).

**A12b — heatmap.j2 (d7) schema** (`misc.py` d7 builder)
- `heatmap.j2` (d7) requires `worst_cell`, `best_cell`, `x_dimension`,
  `y_dimension`, `metric_name`; `misc.py` d7 builder only produces
  `{n_lsoas, urban_rural_gap}`. Compute the cell-level extrema the template needs.

**A12c — ml_prediction.j2 (d8) `top_importance` + d6 cluster scatter** (ML stats builder)
- `ml_prediction.j2` (d8, a8) requires `top_importance` (SHAP value) in addition
  to `top_feature`/`r2`; current stats only have `{r2, top_feature}`. Add
  `top_importance` to the ML prediction stats builder output (SHAP value for
  `nocar_pct`, per ground truth).
- d6_transport_poverty's bottom chart renders as a single solid bar (likely
  `_build_scatter_clusters` receiving a single data point instead of the LSOA
  cluster scatter expected by `ml_clusters.j2`) — check stats shape
  `{n_lsoas: 33755, n_clusters: 3}` against what `_build_scatter_clusters` expects
  and supply the actual per-cluster/per-point data if missing.
- These two (d8 top_importance, d6 cluster scatter) likely come from the same ML
  output artifacts — bundle as one task (A12c).

### A13. d1 correlation variable pairing vs ground truth
- d1 stat r=+0.141 (imd_score vs trips_per_capita) vs CLAUDE.md ground truth
  "IMD–stop Pearson correlation = -0.0644" (presumably IMD vs stop COUNT, not
  trips per capita). These may be measuring different things — confirm d1's
  intended variable pair against the section registry's documented purpose for
  d1_coverage_deprivation, and either correct the column choice or confirm the
  different pairing is intentional (and update CLAUDE.md/figures-registry if a
  new figure should be tracked separately).

### A14. j2_bcr rural/urban region-filter bug
- rural BCR=1.32 and urban BCR=1.12 identical across ALL 9 regions (only "all"
  varies slightly: 1.12-1.20). Strong signal that the rural/urban appraisal_df
  slice isn't filtered by region before BCR aggregation — likely the same
  region-code-vs-name filter bug noted in commit `acd8d35`. Trace
  `stats_builders/economic.py`'s rural/urban BCR computation and apply the
  correct region filter (use the same fixed filter pattern from `acd8d35`).

### A15. f2_disparity_ratio — division-by-zero for London
- E12000007 (London) `all` returns `disparity_ratio: 0` from `p10=0.0`,
  `p90=1.1885` — `0/0` or `x/0` produces a misleading "0" instead of an
  "undefined"/very-high indicator. Add a guard in `equity.py` (~line 131): if
  `p10 == 0`, return `null`/a sentinel and have `equity_decile.j2` render
  "ratio undefined (bottom decile has zero baseline)" instead of "0".

### A16. f3_ethnic_access — stub is WRONG, data exists (NOW BUILDABLE)
- Current code stubs f3 to `{}`, with a comment claiming "requires a ts021
  ethnicity-by-LSOA join that does not exist." **This is incorrect** —
  `master_lsoa_table.parquet` already has `eth_white`, `eth_asian`, `eth_black`,
  `eth_mixed`, `eth_other`, `eth_total`, `nonwhite_pct` columns (ts021 was
  already ingested).
- Implementation: f3_ethnic_access = correlation between `nonwhite_pct` (or
  individual `eth_*` shares) and a bus-access metric (`stops_per_1k` or
  `service_quality_index`), reusing the same `correlation.py` builder/config
  pattern as d1-d5. Remove the incorrect stub in `misc.py`, add an
  `f3_ethnic_access` entry to `correlation.py`'s config dict.
- Chart: scatter plot (same `_chart_correlation_scatter` pattern as d1-d5),
  colored/grouped by ethnicity category if useful.

### A16b. f4_gender_accessibility — genuinely a drop
- Unlike f3, no sex/gender-by-LSOA column exists anywhere in
  `master_lsoa_table.parquet` or other audit parquets (checked: census TS021 is
  ethnicity, not sex/gender — no TS008 or equivalent ingested).
- Stale warehouse's f4 chart shows "Low elderly"/"High elderly" bars — clearly a
  mislabeled leftover from a different metric, not real gender data.
- Action: remove f4_gender_accessibility from the section registry. Confirm the
  frontend (`SectionCard.tsx` / dimension page) handles a dimension with one
  fewer section gracefully (it should — sections are rendered from a list).
  This is a genuine missing-data-source drop (would require new Census table
  ingestion = Phase 0 rescope), unlike A5/A8/A16 which were buildable from
  existing data.

## Part B — Chart redesign (independent of staleness)

### B1. ps1-ps5/g5 scenario charts mix incompatible units on one axis
- `chart_dispatch.py` `_chart_scenario_horizontal_bar` (~lines 413-434) plots
  population (millions), annual cost (£m), and CO₂ (tonnes/yr) on one shared
  linear axis — meaningless regardless of data correctness.
- Recommended fix:
  - **ps1-ps4, g5 (single scenario)**: replace the bar chart with KPI tiles —
    Population affected, Annual cost £m, CO₂ saved t/yr, each with its own
    number/unit, no shared axis. Matches existing "headline figure" patterns
    elsewhere in the dashboard.
  - **ps5 (comparison)**: replace with either small-multiples (one bar chart per
    metric, scenarios as bars within each) or a ranked table (Scenario |
    Population | Cost £m/yr | CO₂ t/yr | Cost/beneficiary), supporting the
    "ranks scenarios by population impact" framing in `scenario_comparison.j2`.
### B2. Region/urban_rural filtering for policy scenarios (NOW BUILDABLE — supersedes earlier "hide filters" idea)
- `policy_scenario.py`'s docstring claims scenarios are England-wide/not
  region-scoped, with `population_affected` as a single national constant per
  scenario (5,689,818 / 8,392,662 / 5,243,877 / 760,008 — see `policy_scenarios`
  table). But each scenario's `scope` column describes a specific LSOA subset:
  - ps1: "3,375 LSOAs (most deprived decile)" → `master_lsoa_table.imd_decile == 10`
  - ps2: "5,189 LSOAs (evening isolated)" → `lsoa_service_quality.evening_isolated`
  - ps3: "3,192 rural LSOAs (high elderly, low density)" → rural + elderly filter
  - ps4: "5 LADs (highest readiness scores)" → top-5 LAD readiness (LA-level, not LSOA)
- **This is buildable**: instead of a precomputed national constant, compute
  `population_affected` (and `annual_additional_trips`) by filtering the
  scenario's target LSOA set by `region`/`urban_rural` (using
  `master_lsoa_table.region` and `.urban_rural`, same columns used everywhere
  else) and summing `population` over the filtered set. For "all/all" this
  reduces to the current national figure (sanity check against existing
  5,689,818 etc.).
- ps4 (LAD-level) is the exception — "top-5 LADs by readiness" doesn't
  decompose by region in the same way (a LAD either is or isn't in the top 5
  nationally). For ps4, either keep it England-wide with a label, or show
  whether the *currently filtered region* contains any of the top-5 LADs (and
  if not, show "0 — no top-5 LAD in this region/filter").
- Implementation: extend `policy_scenario.py`'s stats builder to accept
  `region`/`urban_rural`/the relevant LSOA-level dataframes, recompute
  population_affected per the scope's filter logic. ps5_scenario_comparison
  aggregates the per-region figures for all 4 scenarios.

## Part C — Warehouse rebuild

Once Part A is complete (and B if bundled):

1. `uv run aequitas intelligence` — regenerate narratives (Stage 4)
2. `uv run aequitas warehouse` — rebuild `section_results` (Stage 5), 1530 rows
   (51 sections × 30 region/urban_rural combos)
3. Spot-check via DuckDB queries that previously-empty narratives are now
   populated, previously-identical stats now vary correctly across
   region/urban_rural, and schema fields match what templates require.

## Part D — Re-verify visually

1. Re-run `frontend/scripts/screenshot-all-filters.mjs` (240 screenshots)
2. Spot-check the same representative set used in the audit (all/all,
   region1/urban, region1/rural, region2/all per dimension) for each of the 16
   issues above
3. Confirm narratives render, charts vary by filter where expected, and the
   redesigned scenario charts/tiles look correct

## Part E — Chart-type / visual design audit (240 screenshots, 8 parallel agents, 2026-06-11)

A second audit, separate from Part A's data/wiring audit, asked: **even with
correct data, is this the right chart TYPE for what it represents?** Each of
the 8 dimensions was reviewed across all 30 region/urban_rural screenshots.

### E0. Cross-cutting pattern — "single giant bar" / blank chart on region-filtered views
The dominant finding, recurring across 6 of 8 dimensions: a chart designed to
**compare N regions** (horizontal bar, one bar per region) is shown unchanged
when the user filters to ONE region — collapsing to either (a) one bar filling
the entire chart width (meaningless — no comparison left), or (b) a blank/empty
chart area (worse). Affects:
- equity: "Most Equitable Regions" → single bar with mismatched stat-row region
  names
- accessibility: "Route Density by Region" / "Stop Density by Region" → renders
  completely empty in all 27 single-region screenshots
- service-quality: b1/b2/b3/b4 → entire charts disappear, page header literally
  shows "1 CHARTS · 0 NARRATIVES" (vs national view's multi-chart layout)
- route-network: c3_operator_hhi → one giant bar (one operator, 100% width)
- economic: j1/j3/j4 → one full-width bar per section (3 sections × 27 views)
- bus-services-act: bsa1_franchising_readiness → single bar, large empty space

**Recommended fix (one pattern, reusable across all of the above)**: build a
single `<RegionMetricCard>`-style component — when `region != "all"`, replace
the N-region bar chart with a KPI card showing the value, optionally with
"rank X of 9" or "vs national avg Y" for context. Implement once, apply to all
6 sections above. This is now **E1**.

### E1. Single-region KPI-card fallback (supersedes per-section chart-type fixes above)
- Sections: equity "Most Equitable Regions", accessibility "Route/Stop Density
  by Region", service-quality b1/b2/b3 (b4 covered separately by A5's rebuild —
  ensure the rebuilt b4 doesn't inherit this same collapse), route-network
  c3_operator_hhi, economic j1/j3/j4, bus-services-act bsa1.
- For c3_operator_hhi specifically: consider showing top 4-5 operators by share
  (still useful at regional level) rather than collapsing straight to a KPI
  card — operator landscape composition is itself informative.
- Severity: significant (27/30 screenshots affected per section, ~9 sections).

### E2. Equity "Disparity by IMD Decile" — empty chart in single-region views
- 10-bar decile chart works in "all/all" etc. (3/30), but renders as an empty
  chart shell (title + stat row, no bars) in all 27 single-region screenshots.
- Fix: either recompute the 10-decile breakdown per-region (10 bars from that
  region's LSOAs), or hide the chart for region-filtered views with an
  explanatory note ("decile breakdown shown for England only").
- Severity: significant.

### E3. Equity "Rural Accessibility Penalty" — non-responsive + missing for London
- Stat-row values (0.2773/0.124/0.1533/55.3% for "all", 0.2003/0.2189/0.0694/24.1%
  for E12000001) are **identical across all/urban/rural** for a given region —
  doesn't respond to the area-type filter at all.
- Section is **entirely absent** from all London (E12000007) screenshots.
- Likely shares the region-code-vs-name filter bug pattern from `acd8d35`
  (same family as A14/j2_bcr). Trace the rural-accessibility-penalty stats
  builder's region/urban_rural filter logic.
- Severity: significant.

### E4. Accessibility — London/rural drops 6 of 8 sections
- `accessibility__E12000007__rural.png`: page header shows "2 SECTIONS · 1
  CHARTS · 0 NARRATIVES" — only "Service Deserts" (KPIs) and "Coverage
  Prediction from Demographics" (bar chart) render; Route/Stop Density,
  Population within 400m, Equity of Coverage, Urban vs Rural Coverage Gap, and
  Investment to Reach National Average are all missing.
- Likely cause: London has very few/zero "rural" LSOAs by `urban_rural`
  classification, and the relevant stats builders return `{}`/null for
  near-empty filtered sets instead of a "no data for this filter" state.
- Fix: stats builders for the affected sections should return a populated
  "insufficient data" sentinel (not `{}`) so the frontend renders the section
  shell with an explanatory message, rather than omitting the section entirely.
- Severity: significant (this is a template/data-boundary contract issue, not
  just a chart-type one — likely needs a stats_builders fix, file under Part A
  if picked up: candidate **A17**).

### E5. Accessibility — invalid negative Gini for small rural subsets
- `lsoa_equity_metrics`-derived Gini-equivalent goes negative (-0.066, -0.9525,
  -0.1851) for E12000005/006/008/009 rural — Gini must be in [0,1].
- Likely a small-N artifact (very few LSOAs in some region/rural combos) feeding
  the same Gini formula used for the national 33,755-LSOA computation.
- Fix: add a minimum-LSOA-count guard (e.g., n < 30) — below threshold, suppress
  the Lorenz curve and show "insufficient data for this filter" instead of an
  invalid value. Candidate **A18** if picked up alongside A15 (same
  division-by-zero/small-N class of bug).
- Severity: significant.

### E6. d7 "Urban/Rural Gap" — heatmap is the wrong chart type even once data is fixed
- Currently renders as a single 1×9 row of cells (not a true 2D heatmap) —
  mostly uniform cream with one red outlier cell. A 1×N row doesn't
  communicate "gap" well regardless of whether `{worst_cell, best_cell,
  x_dimension, y_dimension, metric_name}` (A12b) is populated.
- Recommendation: replace with a **diverging horizontal bar chart** — one bar
  per region/group showing the urban-rural delta for the chosen metric, colored
  by sign (e.g., blue = rural higher, orange = urban higher). This communicates
  "gap" far more directly than a heatmap cell.
- Severity: moderate-significant — affects how A12b should be implemented (the
  schema fields like `worst_cell`/`best_cell` may need rethinking if the chart
  type changes from heatmap to diverging bar).

### E7. j2_bcr / bsa2_operator_concentration — need threshold-band gauges
- Both currently render as a bare bar + separate text label (e.g., "BCR 1.16"
  / "VFM BAND: Low"; "HHI 629 — Low concentration") with **no visual indication
  of where the value sits relative to standard thresholds**.
- j2_bcr: HM Treasury Green Book VfM bands — <1.0 poor, 1.0-1.5 low, 1.5-2.0
  medium, 2.0-4.0 high, >4.0 very high. Recommend a horizontal banded gauge with
  shaded zones and reference lines at BCR=1.0 (break-even) and BCR=2.0 (high
  VfM).
- bsa2_operator_concentration: standard HHI thresholds — <1500 low, 1500-2500
  moderate, >2500 high concentration. Same banded-gauge treatment. Also: verify
  axis units are consistent (some screenshots show HHI as small decimals
  ~0.1-0.6 — confirm whether this is HHI/10000 normalized, and label the axis
  accordingly).
- Severity: moderate-significant for both — these are the two sections most
  directly tied to a headline "is this good or bad" policy claim, and currently
  require reading a separate text label to find out.

### E8. bsa3_tier_distribution — stacked bar → 3 separate count bars
- Current: single horizontal stacked bar (3 segments: Tier 1/2/3 readiness).
  For regions where one tier dominates (e.g., London = 100% Tier 1, all 26
  LADs), renders as a single solid color block — visually indistinguishable
  from "no data loaded."
- Recommendation: replace with **3 separate bars** (one per tier, height/length
  = LAD count). Handles the all-one-tier case gracefully (other 2 bars simply
  show 0), and matches the "X LADs are Tier 1, Y are Tier 2..." narrative
  framing better than a proportion bar.
- Severity: moderate.

### E9. c7_network_topology — choropleth is the wrong chart type for "densest corridor"
- Even setting aside A11's schema mismatch, a choropleth (area-fill by LAD)
  doesn't represent "densest corridor" — a corridor is a connection between two
  places, not an area property.
- Recommendation: **ranked horizontal bar list of top corridors** (e.g.,
  "Manchester ↔ Salford: 340 trips/day") — simplest option, pairs naturally
  with existing `n_cross_la`/`pct_cross_la` KPIs. (Alternative considered and
  rejected as higher-effort: flow/desire-line map or node-link graph.)
- Affects how A11 should be implemented — the chart_dispatch builder for c7
  should target a ranked-list/bar shape, not `lad_cd/lad_nm/mean_trips_per_cap`
  choropleth columns.
- Severity: moderate (design input for A11's implementation).

### E10. c1/c2 distribution charts — currently blank; histogram recommended
- Both render as empty chart canvases above KPI stat cards (mean/median/etc.)
  across all 30 screenshots.
- Once A6's schema extension lands (`std/cv/iqr/p10/p90/n_outliers/skew_label`),
  recommend a **histogram** (continuous, right-skewed variables) optionally
  paired with a small box plot for outliers. Consider log-scale x-axis for c2
  (stops per route) if heavily right-skewed.
- Severity: moderate (design input for A6's implementation).

### E11. c6_route_archetypes — scatter overplotting + filter-invariance
- Dominant cluster renders as a dense overplotted red blob with no visible
  internal structure; smaller clusters are sparse.
- Chart appears visually identical across all 30 region/area filters — likely
  showing the national dataset regardless of filter (separate from the
  "Cluster -1: undefined" label bug in A10).
- Recommendations: (1) opacity/alpha blending or density underlay for the
  dominant cluster, (2) companion small-multiples bar chart of cluster sizes
  (n routes per cluster), (3) confirm whether this scatter should be
  filter-responsive (highlight selected region's points within the national
  scatter) or is intentionally national-only.
- Severity: moderate.

### E12. d6_transport_poverty cluster scatter — bar-chart fallback for small-N
- Once A12c's fix lands (real per-cluster/per-point data instead of a single
  bar), a scatter of LSOA clusters is the right primary chart for "all"/large
  regions. But for small rural-region filters where point counts may drop to a
  handful, a scatter of 5-10 points looks like noise.
- Recommendation: below a point-count threshold (e.g., <20 LSOAs), show a bar
  chart of cluster sizes (count of LSOAs per cluster) instead of/alongside the
  scatter.
- Severity: cosmetic-moderate (design input for A12c).

### E13. d8 ML feature importance — needs visual emphasis for top feature
- Horizontal bar chart of 5-8 SHAP importances is appropriate and works across
  all 30 filters — chart type itself is fine.
- Once A12c adds `top_importance`, recommend visually distinguishing the #1 bar
  (different color/highlight) or an adjacent KPI callout ("Top driver:
  nocar_pct — 8.47") rather than relying on bar length alone.
- Severity: cosmetic.

### E14. Scenarios page — confirms B1 plan + adds two refinements
- Confirms B1's diagnosis: ps1-ps4/g5 render as single full-width bars (one
  metric dominates the 0-5,000 axis, other two metrics' bars are
  zero-width/invisible). g5 (scenario comparison) has the SAME collapse — 4
  near-identical full-width bars, currently zero comparative value.
- **Refinement 1**: alongside the KPI tiles for ps1-ps4 (per B1), add a
  **before/after proportion bar** — population_affected vs total England
  population (56,490,056) — since both share the same unit (people) and "X% of
  England's population benefits" is the single most policy-relevant takeaway.
  This is the one place a bar chart still makes sense for ps1-ps4.
- **Refinement 2**: for ps5 (scenario comparison), recommend a **ranked table**
  (Scenario | Population affected | Cost £m/yr | CO2 t/yr | Cost/beneficiary)
  over small-multiples or normalized grouped bars — avoids stripping real units
  (normalizing to 0-100 conflicts with the figures-registry traceability rule).
  Small-multiples is an acceptable fallback if a table feels too plain, but
  table is preferred.
- **New finding (E14b)**: a future choropleth (population_affected by region,
  with a scenario-selector dropdown) becomes valuable ONLY once B2's
  region-aware recomputation is live — building it against today's
  national-constant data would show 9 identical regions. Treat as phase-2,
  after B2 lands.
- **New finding (E14c) — InsightEngine narratives entirely absent on scenarios
  page**: across all 30 screenshots, no narrative text renders anywhere on the
  scenarios page (Scenario Builder controls + KPI tiles + bar charts only). This
  is a content/wiring gap, not a chart-type issue — needs investigation as part
  of Part C's rebuild verification (check whether ps1-ps5/g5 narrative templates
  are wired in `intelligence/engine.py`'s section→template map). Candidate
  **A19**.
- Severity: significant (B1 confirmed + 2 refinements); E14c is significant
  separately (narratives missing entirely).

## Part E summary — new candidate items for Part A
- **A17**: accessibility stats builders return `{}` for near-empty
  region/urban_rural filters (e.g., London/rural) instead of an
  "insufficient data" sentinel — causes whole sections to vanish from the page
  (E4).
- **A18**: Gini/Lorenz computation needs a minimum-LSOA-count guard to avoid
  invalid negative values for small rural subsets (E5) — same class as A15.
- **A19**: scenarios page (ps1-ps5/g5) narratives appear completely unwired —
  confirm `intelligence/engine.py` section→template mapping (E14c).
- **E3** (Rural Accessibility Penalty non-responsive + missing for London) may
  also need a code-bug task akin to A14/A7 — investigate alongside those.

## Resolved decisions (all four originally-open items have concrete builds)

- **A5 (b4_route_frequency)**: build per-route trip frequency from
  `route_stop_sequences.parquet` (groupby route_id/trip_id) — top/bottom routes
  by trips/day. Real, distinct from b1.
- **A8 (c4_urban_rural_routes)**: build route urban/rural classification via
  stop→LSOA spatial join using existing `route_stop_sequences` coordinates +
  `lsoa_service_quality.urban_rural`. Covers all 13,640 routes.
- **A16 (f3_ethnic_access)**: NOT a drop — `master_lsoa_table` already has
  `eth_*`/`nonwhite_pct` columns from ts021. Build as a correlation section
  like d1-d5. The "no data" stub in current code is itself a bug.
- **A16b (f4_gender_accessibility)**: genuine drop — no sex/gender LSOA data
  ingested anywhere, would require new Census table (Phase 0 rescope).
- **B2 (scenario region filters)**: NOT hide-the-filter — recompute
  `population_affected` per region/urban_rural by filtering each scenario's
  target LSOA subset (imd_decile==10, evening_isolated, rural+elderly, etc.) by
  region/urban_rural and summing population. ps4 (LAD-level) is a partial
  exception — see B2 detail.

## Resolved scoping questions (pre-execution check, 2026-06-11)

- **Spatial join for A5/A8**: `src/aequitas/processing/spatial.py::assign_stops_to_lsoa(stops_df, lsoa_gdf)`
  is the existing, reusable, two-pass (sjoin within + sjoin_nearest 2km fallback)
  stop→LSOA join — 99.9993% match rate (Phase 0 audit). DO NOT write a new
  point-in-polygon join. A5/A8 implementations should call this function on
  `route_stop_sequences.parquet`'s `stop_lat`/`stop_lon`, then merge the
  resulting `lsoa_code` to `lsoa_service_quality.urban_rural` (and
  `master_lsoa_table.region` if needed).
- **LA-grain urban_rural for A1/A2**: confirmed absent (`lta_franchising_readiness.parquet`
  has no urban_rural column, 298 LAD rows, region+lad_cd/lad_nm only) — A1/A2 are
  region-only by design, see revised A1/A2 above.

## Execution order / dependencies

1. **A8 before A5** — A5's per-route urban/rural filtering reuses A8's
   `route_urban_rural` intermediate (route_id → urban/rural/mixed +
   primary_region). Build A8 first.
2. **A3+A7 as one task** — shared route→operator→region join /
   `market_concentration.py` helper; do not split across two subagents.
3. **A12 split into A12a/A12b/A12c** — independent builders/templates, can run
   in any order or in parallel (different files).
4. Most other items (A1/A2/A4/A6/A9/A10/A11/A13/A14/A15/A16/A16b, B1/B2) are
   independent and can be sequenced freely.

## Per-task standards (apply to every implementer subagent)

Per `.claude/rules/python-pipeline.md` and `.claude/rules/figures.md`:
- Type hints on every function, loguru logging, no bare `except`, docstrings on
  public functions, ≤50 lines/function, ≤250 lines/file.
- Any new numeric figure (e.g., a newly-computed correlation, HHI value, SHAP
  importance) must be added to `docs/figures-registry.md` as ✅ Confirmed with
  its source.
- Population denominator for any per-capita stat = 56,490,056 (never
  pipeline-filtered).
- No hardcoded narrative strings — narratives stay Jinja2 + evidence-gated.
