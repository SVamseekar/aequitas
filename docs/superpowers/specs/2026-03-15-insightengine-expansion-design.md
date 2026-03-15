# InsightEngine Expansion — Design Spec

**Date:** 2026-03-15
**Goal:** Expand Phase 1 InsightEngine from 7 templates / ~60 narratives to 28 templates (27 unique narrative types) / 51 chart+narrative pairs covering all 51 analytical questions (43 Blueprint + 8 Phase 0 additions), plus auto-generated LAD and regional profiles.

**Scope:** Phase 1 only — templates, chart_data payloads, pre-computation into DuckDB. No frontend code.

---

## 1. Question-to-Template Mapping

### 51 Questions Across 9 Topic Pages

Note: Category letters A, B, C, D, F, G, J are non-sequential by design — the Blueprint reserves E (Temporal Patterns), H (Network Topology), and I (Predictive Modelling) for future analytical categories requiring additional data sources (see Blueprint Section 4).

#### Category A: Coverage & Accessibility (8 questions)

| ID | Section ID | Question | Chart Type | Template | Data Source (warehouse table) |
|---|---|---|---|---|---|
| A1 | `a1_route_density` | Route density by region | Horizontal bar (sorted) | `ranking` | routes, lsoa_demographics |
| A2 | `a2_stop_density` | Stop density by region | Horizontal bar (sorted) | `ranking` | stops, lsoa_demographics |
| A3 | `a3_walking_distance` | Population within 400m of a stop | Stacked bar (covered/not) | `coverage_gap` | lsoa_accessibility |
| A4 | `a4_coverage_equity` | Equity of coverage within regions (Gini) | Lorenz curve + Gini annotation | `equity` | lsoa_equity_metrics |
| A5 | `a5_service_deserts` | Service deserts (no stops) | Choropleth (LAD-aggregated) | `desert_spotlight` | lsoa_service_quality |
| A6 | `a6_urban_rural_gap` | Urban vs rural coverage gap | Grouped bar (urban/rural × region) | `urban_rural_gap` | lsoa_demographics, stops |
| A7 | `a7_investment_gap` | Investment to reach national average | Horizontal bar (£ per region) | `gap_to_target` | lsoa_economic |
| A8 | `a8_coverage_prediction` | Coverage prediction from demographics | Scatter (predicted vs actual, sampled 2,000) + SHAP bar | `ml_prediction` | coverage_prediction, shap_importance |

#### Category B: Service Quality (5 questions)

| ID | Section ID | Question | Chart Type | Template | Data Source (warehouse table) |
|---|---|---|---|---|---|
| B1 | `b1_frequency` | Average frequency by region | Horizontal bar (sorted) | `ranking` | lsoa_service_quality |
| B2 | `b2_operating_hours` | Operating hours (first/last service) | Grouped bar (first/last bus) | `service_hours` | lsoa_service_quality (first_service_min, last_service_min) |
| B3 | `b3_weekend_penalty` | Weekend service penalty | Grouped bar (weekday/sat/sun) | `weekend_penalty` | lsoa_service_quality |
| B4 | `b4_route_frequency` | Most/least frequent routes | Table (top 10 / bottom 10) | `ranking` | routes |
| B5 | `b5_frequency_deprivation` | Frequency vs deprivation | Scatter + regression (sampled 2,000) | `correlation` | lsoa_service_quality × lsoa_demographics |

#### Category C: Route Characteristics (7 questions)

| ID | Section ID | Question | Chart Type | Template | Data Source (warehouse table) |
|---|---|---|---|---|---|
| C1 | `c1_route_length` | Route length distribution by region | Box + violin | `distribution` | route_details |
| C2 | `c2_stops_per_route` | Stops per route | Histogram | `distribution` | route_details |
| C3 | `c3_operator_hhi` | Operator landscape (HHI) | Horizontal bar (HHI by region) | `market_concentration` | lta_readiness |
| C4 | `c4_urban_rural_routes` | Urban vs rural route characteristics | Grouped bar | `urban_rural_gap` | route_details |
| C5 | `c5_length_vs_frequency` | Route length vs frequency | Scatter + regression (sampled 2,000) | `correlation` | route_details |
| C6 | `c6_route_archetypes` | Route archetypes (ML clustering) | Scatter (2D projection, coloured) | `ml_clusters` | route_clusters |
| C7 | `c7_network_topology` | Network topology | Choropleth (LAD-aggregated cross-LA density) | `network_topology` | route_details |

