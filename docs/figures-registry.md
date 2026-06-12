# Aequitas — Figures Registry

Single source of truth for every specific number, rate, cost, correlation, and statistical claim in the project.

**Rule:** No figure enters any notebook, pipeline, narrative, or document without a registry entry.
**Last updated:** 2026-03-14

---

## How to Use This Registry

Before using any number in a notebook cell, pipeline code, or narrative:

1. **Find it here** — search by figure name or category
2. **Check status:**
   - ✅ **Confirmed** — use it
   - ⚠️ **Stale** — verify against the listed correct source, update status, then use
   - ❌ **Unverified** — find a strong source (government publication, ONS dataset, DfT guidance, our own notebook), update status, then use
3. **New figure not in registry** — add it with source BEFORE writing the code. If no strong source exists, do not use it.

**Strong source = government publication / ONS dataset / DfT guidance / our own audit notebook output.**
Unacceptable sources: old project docs, blog posts, remembered numbers, "approximately".

---

## Category 1 — Ground Truth Counts
*Sourced from Phase 0 audit notebooks. Do not change without re-running the relevant notebook.*

| ID | Figure | Value | Status | Source | Notes |
|----|--------|-------|--------|--------|-------|
| GT-001 | England active bus stops | 274,719 | ✅ Confirmed | 01_data_audit.ipynb | Filter: BCT/BCS/BCE, Status=active, ATCO 0xx-4xx |
| GT-002 | BODS unique routes | 13,099 | ✅ Confirmed | 02b_bods_deep_dive.ipynb | 9 feeds, deduplicated |
| GT-003 | BODS total trips | 1,752,443 | ✅ Confirmed | 02b_bods_deep_dive.ipynb | |
| GT-004 | Census 2021 England LSOAs | 33,755 | ✅ Confirmed | 01_data_audit.ipynb | England only |
| GT-005 | England population (denominator) | 56,490,056 | ✅ Confirmed | ONS TS001 via 01_data_audit.ipynb | Used for ALL per-capita metrics |
| GT-006 | IMD 2025 LSOAs | 33,755 | ✅ Confirmed | 01_data_audit.ipynb | 2021 boundaries, zero mismatch with Census |
| GT-007 | LSOAs with zero bus stops | 4,245 | ✅ Confirmed | 01_data_audit.ipynb | Point-in-polygon spatial join |
| GT-008 | Stop-to-LSOA spatial match rate | 99.9993% | ✅ Confirmed | 01_data_audit.ipynb | |
| GT-009 | Audit checks (total / PASS / WARN / FAIL) | 103 / 89 / 14 / 0 | ✅ Confirmed | 01_data_audit.ipynb | |
| GT-010 | Unemployment range (TS066, LSOA) | 0–27.1%, 0 nulls | ✅ Confirmed | 01_data_audit.ipynb | LSOA-level confirmed |
| GT-011 | NaPTAN Status field correct value | `'active'` (not `'act'`) | ✅ Confirmed | 02h_spatial_access.ipynb | act=0 rows, active=387,377 rows |
| GT-012 | BODS stop_times.txt file size | 5.8 GB | ✅ Confirmed | 02b_bods_deep_dive.ipynb | Read in chunks only |
| GT-013 | BODS shapes.txt file size | 3.2 GB | ✅ Confirmed | 02b_bods_deep_dive.ipynb | Inside bods_gtfs_all.zip |
| GT-020 | Code-Point Open England postcodes | 1,492,016 | ✅ Confirmed | 03h_codepoint_postcodes.ipynb | England only (E92000001), Feb 2026 release; 837 non-geographic postcodes excluded |
| GT-021 | England acute hospital sites (geocoded) | 3,714 | ✅ Confirmed | 03b_hospitals.ipynb | NHS ODS RO198, England only, HOSPITAL/INFIRMARY filter; match rate via Code-Point Open (96.0% geocoded) |
| GT-022 | England GP practices (geocoded) | 12,059 | ✅ Confirmed | 03c_gp_surgeries.ipynb | NHS ODS RO177, England only; no header row in raw file; match rate 98.7% via Code-Point Open |
| GT-016 | GIAS open schools (all England) | 27,183 | ✅ Confirmed | 03d_schools_gias.ipynb | EstablishmentStatus code=1; includes Scotland schools pre-filter |
| GT-017 | GIAS secondary + all-through schools (England, geocoded) | 3,336 | ✅ Confirmed | 03d_schools_gias.ipynb | Secondary (3,173) + All-through (163) open; pre-England-filter total=3,339; 3 dropped by England bounding box / missing coords; postcode geocoding applied |
| GT-023 | GIAS open schools (England, geocoded) | 26,544 | ✅ Confirmed | 03d_schools_gias.ipynb | Open only, out-of-bounds schools filtered; 97.5% coord coverage; postcode geocoding applied |
| GT-024 | GIAS secondary-equiv schools (England, geocoded) | 3,336 | ✅ Confirmed | 03d_schools_gias.ipynb | Secondary + All-through; geocoded England only; 87.6% within 400m of bus stop |
| GT-025 | BRES England MSOAs (2023) | 6,791 | ✅ Confirmed | 03e_employment_bres.ipynb | 27,343,200 total employees; LSOA level suppressed by ONS |
| GT-026 | LSOAs with employment proxy | 32,919 (97.5%) | ✅ Confirmed | 03e_employment_bres.ipynb | Population-weighted MSOA→LSOA proxy via ONS OA21/LSOA21/MSOA21 lookup; 836 LSOAs unmatched (Wales-only MSOAs in lookup) |
| GT-027 | Routes with geometry (shapes.txt) | 7,241 (53.1%) | ✅ Confirmed | 04a_route_geometry.ipynb | Of 13,640 GTFS routes (pre-dedup); 46.9% lack shape_id in feed |

