# Aequitas — Figures Audit

Every specific number, rate, cost, and statistical claim used across all project docs.
Classified by confidence level. Must be resolved before pipeline build.

**Last audited:** 2026-03-12
**Audited files:** CLAUDE.md, MEMORY.md, architecture.md, data-quality.md, intelligence-engine.md (rule), session report

---

## Classification

- ✅ **Confirmed** — sourced directly from our own audit notebooks or locked ground truth
- ⚠️ **Stale** — known to be from an outdated source, flagged for update, do not use in calculations until refreshed
- ❌ **Unverified** — no traceable source, unknown vintage, must not be used in any calculation or narrative

---

## ✅ Confirmed Figures
*Safe to use. Sourced from Phase 0 audit notebooks. Do not change without re-running the relevant notebook.*

| Figure | Value | Source Notebook | Notes |
|--------|-------|----------------|-------|
| England active bus stops | 274,719 | 01_data_audit.ipynb | Filter: BCT/BCS/BCE, Status=active, ATCO 0xx-4xx |
| BODS unique routes | 13,099 | 02b_bods_deep_dive.ipynb | 9 feeds, deduplicated |
| BODS total trips | 1,752,443 | 02b_bods_deep_dive.ipynb | |
| Census 2021 England LSOAs | 33,755 | 01_data_audit.ipynb | England only |
| England population | 56,490,056 | ONS TS001 | Used as population denominator for all per-capita metrics |
| IMD 2025 LSOAs | 33,755 | 01_data_audit.ipynb | Uses 2021 LSOA boundaries, zero mismatch |
| LSOAs with zero bus stops | 4,245 | 01_data_audit.ipynb | Point-in-polygon spatial join |
| Stop-to-LSOA spatial match rate | 99.9993% | 01_data_audit.ipynb | |
| IMD–stop Pearson correlation | -0.0644 | 02e_multivariate_clustering.ipynb | Weak negative — deprivation barely predicts coverage |
| LSOA archetypes (KMeans k=4) | 4 | 02e_multivariate_clustering.ipynb | Silhouette-optimised |
| Audit checks | 103 total: 89 PASS, 14 WARN, 0 FAIL | 01_data_audit.ipynb | |
| Unemployment range (TS066) | 0–27.1%, 0 nulls | 01_data_audit.ipynb | LSOA-level confirmed |
| NaPTAN Status field value | `'active'` (not `'act'`) | 02h_spatial_access.ipynb | act=0 rows, active=387,377 rows — confirmed bug fix |
| KDTree index fix | reset_index(drop=True) required | 02h_spatial_access.ipynb | Non-contiguous index after filtering causes misalignment |
| BODS stop_times.txt size | 5.8 GB | 02b_bods_deep_dive.ipynb | Read in chunks only |
| BODS shapes.txt size | 3.2 GB | 02b_bods_deep_dive.ipynb | Inside bods_gtfs_all.zip |
| BCR bands | <1.0 Poor, 1.0–1.5 Low, 1.5–2.0 Medium, 2.0–4.0 High, >4.0 Very High | Session report §7.1 | Confirmed unchanged per March 2026 source check |
| Green Book social discount rate | 3.5%/yr | Session report §7.1 | Confirmed unchanged, 2026 Green Book retains STPR |
| Archetype: Affluent Urban | 16,944 LSOAs (50.2%) | 02e_multivariate_clustering.ipynb | |
| Archetype: Deprived Young Diverse Car-Free Urban | 6,023 LSOAs (17.8%) | 02e_multivariate_clustering.ipynb | |
| Archetype: Elderly Rural | 4,588 LSOAs (13.6%) | 02e_multivariate_clustering.ipynb | |
| Archetype: Deprived Car-Free Urban | 6,200 LSOAs (18.4%) | 02e_multivariate_clustering.ipynb | |

---

## ⚠️ Stale Figures
*From known outdated sources. Still present in docs with warnings. Must be replaced before use in any calculation or narrative. Do not build economic appraisal or carbon analysis until these are refreshed.*