#### Category D: Socio-Economic Correlations (8 questions)

| ID | Section ID | Question | Chart Type | Template | Data Source (warehouse table) |
|---|---|---|---|---|---|
| D1 | `d1_coverage_deprivation` | Coverage vs deprivation (IMD) | Scatter + regression (sampled 2,000) | `correlation` | lsoa_service_quality × lsoa_demographics |
| D2 | `d2_coverage_unemployment` | Coverage vs unemployment | Scatter + regression (sampled 2,000) | `correlation` | same |
| D3 | `d3_coverage_car` | Coverage vs car ownership | Scatter + regression (sampled 2,000) | `correlation` | same |
| D4 | `d4_coverage_elderly` | Coverage vs elderly population | Scatter + regression (sampled 2,000) | `correlation` | same |
| D5 | `d5_coverage_income` | Coverage vs income | Scatter + regression (sampled 2,000) | `correlation` | same |
| D6 | `d6_transport_poverty` | Transport poverty clusters | Scatter (2D projection, coloured) | `ml_clusters` | lsoa_clusters |
| D7 | `d7_deprivation_urban_rural` | Deprivation × urban/rural interaction | Heatmap (decile × urban/rural) | `heatmap` | lsoa_demographics |
| D8 | `d8_feature_importance` | Which factors predict coverage | SHAP waterfall / bar | `ml_prediction` | shap_importance |

#### Category F: Equity & Social Inclusion (6 questions)

| ID | Section ID | Question | Chart Type | Template | Data Source (warehouse table) |
|---|---|---|---|---|---|
| F1 | `f1_gini` | Gini coefficient (stop distribution) | Lorenz curve + Gini annotation | `equity` | lsoa_equity_metrics |
| F2 | `f2_disparity_ratio` | Disparity ratio (most vs least deprived) | Bar (service by IMD decile) | `equity_decile` | lsoa_service_quality × lsoa_demographics |
| F3 | `f3_ethnic_access` | Bus access by ethnic composition | Grouped bar | `demographic_breakdown` | lsoa_demographics |
| F4 | `f4_gender_accessibility` | Gender-adjusted accessibility gap | Bar (school access proxy) | `accessibility_gap` | lsoa_accessibility |
| F5 | `f5_rural_penalty` | Rural accessibility penalty | Grouped bar (urban vs rural) | `urban_rural_gap` | lsoa_accessibility |
| F6 | `f6_equitable_regions` | Most equitable regions | Horizontal bar (regional Gini) | `ranking` | lsoa_equity_metrics by region |

#### Category G: ML Insights (5 questions)

| ID | Section ID | Question | Chart Type | Template | Data Source (warehouse table) |
|---|---|---|---|---|---|
| G1 | `g1_route_clusters` | Route clustering | Scatter (2D PCA/UMAP) | `ml_clusters` | route_clusters |
| G2 | `g2_anomalies` | Anomaly detection | Scatter (SQI vs IMD, anomalies highlighted, sampled 2,000) | `anomaly_spotlight` | anomalies |
| G3 | `g3_coverage_model` | Coverage prediction | Scatter (predicted vs actual, sampled 2,000) | `ml_prediction` | coverage_prediction |
| G4 | `g4_shap` | Feature importance | SHAP bar (horizontal, sorted) | `ml_prediction` | shap_importance |
| G5 | `g5_scenario_model` | Scenario modelling | Grouped bar (baseline vs scenario) | `policy_scenario` | policy_scenarios |

#### Category J: Economic Impact & BCR (4 questions)