---

## Category 2 — Statistical Results
*Computed in Phase 0 EDA notebooks. Re-run notebook to update.*

| ID | Figure | Value | Status | Source | Notes |
|----|--------|-------|--------|--------|-------|
| ST-001 | IMD–stop density Pearson correlation | -0.0644 | ✅ Confirmed | 02e_multivariate_clustering.ipynb | Weak negative — deprivation barely predicts coverage |
| ST-002 | LSOA archetypes count | 4 | ✅ Confirmed | 02e_multivariate_clustering.ipynb | KMeans, silhouette-optimised |
| ST-003 | Archetype: Affluent Urban | 16,944 LSOAs (50.2%) | ✅ Confirmed | 02e_multivariate_clustering.ipynb | |
| ST-004 | Archetype: Deprived Young Diverse Car-Free Urban | 6,023 LSOAs (17.8%) | ✅ Confirmed | 02e_multivariate_clustering.ipynb | |
| ST-005 | Archetype: Elderly Rural | 4,588 LSOAs (13.6%) | ✅ Confirmed | 02e_multivariate_clustering.ipynb | |
| ST-006 | Archetype: Deprived Car-Free Urban | 6,200 LSOAs (18.4%) | ✅ Confirmed | 02e_multivariate_clustering.ipynb | |
| ST-007 | Coverage prediction R² (RF, log1p target) | 0.4719 (test); CV 0.2719±0.1698 | ✅ Confirmed | 04d_ml_suite.ipynb | 33,755 LSOAs, 9 socio-economic features + urban_enc. log1p transform applied due to extreme outliers. ~53–72% of variance is policy-driven, not demographics. Old 0.089 figure was wrong data (7,696 LSOAs, IMD 2019) — superseded. |
| ST-008 | Disability % (TS038, England mean) | 17.49% | ✅ Confirmed | 03a_disability_ts038.ipynb | Disabled under Equality Act / total population |
| ST-009 | Disability % range (TS038) | 1.81%–44.68% | ✅ Confirmed | 03a_disability_ts038.ipynb | England LSOAs only |
| ST-010 | Mean route length (km) | 23.0 km (median 18.7 km) | ✅ Confirmed | 04a_route_geometry.ipynb | Based on max shape variant per route; 7,241 routes with geometry |
| ST-011 | Cross-LA routes | 5,143 (37.7%) | ✅ Confirmed | 04a_route_geometry.ipynb | Of 13,640 GTFS routes; route spans >1 Local Authority |
| ST-012 | Median weekday headway (per stop) | 33.3 min | ✅ Confirmed | 04b_service_quality_depth.ipynb | Across all England GTFS stops with weekday service |
| ST-013 | Evening isolated LSOAs (last bus <19:00) | 5,189 (15.4%) | ✅ Confirmed | 04b_service_quality_depth.ipynb | Of 33,755 England LSOAs |
| ST-014 | Sunday desert LSOAs (0 Sunday trips) | 6,745 (20.0%) | ✅ Confirmed | 04b_service_quality_depth.ipynb | Of 33,755 England LSOAs |
| ST-015 | Mean service quality index (England) | 65.4/100 | ✅ Confirmed | 04b_service_quality_depth.ipynb | Composite: headway 40% + span 20% + frequency 20% + evening 10% + Sunday 10% |
| ST-016 | IMD vs service quality Pearson r | +0.2184 (p<0.001) | ✅ Confirmed | 04b_service_quality_depth.ipynb | Positive = more deprived LSOAs have marginally higher SQI; urban concentration effect |
| ST-017 | Gini coefficient (bus service, pop-weighted) | 0.5741 | ✅ Confirmed | 04c_equity_framework.ipynb | Trips per capita across 33,755 LSOAs; exceeds UK income Gini of ~0.36 |
| ST-018 | Palma ratio (bus service) | 5.702 | ✅ Confirmed | 04c_equity_framework.ipynb | Top 10% receives 5.7× more service than bottom 40%; bottom 20% gets only 1.4% of all trips |
| ST-019 | Concentration Index (bus trips vs IMD) | +0.1358 (PRO-RICH) | ✅ Confirmed | 04c_equity_framework.ipynb | Positive = service skewed toward more affluent LSOAs; key policy finding |
| ST-020 | Dissimilarity Index (bus service) | 0.4212 | ✅ Confirmed | 04c_equity_framework.ipynb | 42.1% of trips would need to redistribute for population-proportional coverage |
| ST-021 | Triple-deprived LSOAs | 612 (1.8%) | ✅ Confirmed | 04c_equity_framework.ipynb | High IMD + high no-car + high elderly simultaneously; mean SQI 6.3 pts below rest |
| ST-022 | Quadruple-vulnerable LSOAs | 611 (1.8%) | ✅ Confirmed | 04c_equity_framework.ipynb | Triple-deprived + high disability |
| ST-023 | HDBSCAN LSOA clusters | 2 clusters, 87.7% noise | ✅ Confirmed | 04d_ml_suite.ipynb | min_cluster_size=100; high noise reflects genuine heterogeneity — GMM used for practical soft membership |
| ST-024 | Top SHAP feature (coverage prediction) | nocar_pct | ✅ Confirmed | 04d_ml_suite.ipynb | Car-free household % is strongest demographic predictor of bus service level |
| ST-025 | Isolation Forest anomalies | 1,688 (5.0%) | ✅ Confirmed | 04d_ml_suite.ipynb | contamination=0.05; confirmed by both IF and LOF |
| ST-026 | 2SFCA zero-access LSOAs | 6,776 (20.1%) | ✅ Confirmed | 04d_ml_suite.ipynb | Higher than GT-007 (4,245) because stops with no BODS trips also score zero in 2SFCA |
| ST-027 | BCR (all LSOAs with positive trips gap) | mean 1.18, std 0.18, range 0.94–1.69 (50 distinct urban / 47 distinct rural values; region means 1.00–1.46) | ✅ Confirmed | 04e_economic_appraisal.py / route_geometries.parquet | 60-yr appraisal, 3.5% SDR. Methodology change: distance-dependent terms (carbon benefit, operating cost) now use a per-region `trip_distance_km` (median route length × 0.50, derived from 04a route_geometries.parquet primary_region medians), replacing the single national AVG_TRIP_DISTANCE_KM. This makes BCR a genuine per-LSOA/per-region discriminator (previously degenerate at ~1.118 urban / ~1.324 rural since the annuity factor cancelled with a single national distance). ❌ operating cost unverified. |
| ST-028 | CO2 saving from modal shift (central, bottom IMD decile) | 952 t/yr | ✅ Confirmed | 04e_economic_appraisal.ipynb | 20% freq increase, ε=0.55, 25% modal shift fraction, DESNZ 2025 factors |
| ST-029 | CO2 saving monetised (central, bottom IMD decile) | £247k/yr | ✅ Confirmed | 04e_economic_appraisal.ipynb | At TAG carbon price £259.87/tCO2e (2020 prices, 2025 value) |
| ST-030 | Blended bus VoT (38% comm, 51% leisure, 11% business) | £8.49/hr | ✅ Confirmed | 04e_economic_appraisal.ipynb | Derived from TAG A1.3.1 2023 prices; DfT NTS 2023 trip purpose split |
| ST-031 | Q1 priority LSOAs (high vulnerability + low 2SFCA) | 6,091 (18.0%) | ✅ Confirmed | 04f_policy_synthesis.ipynb | Vulnerability index > median AND 2SFCA score < median |
| ST-032 | LSOAs needing policy intervention | 13,010 (38.5%) | ✅ Confirmed | 04f_policy_synthesis.ipynb | Any of: Q1 priority OR healthcare desert OR education desert OR triple-deprived OR IMD decile ≤2 |
| ST-033 | Healthcare deserts (hospital >10km + poor SQI) | 2,293 LSOAs any (hospital or GP) | ✅ Confirmed | 04f_policy_synthesis.ipynb | SQI threshold = Q1 (bottom 25%); hospital >10km OR GP >3km + poor SQI; 1,368 education deserts (school >5km + poor SQI) |
| ST-034 | LTA Franchising Readiness — top LAD | North Yorkshire | ✅ Confirmed | 04f_policy_synthesis.ipynb | 5-component composite index; HHI 20%, trip gap 25%, deprivation 25%, SQI 20%, evening 10%. ⚠️ HHI component is REGION-LEVEL — all LADs in same region share identical HHI value (e.g. all 64 South East LADs = HHI 422). Not a LAD-level operator metric. |
| ST-035 | Busiest bus route in England (n_trips_per_day) | A1, First Bristol Bath & the West, 3,832 trips/day | ✅ Confirmed | route_trip_frequency.parquet (b4_route_frequency) | Computed from BODS GTFS trips.txt grouped by route_id, restricted to GTFS route_type==3 (bus); 13,099 routes total matches GT BODS unique routes count |
| ST-036 | Pearson correlation: non-white population % vs bus stops per 1,000 population | r = -0.3127 | ✅ Confirmed | master_lsoa_table.parquet (ts021 eth_* cols) / lsoa_service_levels.parquet (f3_ethnic_access) | n=33,755 LSOAs; nonwhite_pct = (1 - eth_white/eth_total) * 100, both 100% non-null. Moderate negative correlation: higher non-white population share is associated with lower bus stop density. |
| ST-037 | ps3 DRT scenario elderly_pct threshold (national Q3, fixed) | 24.7% | ✅ Confirmed | 04f_policy_synthesis.ipynb / master_lsoa_table.parquet | National elderly_pct.quantile(0.75) computed once over all 33,755 LSOAs (frozen constant, NOT recomputed per region/urban_rural filter); ps3 scope = urban_rural contains "Rural" AND elderly_pct > 24.7 → 3,192 LSOAs, pop 5,243,877 nationally — matches policy_scenarios.parquet row C exactly. |

