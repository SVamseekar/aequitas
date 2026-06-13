# Task #23 — 11-point screenshot audit findings (2026-06-13)

8 parallel subagents audited all 240 screenshots in `frontend/screenshots/` (30 per
dimension) against the 11-point checklist in
`docs/superpowers/plans/2026-06-13-post-staleness-audit-followups.md`.
`frontend/screenshots_old/` was largely unusable for old-vs-new diffing — see
"screenshot tooling issue" below.

Legend: ✅ fine · 🔧 improvable (follow-up) · ❌ broken (needs fix)

---

## Accessibility (a1–a8)

| Section | Status | Notes |
|---|---|---|
| a1_route_density | ✅ | Filter-responsive, plausible values. 🔧 dual-mode (ranking bar on "all", stat card on single-region) — confirm intentional. |
| a2_stop_density | ✅ | Same pattern as a1, values plausible (5.21–6.98 stops/1,000 vs national 5.21). |
| a3_walking_distance | ✅/🔧 | Plausible values, good "INSUFFICIENT DATA" handling for London rural. 🔧 registered chart type "stacked_bar" not confirmed visible anywhere. |
| a4_coverage_equity | ✅ | National Gini 0.5741 matches ground truth exactly; filter-responsive 0.526–0.574. |
| a5_service_deserts | ❌ | Choropleth renders as a blank ~900-1300px black rectangle on **all 30 screenshots** (and pre-existing in screenshots_old). Root cause: `frontend/src/components/charts/ChoroplethMap.tsx` fetches `/boundaries/regions.geojson`, which does not exist in `frontend/public`; fetch error swallowed by empty `.catch(() => {})`. Need to add the GeoJSON (RGN22CD-keyed) to `frontend/public/boundaries/` or show a visible "map data unavailable" fallback. |
| a6_urban_rural_gap | ✅ | Grouped bar correct, London rural correctly shows "INSUFFICIENT DATA" with explanation. |
| a7_investment_gap | ❌ | `gap_to_target.j2` line 14: `(mean_gap * 2)|round(0)|int` with mean_gap=0.08 → 0, producing "approximately 0 fewer round trips available per day" (nonsensical). Visible on `accessibility__all__all.png` and likely others. 🔧 also: £0.7m national total annual cost seems implausibly small — COST-004 £500/LSOA proxy itself flagged "unverified" in methodology footnote. |
| a8_coverage_prediction | ❌ | Top SHAP bar (nocar_pct, importance=0.083, correctly highlighted/colored per E13) is labeled "0.0" on the chart itself, while other bars show correct values. Reproduced on `accessibility__all__all.png` and `accessibility__E12000007__rural.png`. |

**Cross-cutting (accessibility):**
- a5's blank choropleth is pre-existing (also in screenshots_old) — not a staleness regression, but unfixed and creates a large dead zone on every page.
- London (E12000007) rural correctly triggers "INSUFFICIENT DATA" for a3/a6/a7 — good positive pattern, worth reusing elsewhere (see f2/f5 leak below, which is the *bad* version of this pattern).

---

## Bus Services Act (bsa1–bsa3)

| Section | Status | Notes |
|---|---|---|
| bsa1_franchising_readiness | ✅ | Stat cards, LAD-level "not subdivided by urban/rural" caveat renders correctly and consistently (A1/A2). |
| bsa2_operator_concentration | ❌ | **27/30 single-region screenshots**: `chart_data` is literally `{}` (confirmed in DB) — only 4 bare stat cards (HHI, region, top operator, top operator share), no gauge. The E7 threshold-band gauge only renders on the 3 national "all" screenshots (with per-region HHI breakdown list). A docstring at `chart_dispatch.py:821` references a "single-marker HHI gauge for single-region views (E7 follow-up)" that isn't actually wired/producing chart_data. |
| bsa3_tier_distribution | ❌ (1 combo) / 🔧 | 3-separate-bars redesign (E8) correct, LAD-level caveat correct, plausible tier counts. **`bus-services-act__E12000007__rural.png` (London/rural)**: section completely missing from page (page is 1466px vs ~2527px for other London views) even though `section_results` has valid non-empty chart_data/stats identical to London/all (n_total=34, n_tier1=0/n_tier2=2/n_tier3=32). Looks like a `/sections` API query issue for this specific combo, not a data/render issue. |

