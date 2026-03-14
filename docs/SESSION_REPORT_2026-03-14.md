# Aequitas — Session Report

**Date:** 14 March 2026
**Branch:** main
**Commits this session:** 2 (68ab2ed, ae897c5)

---

## What Was Done

### Phase 0 EDA Completed — 04e + 04f

This session completed the final two Series 04 notebooks, bringing Phase 0 to full completion.

---

### 04e — Economic Appraisal

**Notebook:** `notebooks/04e_economic_appraisal.ipynb`
**Commit:** `68ab2ed`

| Output Artifact | Rows | Notes |
|---|---|---|
| `lsoa_economic_appraisal.parquet` | 33,755 | BCR, investment gap, modal shift, CO2 per LSOA |
| `modal_shift_scenarios.parquet` | 9 | 3 elasticities × 3 scopes |

**Key findings:**
- BCR ~1.12–1.32 (Low band, 60-yr, 3.5% SDR) — driven by unverified operating cost estimates; improves with DfT-sourced costs
- Bottom IMD decile CO2 saving: **952 t/yr** (central, 20% freq increase, ε=0.55)
- Monetised at TAG carbon price (£259.87/tCO2e): **£247k/yr**
- England-wide central scenario: 7,258 t CO2/yr, £1.9M/yr
- Sensitivity tornado: operating cost has highest BCR impact (±20% cost shifts BCR ±0.15)

**Methodology notes:**
- VoT: TAG A1.3.1 2023 prices, blended (38% commuting £13.01 + 51% leisure £5.94 + 11% business PSV £13.10) = £8.49/hr
- Carbon: DESNZ 2025 net saving car→bus = 0.00779 kg CO2e/pax-km
- Operating costs: ❌ Unverified (industry estimates £4.50/veh-km urban, £3.80 rural) — all results labelled indicative
- CO2 formula: only modal-shifted trips (25% of new bus trips) generate a saving; `car_replaced × dist × (car_pax_factor − bus_factor)`

---

### 04f — Policy Synthesis (Phase 0 Capstone)

**Notebook:** `notebooks/04f_policy_synthesis.ipynb`
**Commit:** `ae897c5`

| Output Artifact | Rows | Notes |
|---|---|---|
| `lsoa_policy_synthesis.parquet` | 33,755 | 30 policy indicator columns |
| `lta_franchising_readiness.parquet` | 298 | Per-LAD franchising readiness score |
| `policy_scenarios.parquet` | 4 | Scenarios A–D |

**Key findings:**

| Finding | Value |
|---|---|
| Q1 priority LSOAs (high vuln + low access) | 6,091 (18.0%) |
| LSOAs needing intervention (any flag) | 13,010 (38.5%) |
| Top LAD for franchising readiness | North Yorkshire |
| Scenario A (freq restoration, bottom decile) | 5.7M people, 34.6M extra trips/yr |
| Scenario B (evening extension) | 8.4M people, 5,189 LSOAs fixed |
| Scenario C (DRT rural elderly) | 5.2M people, 13.6M trips/yr |
| Scenario D (franchise top-5 LADs) | 760k people, 4.9M extra trips/yr |

**LSOA→region join:** Resolved the "Unknown" region issue by spatial joining LSOA 2021 centroids against ONS RGN22 boundaries. ≥98% LSOAs matched.

**HHI (operator market):** All 9 England regions computed. Results in `lta_franchising_readiness.parquet` via `region_hhi` column.

**Franchising Readiness Index:** 5-component composite (HHI 20% + trip gap 25% + deprivation 25% + SQI 20% + evening isolation 10%). 298 LADs ranked. 1 Tier 1 (North Yorkshire), 102 Tier 2, 195 Tier 3.

**Policy recommendations:** Tiered framework:
- Tier 1 (high confidence, ✅ Confirmed figures): frequency investment in bottom 2 deciles; evening service extension; healthcare desert prioritisation
- Tier 2 (indicative, model outputs): investigate 1,688 ML-flagged anomaly LSOAs; franchising top LADs under Bus Services Act 2025

---

## Phase 0 — Final Status

| Series | Notebooks | Status |
|---|---|---|
| 01 (initial audit) | 1 | ✅ Complete |
| 02–02i (deep dive EDA) | 10 | ✅ Complete |
| 03a–03h (dataset audits) | 8 | ✅ Complete |
| 04a–04f (analytical layers) | 6 | ✅ Complete |
| **Total** | **25** | **✅ Phase 0 COMPLETE** |

All 8 policy dimensions covered:
1. ✅ Equity & deprivation (Gini 0.5741, Palma 5.702, CI +0.1358)
2. ✅ Accessibility (2SFCA, 6,776 zero-access LSOAs)
3. ✅ Service quality (SQI 65.4, 5,189 evening isolated, 6,745 Sunday deserts)
4. ✅ Route network (7,241 routes with geometry, 37.7% cross-LA)
5. ✅ Modal shift & carbon (DESNZ 2025 factors, 952 t CO2/yr central saving)
6. ✅ Economic appraisal (BCR ~1.12–1.32, investment gap, TAG v2.03fc)
7. ✅ Bus Services Act 2025 (298 LADs ranked, HHI per region)
8. ✅ Policy scenario modelling (Scenarios A–D)

All 9 socio-economic factors confirmed in `master_lsoa_table.parquet`.

Ground truth unchanged: 274,719 stops, 13,099 routes, 33,755 LSOAs, 56,490,056 population.

---

## Docs Updated This Session

- `CLAUDE.md` — Current Phase updated to "Phase 0 COMPLETE, Phase 1 begins"
- `docs/figures-registry.md` — ST-027–034 added (04e/04f findings); EL-001/EL-002 updated ⚠️→✅
- `memory/MEMORY.md` — Series 04 status all ✅; Build Phases updated
- `docs/SESSION_REPORT_2026-03-14.md` — this file

---

## Next Session Starting Point

**Phase 1 — Data Pipeline Build**

Per `memory/architecture.md` package structure:
```
src/aequitas/
  core/        — Pydantic v2 models, TAG constants, validators
  ingestion/   — NaPTAN, BODS, ONS, IMD, NOMIS downloaders
  processing/  — Parse, deduplicate, geocode, LSOA-link → Parquet
  intelligence/— InsightEngine: evidence-gated rules + Jinja2 templates
  warehouse/   — Build DuckDB from Parquet + intelligence output
  ml/          — Clustering, prediction, anomaly (from 04d)
  rag/         — FAISS index, Gemini integration
  api/         — FastAPI app
```

Suggested starting point: `core/` — Pydantic models and locked constants first, then `ingestion/` → `processing/` in dependency order.