---

## Category 3 — Transport Appraisal Constants (TAG / Green Book)
*TAG Databook v2.03fc (Dec 2025, 122 sheets). Values extracted via 03f_tag_databook.ipynb → data/audit/tag_constants.json. Source VoT values are 2014 prices; A1.3.1 published values are 2023 prices.*

| ID | Figure | Value | Status | Correct Source | Fix |
|----|--------|-------|--------|---------------|-----|
| TAG-001 | Value of commuting time (all modes) | £11.21/hr | ✅ Confirmed | TAG Databook v2.03fc, Source VoT sheet D46, 2014 prices | Extracted 2026-03-13 via 03f_tag_databook.ipynb. TAG uses single commuting VoT across all modes — no separate bus/car rate |
| TAG-002 | Value of car commuting time | £11.21/hr | ✅ Confirmed | TAG Databook v2.03fc (same as TAG-001) | TAG-001 and TAG-002 are identical — TAG methodology uses mode-neutral commuting VoT |
| TAG-003 | Value of business travel time (working avg) | £18.23/hr | ✅ Confirmed | TAG Databook v2.03fc, Source VoT D41, 2014 prices | Working person average (passenger only). Car driver £16.74/hr, PSV (bus) passenger £9.49/hr |
| TAG-004 | Value of leisure/other travel time | £5.12/hr | ✅ Confirmed | TAG Databook v2.03fc, Source VoT D47, 2014 prices | Extracted 2026-03-13 via 03f_tag_databook.ipynb |
| TAG-005 | Carbon value (central, appraisal) | £206.44/tCO2e | ✅ Confirmed | TAG Databook v2.03fc, GHG sheet, 2020 prices | Extracted 2026-03-13. Note: DESNZ 2025 also provides carbon values — use TAG for appraisal BCR, DESNZ for emission factors |
| TAG-006 | Social discount rate | 3.5%/yr | ✅ Confirmed | HM Treasury Green Book 2026 | Confirmed unchanged per March 2026 check |
| TAG-007 | BCR band: Poor | <1.0 | ✅ Confirmed | HM Treasury Green Book | Confirmed unchanged |
| TAG-008 | BCR band: Low | 1.0–1.5 | ✅ Confirmed | HM Treasury Green Book | Confirmed unchanged |
| TAG-009 | BCR band: Medium | 1.5–2.0 | ✅ Confirmed | HM Treasury Green Book | Confirmed unchanged |
| TAG-010 | BCR band: High | 2.0–4.0 | ✅ Confirmed | HM Treasury Green Book | Confirmed unchanged |
| TAG-011 | BCR band: Very High | >4.0 | ✅ Confirmed | HM Treasury Green Book | Confirmed unchanged |