**Cross-cutting (bsa):**
- London/rural is the only anomalous-height screenshot (149KB/1466px vs ~370KB/~2527-2639px elsewhere) — correlates with the bsa3 missing-section bug. Worth checking no other small-region × rural/urban combos silently drop sections (ties to "sparse-combo" theme across dimensions).
- `screenshots_old/bus-services-act__*` are all ~121,958 bytes, appear to be the marketing homepage — old-vs-new diff not possible (screenshot tooling issue, see below).
- bsa2's single-region stat-card-only layout looks visually inconsistent sitting between bsa1 and bsa3, which both have prominent charts.

---

## Correlations (d1–d8)

| Section | Status | Notes |
|---|---|---|
| d1_coverage_deprivation | ✅ | r varies sensibly by filter (all/all r=-0.0861, London/urban r=-0.0571), n_observations populates, sign/magnitude consistent with ground truth (-0.0644). |
| d2_coverage_unemployment | ✅ | r=0.297 (all/all), narrative consistent. |
| d3_coverage_car | ✅ | r=0.4601 (all/all), "moderate positive" narrative matches. |
| d4_coverage_elderly | ✅ | r=-0.1931 (all/all), "weak negative" narrative matches. |
| d5_coverage_income | ✅ | r=0.1261 (all/all), positive, narrative consistent. |
| d6_transport_poverty | ✅/🔧 | Large-N: scatter + cluster-size mini-bar works. Small-N (London rural): correct "too few points" fallback to bar chart per E12. 🔧 cluster legend/size readout cramped in large-N view — layout pass. |
| d7_deprivation_urban_rural | ❌ | Still dispatched as a 2-row (urban/rural) × decile **heatmap** — E6/A12b's diverging-horizontal-bar redesign was **not implemented**. `chart_dispatch.py` line ~114-115 unconditionally returns `_build_heatmap(...)` for `d7_deprivation_urban_rural`. For London (urban-only), degenerates to a 1×N single-row heatmap — exactly the awkward case E6 flagged. Data itself (decile, SQI, worst/best cell, gap) is correct and non-NaN — this is purely the unimplemented chart-type fix. |
| d8_feature_importance | ✅ | Top feature nocar_pct highlighted (orange vs blue) per E13, R²=0.4719 ≈ ground truth 0.472, narrative correctly calls out SHAP importance 0.083. |

**Cross-cutting (correlations):**
- **London rural**: entire d1-d7 socio-economic/ML section absent from page (13,257px → 5,180px) — page jumps straight to d8 + route-clustering/scenario sections below. May be an intentional "too few LSOAs" guard, but no placeholder/explanation shown — same "silent disappearance" pattern as bsa3/c-dimension London issues.
- `screenshots_old/correlations__*` are all ~1219px landing-page captures — old-vs-new diff not possible (screenshot tooling issue).
- Page composition: correlations page also includes Route Clustering, Anomaly Detection, and Scenario Modelling sections below d8 — appears intentional but worth confirming as desired IA (point 6/10).

---

## Economic (j1–j4, f1–f4 not visible on this tab)

**Scope note:** all 30 `economic__*.png` only capture the "Economic Appraisal" tab (j1-j4). f1-f4 live under "Equity & Deprivation" (covered by the equity-dimension audit below) and weren't evaluable here.