| ID | Section ID | Question | Chart Type | Template | Data Source (warehouse table) |
|---|---|---|---|---|---|
| J1 | `j1_economic_value` | Economic value per region | Horizontal bar (£ by region) | `economic_value` | lsoa_economic |
| J2 | `j2_bcr` | BCR for closing coverage gaps | Horizontal bar (BCR by region/LAD) | `bcr_analysis` | lsoa_economic |
| J3 | `j3_carbon` | Carbon reduction from modal shift | Bar (CO2 saved by scenario) | `carbon_reduction` | modal_shift_scenarios |
| J4 | `j4_investment_priority` | Regional investment prioritisation | Horizontal bar (sorted by BCR) | `ranking` | lsoa_economic |

#### Category BSA: Bus Services Act 2025 (3 questions — NEW)

| ID | Section ID | Question | Chart Type | Template | Data Source (warehouse table) |
|---|---|---|---|---|---|
| BSA1 | `bsa1_franchising_readiness` | LTA franchising readiness ranking | Horizontal bar (top/bottom 20 LADs) | `ranking` | lta_readiness |
| BSA2 | `bsa2_operator_concentration` | Operator concentration by region | Horizontal bar (HHI) | `market_concentration` | lta_readiness |
| BSA3 | `bsa3_tier_distribution` | Readiness tier distribution | Stacked bar (Tier 1/2/3 by region) | `tier_distribution` | lta_readiness |

#### Category PS: Policy Scenario Modelling (5 questions — NEW)

| ID | Section ID | Question | Chart Type | Template | Data Source (warehouse table) |
|---|---|---|---|---|---|
| PS1 | `ps1_freq_restoration` | Frequency restoration (Scenario A) | Bar (cost, CO2, population) | `policy_scenario` | policy_scenarios |
| PS2 | `ps2_evening_extension` | Evening extension (Scenario B) | Bar (cost, CO2, population) | `policy_scenario` | policy_scenarios |
| PS3 | `ps3_drt_rural` | DRT for rural (Scenario C) | Bar (cost, CO2, population) | `policy_scenario` | policy_scenarios |
| PS4 | `ps4_franchise` | Combined franchise (Scenario D) | Bar (cost, CO2, population) | `policy_scenario` | policy_scenarios |
| PS5 | `ps5_scenario_comparison` | Scenario comparison (all 4) | Grouped bar (side by side) | `scenario_comparison` | policy_scenarios |

---

## 2. Template Inventory

### Existing (7) — no changes needed

| Template | Questions Served |
|---|---|
| `ranking.j2` | A1, A2, B1, B4, F6, J4, BSA1 |
| `equity.j2` | A4, F1 |
| `correlation.j2` | B5, C5, D1, D2, D3, D4, D5 |
| `gap_to_target.j2` | A7 |
| `policy_scenario.j2` | PS1, PS2, PS3, PS4, G5 |
| `single_region.j2` | Regional profiles |
| `coverage_density.j2` | Regional density rankings |

### New (20) — to be built