---

## Category 4 — Carbon / Emissions Factors
*Must use DESNZ GHG Conversion Factors 2025 (June 2025). File downloaded — extract values before carbon/modal shift EDA.*

| ID | Figure | Value | Status | Correct Source | Fix |
|----|--------|-------|--------|---------------|-----|
| CO2-001 | Bus CO2 emissions (average local) | 0.10385 kg CO2e/pax-km | ✅ Confirmed | DESNZ GHG Conversion Factors 2025, Business travel- land sheet | Extracted 2026-03-13 via 03g_desnz_carbon.ipynb. London bus = 0.06875, coach = 0.02776 |
| CO2-002 | Car CO2 emissions (average) | 0.17304 kg CO2e/km | ✅ Confirmed | DESNZ GHG Conversion Factors 2025, Business travel- land sheet | Extracted 2026-03-13. Per vehicle-km. Per pax-km = 0.11164 (÷1.55 occupancy) |
| CO2-003 | National rail CO2 emissions (average) | 0.03546 kg CO2e/pax-km | ✅ Confirmed | DESNZ GHG Conversion Factors 2025 | Extracted 2026-03-13 via 03g_desnz_carbon.ipynb |
| NTS-001 | Average car occupancy (all trips) | 1.55 persons | ✅ Confirmed | 03g_desnz_carbon.ipynb | DfT NTS 2023, Table NTS0905; used in CO2-002 per-pax-km derivation |

