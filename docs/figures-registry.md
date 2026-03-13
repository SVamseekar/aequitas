# Aequitas — Figures Registry

Single source of truth for every specific number, rate, cost, correlation, and statistical claim in the project.

**Rule:** No figure enters any notebook, pipeline, narrative, or document without a registry entry.
**Last updated:** 2026-03-12

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
| GT-023 | GIAS open schools (England, geocoded) | 26,503 | ✅ Confirmed | 03d_schools_gias.ipynb | Open only, 6 Scottish schools filtered out; 97.8% coord coverage |
| GT-024 | GIAS secondary-equiv schools (England) | 3,412 | ✅ Confirmed | 03d_schools_gias.ipynb | Secondary + All-through + Middle deemed secondary; geocoded England only |
| GT-025 | BRES England MSOAs (2023) | 6,791 | ✅ Confirmed | 03e_employment_bres.ipynb | 27.3M total employees; LSOA level suppressed by ONS |
| GT-026 | LSOAs with employment proxy | 31,217 (92.5%) | ✅ Confirmed | 03e_employment_bres.ipynb | Derived from LA-level BRES aggregation; 2,538 LSOAs unmatched (small LAs) |

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
| ST-007 | Coverage prediction R² | TBD | ❌ Unverified | Old project reported ~0.089 but used wrong data (7,696 LSOAs, IMD 2019) | Re-run Random Forest in Layer 4 EDA on correct Aequitas data. Do not cite 0.089 until re-derived. |
| ST-008 | Disability % (TS038, England mean) | 17.49% | ✅ Confirmed | 03a_disability_ts038.ipynb | Disabled under Equality Act / total population |
| ST-009 | Disability % range (TS038) | 1.81%–44.68% | ✅ Confirmed | 03a_disability_ts038.ipynb | England LSOAs only |

---

## Category 3 — Transport Appraisal Constants (TAG / Green Book)
*Must use TAG Databook v2.03fc (Dec 2025, rebased 2023 prices, includes May 2026 changes). File downloaded — extract values before economic appraisal EDA.*

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

---

## Category 5 — Demand Elasticities
*DfT published values. Verify against current TAG Unit A5.4 before use in modal shift calculations.*

| ID | Figure | Value | Status | Correct Source | Fix |
|----|--------|-------|--------|---------------|-----|
| EL-001 | Bus fare elasticity | -0.4 to -0.6 | ⚠️ Stale | DfT TAG Unit A5.4 (current version) | Old project cited these but did not trace to specific TAG version. Verify before use. |
| EL-002 | Bus frequency elasticity | +0.4 to +0.7 | ⚠️ Stale | DfT TAG Unit A5.4 (current version) | Same — verify before use in modal shift calculations |

---

## Category 6 — Infrastructure / Operating Costs
*No source ever cited for these. Do not use until properly sourced.*

| ID | Figure | Value | Status | Correct Source | Fix |
|----|--------|-------|--------|---------------|-----|
| COST-001 | Bus stop construction cost (standard) | £15,000 | ❌ Unverified | DfT WebTAG unit costs or current DfT cost database | Find current DfT source before building investment appraisal |
| COST-002 | Route annual operating cost (urban) | £250,000/yr | ❌ Unverified | DfT WebTAG unit costs or CPT operator benchmarks | Same |
| COST-003 | Route annual operating cost (rural) | £180,000/yr | ❌ Unverified | DfT WebTAG unit costs or CPT operator benchmarks | Same |

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
| 03g_desnz_carbon.ipynb | CO2-001, CO2-002, CO2-003 | See Category 4 |
| 03h_codepoint_postcodes.ipynb | GT-020 | See Category 1 |
| *Series 04 analytical layers (pending)* | TBD | Add here as notebooks complete |