| Template | Questions Served | Narrative Pattern | Evidence Gate |
|---|---|---|---|
| `coverage_gap.j2` | A3 | "X% of England's population lives within 400m of a bus stop. Y LSOAs (Z%) have zero access..." | n_lsoas >= 100 |
| `desert_spotlight.j2` | A5 | "N LSOAs have no bus stops within their boundaries, affecting X people. The largest concentration is in [region]..." | n_desert_lsoas >= 1 |
| `urban_rural_gap.j2` | A6, C4, F5 | "[Urban/Rural] areas have X [metric] compared to Y in [rural/urban], a gap of Z%..." | both urban AND rural groups have n >= 30 |
| `ml_prediction.j2` | A8, D8, G3, G4 | "A Random Forest model explains X% of variation in bus coverage. The strongest predictor is [feature] (SHAP value: Y)..." | r2 > 0 AND n_features >= 3 |
| `service_hours.j2` | B2 | "The median first bus departs at HH:MM; the median last bus at HH:MM. N LSOAs (X%) lose all service before 19:00..." | n_lsoas >= 100 |
| `weekend_penalty.j2` | B3 | "Sunday service drops X% compared to weekday levels. N LSOAs (X%) have zero Sunday service..." | n_lsoas >= 100 |
| `distribution.j2` | C1, C2 | "The median [metric] is X (IQR: Y–Z). The distribution is [right-skewed/normal/bimodal]..." | n >= 30 |
| `market_concentration.j2` | C3, BSA2 | "[Region] has an HHI of X, indicating [competitive/moderately concentrated/highly concentrated] operator market..." | n_operators >= 2 |
| `ml_clusters.j2` | C6, D6, G1 | "Clustering reveals N distinct groups. Cluster K (N LSOAs, X%) is characterised by [high/low feature]..." | n_clusters >= 2 |
| `network_topology.j2` | C7 | "X routes (Y%) cross local authority boundaries. The densest cross-LA corridor is [area]..." | n_routes >= 10 |
| `heatmap.j2` | D7 | "The interaction between deprivation and urban/rural classification shows [pattern]. The worst-served cell is [IMD decile × area type]..." | all cells have n >= 10 |
| `equity_decile.j2` | F2 | "The most deprived decile receives X trips/capita vs Y for the least deprived — a ratio of Z:1..." | all 10 deciles have n >= 100 |
| `demographic_breakdown.j2` | F3 | "LSOAs with [demographic characteristic] have X [metric] compared to Y nationally..." | each group n >= 30 |
| `accessibility_gap.j2` | F4 | "N secondary schools (X%) are beyond 400m of a bus stop. This affects an estimated Y students..." | n_schools >= 10 |
| `anomaly_spotlight.j2` | G2 | "N LSOAs (X%) are flagged as anomalous. Of these, Y are 'deprived but well-served' (policy successes) and Z are 'affluent but poorly served' (inefficiencies)..." | n_anomalies >= 10 |
| `economic_value.j2` | J1 | "[Region] generates an estimated £X in annual transport user benefits from bus services..." | n_lsoas >= 100 |
| `bcr_analysis.j2` | J2 | "Closing coverage gaps in [region/LAD] has a BCR of X (Y value-for-money band). The investment required is £Z..." | n_below_target >= 1 |
| `carbon_reduction.j2` | J3 | "Modal shift from car to bus in [scope] would save X tonnes CO2/year, valued at £Y (TAG carbon price)..." | co2_saving > 0 |
| `tier_distribution.j2` | BSA3 | "Of 298 LADs assessed for franchising readiness: X in Tier 1 (high), Y in Tier 2 (medium), Z in Tier 3 (low)..." | n_lads >= 10 |
| `scenario_comparison.j2` | PS5 | "Across all four policy scenarios, Scenario [X] delivers the highest BCR at [Y], affecting [Z] people at a cost of £[W]/year..." | n_scenarios >= 2 |

### LAD Profile Template (1 additional)

| Template | Purpose |
|---|---|
| `lad_profile.j2` | Wraps 5 sub-narratives (single_region, market_concentration, coverage_gap, desert_spotlight, gap_to_target) into a single LAD-level narrative block |

**Total: 7 existing + 20 new + 1 LAD profile = 28 templates. 27 unique narrative types (LAD profile reuses existing templates).**

---

## 3. Warehouse Schema Additions

The following Parquet files must be added to `ANALYTICS_PARQUET_SOURCES` in `schema.py`:

| Table Name | Source Parquet | Rows | Purpose |
|---|---|---|---|
| `stop_headways` | `data/processed/stop_headways.parquet` | ~274,000 | Per-stop headway data (B2 uses lsoa_service_quality instead for first/last service) |
| `coverage_prediction` | `data/processed/coverage_prediction.parquet` | 33,755 | RF predicted vs actual trips per LSOA |
| `shap_importance` | `data/processed/shap_importance.parquet` | ~10 | Feature importance from SHAP TreeExplainer |
| `route_clusters` | `data/processed/route_clusters.parquet` | 13,099 | HDBSCAN cluster labels per route |
| `lsoa_clusters` | `data/processed/lsoa_clusters_hdbscan.parquet` | 33,755 | HDBSCAN + GMM cluster labels per LSOA |
| `anomalies` | `data/processed/anomalies.parquet` | 33,755 | Isolation Forest + LOF scores, anomaly types |
| `modal_shift_scenarios` | `data/processed/modal_shift_scenarios.parquet` | 9 | 3 elasticities × 3 scopes |
| `policy_scenarios` | `data/processed/policy_scenarios.parquet` | 4 | Scenarios A–D with cost/CO2/population |