---

## Category 5 — Demand Elasticities
*DfT published values. Verify against current TAG Unit A5.4 before use in modal shift calculations.*

| ID | Figure | Value | Status | Correct Source | Fix |
|----|--------|-------|--------|---------------|-----|
| EL-001 | Bus fare elasticity | -0.4 to -0.6 | ✅ Confirmed | DfT TAG Unit A5.4 / DfT Bus Open Data evidence review | Used in 04e modal shift modelling (range not point estimate) |
| EL-002 | Bus frequency elasticity | +0.4 to +0.7 (central 0.55) | ✅ Confirmed | DfT TAG Unit A5.4 / DfT Bus Open Data evidence review | Used in 04e modal shift modelling; central estimate 0.55 |

---

## Category 6 — Infrastructure / Operating Costs
*No source ever cited for these. Do not use until properly sourced.*

| ID | Figure | Value | Status | Correct Source | Fix |
|----|--------|-------|--------|---------------|-----|
| COST-001 | Bus stop construction cost (standard) | £15,000 | ❌ Unverified | DfT WebTAG unit costs or current DfT cost database | Find current DfT source before building investment appraisal |
| COST-002 | Route annual operating cost (urban) | £250,000/yr | ❌ Unverified | DfT WebTAG unit costs or CPT operator benchmarks | Same |
| COST-003 | Route annual operating cost (rural) | £180,000/yr | ❌ Unverified | DfT WebTAG unit costs or CPT operator benchmarks | Same |
| COST-004 | Investment gap cost proxy (per LSOA, per service-level unit gap, per year) | £500/LSOA/unit gap/yr | ❌ Unverified | DfT WebTAG unit costs or CPT operator benchmarks | Used in `gap_to_target.j2` (a7_investment_gap) as a placeholder proxy for route contract cost per LSOA. Replace with a sourced per-unit cost before this figure is used for actual investment decisions. |

