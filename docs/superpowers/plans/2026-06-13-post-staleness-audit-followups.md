# Follow-up audits after warehouse-staleness-and-filter-bugs plan

## Task #23 — 🔧 items from the 11-point audit (compiled 2026-06-13)

The 14 ❌ items from `docs/superpowers/plans/2026-06-13-task23-audit-findings.md` are
fixed (see commit). The 🔧 items below are lower-priority follow-ups surfaced by the
same audit, not yet actioned.

### From the fix pass itself
- **`frontend/public/boundaries/regions.geojson` is missing entirely** — a5's
  choropleth now shows a graceful "Map data unavailable" message instead of
  rendering blank, but the actual geojson asset still needs to be sourced/generated
  (e.g. from ONS region boundaries, simplified for web). Until then a5 will always
  show the fallback for all 30 region/filter combos.
- **"Silent section drop for London rural"** — recurring across bsa3, correlations
  (d1-d7), economic (j1-j3), and service-quality (b2-b5) (≥4 dimensions, possibly
  more in accessibility/route-network). For bsa3 specifically the backend
  `section_results` row has valid data and the narrative/stats builders were
  verified correct in this pass — the drop is frontend-side and needs the
  screenshot pipeline (or live browser check) to diagnose, since it couldn't be
  reproduced via pytest. Recommend a shared "insufficient data for this
  region/filter combination" placeholder component (generalizes A17 from the
  original staleness plan, which wasn't rolled out everywhere).

### From per-dimension audit tables
- **j2_bcr single-region gauge** — E7 rollout incomplete elsewhere; bsa2 was fixed
  in this pass via the same `_chart_*_gauge_single_region` pattern, confirm no
  other E7-style gauges are still missing their single-region variant.
- **f2_disparity_ratio / f5_rural_penalty boolean-leak KPI cards** — raw values like
  "RATIO UNDEFINED: false" and "INSUFFICIENT DATA: true / N RURAL 0" render as
  literal KPI cards instead of being hidden/reformatted. Same root-cause class as
  the "nan km" leaks fixed in c1/c7 — needs a shared stat-card/number-formatting
  helper that hides boolean flags from the generic KPI-card renderer.