| Section | Status | Notes |
|---|---|---|
| j1_economic_value | ✅ | "all": horizontal bar across 9 regions + KPI cards (England £1,387.2m, £24.56/capita). Single-region: 4-card KPI grid per E1. Narrative correctly substitutes region/figures. |
| j2_bcr | 🔧 | A14 region-filter bug **fixed** — BCR varies correctly by region and urban/rural (North East urban BCR=1.21/£529.7m vs rural BCR=1.43/£109.3m, "Low" VfM band both). E7 banded gauge renders on "all" page (gradient bar + per-region BCR list 1.00-1.46) but **single-region pages fall back to plain 4-card KPI grid with no gauge** — `_chart_bcr_gauge_single_region` likely returns `{}` due to a stats-shape mismatch. E7 rollout incomplete for single-region views. |
| j3_carbon | ✅ | KPI tiles vary correctly by region/filter (North East: 293.5t/£76.3k/4.35m trips urban vs 46.7t/£12.1k/692k trips rural). "all": horizontal bar (London highest 2,348.5). DESNZ 2025 / TAG methodology text correct. |
| j4_investment_priority | ✅ | Single-region KPI grid + national-avg comparison correct (London -36.5% vs national: 21,685.96 vs 34,165.46 £/yr). "all": horizontal bar with national-average reference line. |
| f1_gini / f2_disparity_ratio / f3_ethnic_access | n/a | Not on this tab — see Equity dimension below. |
| f4_gender_accessibility | ✅ | Confirmed absent from `chart_dispatch.py` f-section list (only f1/f2/f3 remain) — A16b removal confirmed, no layout gap. |

**Cross-cutting (economic):**
- ❌ **`economic__E12000007__rural.png` (London rural)** is severely truncated: 1024px vs ~3417px elsewhere, header says "1 SECTIONS · 1 CHARTS · 1 NARRATIVES" — only j4 renders; j1/j2/j3 completely missing, no placeholder/error. Same "silent section drop for London rural" pattern seen in bsa3 and correlations.
- 🔧 j2_bcr gauge inconsistency (restated above) — single-region pages should get a single-marker gauge per the E7 intent, not a plain KPI grid.
- `screenshots_old/economic__*` are all 1440×1219 landing-page captures — old-vs-new diff not possible (screenshot tooling issue).

---

## Equity (f1_gini, f2_disparity_ratio, f3_ethnic_access, f5_rural_penalty, f6_equitable_regions)

| Section | Status | Notes |
|---|---|---|
| f1_gini | 🔧 | Wiring/data/chart fine; Gini in [0,1] everywhere including previously-broken sparse rural subsets (E12000005/006/008/009 rural: 0.488-0.544, A18 guard confirmed working). Narrative sign-branching (pro-rich vs pro-poor) correct per-region (West Midlands rural correctly shows "+0.0494... pro-rich... contradicts BSA 2025"). Issue is the **global header ticker** — see cross-cutting below. |
| f2_disparity_ratio | 🔧 | 10-decile horizontal bar + KPI cards renders (E2 fix applied). `ratio_undefined: false` boolean leaks as a literal "RATIO UNDEFINED: false" KPI card — internal/debug field in UI. Should be hidden when false. |
| f3_ethnic_access | ✅ | Scatter + regression + r/p/N stats all correct and filter-responsive (N: 33,755→4,969 London; 1,676/1,388/288 North East all/urban/rural). A16 build confirmed working. |
| f5_rural_penalty | ❌ (1) / 🔧 (1) | E3 fix confirmed: now appears for "all" (incl. London) and single-region views, urban/rural-filtered values differ (North East urban 77.2 vs rural 62.93). For London (rural N=0), shows raw "INSUFFICIENT DATA: true / N LSOAS 4,969 / N URBAN 4,969 / N RURAL 0" KPI cards instead of a clean message — same leak pattern as f2. |
| f6_equitable_regions | ❌ | E1 chart-type fix confirmed (N-region bar on "all", KPI cards on single-region). Two narrative bugs, generic to the ranking-family templates: (1) `ranking.j2` hardcodes "lowest" for `worst.value` regardless of `higher_is_better` — e.g. North East has the HIGHEST (worst) vulnerability index 38.14 but narrative says "records the lowest at 38.14... -18.2% below the national average" (self-contradictory). (2) `single_region.j2`/`build_single_region_stats` assumes "above national average = good" via `vs_national_pct >= 0` — for f6 (lower=better), being above-average vulnerability is bad, but narrative says "ahead of the national benchmark... performing relatively well" (backwards) for North East (38.14 vs avg 32.27) and London (33.7 vs avg 32.27). Needs `higher_is_better` propagated into both templates. |

