# Precompute 51-Section Expansion — Design

> Fixes the root-cause issue identified in `ISSUES.md` §2.1: `precompute.py` only
> populates 3 of 51 registered analytical sections, leaving 48 sections empty
> across the warehouse. This cascades into broken overview stats (§5), a
> low-quality FAISS/RAG index (§6), and 18 dead filter combinations (§4.1).

## Problem

`SECTION_REGISTRY` in `section_registry.py` defines 51 section IDs across 8
categories (A, B, C, D, F, G, J, BSA, PS). `precompute.py` still iterates over 5
old-style IDs (`coverage_density`, `equity`, `correlation`, `gap_to_target`,
`policy_scenario`) and `_build_stats` only has real branches for 3 of them.
The other 48 sections produce `stats = {}`, which `InsightEngine` correctly
suppresses — but leaves 48 empty shells in the warehouse, an all-zero overview
page, and a FAISS index built almost entirely from empty narratives.

Additionally, `precompute.py` skips 18 of 30 filter combinations
(single-region + urban/rural) as a "performance optimisation" (§4.1), and three
existing branches have correctness bugs: equity ignores regional breakdowns
(§2.3), `gap_to_target` uses a filtered (moving) median instead of the national
median (§2.5/§8.5), and `coverage_density` produces nothing for single-region
views because it requires `len(by_region) > 1` (§2.4/§8.1).

## Goals

1. Every one of the 51 registered sections produces real `stats`/`narrative`
   for every one of the 30 filter combinations where data permits.
2. Fix the four correctness bugs above (§2.3, §2.4, §2.5, §8.1) as part of the
   rewrite — they live in the same code being replaced.
3. Precompute all 30 combinations (remove the 18-combo skip), since the
   underlying data supports it and skipping creates dead UI states (§4.1).
4. Fix urban-rural comparison sections so they never compute "the other side"
   from a filtered-to-zero subset (§4.2).
5. Cleanly stub the 3 sections that cannot be completed without separate
   analytics-stage work (§8.2–§8.4): `f3_ethnic_access`, `f4_gender_accessibility`,
   `c4_urban_rural_routes`.
6. Update `HEADLINE_SECTIONS` (§5) to reference IDs that now exist.

## Non-Goals

- Implementing the `ts021` ethnicity join, the gender-disaggregated data source
  (which does not exist), or the route-geometry × urban/rural classification
  join. These are analytics-stage data engineering tasks, not precompute wiring.
  The 3 affected sections are stubbed with a status comment for a future pass.
- Rebuilding the FAISS index (§6) — that is a follow-on step run after this
  lands (`aequitas run --stage rag_index`), not part of this design.
- Frontend changes (§4.1 dropdown graying, §9.x). Out of scope.

## Architecture

### 1. Stats builder modules (new package: `warehouse/stats_builders/`)

`_build_stats` currently lives as a single function in `precompute.py`. Growing
it to cover 48 more sections in one function would violate the 50-line
function / 250-line file limits and make the contracts hard to test in
isolation. Instead, sections are grouped by **template contract** — the shape
of stats dict their Jinja2 template expects — and each contract family gets its
own small module with one function per section:

| Module | Sections | Template contract |
|---|---|---|
| `ranking.py` | a1, a2, b1, b4, f6, j4, bsa1 | `{best, worst, national_avg, unit}` (or single-region shape — see §3) |
| `correlation.py` | b5, c5, d1–d5 | `{r, p_value, n, n_observations, x_label, y_label, strength, direction}` |
| `ml_clusters.py` | c6, d6, g1 | `{n_clusters, entity_type, clusters: [{id, n, pct, description}]}` |
| `ml_prediction.py` | a8, d8, g3, g4 | `{r2, top_feature, top_importance, n_features}` |
| `market_concentration.py` | c3, bsa2 | `{hhi, region_name, top_operator, top_operator_share}` |
| `urban_rural_gap.py` | a6, c4 (stub), f5 | `{urban_value, rural_value, gap_pct, n_urban, n_rural, unit}` |
| `policy_scenario.py` | ps1–ps4, g5, ps5 | `{scenario: {...}}` or `{scenarios: [...], best_bcr_scenario}` |
| `economic.py` | j1, j2, j3 | economic_value / bcr_analysis / carbon_reduction shapes |
| `equity.py` | f1, a4, f2 | `{gini, palma, lorenz_x, lorenz_y, ...}` / equity_decile shape |
| `misc.py` | a3, a5, b2, b3, c1, c2, d7, f3 (stub), f4 (stub), g2, bsa3 | one-off shapes, see template contracts |

Each module function receives `(filtered_df, unfiltered_df, region, urban_rural,
**named data sources)` and returns a `dict`. `precompute.py` holds a slim
dispatch table mapping `section_id -> builder_function`.

### 2. `precompute.py` changes

- Replace `_SECTIONS = [...]` with `_SECTIONS = list(SECTION_REGISTRY.keys())`.
- Remove the `if region != "all" and urban_rural != "all": continue` skip —
  precompute all 30 combinations (3 × `all`/`urban`/`rural` + 9 regions ×
  3 area types = 30).