**Total warehouse tables: 7 existing + 8 new = 15 analytics tables.**

---

## 4. chart_data Payloads

Each question's `chart_data` in `section_results` will contain a JSON payload shaped for the chart type. The frontend (Phase 2) consumes these directly.

### Data Size Strategy

- **Scatter charts:** Sampled to max 2,000 points (stratified random sample preserving distribution). Regression line computed on full data, sample is for display only.
- **Choropleth:** Aggregated to LAD level (298 areas) for `chart_data`. LSOA-level data available via direct warehouse query in Phase 2 if needed.
- **All other charts:** Aggregated data only (9 regions, 10 deciles, etc.) — naturally small.

### Chart Data Schemas

#### Horizontal Bar (ranking, gap_to_target, economic_value, bcr_analysis)
```json
{
  "type": "horizontal_bar",
  "title": "Route density by region",
  "x_label": "Routes per 100,000 population",
  "y_label": "Region",
  "national_avg": 23.2,
  "data": [
    {"label": "South East", "value": 31.4, "rank": 1},
    {"label": "North East", "value": 12.1, "rank": 9}
  ]
}
```

#### Scatter + Regression (correlation)
```json
{
  "type": "scatter_regression",
  "title": "Deprivation vs Service Quality",
  "x_label": "IMD Score",
  "y_label": "Service Quality Index",
  "r": 0.2184,
  "p_value": 0.0001,
  "regression_line": {"slope": 0.15, "intercept": 42.3},
  "sample_size": 33755,
  "display_sample_size": 2000,
  "data": [{"x": 45.2, "y": 72.1, "lsoa": "E01000001"}, "... (max 2000)"]
}
```

#### Lorenz Curve (equity)
```json
{
  "type": "lorenz_curve",
  "title": "Bus Service Distribution Equity",
  "gini": 0.5741,
  "reference_gini": 0.36,
  "reference_label": "UK Income Gini",
  "curve_points": [{"cum_pop": 0.0, "cum_service": 0.0}, {"cum_pop": 0.1, "cum_service": 0.02}, "..."]
}
```

#### Stacked Bar (coverage_gap, tier_distribution)
```json
{
  "type": "stacked_bar",
  "title": "Population within 400m of a bus stop",
  "categories": ["North East", "North West", "..."],
  "series": [
    {"name": "Covered", "values": [82.1, 91.3, "..."]},
    {"name": "Not covered", "values": [17.9, 8.7, "..."]}
  ]
}
```

#### Grouped Bar (urban_rural_gap, weekend_penalty, service_hours, scenario_comparison)
```json
{
  "type": "grouped_bar",
  "title": "Urban vs Rural Coverage",
  "categories": ["North East", "North West", "..."],
  "series": [
    {"name": "Urban", "values": [4.2, 5.1, "..."]},
    {"name": "Rural", "values": [1.3, 1.8, "..."]}
  ]
}
```

#### Box + Violin (distribution)
```json
{
  "type": "box_violin",
  "title": "Route Length Distribution by Region",
  "unit": "km",
  "groups": [
    {"label": "North East", "min": 2.1, "q1": 8.4, "median": 15.2, "q3": 28.7, "max": 89.3, "outliers": [95.1, 102.3]},
    "..."
  ]
}
```

#### Choropleth (desert_spotlight, network_topology)
```json
{
  "type": "choropleth",
  "title": "Service Deserts by Local Authority",
  "geography": "lad",
  "metric": "pct_lsoas_no_service",
  "colour_scale": "RdYlGn",
  "data": [{"lad_code": "E06000001", "lad_name": "Hartlepool", "value": 12.3}, "... (298 LADs)"]
}
```

#### Heatmap (heatmap)
```json
{
  "type": "heatmap",
  "title": "Service Quality by Deprivation Decile and Area Type",
  "x_labels": ["1 (most deprived)", "2", "...", "10 (least)"],
  "y_labels": ["Urban", "Rural"],
  "values": [[62.1, 58.3, "..."], [41.2, 39.8, "..."]],
  "colour_scale": "Viridis"
}
```