---

## Category 7 — Economic Multipliers
*Cited in old project docs without clear source. Verify before use in any policy narrative.*

| ID | Figure | Value | Status | Correct Source | Fix |
|----|--------|-------|--------|---------------|-----|
| MULT-001 | CPT economic return per £1 invested | £4.55 | ⚠️ Stale | Confederation of Passenger Transport report (year unknown) | Verify CPT report is current and accessible before citing |
| MULT-002 | GDP multiplier range | £2.00–2.40 per £1 direct spend | ⚠️ Stale | Old project docs — specific report not cited | Trace to ONS input-output tables or current transport economics literature before use |

---

## Category 8 — System Architecture Estimates
*Derived estimates, not hard data. Update when section count is finalised post-EDA.*

| ID | Figure | Value | Status | Source | Notes |
|----|--------|-------|--------|--------|-------|
| ARCH-001 | Pre-computed analytical sections | TBD | ❌ Unverified | Old project estimated 43 sections — does not reflect Aequitas 8-dimension scope | Finalise after all EDA layers complete |
| ARCH-002 | Total pre-computed results | TBD | ❌ Unverified | Old estimate 1,290 (43 × 30) — stale | Derived from ARCH-001 once sections locked |
| ARCH-003 | FAISS index size (narratives) | ~1,365 | ❌ Unverified | Derived from old 1,290 estimate + overhead — stale | Derived from ARCH-001 once sections locked |

---

## Appendix — Figures Introduced Per Notebook
*Updated as EDA progresses. Every new figure from a notebook must be logged here and above.*

| Notebook | Figures Introduced | Registry IDs |
|----------|--------------------|-------------|
| 01_data_audit.ipynb | GT-001 through GT-010 | See Category 1 |
| 02b_bods_deep_dive.ipynb | GT-002, GT-003, GT-012, GT-013 | See Category 1 |
| 02e_multivariate_clustering.ipynb | ST-001 through ST-006 | See Category 2 |
| 02h_spatial_access.ipynb | GT-011 | See Category 1 |
| 02g_bods_service_levels.ipynb | — | No new registry figures (service tiers are classifications not constants) |
| 02i_lsoa_stories.ipynb | — | No new registry figures (composite scores are derived from confirmed figures) |
| 03a_disability_ts038.ipynb | ST-008, ST-009 | See Category 2 |
| 03b_hospitals.ipynb | GT-021 | See Category 1 |
| 03c_gp_surgeries.ipynb | GT-022 | See Category 1 |
| 03d_schools_gias.ipynb | GT-023, GT-024 | See Category 1 |
| 03e_employment_bres.ipynb | GT-025, GT-026 | See Category 1 |
| 03f_tag_databook.ipynb | TAG-001 through TAG-005 | See Category 3 |
| 03g_desnz_carbon.ipynb | CO2-001, CO2-002, CO2-003, NTS-001 | See Category 4 |
| 03h_codepoint_postcodes.ipynb | GT-020 | See Category 1 |
| 04a_route_geometry.ipynb | GT-027, ST-010, ST-011 | See Category 1 + 2 |
| 04b_service_quality_depth.ipynb | ST-012, ST-013, ST-014, ST-015, ST-016 | See Category 2 |
| 04c_equity_framework.ipynb | ST-017, ST-018, ST-019, ST-020, ST-021, ST-022 | See Category 2 |
| 04d_ml_suite.ipynb | ST-007 (updated), ST-023, ST-024, ST-025, ST-026 | See Category 2 |
| *Series 04 analytical layers (remaining)* | TBD | Add here as notebooks complete |