- Load the additional source parquets needed by the new builders
  (`route_geometries`, `route_clusters`, `lsoa_clusters_hdbscan`,
  `lsoa_economic_appraisal`, `coverage_prediction`, `shap_values`,
  `anomalies`, `lta_franchising_readiness`, `policy_scenarios`,
  `modal_shift_scenarios`) once, up front, and pass them through to the
  dispatch layer.
- Replace the inline `_build_stats` with a dispatch dict
  `_SECTION_BUILDERS: dict[str, Callable]` built from the per-module functions.

### 3. `engine.py` — single-region template dispatch (fixes §2.4/§8.1)

`single_region.j2` exists and is correctly written but never selected. Add
shape-based dispatch in `InsightEngine.generate`: if `stats` contains
`region_name`, `value`, and `national_avg` but **not** `best`/`worst`, and the
registered template for `section_id` is `ranking.j2`, render `single_region.j2`
instead. This is a localized, four-line addition — `_SECTION_TEMPLATES` remains
the source of truth for the all-regions case.

Ranking builders (`ranking.py`) detect `region != "all"` and emit the
single-region shape (`region_name`, `value`, `national_avg`, `vs_national_pct`,
`unit`) instead of `{best, worst, ...}`.

### 4. Bug fixes folded into the rewrite

- **§2.3 (regional equity):** `equity.py` reads `equity_summary["regional_equity"][region]`
  when `region != "all"`, falling back to national values if the region key is
  absent.
- **§2.5/§8.5 (gap_to_target moving median):** compute `national_median` from
  the **unfiltered** `policy_df`, use it as `target`, and count `filtered` rows
  below it. Label `target_description: "national median"`.
- **§4.2 (urban-rural self-contradiction):** `urban_rural_gap.py` always
  computes `urban_value` from the urban subset of the **region-filtered but
  area-type-unfiltered** dataframe, and `rural_value` likewise from the rural
  subset — never from a dataframe already collapsed to one area type. This
  guarantees both sides have non-zero `n`.
- **§4.4 (n-aware significance):** `correlation.py` includes `n_observations`
  in stats; `correlation.j2`'s evidence gate is updated to use
  `0.001 if n_observations > 10000 else 0.05`.

### 5. Stubs for incomplete sections (§8.2–§8.4)

`f3_ethnic_access`, `f4_gender_accessibility`, `c4_urban_rural_routes` return
`{}` from their builder functions. Each carries an inline comment explaining
exactly what's missing (ts021 join / no LSOA-level gender travel data / route
geometry × urban-rural classification join) so a future session can pick up
the work without re-deriving the gap. `InsightEngine` already suppresses empty
stats cleanly — no special-casing needed.

### 6. `HEADLINE_SECTIONS` fix (§5)

Update `query_overview()`'s `HEADLINE_SECTIONS` dict in
`api/services/warehouse.py` to reference real new-style IDs now that they
produce data (e.g. `"equity": ("f1_gini", "gini")`,
`"accessibility": ("a3_walking_distance", "pct_covered")`, etc., matching the
mapping already sketched in ISSUES.md §5's "Fix (correct)" path).

## Data Sources (confirmed present in `data/audit/`)

All by `lsoa_cd` / `route_id` / `lad_cd` joins as appropriate:

- `lsoa_policy_synthesis.parquet` (33,755 rows) — base filtered frame
- `lsoa_equity_metrics.parquet`, `equity_summary.json` (incl. `regional_equity`,
  `gini_after_bottom_decile_uplift`)
- `lsoa_accessibility.parquet`, `lsoa_2sfca.parquet`
- `route_geometries.parquet`, `route_clusters.parquet`
- `lsoa_clusters_hdbscan.parquet`
- `coverage_prediction.parquet`, `shap_summary.csv` (columns: `feature`, `mean_abs_shap`)
- `anomalies.parquet`
- `lsoa_economic_appraisal.parquet`
- `lta_franchising_readiness.parquet`
- `policy_scenarios.parquet`, `modal_shift_scenarios.parquet`
- `lsoa_service_quality.parquet`, `lsoa_service_levels.parquet`

## Testing

- Per-builder-module unit tests asserting the returned dict matches the keys
  each Jinja2 template requires (e.g. `ranking.py` output always has
  `best.name`, `best.value`, `best.pct_above`, etc., or the single-region shape).
- Replace/update `tests/warehouse/test_precompute_30.py` to assert
  30 × 51 = 1,530 rows are produced, with non-empty `stats` for 48 sections
  and empty (suppressed) `stats` for the 3 stubs across all 30 combos
  (90 expected-empty rows total).
- `tests/intelligence/test_section_registry.py` — verify every registry entry
  has a corresponding builder (or is an explicitly-listed stub).
- `tests/api/test_overview.py` — verify `HEADLINE_SECTIONS` lookups return
  non-zero values once the warehouse is rebuilt against the new precompute.

## Rollout

1. Land the builder modules + `precompute.py` + `engine.py` + `HEADLINE_SECTIONS`
   changes.
2. Rebuild the warehouse (`aequitas run --stage warehouse` or equivalent).
3. Rebuild the FAISS index (`aequitas run --stage rag_index`) — separate step,
   not part of this change, but a required follow-on noted here for visibility.
4. Run the full test suite; fix any remaining failures surfaced by the rewrite.
