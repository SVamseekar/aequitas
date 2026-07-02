# Chart Data Wiring Design — Restoring `chart_data` for the 51-Section Precompute

Date: 2026-06-10
Status: design only — no code changes in this branch
Scope: fixes `tests/warehouse/test_chart_types.py::test_chart_type_variety`
(currently 0 distinct `chart_data->>'type'` values; needs >=6) by wiring
`src/aequitas/intelligence/chart_data_builder.py`'s 10 `build_*` functions
back into `precompute.py`'s `_dispatch`, reusing data already computed by the
new `stats_builders/*` modules wherever possible.

---

## 1. Architecture

### Decision: new file `src/aequitas/warehouse/chart_dispatch.py`

A single function:

```python
def build_chart_data(
    section_id: str,
    stats: dict,
    region: str,
    region_name: str,
    urban_rural: str,
    filtered: pd.DataFrame,
    region_df: pd.DataFrame,
    sources: "_Sources",
    lsoa_cds: pd.Series,
) -> dict:
    """Return chart_data dict for section_id, or {} if not chartable."""
```

Called from `precompute_all_sections` immediately after `_dispatch(...)`
returns `stats`, with the exact same arguments `_dispatch` already receives
(plus `stats` itself, since several charts are cheap re-derivations of values
already in `stats`, e.g. lorenz curve's `gini` matches `stats["gini"]`, and
shap_bar's `model_r2` matches `stats["r2"]`).

```python
stats = _dispatch(section_id=..., region=..., ..., lsoa_cds=lsoa_cds)
chart_data = build_chart_data(section_id=section_id, stats=stats, region=region,
                               region_name=region_name, urban_rural=urban_rural,
                               filtered=filtered, region_df=region_df,
                               sources=sources, lsoa_cds=lsoa_cds)
result = engine.generate(...)
results.append(SectionResult(..., chart_data=chart_data, ...))
```

### Why a new file, not inside `precompute.py` or inside each stats_builder

- **Not inside stats_builders/**: each stats_builder module owns one
  *template contract* (ranking.j2, correlation.j2, etc.) and is organised
  around `*_CONFIG` dicts keyed by section_id. Chart construction needs a
  parallel per-section dispatch, but its inputs partially overlap with (and
  partially diverge from) the stats inputs — e.g. `c5_length_vs_frequency`'s
  chart needs the *unfiltered* `routes` df with both `length_km` and
  `stop_count` columns (same as its stats), but `f2_disparity_ratio`'s chart
  needs `equity_df` grouped by decile (stats only returns the 2 extreme
  deciles' summary numbers, not the full per-decile series). Bolting chart
  logic onto each stats builder would duplicate `*_CONFIG` dicts and blur
  "stats builder = one template contract" with "chart builder = one chart
  type", which are different groupings (e.g. `horizontal_bar` is used by
  ranking-family, equity_decile, market_concentration, economic, BCR, carbon,
  scenario, and gap-to-target sections — 7 different stats builders, 1 chart
  builder).
- **Not inside `precompute.py`**: `precompute.py` is already large
  (483 lines) and Task 15's rewrite specifically split it into
  single-purpose modules. A `chart_dispatch.py` mirrors that pattern:
  `_dispatch` → stats, `build_chart_data` → chart_data, both orchestrated by
  `precompute_all_sections`.
- **Internal structure of `chart_dispatch.py`**: one private `_chart_<name>`
  helper per *chart-type family that needs custom logic* (not strictly one
  per section_id — e.g. all 7 ranking-family sections funnel through one
  `_chart_horizontal_bar_from_ranking(section_id, sources, region, region_name)`
  helper that re-derives `by_region`/`metric`/`unit` via
  `RANKING_CONFIG`, mirroring `build_ranking_stats`). Sections whose stats
  dict already contains everything needed (e.g. `b5_frequency_deprivation`'s
  scatter just needs `corr_df[[x_col, y_col]]` — same df passed to
  `build_correlation_stats`) get thin one-line wrappers.

### Data access pattern

`chart_dispatch.py` imports the same `*_CONFIG` dicts from
`stats_builders/ranking.py`, `stats_builders/correlation.py`, etc. — these
are already public module-level dicts, so no new exports needed. Two stats
builders need one **small additive change** (see §2 flags below):

- `stats_builders/ranking.py::build_ranking_stats` does not currently return
  the `by_region` Series — `chart_dispatch` recomputes it via the same
  `RANKING_CONFIG` + `national_df.groupby(group_col)[metric].mean()` one-liner
  used internally. This is a 3-line duplication, not a new data dependency
  (no new parquet/columns needed) — acceptable, but flagged in §5 as an
  alternative-design note.
- `stats_builders/equity.py` does not expose per-decile breakdowns for
  `f2_disparity_ratio`'s chart (horizontal_bar by IMD decile) — `chart_dispatch`
  computes `equity_df.groupby("imd_decile")["trips_per_capita"].mean()`
  directly from `equity_df` (already passed to `build_equity_stats`), no new
  source needed.

---

## 2. Per-Section Mapping Table

48 sections (51 minus 3 stubs: `f3_ethnic_access`, `f4_gender_accessibility`,
`c4_urban_rural_routes` — all return `{}` for both stats and chart_data,
unchanged).

Legend: **HB**=horizontal_bar, **SR**=scatter_regression, **LC**=lorenz_curve,
**SB**=stacked_bar, **GB**=grouped_bar, **BV**=box_violin, **CH**=choropleth,
**HM**=heatmap, **SHAP**=shap_bar, **SC**=scatter_clusters.

### Category A

| section_id | chart_type | builder fn | data source |
|---|---|---|---|
| `a1_route_density` | HB | `build_horizontal_bar` | `by_region` from `RANKING_CONFIG["a1_route_density"]` applied to `sources.ranking_df` (`groupby("primary_region")["route_count"].mean()`) → DataFrame `[label, value]`; `national_avg=by_region.mean()`; title from registry; x_label="Routes", y_label="Region". Only emit when `region=="all"` (best/worst ranking view) — for single-region scope `stats` is the `single_region` shape and a bar chart of 1 region adds no value; emit `{}` in that case (see §3 note on scope). |
| `a2_stop_density` | HB | `build_horizontal_bar` | Same pattern, `RANKING_CONFIG["a2_stop_density"]` → `groupby("region")["stops_per_1k"].mean()` on `sources.ranking_df`. x_label="Stops per 1,000 population". |
| `a3_walking_distance` | SB | `build_stacked_bar` | From `filtered` (policy_df, has `sfca_score_norm`, `region`): `by_region = filtered.groupby("region").apply(lambda g: pd.Series({"covered": (g.sfca_score_norm>0).mean()*100, "not_covered": (g.sfca_score_norm==0).mean()*100}))`. `categories=by_region.index.tolist()`, `series=[{"name":"Covered","values":...}, {"name":"Not covered","values":...}]`. Only when `region=="all"` (single-region `filtered` has 1 region → 1-bar chart, still valid but low value — emit anyway, harmless). **Note**: `_build_walking_distance` stats builder uses `policy_df` arg = `filtered`; reuse same `filtered`. |
| `a4_coverage_equity` | LC | `build_lorenz_curve` | `equity_df = _filter_by_lsoa(sources.equity_df, lsoa_cds)` (same df passed to `build_equity_stats`). `build_lorenz_curve(values=equity_df["trips_per_capita"], weights=equity_df["population"], title=...)`. Only when `stats` non-empty (i.e. equity_df has >=2 IMD deciles). |
| `a5_service_deserts` | CH | `build_choropleth` | **FLAG**: old version used `lta_df["sunday_desert_rate"]` per LAD — `lta_franchising_readiness.parquet` (`sources.lta_df`) — check it has `lad_cd`/`lad_nm`/`sunday_desert_rate` columns. If present: `lad_data=lta_df[["lad_cd","lad_nm"]]; lad_data["value"]=(lta_df["sunday_desert_rate"]*100).round(1)`, rename to `area_code`/`area_name`, `build_choropleth(data=lad_data, geography="lad", metric="pct_sunday_desert", colour_scale="RdYlGn")`. If column absent, emit `{}` (acceptable — choropleth also appears via `c7_network_topology`, see below). |
| `a6_urban_rural_gap` | GB | `build_grouped_bar` | From `region_df` (region-filtered, area-type-unfiltered policy_df, same as passed to `build_urban_rural_gap_stats`): group by `region` (only meaningful at `region=="all"`), compute mean `trips_per_capita` for Urban/Rural per region. `categories=sorted(region_df["region"].unique())`, `series=[{"name":"Urban","values":[...]}, {"name":"Rural","values":[...]}]`. For single-region scope, `region_df` has 1 region → 1-category chart; still valid, emit. |
| `a7_investment_gap` | HB | `build_horizontal_bar` | **FLAG — needs new data exposure.** `_build_gap_to_target` returns scalar stats (`n_below`, `pct_below`, `mean_gap`, `total_annual_cost_m`) computed from `filtered` vs `sources.national_median_trips_per_capita`, with no per-region breakdown. For `region=="all"`, compute `by_region = sources.policy_df.groupby("region").apply(lambda g: (national_median - g.loc[g.trips_per_capita<national_median,"trips_per_capita"]).sum()*500/1e6)` → DataFrame `[label="region", value="£m gap"]`. This is a **new computation in chart_dispatch.py**, not currently returned by any stats builder — acceptable since it only needs `sources.policy_df` + `sources.national_median_trips_per_capita`, both already loaded. x_label="Investment gap (£m/yr)", y_label="Region". |
| `a8_coverage_prediction` | SHAP | `build_shap_bar` | `build_shap_bar(features=sources.shap_df.rename(columns={"mean_abs_shap":"importance"}), title=..., model_r2=stats.get("r2"))`. Identical for all 30 combos (national model) — emit every time `stats` non-empty. |

### Category B

| section_id | chart_type | builder fn | data source |
|---|---|---|---|
| `b1_frequency` | HB | `build_horizontal_bar` | `RANKING_CONFIG["b1_frequency"]` → `sources.ranking_df.groupby("region")["service_quality_index"].mean()`. x_label="Service Quality Index". region=="all" only. |
| `b2_operating_hours` | GB | `build_grouped_bar` | From `service_quality_df = _filter_by_lsoa(sources.service_quality_df, lsoa_cds)` (same as passed to `build_misc_stats`), needs a `region` column to group by — **FLAG**: `lsoa_service_quality.parquet` after `_load_service_quality` rename has `lsoa_cd` but does it carry `region`? If not, join `service_quality_df` to `filtered[["lsoa_cd","region"]]` first (cheap merge, both already in scope). Then `by_region = joined.groupby("region").agg(first=("first_service_min","median"), last=("last_service_min","median"))`. `categories=by_region.index.tolist()`, `series=[{"name":"First service (min)","values":...}, {"name":"Last service (min)","values":...}]`. region=="all" only; else `{}`. |
| `b3_weekend_penalty` | GB | `build_grouped_bar` | Same join-to-region pattern as b2, using `total_weekday_departures`/`total_sunday_departures` means by region. `series=[{"name":"Weekday",...}, {"name":"Sunday",...}]`. region=="all" only. |
| `b4_route_frequency` | HB | `build_horizontal_bar` | `RANKING_CONFIG["b4_route_frequency"]` → `sources.ranking_df.groupby("region")["trips_per_capita"].mean()`. x_label="Trips per capita". region=="all" only. |
| `b5_frequency_deprivation` | SR | `build_scatter_regression` | `corr_df = _filter_by_lsoa(sources.correlation_df, lsoa_cds)` (same df passed to `build_correlation_stats`). `build_scatter_regression(df=corr_df, x_col="imd_score", y_col="service_quality_index", id_col="lsoa_cd", title=..., x_label="IMD Score", y_label="Service Quality Index")`. Emit whenever `stats` non-empty (n>=3 already validated by stats builder). |

### Category C

| section_id | chart_type | builder fn | data source |
|---|---|---|---|
| `c1_route_length` | BV | `build_box_violin` | `routes = sources.route_geometries_df`, filter by `primary_region==region_name` if `region != "all"`. **FLAG**: `build_box_violin` needs `groups: dict[str, pd.Series]` keyed by category label. Old code grouped by `routes["region"]` — but `route_geometries_df` uses `primary_region`, not `region`. For `region=="all"`: `groups = {r: g["length_km"].dropna() for r, g in routes.groupby("primary_region")}`. For single-region: `groups = {region_name: routes["length_km"].dropna()}` (1 group — still valid box_violin). `unit="km"`. |
| `c2_stops_per_route` | BV | `build_box_violin` | Same pattern, column `stop_count`, `unit="stops"`. |
| `c3_operator_hhi` | HB | `build_horizontal_bar` | **FLAG — region=="all" only, needs per-region HHI.** `_build_from_routes` (market_concentration.py) computes one scalar HHI for the active scope from `routes_df["agency_name"].value_counts()`. For the chart at `region=="all"`, compute per-region: `by_region = sources.route_geometries_df.groupby("primary_region")["agency_name"].apply(lambda s: (s.value_counts(normalize=True)*100).pow(2).sum())` → DataFrame `[label, value]`. x_label="HHI", y_label="Region". For single-region scope emit `{}` (single HHI value isn't a useful bar chart; stats already shows it via market_concentration.j2). |
| `c4_urban_rural_routes` | GB | — | STUB — `{}` always. |
| `c5_length_vs_frequency` | SR | `build_scatter_regression` | Same `routes` df as `build_correlation_stats` (national, unfiltered — `sources.route_geometries_df`, optionally region-filtered exactly as `_dispatch` does for stats). `build_scatter_regression(df=routes, x_col="length_km", y_col="stop_count", id_col=<route id col, e.g. "route_id" if present else routes.columns[0]>, x_label="Route Length (km)", y_label="Stops per Route (frequency proxy)")`. **FLAG**: confirm `route_geometries.parquet` has a `route_id`-like column for `id_col`; fall back to `routes.index.astype(str)` if not. |
| `c6_route_archetypes` | SC | `build_scatter_clusters` | `cluster_df = sources.route_clusters_df` (region-filtered by `primary_region` if `region != "all"`, same as `_dispatch`). **FLAG**: `build_scatter_clusters` needs `data: pd.DataFrame` with columns `x, y, cluster, id` and `cluster_labels: dict[int, str]`. `route_clusters.parquet` has `cluster`, `length_km`, `stop_count`, `cross_la_int` (per `ml_clusters.py`) — pick 2 numeric cols for x/y, e.g. `x="length_km", y="stop_count"`. `cluster_labels` derived from `stats["clusters"]` (already has `id`+`description` per cluster from `build_ml_clusters_stats`) — `{c["id"]: c["description"] for c in stats["clusters"]}` after excluding noise (`cluster==-1`, already filtered in stats). `id_col`: route id column or fallback to index. |
| `c7_network_topology` | CH | `build_choropleth` | `routes_df = sources.route_geometries_df` (filtered by `primary_region` if region != "all", as `_build_network_topology` does). **FLAG**: old code used `lta_df[["lad_cd","lad_nm","mean_trips_per_cap"]]` — confirm `lta_franchising_readiness.parquet` has `mean_trips_per_cap`; if so `build_choropleth(data=lad_data.rename(columns={"lad_cd":"area_code","lad_nm":"area_name","mean_trips_per_cap":"value"}), geography="lad", metric="cross_la_route_density")`. If `mean_trips_per_cap` absent, fall back to per-LAD `cross_la` route counts if `lad_cd` exists on `routes_df`, else emit `{}`. |

### Category D

| section_id | chart_type | builder fn | data source |
|---|---|---|---|
| `d1_coverage_deprivation` | SR | `build_scatter_regression` | `corr_df` (same as stats), `x_col="imd_score", y_col="trips_per_capita"`, labels from `CORRELATION_CONFIG`. |
| `d2_coverage_unemployment` | SR | `build_scatter_regression` | `x_col="unemployment_rate", y_col="trips_per_capita"`. |
| `d3_coverage_car` | SR | `build_scatter_regression` | `x_col="nocar_pct", y_col="trips_per_capita"`. |
| `d4_coverage_elderly` | SR | `build_scatter_regression` | `x_col="elderly_pct", y_col="trips_per_capita"`. |
| `d5_coverage_income` | SR | `build_scatter_regression` | `x_col="income_score", y_col="trips_per_capita"`. |
| `d6_transport_poverty` | SC | `build_scatter_clusters` | `cluster_df = _filter_by_lsoa(sources.lsoa_clusters_df, lsoa_cds)` (same as stats). **FLAG**: `build_ml_clusters_stats` for d6 uses `hdbscan_archetype` (string labels), but `build_scatter_clusters` needs integer `cluster` ids + `x`/`y` numeric columns. Check `lsoa_clusters_hdbscan.parquet` columns: does it have a numeric `cluster` id alongside `hdbscan_archetype`, and 2 numeric features (e.g. PCA components `pc1`/`pc2`, or reuse `imd_score`/`trips_per_capita`)? If a numeric `cluster` column exists, build `cluster_labels = {row.cluster: row.hdbscan_archetype for distinct rows}` (excluding noise -1) and pick 2 numeric cols for x/y. If no numeric cluster id exists, **emit `{}`** for this section (do not block on inventing IDs) — flagged as open question in §5. |
| `d7_deprivation_urban_rural` | HM | `build_heatmap` | `policy_df = filtered` region-filtered, area-type-unfiltered → actually old code used `region_df`-equivalent (`_filter_data(policy, region, "all")`); use `region_df` here for consistency with the urban/rural-always-both-sides pattern. `clean = region_df.dropna(subset=["urban_rural","imd_decile","trips_per_capita"])`. `pivot = clean.groupby(["urban_rural","imd_decile"])["trips_per_capita"].mean().unstack(fill_value=0)`. `x_labels=[str(d) for d in sorted(pivot.columns)]`, `y_labels=list(pivot.index)`, `values=pivot.values.tolist()`. Reuse `stats["worst_cell"]`/`stats["best_cell"]` already computed by `_build_deprivation_heatmap` — no need to recompute extremes for the chart, just the grid. |
| `d8_feature_importance` | SHAP | `build_shap_bar` | Identical to `a8_coverage_prediction` — `build_shap_bar(features=sources.shap_df.rename(...), title=..., model_r2=stats.get("r2"))`. |

### Category F

| section_id | chart_type | builder fn | data source |
|---|---|---|---|
| `f1_gini` | LC | `build_lorenz_curve` | Identical pattern to `a4_coverage_equity` — `equity_df = _filter_by_lsoa(sources.equity_df, lsoa_cds)`, `build_lorenz_curve(values=equity_df["trips_per_capita"], weights=equity_df["population"], title=...)`. |
| `f2_disparity_ratio` | HB | `build_horizontal_bar` | `equity_df` as above. `by_decile = equity_df.groupby("imd_decile")["trips_per_capita"].mean().reset_index()`; rename to `[label, value]`, `label = "Decile " + str(imd_decile)`. x_label="Trips per capita", y_label="IMD Decile". Emit when `stats` non-empty (>=2 deciles validated by stats builder). |
| `f3_ethnic_access` | GB | — | STUB — `{}` always. |
| `f4_gender_accessibility` | HB | — | STUB — `{}` always. |
| `f5_rural_penalty` | GB | `build_grouped_bar` | Same pattern as `a6_urban_rural_gap` but metric=`service_quality_index` (per `_METRIC_BY_SECTION["f5_rural_penalty"]`), from `region_df`. |
| `f6_equitable_regions` | HB | `build_horizontal_bar` | `RANKING_CONFIG["f6_equitable_regions"]` → `sources.ranking_df.groupby("region")["vulnerability_index"].mean()`. **Note**: `higher_is_better=False` for this metric — `build_horizontal_bar` always sorts descending by value; that's fine, the bar chart shows raw values regardless of "better" direction (only `stats["best"/"worst"]` labels need the direction logic, already handled in `build_ranking_stats`). x_label="Vulnerability index". region=="all" only. |

### Category G

| section_id | chart_type | builder fn | data source |
|---|---|---|---|
| `g1_route_clusters` | SC | `build_scatter_clusters` | Same as `c6_route_archetypes` — `sources.route_clusters_df`, region-filtered by `primary_region` (per `_dispatch`'s existing pattern for `_ML_CLUSTER_SECTIONS`). |
| `g2_anomalies` | SR | `build_scatter_regression` | `anomalies_df = _filter_by_lsoa(sources.anomalies_df, lsoa_cds)` (same as stats). **FLAG**: confirm `anomalies.parquet` has `service_quality_index`, `imd_score`, `lsoa_cd` columns (old code checked these). `build_scatter_regression(df=anomalies_df, x_col="imd_score", y_col="service_quality_index", id_col="lsoa_cd", x_label="IMD Score", y_label="Service Quality Index")`. If columns absent, `{}`. |
| `g3_coverage_model` | SR | `build_scatter_regression` | **FLAG — chart_type mismatch with available data.** Registry declares `scatter_regression` for g3, but `build_ml_prediction_stats` (the actual stats builder for g3) returns only `{r2, top_feature, top_importance, n_features}` — there is no per-LSOA predicted-vs-actual dataframe anywhere in `_Sources` (no `coverage_predictions.parquet`). A true scatter_regression of "predicted vs actual coverage" is **not buildable from current sources**. Two options: (a) emit `{}` for g3 (acceptable — g3 still gets a narrative; chart variety is achieved via other sections), or (b) substitute a `shap_bar` (reusing the same data as a8/d8/g4) even though the registry says `scatter_regression` — **not recommended**, since chart_data.type would then disagree with `SECTION_REGISTRY[g3].chart_type`, which the frontend may use to pick a renderer. **Recommendation: emit `{}` for g3_coverage_model** and note the registry/data mismatch as a follow-up (does not block the >=6-types requirement, see §3). |
| `g4_shap` | SHAP | `build_shap_bar` | Identical to a8/d8 — `build_shap_bar(features=sources.shap_df.rename(...), model_r2=stats.get("r2"))`. |
| `g5_scenario_model` | GB | `build_grouped_bar` | **FLAG — chart_type mismatch.** Registry says `grouped_bar` for g5, but `build_policy_scenario_stats` returns a single `{"scenario": {...}}` dict (one scenario, "A" / freq restoration) — same shape as ps1-ps4, which use `horizontal_bar` per the old code (`_build_scenario`). For g5, build a `horizontal_bar` (NOT grouped_bar) from the single scenario's 3 metrics, exactly like ps1-ps4 below — **but registry says grouped_bar**. Recommendation: implement per old pattern (`build_horizontal_bar` with rows `["Population affected","Annual cost (£m)","CO₂ saved (t/yr)"]`) and accept the type mismatch vs registry for g5 only (flagged for a future registry fix — out of scope for this task), OR emit `{}` for g5. **Recommendation: emit `{}` for g5_scenario_model** to keep `chart_data.type` consistent with `SECTION_REGISTRY` (frontend trust), since ps1-ps4 already cover the horizontal_bar-from-scenario case and g5 is redundant (same row "A"). |

### Category J

| section_id | chart_type | builder fn | data source |
|---|---|---|---|
| `j1_economic_value` | HB | `build_horizontal_bar` | **region=="all" only.** `appraisal_df = _filter_by_lsoa(sources.appraisal_df, lsoa_cds)` (same as stats, but for region=="all" this is the full national appraisal_df which retains `region` column post-join). `by_region = appraisal_df.groupby("region")["annual_time_benefit"].sum().reset_index()`; rename `[label, value]`, `value = (value/1e6).round(1)`. x_label="Annual benefit (£m)", y_label="Region". Single-region scope: `{}` (1-bar chart not useful; stats already shown). |
| `j2_bcr` | HB | `build_horizontal_bar` | **FLAG**: `_build_bcr` computes one scalar `bcr = pv_benefits.sum()/pv_costs.sum()`. For region=="all" chart, compute per-region: `by_region = appraisal_df.groupby("region").apply(lambda g: g["pv_benefits"].sum()/g["pv_costs"].sum() if g["pv_costs"].sum() else 0).reset_index()`, rename `[label, value]`, round 2dp. x_label="BCR", y_label="Region". Single-region: `{}`. |
| `j3_carbon` | HB | `build_horizontal_bar` | **FLAG**: `_build_carbon` sums `modal_shift_co2_net_saving_kg` over `appraisal_df`. For region=="all" chart: `by_region = appraisal_df.groupby("region")["modal_shift_co2_net_saving_kg"].sum().div(1000).round(1).reset_index()`, rename `[label, value]`. x_label="Net CO₂ saved (t/yr)", y_label="Region". Single-region: `{}`. |
| `j4_investment_priority` | HB | `build_horizontal_bar` | `RANKING_CONFIG["j4_investment_priority"]` → `sources.ranking_df.groupby("region")["investment_gap_annual_cost"].mean()`. x_label="£/year investment gap". region=="all" only. |

### Category BSA

| section_id | chart_type | builder fn | data source |
|---|---|---|---|
| `bsa1_franchising_readiness` | HB | `build_horizontal_bar` | `RANKING_CONFIG["bsa1_franchising_readiness"]` → `sources.ranking_df.groupby("region")["franchising_readiness"].mean()`. x_label="Readiness score (0-100)". region=="all" only. **Note**: old code ranked by individual LAD (`lta_df`, top 20); new `ranking_df` aggregates to region — use region-level bars (7 bars, England-wide) for consistency with other ranking sections rather than reintroducing LAD-level data. |
| `bsa2_operator_concentration` | HB | `build_horizontal_bar` | `lta = sources.lta_df` (region-filtered to `region_name` if `region != "all"`, else full). **region=="all" only**: `by_region = lta.groupby("region")["region_hhi"].mean().reset_index()`, rename `[label, value]`. x_label="HHI", y_label="Region". Single-region: `{}`. |
| `bsa3_tier_distribution` | SB | `build_stacked_bar` | `lta_df` filtered as in `_dispatch` for `_MISC_SECTIONS`. **FLAG**: needs `region` column on `lta_df` and a numeric tier extraction from `readiness_tier` (regex `r"Tier (\d)"`, as old code did). For region=="all": `by_region = lta_with_tier.groupby("region")["_tier_num"].value_counts().unstack(fill_value=0)`, `categories=by_region.index.tolist()`, 3 series for tiers 1/2/3. Single-region: `{}` (1-category stacked bar not useful — stats already shows tier counts). |

### Category PS

| section_id | chart_type | builder fn | data source |
|---|---|---|---|
| `ps1_freq_restoration` | HB | `build_horizontal_bar` | `stats["scenario"]` (already computed by `build_policy_scenario_stats`, row A). `bar_data = pd.DataFrame({"label": ["Population affected","Annual cost (£m)","CO₂ saved (t/yr)"], "value": [scenario["population_affected"]/1e6, scenario["estimated_annual_cost_m"], scenario["co2_saving_t_yr"]]})`. `build_horizontal_bar(data=bar_data, x_label="Value", y_label="Metric")`. |
| `ps2_evening_extension` | HB | `build_horizontal_bar` | Same pattern, `stats["scenario"]` = row B. |
| `ps3_drt_rural` | HB | `build_horizontal_bar` | Same pattern, row C. |
| `ps4_franchise` | HB | `build_horizontal_bar` | Same pattern, row D. |
| `ps5_scenario_comparison` | GB | `build_grouped_bar` | `stats["scenarios"]` (list of 4 dicts with `name`, `population`, `cost_m`, `co2_t` — already computed by `_build_comparison`). `categories=[s["name"] for s in stats["scenarios"]]`, `series=[{"name":"Population (millions)","values":[s["population"]/1e6 ...]}, {"name":"Cost (£m/yr)","values":[s["cost_m"]...]}, {"name":"CO₂ saved (t/yr)","values":[s["co2_t"]...]}]`. |

---

## 3. Chart Type Coverage Check

All 10 `chart_data_builder` functions are used by at least one section
(per the table above), **except** where flagged `{}` (g3, g5):

| chart_data_builder fn | sections using it (chart_type producing non-{} output) |
|---|---|
| `build_horizontal_bar` | a1, a2, a7, a8(no—shap, see below)... → a1, a2, a7, b1, b4, c3, f2, f6, j1, j2, j3, j4, bsa1, bsa2, ps1-4 |
| `build_scatter_regression` | b5, c5, d1-d5, g2 |
| `build_lorenz_curve` | a4, f1 |
| `build_stacked_bar` | a3, bsa3 |
| `build_grouped_bar` | a6, b2, b3, f5, ps5 |
| `build_box_violin` | c1, c2 |
| `build_choropleth` | a5 (conditional on lta columns), c7 (conditional) |
| `build_heatmap` | d7 |
| `build_shap_bar` | a8, d8, g4 |
| `build_scatter_clusters` | c6, d6 (conditional), g1 |

**>=6 distinct types confirmed**: horizontal_bar, scatter_regression,
lorenz_curve, stacked_bar, grouped_bar, box_violin, heatmap, shap_bar,
scatter_clusters — 9 of 10 are wired with concrete, non-conditional data
paths (choropleth is the only one with a hard "conditional on column
existing" caveat for both its sections).

**Scope-condition risk** (the test requires distinct types across the full
1530-row table, not per-row): several mappings above are marked
"region=='all' only" (a1, a2, b1, b2, b3, b4, bsa1, bsa2, bsa3, j1, j2, j3,
j4, c3, f6, a7's per-region variant). Since `region=="all"` is one of the 10
region values × 3 area types = **3 of the 30 combos** (region="all" with
urban_rural in {all, urban, rural}), each of these section_ids still
contributes **3 non-empty chart_data rows out of 51** (3 combos × 1 section)
— more than enough for the >=6-distinct-types floor, since:

- `box_violin` (c1, c2): emitted for **all 30 combos** (region-filtered or
  not, always >=1 group).
- `lorenz_curve` (a4, f1): emitted whenever the equity_df slice has >=2 IMD
  deciles — true for essentially all 30 combos (only fails for tiny
  single-decile slices, unlikely given 33,755 LSOAs / 30 combos).
- `scatter_regression` (b5, d1-d5): emitted for all 30 combos (n>=3 always
  true at LSOA granularity).
- `scatter_clusters` (c6, g1): emitted for all 30 combos (route_clusters_df
  is national, region-filtered subset still has clusters).
- `shap_bar` (a8, d8, g4): emitted for all 30 combos (national model,
  identical everywhere).
- `grouped_bar` (a6, f5): emitted for all 30 combos via
  `build_urban_rural_gap_stats`'s always-non-empty contract (§4.2 invariant).
- `heatmap` (d7): emitted for all 30 combos where `region_df` has both
  urban_rural categories present (true at every region scope).
- `horizontal_bar`: emitted for the 3 `region=="all"` combos via a1/a2/b1/etc,
  AND for all 30 combos via ps1-ps4 (scenarios are England-wide, not
  region-scoped) and f2_disparity_ratio (per-combo decile breakdown).
- `stacked_bar`: a3 (region=="all" only, 3 combos) + bsa3 (region=="all"
  only, 3 combos) — **only 3 of 1530 rows**. This is the thinnest type. Still
  satisfies "at least one row has type=stacked_bar" for the test, but is
  worth noting as fragile — if `a3`'s `lta_df` lookup or `bsa3`'s region
  column turns out missing (see flags), stacked_bar could drop to 0. **Action
  for implementer**: verify at least ONE of {a3, bsa3} produces a non-empty
  stacked_bar before considering Task 2/3 complete; if both fail, consider
  adding a region-level stacked_bar fallback (e.g. urban/rural population
  split per region from `policy_df`) as a backstop.
- `choropleth`: a5 and c7, both conditional on `lta_df`/`route_geometries_df`
  columns existing — **verify column existence early** (Task 1, see §4); if
  neither has the needed columns, choropleth would be 0/1530 and the test
  would still pass at >=6 (we have 8-9 other types) but choropleth coverage
  would be a documented gap.

**Conclusion**: even with the most conservative assumptions (g3, g5 → `{}`,
choropleth → `{}` if columns missing, a3/bsa3 stacked_bar uncertain), we have
**8 guaranteed types** (horizontal_bar via ps1-4/f2, scatter_regression,
lorenz_curve, grouped_bar, box_violin, heatmap, shap_bar, scatter_clusters) —
comfortably >=6. Stacked_bar and choropleth are bonus/best-effort.

---

## 4. Proposed Task Breakdown

### Task 1 — `chart_dispatch.py` skeleton + ranking/correlation/equity/cluster/shap families (guaranteed-coverage types)

Build `src/aequitas/warehouse/chart_dispatch.py` with `build_chart_data(...)`
dispatcher (mirroring `_dispatch`'s if/elif structure, keyed by the same
`_RANKING_SECTIONS` / `_CORRELATION_SECTIONS` / etc. sets imported from
`precompute.py`, or re-declared locally — implementer's choice, prefer
import to avoid drift). Implement:

- **scatter_regression**: `b5_frequency_deprivation`, `c5_length_vs_frequency`,
  `d1_coverage_deprivation`, `d2_coverage_unemployment`, `d3_coverage_car`,
  `d4_coverage_elderly`, `d5_coverage_income`, `g2_anomalies`
- **lorenz_curve**: `f1_gini`, `a4_coverage_equity`
- **shap_bar**: `a8_coverage_prediction`, `d8_feature_importance`, `g4_shap`
- **scatter_clusters**: `c6_route_archetypes`, `g1_route_clusters`,
  `d6_transport_poverty` (investigate numeric cluster-id availability per §2
  flag; emit `{}` if not feasible)
- **box_violin**: `c1_route_length`, `c2_stops_per_route`
- **heatmap**: `d7_deprivation_urban_rural`

Unit tests: for each section_id above, call `build_chart_data` with a small
synthetic `_Sources`/dataframes fixture and assert `chart_data["type"]`
matches `SECTION_REGISTRY[section_id].chart_type` and required keys are
present (e.g. `data`, `curve_points`, `clusters`, `groups`, `values`).

This task alone produces 6 distinct chart types — sufficient to pass
`test_chart_type_variety` even before Tasks 2/3, but Tasks 2/3 are needed for
full 51-section coverage and to wire into `precompute.py`.

### Task 2 — horizontal_bar / grouped_bar / stacked_bar / choropleth families

Implement remaining sections in `chart_dispatch.py`:

- **horizontal_bar (ranking-derived, region=="all" only)**: `a1_route_density`,
  `a2_stop_density`, `b1_frequency`, `b4_route_frequency`,
  `f6_equitable_regions`, `j4_investment_priority`,
  `bsa1_franchising_readiness` — via a shared
  `_chart_horizontal_bar_from_ranking(section_id, sources, region, region_name)`
  helper using `RANKING_CONFIG`.
- **horizontal_bar (other)**: `a7_investment_gap` (new per-region gap
  computation, §2 flag), `c3_operator_hhi` (new per-region HHI, §2 flag),
  `f2_disparity_ratio` (per-decile from equity_df), `j1_economic_value`,
  `j2_bcr`, `j3_carbon` (all three: per-region from `appraisal_df`, §2 flags),
  `bsa2_operator_concentration`, `ps1_freq_restoration`,
  `ps2_evening_extension`, `ps3_drt_rural`, `ps4_franchise` (all 4 from
  `stats["scenario"]`).
- **grouped_bar**: `a6_urban_rural_gap`, `f5_rural_penalty` (from
  `region_df`), `ps5_scenario_comparison` (from `stats["scenarios"]`),
  `b2_operating_hours`, `b3_weekend_penalty` (region join + groupby, §2 flags
  — investigate `lsoa_service_quality.parquet` region availability first).
- **stacked_bar**: `a3_walking_distance`, `bsa3_tier_distribution` (§2/§3
  flags — verify at least one produces non-empty output).
- **choropleth**: `a5_service_deserts`, `c7_network_topology` (§2 flags —
  verify `lta_franchising_readiness.parquet` / `route_geometries.parquet`
  column availability FIRST; if neither viable, document as known gap and
  emit `{}` for both — does not block the >=6 types requirement per §3).
- **g3_coverage_model, g5_scenario_model**: emit `{}` per §2 recommendation
  (registry/data mismatch — document as follow-up, do not attempt a
  workaround that produces a `chart_data.type` disagreeing with
  `SECTION_REGISTRY`).

Unit tests per section as in Task 1.

### Task 3 — Wire into `precompute.py` + integration test

- Add `chart_data = build_chart_data(...)` call in
  `precompute_all_sections`'s loop (replacing the hardcoded `chart_data={}`),
  passing `stats`, `region`, `region_name`, `urban_rural`, `filtered`,
  `region_df`, `sources`, `lsoa_cds` — same arguments already available at
  that point.
- Run a full `precompute_all_sections` (or a representative subset across
  multiple regions/area-types) and assert:
  - `tests/warehouse/test_chart_types.py::test_chart_type_variety` passes
    (>=6 distinct `chart_data->>'type'` values across `section_results`).
  - No section_id raises an exception (wrap `build_chart_data` calls in a
    try/except + loguru warning per section, OR ensure every helper has
    defensive empty-df/missing-column guards matching the corresponding
    stats builder's guards — prefer the latter for consistency, but a
    top-level try/except in `precompute_all_sections` as a safety net is
    reasonable given 1530 calls).
  - Spot-check 2-3 sections' `chart_data` payloads against expected shapes
    (e.g. `f1_gini`'s `chart_data["gini"]` ≈ `stats["gini"]`; `c6`'s
    `chart_data["clusters"]` ids match `stats["clusters"]` ids).
- Run the full warehouse rebuild (whatever CLI/script Task 15 used) and
  re-verify row counts (1530) and `chart_data != '{}'` for the sections
  expected to be non-empty per §2/§3 (everything except the 3 stubs + g3 + g5
  + possibly a5/c7/d6 if data unavailable).

---

## 5. Risks / Open Questions

1. **`d6_transport_poverty` scatter_clusters**: `lsoa_clusters_hdbscan.parquet`
   may only have string `hdbscan_archetype` labels, not a numeric `cluster`
   id + 2 numeric feature columns required by `build_scatter_clusters`'s
   `data: pd.DataFrame[x,y,cluster,id]` contract. **Needs inspection of the
   actual parquet schema** before Task 1 starts — if numeric IDs/features are
   absent, d6 emits `{}` (acceptable, c6/g1 already cover scatter_clusters).

2. **`g3_coverage_model` registry/data mismatch**: registry says
   `scatter_regression`, but no per-LSOA predicted-vs-actual dataframe exists
   in `_Sources`. Recommend `{}` + a follow-up note to either (a) add a
   `coverage_predictions.parquet` with per-LSOA actual/predicted values to a
   future analytics-stage pass, or (b) change the registry's `chart_type` for
   g3 to `shap_bar` (reusing a8/d8/g4's data) in a separate, explicit registry
   change — out of scope here.

3. **`g5_scenario_model` registry/data mismatch**: registry says
   `grouped_bar`, but stats shape (`{"scenario": {...}}`, single row) matches
   ps1-ps4's `horizontal_bar` pattern, not ps5's `grouped_bar` (`{"scenarios":
   [...]}`). Recommend `{}` for g5 — same rationale as g3.

4. **`a5_service_deserts` / `c7_network_topology` choropleth columns**: both
   depend on `lta_franchising_readiness.parquet` having `lad_cd`, `lad_nm`,
   and either `sunday_desert_rate` (a5) or `mean_trips_per_cap` (c7). The new
   `_Sources.lta_df` is loaded via `_read_parquet_or_empty` with no column
   contract documented in `precompute.py`. **First action of Task 2**:
   `pd.read_parquet(audit/"lta_franchising_readiness.parquet").columns` — if
   these columns are absent, choropleth becomes 0/1530 (acceptable per §3 but
   should be documented as a known gap rather than silently producing `{}`
   forever).

5. **`b2_operating_hours` / `b3_weekend_penalty` region column on
   `service_quality_df`**: `_load_service_quality` only renames `LSOA21CD` →
   `lsoa_cd`; unclear if `region` is present. If not, a merge with
   `filtered[["lsoa_cd","region"]]` is needed inside `chart_dispatch.py` — a
   small extra join, not a new data source, but adds a step not present in
   any stats builder today. Verify column presence before implementing.

6. **`a7_investment_gap`, `c3_operator_hhi`, `j1/j2/j3` per-region
   horizontal_bar charts** all require a NEW `groupby("region")` aggregation
   over `sources.policy_df` / `sources.route_geometries_df` /
   `sources.appraisal_df` that no existing stats builder performs (the stats
   builders compute one scalar for the active scope). These are
   straightforward pandas one-liners using data already in `_Sources`, but
   they are genuinely new code (not reuse) — flagged so implementers don't
   spend time searching for an existing helper that doesn't exist.

7. **`build_ranking_stats` does not return `by_region`**: chart_dispatch.py
   will recompute `by_region = national_df.groupby(group_col)[metric].mean().dropna()`
   for the 7 ranking sections + bsa1 + bsa2 + j1-j4 + c3 (12 sections total
   use a "groupby region" pattern). Consider, as a follow-up refactor (NOT
   part of this task), having `build_ranking_stats` optionally return
   `by_region` in its dict (e.g. under a private `_by_region` key stripped
   before storage) to avoid the duplication — but this would change the
   `stats` dict shape stored in the warehouse, which is out of scope and
   risky for this task. Recommend leaving the small duplication as-is.

8. **Performance**: `build_chart_data` is called 1530 times (51 sections × 30
   combos). Several charts (scatter_regression with `max_points=2000`,
   scatter_clusters) sample large LSOA-level dataframes — already bounded by
   `max_points` in `chart_data_builder.py`, so no new performance risk beyond
   what the old `_build_section` already did at this same scale.