- **b4_route_frequency y-axis label clipping** — route/agency names (e.g. "First
  West of England (West Bristol, Bath & the West)") are clipped on the left edge,
  losing the route number for top bars. Needs label truncation/ellipsis or a wider
  label column.
- **c3_operator_hhi "all" aggregate (84) vs regional values (500-1600)** — the
  national aggregate HHI looks inconsistent with regional HHIs; worth checking
  whether the "all" calculation is using the right grouping/weighting.
- **c4/c5/c6 urban_rural-filter non-responsiveness** — c4's region-awareness was
  fixed in this pass, but urban/rural filter responsiveness for c4/c5/c6 is a
  separate, still-open gap.
- **ps1/ps2 cost (£m/yr) and CO2 (t/yr) don't scale with region** — `population_affected`
  correctly recomputes per region/filter (by design, per B2), but cost/CO2 remain
  fixed national constants. Most visible at filter extremes (ps3/London got a
  caveat in this pass; ps1/ps2 still show static costs against scaled populations
  without explanation).
- **ps2/ps3 CO2 saved = 0t everywhere** — confirm whether this is methodologically
  correct (no defined CO2 pathway for these scenarios) or a missing computation; if
  intentional, add a note/tooltip rather than a bare "0t".
- **ps4_franchise £0m/0t alongside non-filtering population (760,008)** — least
  "finished" of the five scenario sections; population is correctly LAD-level
  (documented exception) but not labeled as such in the UI, and cost/CO2 are
  unexplained zeros.
- **c6_route_archetypes "national" framing** — clusters/n/labels are identical
  across every region/filter (intentional, national-level clustering), but
  narrative phrasing ("...across England") reads oddly on region-specific pages.
  Should explicitly say "national archetypes" rather than implying region-specific
  clustering.
- **d6 cluster legend layout cramped** — visual-only, needs a layout pass.
- **a1/a2 dual-mode chart rendering** — confirm intentional vs needs consolidation.
- **a3 stacked_bar chart type** — unconfirmed whether this is the right chart type
  for the underlying data.
- **b2/b3 "X SECTIONS · Y CHARTS · Z NARRATIVES" header mismatch** — b2/b3 are
  KPI-only (no chart) but counted under "CHARTS" in the header, consistent with E1
  design but could read as a bug. Consider clearer phrasing ("chart sections" vs
  "KPI sections").
- **Methodology footnote spacing** (b5 and likely others) — footnote runs into the
  next section without clear visual separation.
- **Screenshot tooling**: `screenshots_old/` for 5/8 dimensions (bus-services-act,
  correlations, economic, scenarios, service-quality) captured the landing page
  instead of the dimension page — not a code bug, but old-vs-new diffing for these
  dimensions was not meaningful. Only useful if a true before/after comparison is
  wanted later (would need re-capture from a pre-rebuild git ref).


## Task #23 — 11-point full screenshot audit (2026-06-13)

Full audit of all 240 screenshots in `frontend/screenshots/` (post-rebuild), with
`frontend/screenshots_old/` (pre-rebuild) available for diffing. Run as 8 parallel
per-dimension subagents (one per dimension: accessibility, bus-services-act,
correlations, economic, equity, route-network, scenarios, service-quality — 30
screenshots each), each covering all 11 points below for its dimension. Each agent
reports findings per section as ✅ (fine) / 🔧 (improvable, log to this doc) / ❌
(broken, needs immediate fix).

### 11 audit points
1. **Wiring** — backend data reaching and rendering in frontend
2. **Data correctness** — numbers match ground truth / internal consistency
3. **Chart-type fitness** — right chart for the data
4. **Narrative accuracy** — narratives describe the chart/data correctly
5. **Coverage gaps** — backend data with no frontend representation at all
6. **Broad frontend choices** — across all 50 sections, not just plan-touched ones
7. **Filter responsiveness** — figures, stats, AND narratives change correctly
   across all 30 region/urban_rural combos
8. **Old vs new diff** — what changed per screenshot (vs `screenshots_old/`), is it
   fine or still improvable
9. **General UI/UX health** — layout, NaN/undefined, console/network errors
10. **Cross-dimension consistency** — same concepts/components used consistently
    across dimensions
11. **Sparse-combo edge cases** — other London/rural-style "too few LSOAs" combos
    beyond the ones already known (E4/E5/A17/A18)

### Explicitly out of scope (log as follow-ups, do not investigate now)
- Accessibility / WCAG
- Performance / load times
- Mobile / responsive layouts
- Tooltip / interactivity
- Print / PDF export

### Workflow
1. 8 parallel agents report findings (✅/🔧/❌ per section) for their dimension.
2. Fix all ❌ items directly.
3. Compile all 🔧 items into this doc (below, per dimension).
4. Spec + quality review of fixes.
5. Commit, mark task #23 complete, proceed to finishing-a-development-branch.

## Context

`docs/superpowers/plans/2026-06-11-warehouse-staleness-and-filter-bugs.md` (tasks #1-23)
fixed code bugs, redesigned charts, rebuilt the warehouse, and re-verified visually.
That plan answers: **"did the changes we made land correctly?"**

During wrap-up, four further questions surfaced that are out of scope for that plan
(different in kind — broader audits, not verification of specific fixes) but should
be tracked as explicit follow-ups. They form a layered audit:

1. **Wiring** — does every backend stat/chart_data field reach and render in the
   frontend? (covered by #23 for plan-touched sections; not yet done exhaustively
   for all 50 sections)
2. **Correctness** — for what's wired and rendering, is the data numerically right?
3. **Coverage gaps** — is there backend data/sections with NO frontend representation
   at all (silent gaps, not rendering bugs)?
4. **Chart-design fitness** — across the entire frontend (not just E1-E14's targets),
   are the current chart/UI choices the right representation for policy-maker
   consumption, or should anything be redesigned?

Layers 2-4 only matter once layer 1 (wiring) is solid for a given section — no point
auditing correctness or design of something that isn't even rendering.

## Candidate Task A — Data correctness audit (layer 2)

Pure DuckDB/Python verification, no screenshots, no UI.

1. **Ground-truth reproduction**: for every figure in CLAUDE.md's "Ground Truth"
   table that maps to a `section_results` stat (Gini 0.5741, Palma 5.702, RF
   R²=0.472, top SHAP feature `nocar_pct`, Concentration Index +0.1358,
   evening-isolated 5,189, Sunday desert 6,745, mean SQI 65.4, etc.), query the
   `all/all` combo and confirm exact reproduction — not just non-null.
2. **Filter responsiveness — figures, stats, AND narratives all vary with filters**:
   for every section_id, pull `stats` and `narrative_text` across all 30
   (region, urban_rural) combos and confirm:
   - **Stats vary**: at least the numeric values that are filter-dependent by
     definition (means, counts, percentages, correlations computed over the
     filtered LSOA/route subset) differ across combos for the same section — flag
     any section where stats are byte-identical across 2+ combos that should
     differ (this was the root cause of A3/A7/A14/E3 in the staleness plan; confirm
     no NEW instances of this class slipped in elsewhere).
   - **Narratives vary accordingly**: `narrative_text` should reference the
     filtered region/area-type by name and reflect the filtered figures (not a
     generic England-wide narrative reused verbatim across combos). Flag any
     section where narrative text is identical across different regions/area-types
     despite different underlying stats — this is a template/context-binding bug
     even if the stats themselves are correct.
   - **Exceptions are documented, not silent**: some sections are legitimately
     non-subdividable (A1/A2 LAD-grain bsa1/bsa3, ps4 LAD-level — see staleness
     plan). For these, confirm the narrative explicitly says so (e.g. "LAD-level
     metric — not subdivided by urban/rural") rather than silently repeating
     identical text with no explanation.
3. **Internal consistency across the 30 combos**: for each section_id, pull `stats`
   across all (region, urban_rural) combos and check:
   - Range/bounds: percentages in [0,100], correlations in [-1,1], Gini in [0,1],
     ratios non-negative where expected
   - Aggregation sanity: does `region/all` roughly relate to `region/urban` +
     `region/rural` in a way consistent with the underlying population split?
   - Plausibility: e.g. London `urban` % near 100%, `rural` % near 0%
4. **Trace-to-source spot checks**: pick 3-5 figures per dimension (24-40 total),
   recompute independently from `data/audit/*.parquet` via a short script, compare
   to `section_results.stats`. Per CLAUDE.md: "every metric must trace to source
   data through a documented formula."
5. **Figures registry compliance**: grep `docs/figures-registry.md` for every new
   numeric figure introduced by tasks A5/A8/A10/A16/B2 (route frequency, urban/rural
   route classification, cluster labels, ethnic-access correlation, scenario
   population_affected) — confirm each has a ✅ Confirmed entry with source.

## Candidate Task B — Backend → frontend coverage gap audit (layer 3)

Static code comparison, no pipeline runs.

1. **Section inventory diff**: list all 50 `section_id`s from `section_results`
   (distinct), cross-reference against the frontend's section registry/routing
   (wherever section_id → component/template is mapped). Flag any section_id with
   no frontend mapping at all — computed but never surfaced.
2. **Field-level diff**: for sections that ARE wired, compare full `stats` JSON keys
   and `chart_data` structure against what the frontend component actually reads.
   Flag backend fields never referenced by any frontend code (dead computation, or
   a missed opportunity to surface useful info).
3. **Table-level diff**: beyond `section_results`, check other warehouse tables
   (`lsoa_clusters`, `coverage_prediction`, `routes`, `stops`, `policy_scenarios`,
   `lsoa_demographics`, etc.) against `frontend/src/api/hooks.ts` — which
   tables/endpoints have zero consuming hooks? (Known existing example: `useLsoa`
   hook exists but is unused by any page — flagged during #22's review, along with
   a related `warehouse/builder.py` bug where several `lsoa_*` derived tables never
   get populated due to a `data/processed/` vs `data/audit/` path mismatch.)

## Candidate Task C — Comprehensive chart-design review (layer 4)

This is an **open design exploration**, not a verification task — use
`superpowers:brainstorming` to scope it, not `subagent-driven-development`.

Walk every dimension page and every section (all 50, not just the ~16 touched by
E1-E14) and ask, independent of whether this plan touched it: "is this the best way
to represent this specific data for a DfT/LTA policy-maker audience?" This could
surface entirely new redesign candidates beyond E1-E14's scope (e.g. tables vs
charts, KPI tiles vs full charts, map/choropleth opportunities not yet used,
small-multiples, etc.).

Recommended sequencing: do this AFTER Task A and B — no point redesigning the
presentation of a section whose data might be wrong (A) or that might not even be
wired to the frontend yet (B).

## Sequencing recommendation

1. Finish and merge `2026-06-11-warehouse-staleness-and-filter-bugs.md` (tasks #22-23,
   in progress) first.
2. Task A (data correctness) — can run via subagent-driven-development, mostly
   mechanical DuckDB queries + spot recomputation.
3. Task B (coverage gaps) — can run via subagent-driven-development, static code
   diff.
4. Task C (chart-design review) — separate brainstorming session once A and B are
   resolved (their findings may change what C even needs to look at).