**Cross-cutting (equity):**
- ❌ **Header ticker / AboutPage hardcoded Concentration Index**: `frontend/src/components/layout/MetricsTicker.tsx` line 13 (and `AboutPage.tsx` line 5) hardcode `"+0.1358"` / "pro-rich bias" (the CLAUDE.md ground-truth value from notebook 04c). The live-computed f1_gini Concentration Index across nearly all region/filter combos is now **negative** (pro-poor/pro-equity, e.g. -0.1306, -0.0965, -0.0266). The global header banner and the in-page f1_gini narrative now tell **contradictory policy stories** on every one of the 30 screenshots (header visible on all pages). Needs reconciling: either the ticker should compute the live national concentration index, or — if 04c's methodology differs from the warehouse's per-LSOA `_concentration_index` — the discrepancy needs investigating and one of the two claims corrected.
- 🔧 Internal boolean/flag leak pattern (`ratio_undefined`, `insufficient_data`+`n_rural=0`) rendering as raw debug-looking KPI cards — likely a shared stat-card component issue; worth checking other dimensions for the same pattern (cross-dimension consistency, point 10).
- Point 11 (sparse rural Gini guard, A18) fully ✅ verified.

---

## Route Network (c1–c7)

| Section | Status | Notes |
|---|---|---|
| c1_route_length | ❌ (London) / 🔧 | Works correctly elsewhere (histogram/box-violin, region+urban/rural filtered, "all/all" median 18.75km ≈ ground truth 18.7km). **London (E12000007), all 3 filters**: `chart_data={}`, narrative shows literal "nan km" / "nan-nan km". Likely a single-region edge case in misc.py's distribution builder. |
| c2_stops_per_route | ✅ | Box-violin renders correctly everywhere including London (inconsistent with c1 despite sharing a code path — worth checking why c1 fails and c2 doesn't for the same region). |
| c3_operator_hhi | ✅/🔧 | Single-region: KPI tiles + HHI correctly vary (London 929→986 urban; E12000002 rural HHI 2955.4 "Stagecoach Cumbria"). "all": ranking bar by HHI, correct. 🔧 "all/all" narrative says England HHI=84/160/158 — seems too low vs regional HHIs of 500-1600; possibly a different denominator/average-of-averages — worth double-checking the aggregate calc. |
| c4_urban_rural_routes | ❌ | **Not region/filter-aware at all** — identical stacked_bar chart_data (9-region breakdown) returned for every region and urban/rural combo. Narrative cherry-picks numbers from this fixed table (London narrates "95.6% urban/0.0% rural" — London's row from the global table; "all" narrates "50.9%/6.4%" — a different aggregate row), so chart and narrative are inconsistent for region-specific pages, and the chart adds nothing when viewing a single region. A8's fix appears to have parameterized only the narrative, not the chart/stats builder. |
| c5_length_vs_frequency | ❌ (London) / 🔧 | Region-aware (A9 landed: E12000001 r=0.50/n=203, E12000002 r=0.62/n=643, E12000009 r=0.31/n=1349). 🔧 not urban_rural-filtered — identical across all/urban/rural within a region (inconsistent with c1-c3 which do vary). ❌ **London, all 3 filters**: r=0, p=1.0, sample_size=0, data=[], empty narrative. |
| c6_route_archetypes | 🔧 | A10/E11 label fix confirmed (descriptive names, e.g. "Long-distance within-authority routes averaging 47.8km with 39 stops"). But identical clusters/n/labels across **every** region and filter including London and "all" — if intentionally national-level, the narrative ("...across England") reads oddly on region-specific pages and should say "national archetypes" explicitly rather than implying region-specific clustering. Small-N fallback/overplotting fix not verifiable visually (data never varies by region so the small-N path is never triggered). |
| c7_network_topology | ❌ | `chart_data={}` for **27/30 screenshots** (all region-specific pages, all filters) — only the 3 "all" pages have a populated horizontal_bar of ranked corridors (E9/A11 redesign correct there, e.g. "South East 861", "London 745"). For region-specific pages, narrative text computes correctly (e.g. E12000002: "668 routes (40.6%) cross local authority boundaries") but chart renders empty. Also: "all/all" narrative still shows "nan km (median nan km)" for c7's own length stats — separate nan leak from c1's, possibly same root cause (a join/lookup failing to find a length stat). |

**Cross-cutting (route-network):**
- ❌ London (E12000007) is the worst-affected region across this dimension: c1 fully empty/nan (3 filters), c5 fully empty (3 filters), c7 empty (shared with all other regions). c4's narrative for London claims "0.0% rural / 100% urban premium" — a division-by-zero-flavored edge case worth sanity-checking.
- Literal "nan km"/"nan-nan km" strings leaking into rendered narratives (c1, c7) — significant polish/correctness issue.
- c4 and c7 share very similar underlying data (cross-LA / urban-rural mix per region) but only c7 was restructured to the new ranked design for "all" — c4 appears to still use the old flat global table; A8 may not be fully wired into `chart_dispatch.py`.
- **Priority order suggested by this agent**: c7 chart_data empty for non-"all" (27 screenshots) > c4 not filter-aware (30 screenshots) > c1+c5 London-only breaks (3 screenshots each) > nan strings in narratives.

---

## Scenarios (ps1–ps5, g5)

| Section | Status | Notes |
|---|---|---|
| ps1_freq_restoration | 🔧 | KPI tiles + narrative present (B1/A19 done). `population_affected` correctly varies (national "all/all"=5,689,818 matches B2 constant; London/all=361,453; E12000001/urban=502,297 — plausible subsets of 3,375 LSOAs). Annual cost (£72.7m) and CO2 saved (952t) are **fixed national values**, don't scale with region/filter. No E14 proportion bar anywhere. |
| ps2_evening_extension | 🔧 | Same pattern: population_affected scales correctly (London/all=950,279 vs national 8,392,662, ≤5,189-LSOA subset). CO2 saved = 0t everywhere — confirm methodologically correct vs missing computation. Cost (£116.8m) doesn't scale. No E14 bar. |
| ps3_drt_rural | ❌ | For London, population_affected correctly → 0 (sensible, point 11 ✅), **but narrative explicitly states "0 people affected, £109.1m/yr, 0 t CO2 saved/yr"** — internally inconsistent (spending £109m to affect 0 people). Cost should scale toward £0 for zero-population regions, or the narrative needs to clarify £109.1m is a national baseline. CO2=0t everywhere (same concern as ps2). No E14 bar. |
| ps4_franchise | 🔧 | population_affected=760,008 correctly identical for "all" and London (LAD-level, doesn't decompose — documented exception) but **not labeled as such** in the UI — looks like a bug to a user comparing regions. Cost=£0m and CO2=0t throughout, also unexplained. No E14 bar. |
| g5_scenario_model | 🔧 | Not visibly rendered as its own section on this page (page header says "5 SECTIONS", shares template/index-0 slot with ps1) — likely belongs to a different page/category; flagged for verification, not necessarily a bug. |
| ps5_scenario_comparison | ✅ | Ranked table renders correctly per B1 (all 4 scenarios, Population/Cost/CO2/Cost-per-beneficiary columns), "Best BCR scenario" callout present, portfolio narrative echoes per-scenario figures including London's 0-population DRT row (cost/beneficiary correctly 0 via div-by-zero guard, even though raw cost is non-zero — see ps3 above). |

**Cross-cutting (scenarios):**
- ❌ **E14 (before/after proportion bar vs England total 56,490,056) is entirely absent** from all 30 screenshots for ps1-ps4/g5 — `_SCENARIO_KPI_TILE_SECTIONS` returns `{}` from `build_chart_data` beyond the KPI tile stats. This was one of the four things this audit was meant to verify and appears **not implemented at all**.
- ❌ Cost (£m/yr) and CO2 (t/yr) are static national constants that don't scale with the recomputed population_affected for ps1-ps3 — most visibly broken for ps3/London (£109.1m attributed to 0 people). B2 only recomputes population/trips by design, but the UI doesn't communicate this, so static cost/CO2 look like bugs at filter extremes.
- ps2/ps3 always show CO2 saved=0t — confirm intentional (no defined CO2 pathway) vs missing computation; if intentional, a note/tooltip would help vs a bare "0t".
- ps4's £0m/0t are unexplained alongside its non-filtering 760,008 population — least "finished" of the five sections.
- `screenshots_old/scenarios__all__all.png` appears to be the marketing landing page, not the old scenarios page — old-vs-new diff not meaningful here (screenshot tooling issue), though the directional improvement (bars→KPI tiles/table+narratives) is clear regardless.

---

## Service Quality (b1–b5)

| Section | Status | Notes |
|---|---|---|
| b1_frequency | ✅ | Bar chart of avg SQI by region ("all") correct, London 82.21/national avg 65.42≈65.4 matches ground truth. Single-region KPI-card layout confirmed (E1), "1 CHARTS · 0 NARRATIVES" header issue gone. |
| b2_operating_hours | ✅ | A4 fix confirmed — filter-aware (North East urban: 70 evening-isolated/5.0% vs rural: 25/8.7%). London-specific (574/11.6% vs national 5,189/15.4%). Narrative present (previously zero). 🔧 multi-region "all" view has no overall KPI summary cards above the chart, unlike b1. |
| b3_weekend_penalty | ✅ | A4 fix confirmed — filter-aware (North East urban 47.5%/70 deserts/5.0% vs rural 62.3%/42/14.6%). National "all" matches ground truth exactly (6,745, 20.0%, 50.8% drop). Narrative present. |
| b4_route_frequency | 🔧 | A5 fix confirmed — real top/bottom-5 by trips/day, distinct from b1, filter/region-aware (London r=0.063, South West urban r=0.130, national r=0.218). Route/agency-name y-axis labels are **clipped on the left edge** across multiple screenshots (e.g. "st Bristol, Bath & the West)" truncating "First West of England (West Bristol, Bath & the West)" and losing the route number for top bars) — needs label truncation/ellipsis or wider label column. |
| b5_frequency_deprivation | ✅ | Scatter + r/p/strength/direction KPI cards correct, national r=0.2184 matches ground truth (IMD vs SQI), narrative + methodology footnote correct. |

**Cross-cutting (service-quality):**
- 🔧 London (E12000007) rural: only b1 renders (KPI cards); b2-b5 vanish entirely ("1 SECTIONS · 1 CHARTS · 1 NARRATIVES", page 1024px vs ~3490px elsewhere) — same "silent section drop for London rural" pattern as bsa3/correlations/economic/route-network. Recommend an explicit "insufficient rural data for London" placeholder.
- 🔧 Methodology footnote (b5 and likely others) runs into the next section without clear spacing — visual check needed.
- 🔧 Single-region header "5 SECTIONS · 3 CHARTS · 5 NARRATIVES" mismatch (b2/b3 are KPI-only, no chart) is consistent with E1 design but could read as a bug — consider clearer phrasing ("chart sections" vs "KPI sections").
- ✅ No NaN/undefined/error text anywhere in this dimension. Header KPI strip consistent across regions/filters.

---

## Cross-dimension theme: "silent section drop for London rural"

Recurring across **4 of 8 dimensions** (bsa3, correlations d1-d7, economic j1-j3, service-quality b2-b5) and likely also accessibility/route-network in part: when a region×urban_rural combo has very few LSOAs (worst case: London rural), entire sections vanish from the page with no placeholder or explanation — page height drops dramatically (e.g. economic: 3417px→1024px) and the header section/chart/narrative counts shrink accordingly. For bsa3 specifically, the underlying `section_results` row has valid data (suggesting an API/query issue, not a stats-builder issue), while for the others it's plausibly a stats builder returning `{}`/empty for near-empty filtered sets (the A17 pattern from the original staleness plan, which doesn't appear to have been applied universally).

**Recommendation**: a single shared "insufficient data for this region/filter combination" placeholder component, applied wherever a section's stats builder returns empty for a sparse combo — this was flagged as A17 in the original plan but evidently wasn't rolled out everywhere.

## Cross-dimension theme: "nan" / raw debug values leaking into UI

- "nan km" / "nan-nan km" in c1 (London) and c7 (all regions) narratives.
- "RATIO UNDEFINED: false" (f2) and "INSUFFICIENT DATA: true / N RURAL 0" (f5, London) rendering as literal KPI cards.
- a8's top SHAP bar shows "0.0" instead of 0.083.

All four are variations of "a backend value that should be hidden/reformatted is instead rendered raw" — likely fixable via a shared stat-card/number-formatting helper plus hiding boolean flags from the generic KPI-card renderer.

## Screenshot tooling issue (point 8, old-vs-new diff)

`frontend/screenshots_old/*` for **5 of 8 dimensions** (bus-services-act, correlations, economic, scenarios, service-quality) are landing-page/homepage captures (~1219-1466px), not the actual dimension pages — the old capture script apparently failed to navigate before screenshotting. Old-vs-new diffing (point 8) was not meaningful for these. Only accessibility and equity had usable old screenshots. If a true before/after comparison is wanted, the old screenshots would need to be re-captured from a pre-rebuild git ref — likely not worth doing retroactively given the new screenshots already demonstrate clear improvements (narratives appearing, charts rendering, label fixes).

---

## Summary table — ❌ items needing fixes (14)

| # | Dimension | Section | Issue | Scope |
|---|---|---|---|---|
| 1 | accessibility | a5_service_deserts | Choropleth blank — missing `regions.geojson` | all 30 (pre-existing) |
| 2 | accessibility | a7_investment_gap | "0 fewer round trips" narrative rounding bug | ≥1, likely several |
| 3 | accessibility | a8_coverage_prediction | Top SHAP bar labeled "0.0" instead of 0.083 | ≥2 confirmed |
| 4 | bus-services-act | bsa2_operator_concentration | chart_data={} for single-region views (no gauge) | 27 |
| 5 | bus-services-act | bsa3_tier_distribution | Section missing for London/rural despite valid data | 1 |
| 6 | correlations | d7_deprivation_urban_rural | Heatmap not converted to diverging bar (E6/A12b) | 30 |
| 7 | route-network | c1_route_length | chart_data={}, "nan km" for London | 3 |
| 8 | route-network | c4_urban_rural_routes | Not region/filter-aware at all | 30 |
| 9 | route-network | c5_length_vs_frequency | r=0/n=0/empty narrative for London | 3 |
| 10 | route-network | c7_network_topology | chart_data={} for all non-"all" regions; "nan km" in "all" narrative | 27 |
| 11 | scenarios | ps3_drt_rural | "£109.1m for 0 people" inconsistent narrative (London) | ≥1 |
| 12 | scenarios | E14 (ps1-ps4/g5) | Before/after proportion bar entirely unimplemented | 30 |
| 13 | equity | header ticker / f1_gini | Hardcoded "+0.1358 pro-rich" contradicts live mostly-negative Concentration Index | all 30 (header) |
| 14 | equity | f6_equitable_regions | ranking.j2/single_region.j2 backwards "lowest"/"ahead of benchmark" when higher_is_better=False | several |

## 🔧 items for follow-up doc (non-exhaustive — see per-dimension tables above for full list)

- j2_bcr single-region gauge missing (E7 incomplete rollout)
- f2_disparity_ratio / f5_rural_penalty boolean-leak KPI cards
- b4_route_frequency y-axis label clipping
- c3_operator_hhi "all" aggregate HHI (84) seems inconsistent with regional values (500-1600)
- c4/c6/c5 urban_rural-filter non-responsiveness (separate from c4's region issue)
- ps1/ps2 cost/CO2 not scaling with region (related to but distinct from ps3's worse case)
- "silent section drop for London rural" — shared placeholder component (A17 generalization)
- a3 stacked_bar chart type unconfirmed
- d6 cluster legend layout cramped
- accessibility a1/a2 dual-mode chart rendering — confirm intentional