#### SHAP Bar (ml_prediction)
```json
{
  "type": "shap_bar",
  "title": "Feature Importance — Coverage Prediction",
  "model_r2": 0.472,
  "features": [
    {"name": "nocar_pct", "importance": 0.142},
    {"name": "imd_score", "importance": 0.098},
    "..."
  ]
}
```

#### Scatter Clusters (ml_clusters)
```json
{
  "type": "scatter_clusters",
  "title": "LSOA Transport Poverty Clusters",
  "x_label": "PC1",
  "y_label": "PC2",
  "clusters": [
    {"id": 0, "label": "Affluent Urban", "colour": "#1f77b4"},
    {"id": 1, "label": "Deprived Car-Free", "colour": "#ff7f0e"}
  ],
  "data": [{"x": 1.2, "y": -0.8, "cluster": 0, "lsoa": "E01000001"}, "... (max 2000)"]
}
```

---

## 5. Auto-Generated Profiles

### Regional Profiles (9)

Each region gets a profile page with ~6 narratives reusing existing templates:
1. `single_region` — region vs national average
2. `ranking` — region's rank on key metrics
3. `equity` — intra-region Gini
4. `correlation` — region-specific deprivation vs service
5. `coverage_gap` — region-specific access %
6. `gap_to_target` — region-specific investment need

### LAD Profiles (298)

Each LAD gets a profile with ~5 narratives composed by `lad_profile.j2`:
1. `single_region` (adapted for LAD) — LAD vs regional and national average
2. `market_concentration` — operator HHI for the LAD
3. `coverage_gap` — LAD-specific access %
4. `desert_spotlight` — LAD-specific service deserts
5. `gap_to_target` — LAD-specific investment need

---

## 6. Pre-Computation Expansion

### Current State
- 5 sections × 12 effective filter combos = ~60 rows in `section_results`
- `chart_data` field: empty `{}`

### Target State
- 51 sections × 12 filter combos = ~612 rows (topic pages)
- 9 regional profiles × 6 sections = 54 rows
- 298 LAD profiles × 5 sections = 1,490 rows
- `chart_data` field: populated with typed JSON payloads
- **Total: ~2,156 rows in `section_results`**

### Filter Space (unchanged)
- Regions: 10 (all + 9 ONS regions)
- Area types: 3 (all, urban, rural)
- Suppression: skip single-region + urban/rural combos
- Effective combos per section: 12 (1 all×all + 1 all×urban + 1 all×rural + 9 region×all)

### Section Registry

`precompute.py` will use a section registry dict mapping section_id → builder function:

```python
_SECTION_REGISTRY: dict[str, Callable] = {
    # Category A
    "a1_route_density": build_ranking_section,
    "a2_stop_density": build_ranking_section,
    "a3_walking_distance": build_coverage_gap_section,
    "a4_coverage_equity": build_equity_section,
    "a5_service_deserts": build_desert_section,
    "a6_urban_rural_gap": build_urban_rural_section,
    "a7_investment_gap": build_gap_to_target_section,
    "a8_coverage_prediction": build_ml_prediction_section,
    # ... (all 51 sections follow same pattern)
}
```

Each builder function:
1. Receives the filtered DataFrame + context
2. Computes stats (reusing existing calculators)
3. Generates chart_data payload (new `chart_data_builder.py` module)
4. Renders narrative via InsightEngine (existing template dispatch)
5. Returns `(stats, chart_data, narrative)` tuple

---

## 7. Implementation Approach

### New Modules

| Module | Responsibility |
|---|---|
| `intelligence/chart_data_builder.py` | Pure functions: DataFrame → typed chart_data JSON. One function per chart type (e.g., `build_horizontal_bar()`, `build_scatter_regression()`, `build_lorenz_curve()`). |
| `intelligence/section_registry.py` | Maps section_id → (template, builder_fn, evidence_gate, data_sources). Single source of truth for all 51 sections. |

### Changes to Existing Modules

