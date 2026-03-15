# Aequitas — Phase 0 Session Report

**Date:** 11-12 March 2026
**Duration:** ~17 hours across 4 context windows
**Branch:** main
**Commits:** 4

---

## Table of Contents

1. [Session Overview](#1-session-overview)
2. [Phase 1: Data Audit Completion](#2-phase-1-data-audit-completion)
3. [Phase 2: Deep Data Understanding Notebooks](#3-phase-2-deep-data-understanding-notebooks)
4. [Phase 3: Old Project Analysis](#4-phase-3-old-project-analysis)
5. [Phase 4: Doc Curation](#5-phase-4-doc-curation)
6. [Phase 5: Gap Analysis — Notebooks vs Old Project Requirements](#6-phase-5-gap-analysis)
7. [Phase 6: Source Verification & Question Quality Assessment](#7-phase-6-source-verification--question-quality-assessment)
8. [All Output Artifacts](#8-all-output-artifacts)
9. [Ground Truth Numbers (Locked)](#9-ground-truth-numbers-locked)
10. [Critical Findings](#10-critical-findings)
11. [What Comes Next](#11-what-comes-next)

---

## 1. Session Overview

This session completed Phase 0 (Data Audit) of the Aequitas project and performed a comprehensive analysis of the predecessor project (uk_bus_analytics) to understand what to carry forward and what to avoid.

**Work performed:**
- Created and executed 11 Jupyter notebooks covering every dimension of the data
- Fixed 2 bugs (NaPTAN Status filter, KDTree index alignment)
- Produced 15 output artifacts in `data/audit/`
- Created 8 data dictionary files
- Read and analyzed 7 old project docs and the entire uk_bus_analytics codebase
- Performed an exhaustive gap analysis: 61 questions mapped against notebook outputs
- Verified all data source links, TAG values, and consulting report references for currency (March 2026)
- Assessed the quality and relevance of all 61 questions

**Commits made:**
1. `148b64f` — fix(audit): achieve 100% stop-to-LSOA match rate, fix all data sources
2. `e93383c` — feat(audit): add section 9 data quality report
3. `834df22` — feat(audit): section 10 — deep data understanding, data dictionaries, join integrity
4. `af4212f` — Phase 0 complete: exhaustive data audit with 103 checks, zero FAILs

---

## 2. Phase 1: Data Audit Completion

**Trigger:** "check the entire data each column and check how and why and what data audits we did and fix things, i want you to understand the data at its entirety"

**What was done:**
- Reviewed the existing `01_data_audit.ipynb` and identified gaps in column-level profiling, cross-dataset validation, and deep understanding
- Discussed 3 approaches: (A) extend existing notebook, (B) create new deep-dive notebooks, (C) both
- Agreed on Option C: extend the audit notebook AND create separate deep-dive notebooks for each dimension

**What was found:**
- The audit notebook had basic profiling but lacked complete column inventory, data dictionaries, cross-dataset relationship analysis, and service frequency extraction from BODS
- The notebook was extended with sections 9 (data quality report with 103 checks) and section 10 (data dictionaries, join integrity)

**Result:** 103 data quality checks — 89 PASS, 14 WARN, 0 FAIL, 0 CRITICAL.

---

## 3. Phase 2: Deep Data Understanding Notebooks

**Trigger:** "i want you to do more exploratory data analysis, because i think this isnt enough"

Nine deep-dive notebooks were created, converted to `.ipynb` via jupytext, and executed. All ran successfully. The `.py` source files were deleted after execution, leaving only the `.ipynb` files with embedded outputs.

### 3.1 Notebook Inventory

#### 02_data_understanding.ipynb — Core Understanding
- Single-LSOA deep dives for 6 diverse LSOAs (City of London, Sunderland deprived, Basildon deprived, rural elderly, suburban, mid-tier)
- All 8 socio-economic factors profiled with source columns, formulas, and distributions
- Cross-factor pairwise analysis
- Bus coverage integration with socio-economic need
- **Output:** `master_lsoa_table.parquet` (33,755 rows, all 8 factors merged)

#### 02a_column_inventory.ipynb — Complete Column Audit
- Documented all 238 columns across 7 datasets
- Every column classified as JOIN KEY, USE, or SKIP with rationale
- Datasets covered: NaPTAN (43 cols), IMD 2025 (56 cols), Census TS001 (6 cols), TS007a (22 cols), TS045 (8 cols), TS021 (28 cols), NOMIS TS066 (34 cols)

#### 02b_bods_deep_dive.ipynb — BODS Service Analysis
- Operator/agency analysis: market concentration, operator counts by region
- Route analysis: route types, naming patterns, geographic coverage
- Trip volume analysis: trips per route distribution
- Calendar and service day patterns: weekday vs weekend
- Stop_times frequency analysis: chunked reading of the 5.8 GB stop_times.txt file
- Stop geographic analysis: BODS-NaPTAN overlap
- **Output:** `bods_operator_summary.csv`, `bods_stop_frequency.parquet`

#### 02c_spatial_analysis.ipynb — Geographic Visualization
- Bus stop density choropleth map (England overview)
- IMD deprivation choropleth map
- Stop density vs deprivation overlay map
- Transport desert identification (high deprivation + low coverage)
- Regional comparison maps
- Urban vs rural spatial patterns
- Zoomed maps: London, North West, South West

#### 02d_imd_subdomain_deep_dive.ipynb — IMD Domain Exploration
- All 7 IMD domains profiled individually (Income, Employment, Education, Health, Crime, Barriers, Living Environment)
- Sub-domains explored (Geographical Barriers to Services, Education sub-domains)
- IDACI and IDAOPI supplementary indices profiled
- Domain-vs-domain cross-analysis
- Population columns mapped and validated

#### 02e_multivariate_clustering.ipynb — LSOA Archetype Discovery
- Full feature matrix built: one row per LSOA, all 8 socio-economic factors plus coverage
- Full correlation matrix computed (Pearson)
- PCA analysis: variance explained, component loadings, interpretation
- KMeans clustering with silhouette optimization tested for k=3 through k=10
- Optimal k=4 selected
- **4 archetypes identified:**
  - Affluent Urban: 16,944 LSOAs (50.2%)
  - Deprived Young Diverse Car-Free Urban: 6,023 LSOAs (17.8%)
  - Elderly Rural: 4,588 LSOAs (13.6%)
  - Deprived Car-Free Urban: 6,200 LSOAs (18.4%)
- Violin plots and box plots by cluster and region
- Multi-deprivation analysis: LSOAs deprived on multiple dimensions simultaneously
- **Output:** `lsoa_feature_matrix_clustered.parquet`, `cluster_archetypes.csv`

#### 02f_cross_factor_synthesis.ipynb — Capstone Synthesis
- 14 derived metrics defined with exact source-to-formula-to-output mapping
- Join key validation across all datasets: 100% match on LSOA codes
- Three-way conditional analysis: cross-factor interactions (e.g., high deprivation + low car ownership + low coverage)
- 25 data traps documented comprehensively with mitigation steps
- Cross-dataset relationship map
- Factor-to-factor summary matrix
- Pipeline readiness checklist
- **Output:** `metrics_catalog.csv`, `metrics_catalog.json`, `data_traps.csv`

#### 02g_bods_service_levels.ipynb — Service Frequency Deep Dive
- Per-stop daily trip counts computed: weekday, Saturday, Sunday
- Service tier classification: No service, Minimal (<4 trips/day), Low (4-12), Moderate (12-24), Good (24-48), High (>48)
- Weekend service gap analysis: LSOAs with weekday service but no weekend service
- First/last bus timing analysis per stop
- Service level by IMD decile (deprivation-frequency correlation)
- Weekend service deserts identified
- Peak vs off-peak analysis: AM peak, PM peak, inter-peak, evening
- Service level by cluster archetype
- "Typical day" stop-level time profiles by IMD decile
- **Output:** `lsoa_service_levels.parquet` (33,755 rows × 17 columns), `stop_service_profiles.parquet` (298,072 rows)

#### 02h_spatial_access.ipynb — Spatial Accessibility Analysis
- Distance to nearest bus stop via KDTree (scipy.spatial.cKDTree) for every LSOA centroid
- Distance to 5th nearest stop
- Distance vs deprivation scatter analysis
- Distance by urban/rural classification
- Choropleth map of distances
- Service frequency at nearest stop
- NaPTAN deep dive: stop types, pairing analysis
- Composite accessibility metric combining: distance, service frequency, deprivation
- **Output:** `lsoa_accessibility.parquet` (33,755 rows × 11 columns, zero nulls)

**Bugs fixed in 02h:**
1. NaPTAN Status filter used `'act'` but actual data uses `'active'`. Diagnostic confirmed: `Status=act: 0 rows`, `Status=active: 387,377 rows`. Fix: changed `== 'act'` to `== 'active'`.
2. KDTree index alignment: filtered NaPTAN DataFrame had non-contiguous index. Fix: added `.reset_index(drop=True)` after filtering.

#### 02i_lsoa_stories.ipynb — LSOA Narratives & Policy Insights
- Cluster archetype naming and profiling (summary statistics per archetype)
- Single-LSOA deep dives: one representative from each archetype
- Transport desert composite score: multi-criteria combining IMD deprivation + no-car household % + elderly % + coverage deficit
- Top 500 transport deserts ranked by composite score
- Cluster comparison across every dimension
- Anomaly identification: LSOAs that defy expectations (deprived with good coverage, affluent with poor coverage, triple-vulnerable)
- "Day in the life" policy narratives by archetype
- **Output:** `top_500_transport_deserts.csv` (500 rows), `cluster_archetypes.csv` (4 archetypes)

### 3.2 Analytical Methods Demonstrated

| Method | Notebook | Status |
|--------|----------|--------|
| Pearson/Spearman correlation | 01, 02, 02e, 02f | Done |
| PCA (dimensionality reduction) | 02e | Done |
| KMeans clustering (silhouette-optimized) | 02e | Done |
| KDTree nearest-neighbor distance | 02h | Done |
| Spatial join (point-in-polygon) | 01 | Done |
| IsolationForest (anomaly detection) | 01 | Done (limited, 1% contamination) |
| Choropleth mapping (GeoJSON) | 02c, 02h | Done |
| Box/violin plots by group | 02e, 02g | Done |
| Service tier classification | 02g | Done |
| Peak/off-peak temporal patterns | 02g | Done |
| Transport desert composite scoring | 02i | Done |
| Archetype narrative generation | 02i | Done |

---

## 4. Phase 3: Old Project Analysis

**Trigger:** "read the docs in @docs/docs-old-project/... they are from the uk_bus_analytics project which was very messy and very hard to continue to implement... capture all the details nothing should be overseen"

Then: "you can also check the entire folder of uk_bus_analytics in the projects folder to actually understand why we started a new project abandoning it"

### 4.1 Four Docs Read (Already in Aequitas)

**initial_plan.md** — Original requirements capture:
- 57 guiding questions for the platform
- 22 consulting gaps identified vs McKinsey/KPMG/BCG reports
- ML model plans: Sentence Transformers, TimeGPT, Isolation Forest
- Deployment target: Hugging Face Spaces
- 41 consulting report links (references 1-41)
- Portfolio-ready goal

**uk-transport-consulting-analysis.md** — Industry standards benchmark:
- Visualization standards from £100K+ consulting reports
- Geographic granularity hierarchy (national → regional → LA → LSOA → route → stop)
- HM Treasury Green Book methodology: 3.5% discount, 60-year appraisal, BCR bands
- DfT TAG 2024/25 values: car commuting £12.65/hr, bus £9.85/hr, carbon £75-85/tonne
- Accessibility analysis methods: cumulative opportunities, Hansen, 2SFCA, logsum
- Equity frameworks: Gini, Palma, Lorenz, Theil
- 25 policy questions for transport planners
- Demand elasticities: fare -0.4 to -0.6, frequency +0.4 to +0.7
- Economic multipliers: £2.00-2.40 per £1 direct spend
- WCAG 2.1 AA accessibility compliance standards

**01. PROJECT_PLAN_CONSULTING_GRADE.md** — Aspirational pitch:
- 6 strategic intelligence modules: Coverage, Network Optimization, Equity, Investment Appraisal, Policy Scenarios, Predictive Performance
- Policy Intelligence Assistant (NLP chatbot)
- Economic modeling: BCR, GDP multipliers, carbon
- Technology stack: Streamlit + DuckDB + Sentence Transformers

**05. PROJECT_STATUS_AND_PLAN.md** — Most operationally detailed doc:
- 61 questions: 50 spatial (Phase 1) + 11 temporal (Phase 2), categories A through J
- 28 consulting gaps (expanded from 22)
- What was built vs not built
- Hugging Face Spaces deployment strategy (~300 MB under 1 GB limit)
- Day-by-day tactical plan (10 days)
- Data download plan (Zenodo 19.5 GB for temporal)
- File status inventory
- Critical finding: used 7,696 LSOAs (wrong), 3M stops (unfiltered), IMD 2019 (outdated)

### 4.2 Full Codebase Exploration of uk_bus_analytics

An agent explored the entire `/Users/souravamseekarmarti/Projects/uk_bus_analytics` codebase.

**Why uk_bus_analytics was abandoned — 5 reasons:**

1. **Architectural drift.** CLAUDE.md said "no Streamlit" but the entire frontend was Streamlit. The project violated its own rules.

2. **Data pipeline chaos.** 4 duplicate TransXChange parsers existed in different directories. 20+ one-off scripts scattered across `dashboard/`, `data_processing/`, `scripts/`, `notebooks/`, and root-level `.py` files. No single canonical pipeline. No clear execution order.

3. **Wrong ground truth numbers.** 7,696 LSOAs (correct: 33,755 for England). ~3M stops (correct: 274,719 England active bus stops after filtering StopType BCT/BCS/BCE, Status=active, ATCO prefix 0xx-4xx). IMD 2019 (now IMD 2025). These cascading errors meant every per-capita metric was wrong.

4. **Zero tests, zero CI/CD.** No pytest files. No GitHub Actions. No way to catch regressions. No data validation gates.

5. **Incomplete integration.** Individual pieces worked in isolation but were never wired together. The InsightEngine existed (and was well-architected) but the data feeding it was unreliable.

**The project reached ~60-70% completion but was unmaintainable. Death by 1,000 cuts, not one fatal flaw.**

### 4.3 InsightEngine Deep Read

Three source files were read in detail from `/Users/souravamseekarmarti/Projects/uk_bus_analytics/dashboard/utils/insight_engine/`:

**engine.py (500 lines):**
- `InsightEngine` class with `run()`, `run_correlation()`, `run_power_law()` methods
- 4-step pipeline: resolve_context → compute_metrics → apply_rules → render_templates
- Population-weighted national average calculation (never simple mean for per-capita metrics)
- Single-region positioning with true rank against full dataset
- Gap-to-investment calculation with BCR
- Worth carrying forward to Aequitas

**rules.py (448 lines):**
- Evidence-gated rule system using Protocol pattern
- `InsightRule` protocol: `applies(ctx, metrics) -> bool`, `emit(ctx, metrics) -> List[Insight]`
- `InsightRegistry` class for rule registration and lookup
- 10 rules registered:
  1. RankingRule — ranks regions by metric
  2. SingleRegionPositioningRule — "you are 3rd of 9 regions"
  3. SubsetSummaryRule — summary stats for filtered view
  4. CorrelationRule — Pearson r with p-value significance gate
  5. OutlierRule — flags statistical outliers
  6. GapToInvestmentRule — calculates cost to reach target + BCR
  7. VariationRule — coefficient of variation analysis
  8. QuartileComparisonRule — Q1 vs Q4 gap
  9. PowerLawRule — tests for power law distribution
  10. EfficiencyRule — cost per unit output
- Each rule has `requirements` dict (min_n, min_groups) and evidence gates (p-value thresholds, CV minimums)

**templates.py (200 lines):**
- Jinja2 consulting-tone narrative templates
- Custom filters: `currency` (£ formatting), `pct` (percentage), `num` (number with commas)
- Templates: RANKING, SINGLE_REGION, SUBSET_DESCRIPTION, VARIATION, CORRELATION, OUTLIER, QUARTILE_COMPARISON, POWER_LAW, EFFICIENCY, GAP_INVESTMENT, INVESTMENT_DETAIL
- `TemplateRenderer` class maps (kind, key) tuples to templates

---

## 5. Phase 4: Doc Curation

**Trigger:** "so which md docs you recommend we bring into this folder? i already brought 4"

Scanned all `.md` files in the uk_bus_analytics project (~80+ files, most in `docs/not_imp/`). Read 6 additional candidates from `docs/imp/`.

**Recommended and copied 3 additional docs:**

1. **DATA_STRATEGY_COMPLETE.md** — Maps every single question (A1 through J50) to exact data requirements, what data was available vs missing, and extraction methods. The most operationally useful doc for Phase 1 pipeline build.

2. **ML_MODELS_EVALUATION_REPORT.md** — Documents the 3 ML models with real performance numbers:
   - Route Clustering: SentenceTransformers + HDBSCAN, 198 clusters, 5,822 routes
   - Service Gap Detection: Isolation Forest, 1,436 gaps (15%), 2.6M people affected
   - Coverage Prediction: Random Forest, R²=0.089, MAE=2.20
   - Key finding: demographics explain only 8.9% of coverage variation; 91.1% is policy-driven

3. **INSIGHT_ENGINE_README.md** (renamed from README.md) — InsightEngine 5-layer architecture doc with usage examples

**Docs skipped (with reasons):**
- FINAL_IMPLEMENTATION_ROADMAP_PART1/PART2 — Status tracking, superseded
- UK_BUS_ANALYTICS_COMPLETE_JOURNEY — Narrative retrospective, claims "production-ready" with wrong counts
- CATEGORY_G_IMPLEMENTATION_SUMMARY — Streamlit-specific, not reusable
- HOMEPAGE_IMPLEMENTATION_SUMMARY, LSOA_DEMOGRAPHICS_FIX, REVOLUTIONARY_FEATURE_DESIGN — Implementation artifacts tied to old Streamlit codebase
- reports.md — 22 consulting gaps already covered in initial_plan.md and 05. PROJECT_STATUS_AND_PLAN.md

**Total: 7 docs now in `docs/docs-old-project/`**

---

## 6. Phase 5: Gap Analysis

**Trigger:** "so how close are we with the notebooks we created as part of data audit and data exploratory analysis with the docs we added from the old project?"

An agent read all 11 notebooks AND all 7 old project docs, then produced an exhaustive question-by-question mapping.

### 6.1 Scorecard

| Category | Name | Total Qs | Data Ready | Method Done | Fully Answerable | Gaps |
|----------|------|----------|------------|-------------|-----------------|------|
| A | Coverage & Accessibility | 8 | 7 | 5 | 5 | 3 |
| B | Frequency (spatial only) | 5 | 4 | 2 | 2 | 3 |
| C | Route Characteristics | 7 | 0 | 0 | 0 | 7 |
| D | Socio-Economic Correlations | 8 | 5 | 4 | 4 | 4 |
| E | Temporal (all deferred) | 5 | 0 | 0 | 0 | — |
| F | Equity (spatial only) | 6 | 3 | 2 | 2 | 4 |
| G | Advanced ML (spatial) | 5 | 2 | 0 | 0 | 5 |
| H | Accessibility Deep Dive | 4 | 1 | 0 | 0 | 4 |
| I | Economic Impact | 3 | 0 | 0 | 0 | 3 |
| J | Advanced Economic | 4 | 0 | 0 | 0 | 4 |
| **Total (spatial)** | | **50** | **22** | **13** | **13** | **37** |
| **Total (all 61)** | | **61** | **22** | **13** | **13** | **48** |

**13 of 50 spatial questions are fully answerable from Phase 0 outputs.**

### 6.2 Question-by-Question Detail

#### Category A: Coverage & Accessibility (5 answerable, 3 gaps)

| Q | Question | Verdict | Detail |
|---|----------|---------|--------|
| A1 | Routes per capita by region | Answerable | BODS routes + Census population, ground truth locked |
| A2 | Stops per 1,000 residents | Answerable | NaPTAN + Census, regional breakdown in ground_truth.json |
| A3 | Stop density vs population density mismatch | Answerable | Stops + population + LSOA area from boundaries |
| A4 | Bus desert count (0 stops) | Answerable | ground_truth.json: 4,245 LSOAs with zero stops, mapped in 02c |
| A5 | Avg distance to nearest stop | Answerable | 02h KDTree computes for every LSOA, in lsoa_accessibility.parquet |
| A6 | LAs with >50% residents >500m from stop | Gap | Have centroid distance but NOT buffer-based population coverage analysis |
| A7 | Urban vs rural coverage | Answerable | RUC 2021 joined, analyzed in 02c/02g/02h |
| A8 | High pop density + low service | Answerable | Transport deserts mapped in 02c, ranked in 02i |

#### Category B: Frequency (2 answerable, 3 gaps)

| Q | Question | Verdict | Detail |
|---|----------|---------|--------|
| B9 | Highest trips per day by region | Answerable | 02g computes per-stop and per-LSOA trip counts |
| B10 | Lowest frequency relative to population | Answerable | 02g computes weekday_trips_per_1k |
| B12 | Late-night/early-morning routes | Gap | Have first/last service times per stop but not route-level identification |
| B15 | Average headway by region | Gap | Have departure times but headway (time between consecutive buses) not computed |
| B16 | Rural vs urban frequency proportionality | Gap | Have data, no explicit proportionality index computed |
| B11, B13, B14 | (temporal) | Deferred | By design — Phase 2 |

#### Category C: Route Characteristics (0 answerable, 7 gaps)

| Q | Question | Verdict | Detail |
|---|----------|---------|--------|
| C17 | Avg route length per region | Gap | No route geometry/shapes extracted from GTFS |
| C18 | Highest mileage routes | Gap | Depends on C17 |
| C19 | Overlapping routes | Gap | No route stop sequences, no route-level embeddings |
| C20 | Routes crossing multiple LAs | Gap | No route geometry + LA boundary spatial join |
| C21 | High population, few inter-city routes | Gap | No inter-city route classification |
| C22 | Routes serving schools | Gap | No school data loaded |
| C23 | School hour vs work hour patterns | Gap | No school-hour classification of trips |

**Category C is the single largest gap. Root cause: TransXChange/GTFS route geometry (shapes.txt, JourneyPatternSection distance tags) was never extracted in Phase 0.**

#### Category D: Socio-Economic (4 answerable, 4 gaps)

| Q | Question | Verdict | Detail |
|---|----------|---------|--------|
| D24 | Deprivation vs stop density | Answerable | imd_stop_correlation = -0.0644 in ground_truth.json |
| D25 | Wealthier areas = better coverage? | Answerable | IMD income domain profiled in 02d, correlations computed |
| D26 | Unemployment vs bus accessibility | Partial | Unemployment-IMD correlation (0.792) computed, but direct unemployment-coverage correlation not highlighted |
| D27 | Elderly population vs stops | Partial | In feature matrix and correlations but not standalone analysis |
| D28 | Car ownership vs route frequency | Answerable | Part of 8 factors, in feature matrix, correlations in 02e |
| D29 | Schools per region vs stops | Gap | No school data loaded in Phase 0 |
| D30 | High deprivation + low coverage | Answerable | Transport deserts (decile 1-3 + low coverage) mapped in 02c, ranked in 02i |
| D31 | Residential vs commercial zone coverage | Gap | No business density data loaded |

#### Category E: Temporal (0 answerable — deferred by design)
All 5 questions (E32-E36) require historical data. Phase 0 is spatial only. Not a gap — this is the plan.

#### Category F: Equity (2 answerable, 4 gaps)

| Q | Question | Verdict | Detail |
|---|----------|---------|--------|
| F37 | Priority LSOAs for new routes | Answerable | 02i transport desert ranking with multi-criteria composite score |
| F38 | Weekend service gaps | Answerable | 02g identifies weekend service deserts |
| F39 | Predicted vs actual coverage (ML) | Gap | No Random Forest coverage prediction model |
| F40 | School catchment bus coverage | Gap | No school data |
| F41 | Low-income access to jobs | Gap | No employment center POI data |
| F42 | Rural vs urban equity index | Gap | No formal equity metric (Gini/Palma/Lorenz) computed |

#### Category G: Advanced ML (0 answerable, 5 gaps)

| Q | Question | Verdict | Detail |
|---|----------|---------|--------|
| G44 | Overlapping route clusters | Gap | No SentenceTransformers, no HDBSCAN, no route embeddings |
| G46 | Low frequency + high population stops | Partial | 02g classifies service tiers but no explicit cross-filter |
| G47 | Connectivity to healthcare/schools/jobs | Gap | No POI data loaded |
| G48 | DRT opportunity zones | Gap | No DRT suitability criteria defined |
| G50 | Multivariate inequality (SHAP) | Gap | No Gradient Boosting model, no SHAP |
| G45, G49 | (temporal) | Deferred | By design |

#### Category H: Accessibility Deep Dive (0 answerable, 4 gaps)

| Q | Question | Verdict | Detail |
|---|----------|---------|--------|
| H51 | Wheelchair accessible vehicles | Gap (unanswerable) | GTFS wheelchair_accessible field 80% missing nationally |
| H52 | Evening/weekend vs shift work | Partial | Evening service by IMD in 02g, but no industry-type employment data |
| H53 | Low-income connected to jobs | Gap | Same as F41 — no network connectivity analysis |
| H54 | Good coverage but poor connectivity | Gap | No unique-destination-count metric per LSOA |

#### Category I: Economic Impact (0 answerable, 3 gaps)

| Q | Question | Verdict | Detail |
|---|----------|---------|--------|
| I55 | Service quality vs business density | Gap | No business data loaded |
| I56 | Accessibility vs property values | Gap | No property price data (none available at LSOA in open data) |
| I57 | BCR for underserved areas | Gap | No BCR calculator, no TAG constants in code |

#### Category J: Advanced Economic (0 answerable, 4 gaps)

| Q | Question | Verdict | Detail |
|---|----------|---------|--------|
| J58 | BCR for top 10 underserved LSOAs | Gap | No BCR calculator |
| J59 | GDP multiplier for deprived areas | Gap | No ONS input-output multipliers |
| J60 | Jobs from 20% frequency increase | Gap | No employment impact model |
| J61 | Carbon reduction from modal shift | Gap | No BEIS conversion factors, no modal shift model |

### 6.3 Five Critical Gap Clusters

1. **Route geometry (blocks 7 questions, all of Category C).** TransXChange/GTFS shapes, stop sequences, and distances were never extracted. No route lengths, no route-level features, no overlapping route detection. This is the single largest gap.

2. **ML models (blocks 5+ questions).** No SentenceTransformer + HDBSCAN route clustering. No Random Forest coverage prediction with residual analysis. No SHAP explanations. The KMeans on LSOA features in 02e is useful but is NOT the route-level ML the old project built.

3. **Economic appraisal infrastructure (blocks 7 questions, all of I+J).** Zero BCR calculator. No TAG constants in code. No Green Book methodology. No GDP multipliers, employment impact models, or carbon calculations.

4. **Equity metrics (blocks 4+ questions).** No Gini coefficient of coverage distribution. No Palma ratio. No Lorenz curves. No Theil index. No 2SFCA (Two-Step Floating Catchment Area). The transport desert composite score in 02i is a useful precursor but not a recognized equity framework measure.

5. **Missing auxiliary datasets (blocks 5 questions).** Schools (GIAS), business density (NOMIS business counts), healthcare POI (NHS ODS) not loaded in Phase 0.

### 6.4 What Phase 0 Did Well

1. **Data foundation is rock-solid.** 9 core datasets ingested, profiled, and joined at 33,755-LSOA level with 99.9993% match rate. Ground truth locked with 103 quality checks, zero FAILs. This is what the old project never had.

2. **Improved on old project data.** IMD upgraded from 2019 to 2025. Unemployment corrected from MSOA to native LSOA (TS066 — was a wrong assumption in the old project). Car ownership (TS045) and rural/urban classification (RUC 2021) obtained — the old project listed both as "missing."

3. **Service frequency depth.** Notebooks 02g and 02h go far beyond stop counts to actual trips per day, weekday vs weekend, first/last bus, peak/off-peak, service tiers. The old project's data pipeline never extracted this from BODS.

4. **Transport desert identification.** Multi-criteria composite scoring producing a ranked list of 500 most transport-deprived LSOAs. Directly policy-relevant, immediately usable.

5. **LSOA archetype clustering.** 4 meaningful archetypes discovered through PCA + silhouette-optimized KMeans. Useful foundation for policy narratives and dashboard segmentation.

### 6.5 InsightEngine Readiness

The old project's InsightEngine (5-layer architecture) is entirely unbuilt in Aequitas:

| Layer | Status |
|-------|--------|
| Layer 1: Context Resolver | Not built |
| Layer 2: Calculators (TAG, Gini, BCR) | Not built |
| Layer 3: Metric Config | Not built |
| Layer 4: Insight Rules (10 rules) | Not built |
| Layer 5: Template Renderer (Jinja2) | Not built |
| Orchestrator | Not built |

The architecture is well-documented in the old project docs and source code, ready to be carried forward with correct data.

### 6.6 ML Model Readiness

| Model | Old Project | Aequitas Phase 0 |
|-------|-------------|-----------------|
| Route Clustering (SentenceTransformers + HDBSCAN) | 198 clusters, 5,822 routes | Not implemented. No route-level features. |
| Service Gap Detection (Isolation Forest) | 15% contamination, 1,436 gaps | Minimal proof-of-concept only (1% contamination, data quality check) |
| Coverage Prediction (Random Forest) | R²=0.089, "91% is policy-driven" | Not implemented |
| SHAP explanations | Not in old project either | Not implemented |

---

## 7. Phase 6: Source Verification & Question Quality Assessment

**Trigger:** "how meaningful and useful do you think are the questions we designed" and "there are links to the reports in one of the docs... go through all of them and tell me is everything latest"

### 7.1 Data Source Currency Check (March 2026)

| Source | Old Doc Reference | Current Status (March 2026) | Action Needed |
|--------|------------------|----------------------------|---------------|
| IMD | "IMD 2019" | **IMD 2025 released 30 Oct 2025.** 20 new indicators, 14 modified. We already use 2025. | None — we're ahead |
| NaPTAN | "767,000+ stops" | Still at beta-naptan.dft.gov.uk. ~350K GB-wide. Our filter gives 274,719 England active. | None — we're correct |
| BODS | data.bus-data.dft.gov.uk | Still active. Since June 2025, National Data Library also archives GTFS-RT. | None |
| Census 2021 | "35,672 LSOAs" | 33,755 LSOAs in England (doc mixed England+Wales). We use correct count. | None — we're correct |
| TAG Databook | "2024/25 values" | **v2.02 (Dec 2025), rebased to 2023 prices.** Car commuting £12.65/hr, bus £9.85/hr were 2024 price year — now slightly different after rebase. Minor technical VOT corrections. | **Must download v2.02 spreadsheet for current values** |
| Green Book | "3.5% discount rate" | **Still 3.5%** for first 30 years. 2026 Green Book published, retains STPR. Independent review commissioned but not complete. | None — current |
| BCR categories | "Poor <1.0 to Very High >4.0" | **Unchanged.** | None |
| Carbon values | "£75-85/tonne, bus 0.0965 kg/pkm" | 2025 GHG conversion factors published June 2025 by DESNZ. UK electricity -15%. Bus emissions factor may differ from 2022 citation. | **Must download 2025 factors** |
| RUC | Old doc said "MISSING" | **RUC 2021 released March 2025**, LSOA-level. We already have it. | None — we're ahead |
| Bus patronage | Not referenced | **3.7 billion journeys** year ending March 2025, 90% pre-pandemic. London 1.8B (down 1%), outside London 1.8B (up 4%). | New context available |
| Bus Services Act | Not referenced | **Became law 27 Oct 2025.** Franchising powers for all LTAs. £925M investment. £3 fare cap. Zero-emission mandate from 2030. | **Critical policy gap — must add** |
| GIAS Schools | get-information-schools.service.gov.uk | Still active, data last updated Jan 2025 census. | Available when needed |
| BEIS/DESNZ Carbon | Published annually | 2025 factors published June 2025. | Available when needed |
| CPT Economic Impact | Link 1 in initial_plan.md | Still accessible. £4.55 return per £1 invested. | Current |

### 7.2 Bus Services Act 2025 — Missing Policy Context

This is the biggest gap in our framework. The Bus Services Act 2025 (Royal Assent 27 October 2025) fundamentally changes the policy landscape our platform operates in:

- **All Local Transport Authorities** can now franchise bus services without Secretary of State consent
- **Municipal bus companies** can now be created (previously prohibited)
- **Route protection:** strict requirements for operators cancelling "socially necessary" services
- **£925 million** allocated for new routes, frequency improvements, route protection
- **£955 million** to support bus services until 2026
- **£3 bus fare cap** extended (raised from £2)
- **Zero-emission mandate:** no new non-zero-emission buses from 1 January 2030 at earliest
- **Enhanced Partnerships** strengthened

None of our 61 questions address franchising readiness, the impact of new LTA powers, or zero-emission transition planning. These are arguably THE policy questions for 2025-2026.

### 7.3 Question Quality Assessment

#### Strong Questions (Keep — Policy-Relevant)

These questions are what DfT officials and LTA planners actually need answers to:

- **A1-A5, A7-A8** — Coverage and accessibility fundamentals. Bread and butter of transport equity analysis.
- **B9-B10, B12** — Service frequency. Essential operational intelligence.
- **D24-D28, D30** — Deprivation, unemployment, elderly, car ownership vs coverage. The core thesis of the platform.
- **F37** — Priority LSOAs for new routes. Directly actionable. A policy maker could take this to a budget meeting.
- **F38** — Weekend service gaps. Real operational insight with clear remediation.

#### Weak or Redundant Questions (Merge or Rethink)

- **C17-C18** (average route length, highest mileage) — Technically interesting but not policy-actionable. No policy maker makes a decision based on average route length. Better framed as "route efficiency" if kept.
- **C22-C23 / D29** (school routes, school hours, schools vs stops) — Requires GIAS data we don't have, and the insight is narrow. Should be folded into a broader "access to essential services" question.
- **D31** (residential vs commercial zone coverage) — Needs business data, and the framing is vague. What policy action follows from this?
- **H51** (wheelchair accessibility) — Old project noted GTFS wheelchair_accessible field is 80% missing nationally. This question is unanswerable with available data. Drop it.
- **H52** (shift work patterns) — Requires employment-by-industry data at LSOA level that doesn't readily exist. Hard to operationalize.
- **G48** (DRT opportunity zones) — Interesting but scope creep. Demand-responsive transport is a different product and policy domain.
- **I55-I56** (business density vs service quality, accessibility vs property values) — Property values aren't available at LSOA level in open data. Business counts are available but the policy link is weak.

#### Sounds Impressive But Delivers Little

- **J59** (GDP multiplier for deprived area investment) — Without regional input-output tables, this applies a generic national multiplier (£2.00-2.40) to local areas. Looks rigorous in a report but is actually imprecise. The number is always the same regardless of which area you're looking at.
- **J60** (jobs created by 20% frequency increase) — Same problem. Employment multipliers are national-level constants; applying them to individual LSOAs is methodologically hand-wavy.
- **G50** (multivariate inequality with SHAP) — Technically interesting for a data science portfolio but policy makers won't understand SHAP values. The insight needs translation into plain language to be useful. The PCA + clustering in 02e achieves a similar goal more accessibly.

#### Questions We Should Add

These are missing from the current 61 and are arguably more important than some existing questions:

1. **Bus Services Act 2025 franchising readiness** — Which LTAs are best positioned to use new franchising powers? Based on current service levels, operator concentration, deprivation, and political readiness.

2. **Service decline mapping** — Where have services been cut or reduced? Comparing BODS archives (2023 vs 2025 snapshots) to identify areas of service withdrawal.

3. **Fare cap impact analysis** — The £2 cap ended, £3 cap in effect. Which areas are most price-sensitive? Cross-reference with IMD income domain and car ownership.

4. **Zero-emission bus transition readiness** — The Act mandates no new non-zero-emission buses from 2030. Which operators and regions are behind on electrification?

5. **Actual accessibility by journey time** — Not just "is there a stop nearby?" but "where can you actually GET TO by bus within 30/45/60 minutes?" Cumulative opportunity analysis (jobs, healthcare, education reachable). This is what 2SFCA and Hansen accessibility measure — far more meaningful than stop counts.

---

## 8. All Output Artifacts

### 8.1 Data Artifacts (data/audit/)

| File | Size | Rows | Columns | Description |
|------|------|------|---------|-------------|
| ground_truth.json | 17 KB | — | — | Locked counts, distributions, correlations |
| master_lsoa_table.parquet | 3.1 MB | 33,755 | ~30 | All LSOAs with 8 factors merged |
| lsoa_feature_matrix_clustered.parquet | 2.8 MB | 33,755 | ~20 | Feature matrix with PCA + KMeans cluster IDs |
| lsoa_service_levels.parquet | 680 KB | 33,755 | 17 | Service metrics per LSOA (weekday/weekend trips, span) |
| stop_service_profiles.parquet | 6.3 MB | 298,072 | ~15 | Per-stop service profiles (trips by day, first/last time) |
| lsoa_accessibility.parquet | 1.8 MB | 33,755 | 11 | Distance to nearest/5th stop, composite score |
| bods_stop_frequency.parquet | 2.3 MB | varies | varies | Stop-level frequency from BODS |
| bods_operator_summary.csv | 23 KB | varies | varies | Operator/agency summary |
| data_quality_audit_log.csv | 14 KB | 103 | varies | Quality checks with PASS/WARN/FAIL |
| metrics_catalog.csv | 5 KB | 14 | varies | Derived metrics with formulas |
| metrics_catalog.json | 8 KB | 14 | varies | Same in JSON format |
| data_traps.csv | 2 KB | 25 | varies | Documented data traps with mitigations |
| top_500_transport_deserts.csv | 89 KB | 500 | varies | Ranked transport desert LSOAs |
| cluster_archetypes.csv | 146 B | 4 | 2 | Archetype names and counts |

### 8.2 Documentation Created

| File | Description |
|------|-------------|
| docs/data-dictionary/naptan-stops.md | NaPTAN column definitions and filtering rules |
| docs/data-dictionary/imd-2025.md | IMD 2025 domains, sub-domains, scoring |
| docs/data-dictionary/census-ts001-population.md | Census population table structure |
| docs/data-dictionary/census-ts007a-age.md | Age structure table |
| docs/data-dictionary/census-ts021-ethnicity.md | Ethnicity table |
| docs/data-dictionary/census-ts045-car-ownership.md | Car ownership table |
| docs/data-dictionary/nomis-ts066-unemployment.md | Unemployment table |
| docs/data-dictionary/rural-urban-classification-2021.md | RUC categories |

### 8.3 Docs Brought from Old Project

| File | Description |
|------|-------------|
| docs/docs-old-project/initial_plan.md | Original requirements, 57 questions, 41 report links |
| docs/docs-old-project/uk-transport-consulting-analysis.md | Industry benchmarks, TAG/Green Book, equity frameworks |
| docs/docs-old-project/01. PROJECT_PLAN_CONSULTING_GRADE.md | Strategic vision, 6 modules |
| docs/docs-old-project/05. PROJECT_STATUS_AND_PLAN.md | 61 questions, build status, tactical plan |
| docs/docs-old-project/DATA_STRATEGY_COMPLETE.md | Question-by-question data requirements |
| docs/docs-old-project/ML_MODELS_EVALUATION_REPORT.md | ML model performance and findings |
| docs/docs-old-project/INSIGHT_ENGINE_README.md | InsightEngine architecture |

### 8.4 Notebooks

| File | Size | Description |
|------|------|-------------|
| notebooks/01_data_audit.ipynb | 251 KB | Core audit: 103 checks, ground truth, data dictionaries |
| notebooks/02_data_understanding.ipynb | 96 KB | Single-LSOA dives, 8 factors, cross-factor analysis |
| notebooks/02a_column_inventory.ipynb | 673 KB | All 238 columns classified |
| notebooks/02b_bods_deep_dive.ipynb | 439 KB | BODS operators, routes, trips, frequency |
| notebooks/02c_spatial_analysis.ipynb | 3.4 MB | Choropleth maps, density, deprivation, deserts |
| notebooks/02d_imd_subdomain_deep_dive.ipynb | 2.0 MB | IMD 7 domains, IDACI, IDAOPI |
| notebooks/02e_multivariate_clustering.ipynb | 1.4 MB | PCA, KMeans, 4 archetypes |
| notebooks/02f_cross_factor_synthesis.ipynb | 236 KB | 14 metrics, 25 traps, pipeline readiness |
| notebooks/02g_bods_service_levels.ipynb | 423 KB | Service tiers, weekend gaps, peak/off-peak |
| notebooks/02h_spatial_access.ipynb | 4.2 MB | KDTree distances, composite accessibility |
| notebooks/02i_lsoa_stories.ipynb | 504 KB | Archetypes, top 500 deserts, anomalies |

---

## 9. Ground Truth Numbers (Locked)

These numbers were verified through the data audit and are the authoritative reference for all subsequent pipeline work.

| Metric | Value | Source |
|--------|-------|--------|
| England active bus stops | 274,719 | NaPTAN (BCT/BCS/BCE, Status=active, ATCO 0xx-4xx) |
| BODS unique bus routes | 13,099 | BODS GTFS (all 9 regional feeds, deduplicated) |
| BODS total trips | 1,752,443 | BODS GTFS |
| Census 2021 England LSOAs | 33,755 | ONS Census |
| Census population (England) | 56,490,056 | ONS TS001 |
| IMD 2025 LSOAs | 33,755 | MHCLG (zero mismatch with Census) |
| NOMIS TS066 LSOAs | 33,755 | ONS NOMIS |
| Stop-to-LSOA spatial join match | 99.9993% | Point-in-polygon against BFE boundaries |
| LSOAs with zero bus stops | 4,245 | Spatial join result |
| IMD-stop correlation (Pearson) | -0.0644 | Weak negative — deprivation barely predicts coverage |
| Cluster archetypes | 4 | KMeans with silhouette optimization |
| Data quality checks | 103 | 89 PASS, 14 WARN, 0 FAIL, 0 CRITICAL |

---

## 10. Critical Findings

### 10.1 The Old Project Failed Because of Bad Foundations

The uk_bus_analytics project reached 60-70% completion but was abandoned because it built features on wrong data (7,696 LSOAs, 3M unfiltered stops, IMD 2019). Aequitas took the opposite approach: lock the data foundation first, then build. This was the right call. Our 103-check audit with zero FAILs proves the foundation is solid.

### 10.2 The InsightEngine Pattern Is Worth Carrying Forward

The Protocol-based rule system (InsightRule → InsightRegistry → evidence-gated applies/emit) with Jinja2 consulting-tone templates is well-architected. The 4-step pipeline (resolve_context → compute_metrics → apply_rules → render_templates) maps cleanly to Aequitas's pre-compute architecture. The 10 rules cover the analytical patterns we need. This is the crown jewel of the old project.

### 10.3 The Question Framework Needs Revision

The 61-question framework has strong bones but:
- **Category C is entirely blocked** by missing route geometry (7 questions)
- **Categories I+J are aspirational** — generic national multipliers applied locally look rigorous but aren't
- **Several questions are unanswerable** with open data (H51 wheelchair, I56 property values)
- **The Bus Services Act 2025 isn't addressed** — this is THE policy context for the platform's target users
- **Professional section naming needed** — "Category A/B/C" is an internal tracking system, not dashboard UX

### 10.4 TAG Values Need Refreshing

The TAG Databook was rebased from 2010 to 2023 prices in May 2025 and updated to v2.02 in December 2025. The specific values cited in our old docs (car commuting £12.65/hr, bus £9.85/hr) are from the 2024 price year and have had minor technical corrections. Before building the economic appraisal module, we must download the current v2.02 spreadsheet from GOV.UK for authoritative numbers.

### 10.5 Phase 0 Delivered More Than Expected

The service frequency analysis (02g), spatial accessibility (02h), and LSOA stories (02i) go significantly beyond what a typical "data audit" covers. These notebooks don't just profile data — they demonstrate the analytical methods and produce directly usable outputs (service tiers, accessibility scores, transport desert rankings) that can feed the pipeline.

---

## 11. What Comes Next (Phase 0 is NOT complete — EDA continues)

Phase 0 remains open until all datasets are loaded and all gap clusters are addressed. Next steps in priority order:

### Remaining Phase 0 Work — 7 EDA Layers

**Layer 0 — Data Acquisition (prerequisite for Layers 5 + 6)**
Download 6 missing datasets before starting economic appraisal and policy synthesis notebooks.
See `docs/data-downloads.md` for exact Gemini prompts to get download links.
- Census TS038 (disability — factor 9)
- NHS ODS hospitals + GP surgeries (healthcare accessibility)
- GIAS schools (education accessibility)
- TAG Databook v2.02 (BCR time values, rebased Dec 2025)
- DESNZ GHG Conversion Factors 2025 (carbon/modal shift)
- NOMIS BRES (employment counts by LSOA — job accessibility proxy)

**Layer 1 — Route Geometry**
- Extract shapes.txt (3.2 GB, confirmed in bods_gtfs_all.zip) → route lengths, stop sequences
- Overlapping routes, cross-LA boundary routes
- Unblocks all 7 Category C questions

**Layer 2 — Service Quality Depth**
- Headway computation (consecutive departure gaps per stop per time period)
- Reliability proxy: coefficient of variation of headways
- Buffer-based population coverage (400m threshold, population-weighted — not just centroid)
- Evening isolation score (no service after 7pm), Sunday desert classification
- Peak vs interpeak ratio as policy metric

**Layer 3 — Equity Framework**
- Gini coefficient of bus service distribution across LSOAs
- Lorenz curve (cumulative coverage vs cumulative population)
- Palma ratio (top 10% vs bottom 40% — preferred by UN/OECD)
- Concentration Index (coverage inequality correlated with socio-economic rank)
- Dissimilarity Index (spatial segregation of access)
- Triple deprivation intersectionality matrix (IMD + no-car + elderly + disability)
- Combined Vulnerability Score aligned with DfT/ONS frameworks

**Layer 4 — ML Suite**
- HDBSCAN upgrade over KMeans + Gaussian Mixture Models (soft cluster membership)
- Route clustering: SentenceTransformers + HDBSCAN on route names + stop sequences + geometry
- Coverage prediction: Random Forest + XGBoost/LightGBM + SHAP (R²~0.089 expected — 91% policy-driven variance IS the finding)
- Anomaly detection: Isolation Forest (production, not 1%) + Local Outlier Factor
- 2SFCA (Two-Step Floating Catchment Area) accessibility — industry standard, used in NHS + DfT research
- No true isochrones — deferred to Phase 4 RAG chatbot as on-demand query

**Layer 5 — Economic Appraisal** (requires TAG v2.02 + DESNZ downloads first)
- BCR calculator (Green Book methodology, TAG v2.02 values)
- Investment gap: cost to bring bottom deprivation decile to median service level
- Modal shift + elasticities (DfT published: fare -0.4 to -0.6, frequency +0.4 to +0.7)
- Car dependency reduction potential by LSOA
- Carbon reduction from modal shift (DESNZ 2025 factors)
- GDP multipliers + employment impact (note: applying national multipliers to LSOAs is methodologically limited — frame as investment gap, not precision economics)

**Layer 6 — Policy Synthesis** (requires NHS ODS + GIAS + NOMIS BRES downloads first)
- Bus Services Act 2025: LTA franchising readiness index (HHI + service level + deprivation + operator concentration)
- Operator market analysis: HHI per region, operator presence vs coverage gaps
- Job accessibility index (NOMIS BRES employment counts as employment centre proxy)
- Healthcare accessibility gap (NHS ODS hospitals + GP surgeries vs bus coverage)
- Education accessibility (GIAS schools vs bus coverage)
- Policy scenario modelling: parameterised scenarios on existing data
  - Scenario A: restore frequency to median in bottom deprivation decile → cost, BCR, modal shift, carbon
  - Scenario B: extend last bus to 11pm in transport deserts → population affected, employment impact
  - Scenario C: introduce DRT in rural elderly archetypes → cost per trip vs fixed route

### After Phase 0
- Revise question framework (drop H51 wheelchair unanswerable, merge weak C17-C18, add Bus Services Act questions, apply professional section naming)
- Design pipeline architecture (informed by InsightEngine patterns, gap analysis, revised questions)
- Build Phase 1 pipeline — ingestion → processing → validation → Parquet → DuckDB
