# Aequitas — Phase 0 Session Report

**Date:** 13 March 2026
**Branch:** main
**Commits this session:** 9

---

## What Was Done

### Series 03 — New Dataset Audits

All 8 Series 03 notebooks now exist and have been executed. However only 03a, 03b, 03c, and 03h are fully production-grade (plan-compliant + code quality reviewed). The others (03d–03g) were built quickly in the previous session and need to be rebuilt to the same standard.

| Notebook | Status | Output Artifact | Notes |
|---|---|---|---|
| 03a_disability_ts038 | ✅ Full (plan-compliant + reviewed) | master_lsoa_table.parquet (+2 cols) | Factor 9 integrated |
| 03b_hospitals | ✅ Full (plan-compliant + reviewed) | hospitals_geocoded.parquet (3,870 rows, 156 NaN) | Spatial plots, type categorisation |
| 03c_gp_surgeries | ✅ Full (plan-compliant + reviewed) | gp_surgeries_geocoded.parquet (12,213 rows) | Density per 100k, GP–IMD correlation |
| 03d_schools_gias | ⚠️ Quick build only — needs rebuild | schools_geocoded.parquet | Missing: 135-col inventory, KDTree bus stop proximity, two output files |
| 03e_employment_bres | ⚠️ Quick build only — needs rebuild | lsoa_employment_proxy.parquet | Missing: histogram, LSOA→MSOA proper mapping, employment vs IMD cross-ref |
| 03f_tag_databook | ⚠️ Quick build only — needs rebuild | tag_constants.json | Missing: all sheet names documented, A1.3.7 VOC tab, architecture.md update |
| 03g_desnz_carbon | ⚠️ Quick build only — needs rebuild | desnz_carbon_constants.json | Missing: scope documentation, architecture.md update, file renamed to desnz_carbon_factors.json |
| 03h_codepoint_postcodes | ✅ Full (plan-compliant + reviewed) | postcode_lookup.parquet (1,492,016 rows) | All 120 CSVs profiled |

### figures-registry.md
- TAG-001–005: updated from ⚠️ Stale → ✅ Confirmed
- CO2-001–003: updated from ⚠️ Stale → ✅ Confirmed
- GT-021 (hospitals), GT-022 (GPs), GT-023–026 (schools, employment): added

---

## What Remains Before Series 04

### Immediate (03d–03g need rebuilding to plan standard)

- **03d_schools_gias**: rebuild with 135-column inventory → `gias_column_inventory.csv`, KDTree nearest bus stop per school, two output files (`schools_secondary_geocoded.parquet` + `schools_all_open_geocoded.parquet`)
- **03e_employment_bres**: rebuild with employment histogram, IMD cross-reference (employment deserts vs deprivation), validate proxy sums equal MSOA totals
- **03f_tag_databook**: rebuild documenting all sheet names, extract A1.3.7 (Vehicle Operating Costs), document each value with cell reference and stale comparison, update `memory/architecture.md`
- **03g_desnz_carbon**: rebuild documenting scope (WTT vs TTW), rename output to `desnz_carbon_factors.json`, update `memory/architecture.md`

### Then Series 04 (6 analytical layer notebooks)

Per plan dependency order:
1. **04a_route_geometry** — BODS shapes.txt → route lengths, stop sequences, cross-LA routes
2. **04b_service_quality_depth** — headway, evening isolation, Sunday deserts, peak ratios
3. **04c_equity_framework** — Gini, Lorenz, Palma, Concentration Index, vulnerability index
4. **04d_ml_suite** — HDBSCAN, route clustering, RF+SHAP, Isolation Forest, 2SFCA
5. **04e_economic_appraisal** — BCR, investment gap, modal shift, carbon reduction
6. **04f_policy_synthesis** — Bus Services Act readiness, HHI, policy scenario modelling, job/healthcare/education accessibility

---

## Key Numbers (confirmed this session)

| Figure | Value | Source |
|---|---|---|
| England acute hospitals (total) | 3,870 | NHS ODS via ORD API |
| England acute hospitals (geocoded) | 3,714 (96.0%) | 03b, Code-Point Open |
| England GP practices | 12,213 | NHS ODS via ORD API |
| England GPs (geocoded) | 12,059 (98.7%) | 03c, Code-Point Open |
| National GP density | 21.35 per 100,000 | 03c |
| GP–IMD Pearson correlation | -0.059 (p=0.57) | 03c, weak negative |
| TAG commuting VoT (all modes) | £11.21/hr | TAG v2.03fc, Source VoT D46 |
| TAG business VoT (working avg) | £18.23/hr | TAG v2.03fc, Source VoT D41 |
| TAG leisure VoT | £5.12/hr | TAG v2.03fc, Source VoT D47 |
| Bus CO2 (avg local) | 0.10385 kg CO2e/pax-km | DESNZ 2025 |
| Car CO2 (avg) | 0.17304 kg CO2e/km | DESNZ 2025 |

---

## Next Session Starting Point

1. Continue Series 03 with **03d** (schools) — use subagent-driven-development, implement + spec review + code quality review per task
2. Then 03e, 03f, 03g in sequence
3. Then begin Series 04 starting with 04a (route geometry from BODS shapes.txt)
4. Plan file: `docs/superpowers/plans/2026-03-12-phase0-complete-eda.md`