| Module | Change |
|---|---|
| `intelligence/engine.py` | Expand `_SECTION_TEMPLATES` to contain all 51 section_id → template filename mappings (multiple section_ids map to the same template, e.g. `"a1_route_density": "ranking.j2"`, `"a2_stop_density": "ranking.j2"`, etc.). Register `format_thousands` Jinja2 custom filter. Retire old keys (`"coverage_density"`, `"equity"`, etc.) — they are replaced by the new explicit section_ids. |
| `intelligence/rules.py` | Add new rule classes for evidence gates (see Section 7.1 below). |
| `warehouse/schema.py` | Add 8 new entries to `ANALYTICS_PARQUET_SOURCES` (see Section 3). |
| `warehouse/precompute.py` | Replace hardcoded `_SECTIONS` list with `_SECTION_REGISTRY` import. Loop over all 51 sections. Old section_ids (`"coverage_density"`, `"equity"`, etc.) are replaced — no backward compatibility needed since Phase 1 warehouse is rebuilt from scratch on every run. |
| `analytics/ml_prediction.py` | Export SHAP importance to `shap_importance.parquet` (currently only returned in memory). |

### 7.1 New Rule Classes for rules.py

The existing 5 rule classes remain. New rule classes use the same pattern (`should_fire()` → bool):

| Rule Class | Parameters | Threshold | Used By Templates |
|---|---|---|---|
| `MinLsoaRule` | `n_lsoas: int` | n_lsoas >= 100 | coverage_gap, service_hours, weekend_penalty, economic_value |
| `DesertRule` | `n_desert_lsoas: int` | n_desert_lsoas >= 1 | desert_spotlight |
| `UrbanRuralRule` | `n_urban: int, n_rural: int` | both >= 30 | urban_rural_gap |
| `MLPredictionRule` | `r2: float, n_features: int` | r2 > 0 AND n_features >= 3 | ml_prediction |
| `DistributionRule` | `n: int` | n >= 30 | distribution |
| `MarketConcentrationRule` | `n_operators: int` | n_operators >= 2 | market_concentration |
| `ClusterRule` | `n_clusters: int` | n_clusters >= 2 | ml_clusters |
| `NetworkRule` | `n_routes: int` | n_routes >= 10 | network_topology |
| `HeatmapRule` | `min_cell_n: int` | all cells >= 10 | heatmap |
| `DecileRule` | `decile_counts: list[int]` | all 10 deciles >= 100 | equity_decile |
| `DemographicRule` | `group_counts: list[int]` | each group >= 30 | demographic_breakdown |
| `AccessibilityRule` | `n_pois: int` | n_pois >= 10 | accessibility_gap |
| `AnomalyRule` | `n_anomalies: int` | n_anomalies >= 10 | anomaly_spotlight |
| `CarbonRule` | `co2_saving: float` | co2_saving > 0 | carbon_reduction |
| `TierRule` | `n_lads: int` | n_lads >= 10 | tier_distribution |
| `ScenarioComparisonRule` | `n_scenarios: int` | n_scenarios >= 2 | scenario_comparison |

Each builder function in `section_registry.py` calls its rule's `should_fire()` before rendering. If the rule returns False, the section is suppressed (narrative = "", suppressed = True).

### What Does NOT Change
- Pipeline stages (ingest → process → analytics → intelligence → warehouse → validate)
- Analytics computation logic (equity.py, accessibility.py, economic.py, etc.)
- DuckDB DDL (section_results table structure unchanged — already uses JSON columns)
- Ground truth values
- Pydantic models

---

## 8. Bugfixes Required

| Bug | Location | Fix |
|---|---|---|
| `format_thousands` Jinja2 filter used but not registered | `policy_scenario.j2` line 4 | Register custom filter in `InsightEngine.__init__()`: `env.filters["format_thousands"] = lambda v: f"{int(v):,}"` |

---

## 9. Colorblind-Safe Palette (from Blueprint Section 10.5)

All charts use Viridis or Cividis colour scales. No red/green encoding.

---

## 10. Success Criteria

1. `section_results` table contains ~2,156 rows (up from ~60)
2. Every row has non-empty `chart_data` JSON matching the schema for its chart type
3. Every row has non-empty `narrative` matching its template
4. All evidence gates fire correctly (no misleading narratives)
5. Pipeline still runs end-to-end with `python -m aequitas.pipeline --stage=all`
6. Ground truth validation still passes (0 FAIL)
7. Total warehouse build time < 30 minutes
8. `format_thousands` filter bug fixed