| Figure | Current Value in Docs | Stale Source | Correct Source | Action Required |
|--------|----------------------|-------------|----------------|-----------------|
| Value of bus commuting time | £9.85/hr | TAG Databook 2024 price year | TAG Databook v2.03fc (Dec 2025, 2023 prices) | v2.03fc downloaded — extract values from tabs A1.3.1, A1.3.2, A1.3.7 |
| Value of car commuting time | £12.65/hr | TAG Databook 2024 price year | TAG Databook v2.03fc | Same — extract from downloaded v2.03fc |
| Value of business travel time | £28.30/hr | TAG Databook 2024 price year | TAG Databook v2.03fc | Same — extract from downloaded v2.03fc |
| Value of leisure travel time | £7.85/hr | TAG Databook 2024 price year | TAG Databook v2.03fc | Same — extract from downloaded v2.03fc |
| Carbon value (central) | £80/tonne CO2e | TAG Databook 2024 price year | TAG Databook v2.03fc | Same — extract from downloaded v2.03fc |
| Bus CO2 emissions | 0.0965 kg/pax-km | DESNZ 2022 GHG factors | DESNZ GHG Conversion Factors 2025 (June 2025) | 2025 factors downloaded — extract from `data/raw/carbon/ghg-conversion-factors-2025-condensed-set.xlsx` |
| Car CO2 emissions | 0.171 kg/km | DESNZ 2022 GHG factors | DESNZ GHG Conversion Factors 2025 | Same — extract from downloaded DESNZ 2025 xlsx |
| DfT fare elasticity | -0.4 to -0.6 | Old project docs (uk_bus_analytics) — original source not traced | Current DfT demand elasticity guidance | Verify against current DfT TAG Unit A5.4 before use in modal shift calculations |
| DfT frequency elasticity | +0.4 to +0.7 | Old project docs — original source not traced | Current DfT TAG Unit A5.4 | Same verification needed |
| FAISS index size | ~1,365 pre-computed narratives | Derived from old 43-section estimate | TBD after EDA section count finalised | Update once analytical sections are locked post-EDA |
| CPT economic impact multiplier | £4.55 return per £1 invested | Old project, Confederation of Passenger Transport report | CPT report — check if updated since old project | Verify before citing in any narrative |
| GDP multiplier range | £2.00–2.40 per £1 direct spend | Old project docs — specific report not cited | ONS input-output tables or current transport economics literature | Verify and source properly before use |

---

## ❌ Unverified Figures
*No traceable source. Unknown vintage. Must not appear in any calculation, narrative, or pipeline output until properly sourced.*

| Figure | Value in Docs | Where Used | Problem | Resolution |
|--------|--------------|-----------|---------|------------|
| Bus stop construction cost | £15,000 (standard) | architecture.md TAG constants | No source cited. Possibly DfT 2019 estimate. Costs vary significantly by location and specification. | Find current DfT cost database or TAG WebTAG unit costs before building economic appraisal module |
| Route annual operating cost (urban) | £250,000/yr | architecture.md TAG constants | No source cited. Old project assumption with no traceable origin. | Same resolution — current DfT/CPT operator cost benchmarks needed |
| Route annual operating cost (rural) | £180,000/yr | architecture.md TAG constants | Same problem | Same resolution |
| Coverage prediction R² | ~0.089 | MEMORY.md ML decisions | Stated as expected value but was from old project's Random Forest trained on **wrong data** (7,696 LSOAs, IMD 2019, unfiltered stops). Our model on correct data may produce a different result. | Remove "expected ~0.089" framing. Run the model in Phase 0 Layer 4. Report actual result. The finding that "91% is policy-driven" may still hold but must be re-derived. |

---

## Summary — What Blocks What

| Blocked Analysis | Blocked By | Unblocked When |
|-----------------|-----------|----------------|
| BCR calculations | TAG stale values (v2.03fc downloaded but not extracted) | Extract values from `data/raw/tag/tag-data-book-v2-03fc-dec-2025.xlsm` + update architecture.md |
| Carbon / modal shift | DESNZ 2022 stale values (2025 file downloaded but not extracted) | Extract values from `data/raw/carbon/ghg-conversion-factors-2025-condensed-set.xlsx` + update architecture.md |
| Modal shift elasticities | Unverified DfT elasticity figures | Verified against TAG Unit A5.4 |
| Route investment cost modelling | £15k/£250k/£180k unverified | Sourced from current DfT WebTAG unit costs |
| Coverage prediction finding | R²=0.089 from wrong data | Re-run Random Forest on correct Aequitas data in Layer 4 |
| FAISS index size estimate | Section count not finalised | Post-EDA once all analytical sections locked |

---

## Action Checklist (before pipeline build)

- [x] Download TAG Databook → ✅ v2.03fc downloaded to `data/raw/tag/tag-data-book-v2-03fc-dec-2025.xlsm` (supersedes v2.02)
- [ ] Extract TAG v2.03fc values (tabs A1.3.1, A1.3.2, A1.3.7) → update architecture.md + figures-registry.md TAG-001 through TAG-005
- [x] Download DESNZ GHG Conversion Factors 2025 → ✅ downloaded to `data/raw/carbon/ghg-conversion-factors-2025-condensed-set.xlsx`
- [ ] Extract DESNZ 2025 transport factors → update figures-registry.md CO2-001, CO2-002
- [ ] Verify DfT elasticity values against TAG Unit A5.4 (fare and frequency)
- [ ] Source bus stop and route operating costs from current DfT WebTAG unit costs
- [ ] Run Random Forest coverage prediction in Layer 4 EDA → replace R²=0.089 with actual result
- [ ] Finalise analytical section count post-EDA → update FAISS index estimate
- [ ] Verify CPT £4.55 multiplier and GDP £2.00–2.40 multiplier against current sources before citing
