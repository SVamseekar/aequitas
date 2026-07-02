


# Phase 2 Complete Fixes — Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix all 44 identified issues across 6 sprints — from broken filter wiring and missing FAISS index through rich narratives, interactive charts, full auth, landing page, and power features — to make Aequitas a production-grade policy intelligence tool.

**Architecture:** All work targets the `feature/phase2-frontend-rag` worktree at `.worktrees/phase2-frontend-rag/`. Backend is FastAPI + DuckDB (pre-computed). Frontend is React 19 + Vite + Observable Plot. Auth via Supabase (transplanted from bharat-alpha). RAG via FAISS + Gemini Flash. Zero runtime analytics.

**Tech Stack:** Python 3.12+, FastAPI, DuckDB, faiss-cpu, sentence-transformers, google-generativeai, python-jose | React 19, Vite, TypeScript, Tailwind CSS 4, shadcn/ui, Observable Plot, D3, MapLibre GL, React Router v7, TanStack React Query, @supabase/supabase-js, sonner

**Working directory:** `/Users/souravamseekarmarti/Projects/aequitas/.worktrees/phase2-frontend-rag/`

---

## File Structure Overview

### Sprint 1 (Data Foundation) — Modified files
```
src/aequitas/warehouse/precompute.py           — MODIFY: expand to 30 filter combos
src/aequitas/warehouse/builder.py              — MODIFY: ensure core tables populated
src/aequitas/warehouse/schema.py               — MODIFY: add missing table schemas
src/aequitas/rag/index_builder.py              — NO CHANGE (already correct)
src/aequitas/intelligence/chart_data_builder.py — MODIFY: fix type mismatches
tests/test_precompute_30.py                    — CREATE: verify 30 combos
tests/test_chart_types.py                      — CREATE: verify chart type alignment
```

### Sprint 2 (Rich Narratives) — Modified files
```
src/aequitas/intelligence/templates/*.j2       — MODIFY: all 20 templates expanded
src/aequitas/intelligence/engine.py            — MODIFY: relax suppression gates
tests/test_narrative_length.py                 — CREATE: min length assertions
```

### Sprint 3 (Interactive Charts) — Modified files
```
frontend/src/components/charts/HorizontalBarChart.tsx    — MODIFY: add tooltips + hover
frontend/src/components/charts/ScatterRegressionChart.tsx — MODIFY: add tooltips + crosshairs
frontend/src/components/charts/LorenzCurveChart.tsx      — MODIFY: add tooltips
frontend/src/components/charts/ShapBarChart.tsx           — MODIFY: add tooltips
frontend/src/components/charts/ChoroplethMap.tsx          — MODIFY: add zoom/pan + hover popup
frontend/src/components/charts/HeatmapChart.tsx           — MODIFY: add cell hover tooltip
frontend/src/components/charts/BoxViolinChart.tsx         — MODIFY: add quartile tooltips
frontend/src/components/charts/ScatterClustersChart.tsx   — MODIFY: add tooltips + cluster legend
frontend/src/components/charts/ChartRenderer.tsx          — MODIFY: add animation wrapper
```

### Sprint 4 (Auth & Users) — New + Modified files
```
frontend/src/integrations/supabase/client.ts   — CREATE: Supabase JS client init
frontend/src/contexts/AuthContext.tsx           — CREATE: auth provider + useAuth hook
frontend/src/components/auth/ProtectedRoute.tsx — CREATE: redirect if unauthenticated
frontend/src/pages/AuthPage.tsx                — CREATE: sign in/up with Google + email
frontend/src/pages/ProfilePage.tsx             — CREATE: user settings
frontend/src/components/chat/ChatSidebar.tsx    — CREATE: conversation history sidebar
frontend/src/components/layout/UserMenu.tsx     — CREATE: avatar dropdown menu
frontend/src/components/saved/SavedAnalyses.tsx — CREATE: bookmarked insights list
frontend/src/components/saved/PolicyNotes.tsx   — CREATE: journal-style policy notes
frontend/src/components/saved/SavedRegions.tsx  — CREATE: tracked regions
frontend/src/lib/db.ts                         — CREATE: Supabase table helpers
frontend/src/App.tsx                           — MODIFY: add auth routes + protected wrapper
frontend/src/api/hooks.ts                      — MODIFY: add auth header to chat requests
src/aequitas/api/auth.py                       — CREATE: JWT validation middleware
src/aequitas/api/config.py                     — MODIFY: add Supabase JWT secret
src/aequitas/api/routers/chat.py               — MODIFY: add auth dependency
src/aequitas/api/routers/conversations.py      — CREATE: CRUD for conversations
supabase/config.toml                           — CREATE: Supabase project config
supabase/migrations/001_initial.sql            — CREATE: tables + RLS policies
```

### Sprint 5 (Landing & Polish) — New + Modified files
```
frontend/src/pages/LandingPage.tsx             — CREATE: hero + dimension cards + CTA
frontend/src/pages/AboutPage.tsx               — CREATE: dimensions + data sources
frontend/src/pages/DisclaimerPage.tsx           — CREATE: legal caveats
frontend/src/pages/ContactPage.tsx             — CREATE: contact form + links
frontend/src/components/layout/StatusBar.tsx    — CREATE: top indicator bar
frontend/src/components/layout/MetricsTicker.tsx — CREATE: scrolling headline stats
frontend/src/components/layout/Footer.tsx       — CREATE: navigation footer
frontend/src/components/chat/SuggestedQuestions.tsx — CREATE: dimension-aware prompts
frontend/src/components/chat/QuickActions.tsx    — CREATE: explore/compare/ask buttons
frontend/src/components/shared/EmptyState.tsx   — CREATE: consistent empty state
frontend/src/index.css                         — MODIFY: dark theme + animations
frontend/src/App.tsx                           — MODIFY: add new routes
frontend/src/components/layout/AppShell.tsx     — MODIFY: add status bar + footer
frontend/src/components/layout/Header.tsx       — MODIFY: add logo + user menu
frontend/src/components/chat/ChatDrawer.tsx     — MODIFY: add suggested questions + auto-resize
```

### Sprint 6 (Power Features) — New + Modified files
```
src/aequitas/api/routers/export.py             — CREATE: PDF generation endpoint
src/aequitas/api/routers/metrics.py            — CREATE: ticker metrics endpoint
frontend/src/pages/ComparePage.tsx              — CREATE: side-by-side region comparison
frontend/src/components/dimension/LsoaDetailPanel.tsx — CREATE: LSOA deep-dive
frontend/src/components/dimension/ScenarioBuilder.tsx — CREATE: interactive sliders
frontend/src/components/dimension/ProvenancePanel.tsx — CREATE: click-to-see-formula
frontend/src/components/dimension/SectionCard.tsx — MODIFY: add provenance + export buttons
frontend/src/App.tsx                           — MODIFY: add compare route
```

---

## Sprint 1: Data Foundation

**Goal:** Fix filter combos, build FAISS index, align chart types, populate core tables.

### Task 1.1: Expand precompute to 30 filter combos

**Files:**
- Modify: `src/aequitas/warehouse/precompute.py:156-165`
- Create: `tests/test_precompute_30.py`

- [ ] **Step 1: Write test for 30 filter combos**

```python
# tests/test_precompute_30.py
"""Verify precompute generates all 30 filter combinations."""
import pytest
from aequitas.warehouse.precompute import _REGIONS, _AREA_TYPES

def test_filter_combo_count():
    """30 combos = 10 regions × 3 area_types."""
    combos = [(r, a) for r in _REGIONS for a in _AREA_TYPES]
    assert len(combos) == 30

def test_no_combos_skipped():
    """Every region × area_type pair must be included."""
    combos = [(r, a) for r in _REGIONS for a in _AREA_TYPES]
    # Verify specific previously-skipped combos exist
    assert ("E12000001", "urban") in combos  # North East urban
    assert ("E12000007", "rural") in combos  # London rural
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /Users/souravamseekarmarti/Projects/aequitas/.worktrees/phase2-frontend-rag && .venv/bin/python -m pytest tests/test_precompute_30.py -v`
Expected: FAIL (current code skips region+area combos)

- [ ] **Step 3: Remove the filter skip in precompute.py**

In `precompute.py` around line 159, remove:
```python
# REMOVE this block:
if region != "all" and urban_rural != "all":
    continue
```

The loop should now iterate all 30 combinations without skipping.

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/python -m pytest tests/test_precompute_30.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add tests/test_precompute_30.py src/aequitas/warehouse/precompute.py
git commit -m "fix(precompute): expand to all 30 filter combos — region×area_type"
```

### Task 1.2: Audit and fix chart_data.type alignment

**Files:**
- Create: `tests/test_chart_types.py`
- Modify: `src/aequitas/intelligence/chart_data_builder.py` (if mismatches found)
- Modify: `src/aequitas/warehouse/precompute.py` (if section builders emit wrong types)

- [ ] **Step 1: Write audit script to compare backend types vs frontend**

```python
# tests/test_chart_types.py
"""Verify every section's chart_data.type matches a frontend ChartRenderer case."""
import json
import duckdb
import pytest

FRONTEND_CHART_TYPES = {
    "horizontal_bar", "grouped_bar", "stacked_bar",
    "scatter_regression", "lorenz_curve", "shap_bar",
    "choropleth", "heatmap", "box_violin", "scatter_clusters",
}

@pytest.fixture
def db():
    conn = duckdb.connect("data/aequitas.duckdb", read_only=True)
    yield conn
    conn.close()

def test_all_chart_types_recognized(db):
    """Every chart_data.type in the warehouse must match a frontend case."""
    rows = db.execute("""
        SELECT DISTINCT section_id, chart_data->>'type' AS chart_type
        FROM section_results
        WHERE chart_data IS NOT NULL AND chart_data != '{}'
    """).fetchall()
    unrecognized = [
        (sid, ct) for sid, ct in rows
        if ct is not None and ct not in FRONTEND_CHART_TYPES
    ]
    assert unrecognized == [], f"Unrecognized chart types: {unrecognized}"

def test_no_null_chart_types(db):
    """Sections with chart_data should always have a type field."""
    rows = db.execute("""
        SELECT section_id, chart_data
        FROM section_results
        WHERE chart_data IS NOT NULL
          AND chart_data != '{}'
          AND (chart_data->>'type') IS NULL
    """).fetchall()
    assert rows == [], f"Sections missing chart_data.type: {[r[0] for r in rows]}"

def test_chart_type_variety(db):
    """At least 6 different chart types should be used across sections."""
    rows = db.execute("""
        SELECT DISTINCT chart_data->>'type' AS ct
        FROM section_results
        WHERE chart_data IS NOT NULL AND chart_data != '{}'
    """).fetchall()
    types_used = {r[0] for r in rows if r[0]}
    assert len(types_used) >= 6, f"Only {len(types_used)} chart types used: {types_used}"
```

- [ ] **Step 2: Run audit to identify mismatches**

Run: `.venv/bin/python -m pytest tests/test_chart_types.py -v`
Expected: May FAIL — fix any reported mismatches

- [ ] **Step 3: Fix any mismatches found**

For each unrecognized type, either:
- Fix the builder function in `chart_data_builder.py` to emit the correct type string
- Or update the section's builder call in `precompute.py` to use the correct builder

Common mismatches to check:
- `"bar"` should be `"horizontal_bar"`
- `"scatter"` should be `"scatter_regression"`
- `"violin"` should be `"box_violin"`
- Sections with `chart_data: {}` need their builder function wired

- [ ] **Step 4: Run tests again**

Run: `.venv/bin/python -m pytest tests/test_chart_types.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add tests/test_chart_types.py src/aequitas/intelligence/chart_data_builder.py src/aequitas/warehouse/precompute.py
git commit -m "fix(charts): align all chart_data.type values with frontend ChartRenderer"
```

### Task 1.3: Build FAISS index

**Files:**
- No code changes — `src/aequitas/rag/index_builder.py` is already correct
- Verify: `data/faiss_index.bin` and `data/faiss_metadata.json` are created

- [ ] **Step 1: Verify warehouse has narratives**

```bash
cd /Users/souravamseekarmarti/Projects/aequitas/.worktrees/phase2-frontend-rag
.venv/bin/python -c "
import duckdb
conn = duckdb.connect('data/aequitas.duckdb', read_only=True)
count = conn.execute(\"SELECT COUNT(*) FROM section_results WHERE narrative IS NOT NULL AND narrative != ''\").fetchone()[0]
print(f'Narratives available: {count}')
conn.close()
"
```
Expected: 300+ narratives

- [ ] **Step 2: Build the FAISS index**

```bash
.venv/bin/python -c "
from aequitas.core.config import PipelineConfig
from aequitas.rag.index_builder import build_faiss_index
cfg = PipelineConfig()
result = build_faiss_index(cfg)
print(result)
"
```
Expected: `faiss_index.bin` and `faiss_metadata.json` created in `data/`

- [ ] **Step 3: Verify index files exist**

```bash
ls -la data/faiss_index.bin data/faiss_metadata.json
```
Expected: Both files exist, non-zero size

- [ ] **Step 4: Add FAISS files to .gitignore and document rebuild**

FAISS binary files can be large and should not bloat the git repo. Add to `.gitignore`:
```
data/faiss_index.bin
data/faiss_metadata.json
```

Document the rebuild step in a comment at the top of `index_builder.py`:
```python
# To rebuild: .venv/bin/python -c "from aequitas.core.config import PipelineConfig; from aequitas.rag.index_builder import build_faiss_index; build_faiss_index(PipelineConfig())"
```

```bash
git add .gitignore src/aequitas/rag/index_builder.py
git commit -m "chore: gitignore FAISS binary files — rebuild with 'aequitas rag'"
```

### Task 1.4: Populate core DuckDB tables from Phase 0 parquets

**Files:**
- Modify: `src/aequitas/warehouse/builder.py`

- [ ] **Step 1: Check what Phase 0 parquets are available**

```bash
ls data/audit/*.parquet | head -20
```

- [ ] **Step 2: Add loader for core tables in builder.py**

In `builder.py`, add a function to load stops, routes, and lsoa_demographics from the Phase 0 audit parquets:

```python
def load_core_tables(conn: duckdb.DuckDBPyConnection, audit_dir: Path) -> None:
    """Load core reference tables from Phase 0 parquets."""
    parquet_map = {
        "lsoa_demographics": "master_lsoa_table.parquet",
        "lsoa_service_quality": "lsoa_service_quality.parquet",
        "lsoa_equity_metrics": "lsoa_equity_metrics.parquet",
    }
    for table_name, filename in parquet_map.items():
        path = audit_dir / filename
        if path.exists():
            conn.execute(f"CREATE OR REPLACE TABLE {table_name} AS SELECT * FROM read_parquet('{path}')")
            count = conn.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()[0]
            logger.info(f"Loaded {table_name}: {count} rows")
```

- [ ] **Step 3: Call loader during warehouse build**

Wire `load_core_tables()` into the warehouse build pipeline so it runs before precompute.

- [ ] **Step 4: Verify tables populated**

```bash
.venv/bin/python -c "
import duckdb
conn = duckdb.connect('data/aequitas.duckdb', read_only=True)
for t in ['lsoa_demographics', 'lsoa_service_quality', 'lsoa_equity_metrics']:
    n = conn.execute(f'SELECT COUNT(*) FROM {t}').fetchone()[0]
    print(f'{t}: {n} rows')
conn.close()
"
```
Expected: 33,755 rows per LSOA table

- [ ] **Step 5: Commit**

```bash
git add src/aequitas/warehouse/builder.py
git commit -m "feat(warehouse): populate core tables from Phase 0 parquets"
```

### Task 1.5: Rebuild warehouse with 30 combos + fixed charts

**Files:**
- No code changes — this is a build step

- [ ] **Step 1: Rebuild the warehouse**

```bash
cd /Users/souravamseekarmarti/Projects/aequitas/.worktrees/phase2-frontend-rag
.venv/bin/python -m aequitas.pipeline run --stages warehouse
```

- [ ] **Step 2: Verify 30 × 51 = 1,530 section_results**

```bash
.venv/bin/python -c "
import duckdb
conn = duckdb.connect('data/aequitas.duckdb', read_only=True)
total = conn.execute('SELECT COUNT(*) FROM section_results').fetchone()[0]
combos = conn.execute('SELECT COUNT(DISTINCT region || urban_rural) FROM section_results').fetchone()[0]
print(f'Total rows: {total}, Distinct filter combos: {combos}')
conn.close()
"
```
Expected: ~1,530 rows, 30 distinct filter combos

- [ ] **Step 3: Rebuild FAISS index with new narratives**

```bash
.venv/bin/python -c "
from aequitas.core.config import PipelineConfig
from aequitas.rag.index_builder import build_faiss_index
result = build_faiss_index(PipelineConfig())
print(result)
"
```

- [ ] **Step 4: Commit rebuilt data**

```bash
git add data/aequitas.duckdb data/faiss_index.bin data/faiss_metadata.json
git commit -m "data: rebuild warehouse with 30 filter combos + FAISS index"
```

---

## Sprint 2: Rich Narratives

**Goal:** Expand every template from 5-10 lines to 30-60 lines with headline finding, regional comparison, policy implication, methodology note.

### Task 2.1: Expand Jinja2 templates — Equity & Core group

**Files:**
- Modify: `src/aequitas/intelligence/templates/equity.j2`
- Modify: `src/aequitas/intelligence/templates/equity_decile.j2`
- Modify: `src/aequitas/intelligence/templates/ranking.j2`
- Modify: `src/aequitas/intelligence/templates/correlation.j2`
- Modify: `src/aequitas/intelligence/templates/coverage_gap.j2`
- Create: `tests/test_narrative_length.py`

- [ ] **Step 1: Write minimum narrative length test**

```python
# tests/test_narrative_length.py
"""Narratives must be substantive — minimum 200 characters when not suppressed."""
import duckdb
import pytest

@pytest.fixture
def db():
    conn = duckdb.connect("data/aequitas.duckdb", read_only=True)
    yield conn
    conn.close()

def test_narrative_minimum_length(db):
    """Non-suppressed narratives must be at least 200 chars."""
    rows = db.execute("""
        SELECT section_id, region, LENGTH(narrative) as len
        FROM section_results
        WHERE narrative IS NOT NULL AND narrative != ''
          AND LENGTH(narrative) < 200
    """).fetchall()
    short = [(r[0], r[1], r[2]) for r in rows]
    assert len(short) == 0, f"{len(short)} narratives too short: {short[:5]}..."

def test_narrative_has_policy_implication(db):
    """At least 80% of narratives should mention 'policy' or 'implication' or 'recommendation'."""
    total = db.execute("""
        SELECT COUNT(*) FROM section_results
        WHERE narrative IS NOT NULL AND narrative != ''
    """).fetchone()[0]
    policy = db.execute("""
        SELECT COUNT(*) FROM section_results
        WHERE narrative IS NOT NULL AND narrative != ''
          AND (LOWER(narrative) LIKE '%policy%'
            OR LOWER(narrative) LIKE '%implication%'
            OR LOWER(narrative) LIKE '%intervention%'
            OR LOWER(narrative) LIKE '%recommendation%')
    """).fetchone()[0]
    pct = policy / total * 100 if total > 0 else 0
    assert pct >= 80, f"Only {pct:.1f}% of narratives mention policy implications"
```

- [ ] **Step 2: Run test to verify current narratives fail**

Run: `.venv/bin/python -m pytest tests/test_narrative_length.py -v`
Expected: FAIL (current narratives are 53-505 chars, median 235)

- [ ] **Step 3: Expand equity.j2 template**

Each template should follow this structure:
1. **Headline finding** (1-2 sentences, bold key numbers)
2. **Context** (what this means, UK income Gini comparison, etc.)
3. **Regional comparison** (best vs worst, if available)
4. **Policy implication** (what policymakers should consider)
5. **Methodology note** (data source, confidence level)

Example expanded `equity.j2`:

```jinja2
{% if gini is not none -%}
## Key Finding

The Gini coefficient for bus service distribution is **{{ gini|round(4) }}**, {{ "significantly exceeding" if gini > 0.5 else "exceeding" if gini > 0.36 else "below" }} the UK income Gini of approximately 0.36. This indicates {% if gini > 0.36 %}bus service access is distributed more unequally than household incomes across England{% else %}a relatively equitable distribution of bus services{% endif %}.

## Distribution Analysis

The Palma ratio of **{{ palma|round(2) }}** reveals that the top 10% of LSOAs by service level receive {{ palma|round(1) }}× more bus trips per capita than the bottom 40%. {% if palma > 4 %}This level of concentration represents a significant structural inequity in public transport provision — the most well-served areas receive disproportionately more investment relative to population need.{% endif %}

{%- if concentration_index is not none %}

The Concentration Index of **{{ "%+.4f"|format(concentration_index) }}** confirms that bus services are concentrated in {{ "more affluent" if concentration_index > 0 else "more deprived" }} areas. {% if concentration_index > 0 %}Despite policy intentions, bus services disproportionately serve wealthier communities — a pattern driven by commercially viable routes clustering in high-density, higher-income corridors.{% else %}Services show a pro-equity distribution, serving more deprived communities proportionally more.{% endif %}
{%- endif %}

{%- if best and worst %}

## Regional Comparison

**{{ best.name }}** shows the most equitable distribution (lowest Gini), while **{{ worst.name }}** has the greatest inequality. The gap between best and worst regions suggests that local authority-level transport planning significantly influences equity outcomes.
{%- endif %}

## Policy Implications

{% if gini > 0.5 -%}
The high Gini ({{ gini|round(3) }}) combined with a {{ "pro-rich" if concentration_index > 0 else "pro-poor" }} Concentration Index suggests intervention is needed to redistribute service provision. Under the Bus Services Act 2025, Local Transport Authorities gaining franchising powers should prioritise route planning that addresses these distributional inequities.
{%- else -%}
While the distribution is {{ "moderately unequal" if gini > 0.36 else "relatively equitable" }}, ongoing monitoring through the equity framework ensures service changes do not worsen inequality. The Bus Services Act 2025 provides new tools for LTAs to maintain equitable coverage.
{%- endif %}

*Methodology: Gini and Palma calculated from per-capita bus trips across {{ n_lsoas|default(33755)|int|format_thousands }} LSOAs, population-weighted using Census 2021 data. Concentration Index uses IMD 2025 deprivation ranking.*
{%- endif %}
```

- [ ] **Step 4: Expand remaining templates in this group**

Apply the same 5-part structure (headline, context, regional comparison, policy implication, methodology) to:
- `equity_decile.j2` — decile-by-decile breakdown with disparity interpretation
- `ranking.j2` — best/worst with gap analysis and intervention framing
- `correlation.j2` — strength interpretation, causal caveats, policy relevance
- `coverage_gap.j2` — zero-access population, worst regions, investment case

- [ ] **Step 5: Commit**

```bash
git add src/aequitas/intelligence/templates/ tests/test_narrative_length.py
git commit -m "feat(narratives): expand equity + core templates to policy-grade depth"
```

### Task 2.2: Expand Jinja2 templates — Service Quality & Route group

**Files:**
- Modify: `src/aequitas/intelligence/templates/service_hours.j2`
- Modify: `src/aequitas/intelligence/templates/weekend_penalty.j2`
- Modify: `src/aequitas/intelligence/templates/distribution.j2`
- Modify: `src/aequitas/intelligence/templates/market_concentration.j2`
- Modify: `src/aequitas/intelligence/templates/network_topology.j2`
- Modify: `src/aequitas/intelligence/templates/desert_spotlight.j2`
- Modify: `src/aequitas/intelligence/templates/urban_rural_gap.j2`

- [ ] **Step 1: Expand all 7 templates**

Each follows the 5-part structure: headline finding, context, regional comparison, policy implication, methodology note.

Key content per template:
- **service_hours.j2** — operating span analysis, evening isolation % and impact, comparison with DfT minimum standards
- **weekend_penalty.j2** — Sunday desert count and %, economic impact of weekend service gaps, NHS access implications
- **distribution.j2** — quartile interpretation, outlier analysis, what the spread means for consistency of service
- **market_concentration.j2** — HHI interpretation, operator landscape, Bus Services Act franchising implications
- **network_topology.j2** — cross-LA routes %, network connectivity, dead-end vs through routes
- **desert_spotlight.j2** — service desert characteristics, demographic vulnerability, DRT intervention case
- **urban_rural_gap.j2** — gap magnitude, population affected, policy options (DRT, frequency restoration)

- [ ] **Step 2: Run narrative length tests**

Run: `.venv/bin/python -m pytest tests/test_narrative_length.py -v`

- [ ] **Step 3: Commit**

```bash
git add src/aequitas/intelligence/templates/
git commit -m "feat(narratives): expand service quality + route templates"
```

### Task 2.3: Expand Jinja2 templates — ML, Economic, Policy group

**Files:**
- Modify: `src/aequitas/intelligence/templates/ml_prediction.j2`
- Modify: `src/aequitas/intelligence/templates/ml_clusters.j2`
- Modify: `src/aequitas/intelligence/templates/anomaly_spotlight.j2`
- Modify: `src/aequitas/intelligence/templates/economic_value.j2`
- Modify: `src/aequitas/intelligence/templates/bcr_analysis.j2`
- Modify: `src/aequitas/intelligence/templates/carbon_reduction.j2`
- Modify: `src/aequitas/intelligence/templates/policy_scenario.j2`
- Modify: `src/aequitas/intelligence/templates/scenario_comparison.j2`
- Modify: `src/aequitas/intelligence/templates/tier_distribution.j2`
- Modify: `src/aequitas/intelligence/templates/gap_to_target.j2`
- Modify: `src/aequitas/intelligence/templates/accessibility_gap.j2`
- Modify: `src/aequitas/intelligence/templates/demographic_breakdown.j2`
- Modify: `src/aequitas/intelligence/templates/heatmap.j2`

- [ ] **Step 1: Expand all 13 remaining templates**

Key content per template:
- **ml_prediction.j2** — R² interpretation, SHAP top-3 features with explanations, policy-driven variance claim, model limitations caveat
- **ml_clusters.j2** — cluster descriptions, archetype profiles, what cluster membership means for intervention targeting
- **anomaly_spotlight.j2** — anomaly count and %, characteristics of anomalous LSOAs, investigation recommendations
- **economic_value.j2** — GDP multiplier context, regional economic contribution of bus services
- **bcr_analysis.j2** — BCR band interpretation (Poor/Low/Medium/High/Very High), TAG methodology reference, BCR limitations (degenerate urban/rural issue noted)
- **carbon_reduction.j2** — modal shift CO2 savings, DESNZ 2025 factors cited, monetised value at TAG carbon price
- **policy_scenario.j2** — scenario parameters, population affected, cost-benefit summary, confidence level
- **scenario_comparison.j2** — ranked scenarios by impact/cost, recommended portfolio
- **tier_distribution.j2** — BSA tier breakdown, franchising readiness interpretation
- **gap_to_target.j2** — investment quantum, areas below target, cost per beneficiary
- **accessibility_gap.j2** — 2SFCA methodology, zero-access demographics, NHS/education access implications
- **demographic_breakdown.j2** — protected characteristic analysis, Equality Act compliance framing
- **heatmap.j2** — cross-tabulation interpretation, where deprivation and poor service intersect

- [ ] **Step 2: Run all narrative tests**

Run: `.venv/bin/python -m pytest tests/test_narrative_length.py -v`
Expected: PASS (all narratives ≥200 chars, ≥80% mention policy)

- [ ] **Step 3: Commit**

```bash
git add src/aequitas/intelligence/templates/
git commit -m "feat(narratives): expand ML, economic, and policy templates"
```

### Task 2.4: Fix narrative suppression — populate empty stats dicts

**Root cause:** The 52% suppression rate is NOT caused by strict evidence gate rules. The rules defined in `rules.py` are not wired into `engine.py`'s `generate()` path. Suppression happens because `_build_section()` in `precompute.py` returns empty `stats` dicts for many section/filter combinations — and `engine.py` suppresses when `stats` is empty. The fix is in `precompute.py`, not `engine.py`.

**Files:**
- Modify: `src/aequitas/warehouse/precompute.py` (fix `_build_section` to populate stats for all combos)
- Modify: `src/aequitas/intelligence/engine.py` (add loguru logging to except block for debugging)

- [ ] **Step 1: Audit which sections return empty stats**

```bash
.venv/bin/python -c "
import duckdb, json
conn = duckdb.connect('data/aequitas.duckdb', read_only=True)
rows = conn.execute(\"\"\"
    SELECT section_id, region, urban_rural, stats
    FROM section_results
    WHERE narrative IS NULL OR narrative = ''
    ORDER BY section_id, region
\"\"\").fetchall()
# Group by section_id to see pattern
from collections import Counter
by_section = Counter(r[0] for r in rows)
for sid, count in by_section.most_common():
    # Check if stats are empty
    sample = next(r for r in rows if r[0] == sid)
    stats = json.loads(sample[3]) if sample[3] else {}
    print(f'{sid}: {count} suppressed, stats keys: {list(stats.keys())[:5]}')
conn.close()
"
```

- [ ] **Step 2: Fix _build_section for each suppressed section**

For each section_id with empty stats, trace the data pipeline:
1. Check which Parquet file the section reads from (see `SECTION_REGISTRY`)
2. Check if the filter logic in `_build_section` correctly subsets the data
3. Ensure the stats dict is populated even for filtered subsets (use national fallback values where regional data is unavailable)

- [ ] **Step 3: Add logging to engine.py except block**

In `engine.py`, the broad `except Exception` silently swallows errors. Add loguru logging:

```python
except Exception as e:
    logger.warning(f"Narrative generation failed for {section_id}: {e}")
    suppressed = True
    narrative = ""
```

- [ ] **Step 4: Target ≤20% suppression rate**

After fixing stats population, suppression should drop from ~52% to ≤20%. The remaining 20% should be genuinely unsupported sections (e.g., no data for that region+area combo).

- [ ] **Step 5: Commit**

```bash
git add src/aequitas/warehouse/precompute.py src/aequitas/intelligence/engine.py
git commit -m "fix(precompute): populate stats for all sections — reduce suppression from 52% to <20%"
```

### Task 2.5: Rebuild warehouse + FAISS with expanded narratives

- [ ] **Step 1: Rebuild warehouse**

```bash
.venv/bin/python -m aequitas.pipeline run --stages warehouse
```

- [ ] **Step 2: Verify narrative quality**

```bash
.venv/bin/python -c "
import duckdb
conn = duckdb.connect('data/aequitas.duckdb', read_only=True)
stats = conn.execute(\"\"\"
    SELECT
        COUNT(*) as total,
        SUM(CASE WHEN narrative IS NULL OR narrative = '' THEN 1 ELSE 0 END) as suppressed,
        AVG(LENGTH(narrative)) FILTER (WHERE narrative IS NOT NULL AND narrative != '') as avg_len,
        MIN(LENGTH(narrative)) FILTER (WHERE narrative IS NOT NULL AND narrative != '') as min_len
    FROM section_results
\"\"\").fetchone()
print(f'Total: {stats[0]}, Suppressed: {stats[1]} ({stats[1]/stats[0]*100:.1f}%)')
print(f'Avg length: {stats[2]:.0f} chars, Min: {stats[3]} chars')
conn.close()
"
```
Expected: ≤20% suppressed, avg length ≥400 chars, min ≥200 chars

- [ ] **Step 3: Rebuild FAISS index**

```bash
.venv/bin/python -c "
from aequitas.core.config import PipelineConfig
from aequitas.rag.index_builder import build_faiss_index
result = build_faiss_index(PipelineConfig())
print(result)
"
```

- [ ] **Step 4: Run all tests**

Run: `.venv/bin/python -m pytest tests/ -v`

- [ ] **Step 5: Commit**

```bash
git add data/aequitas.duckdb data/faiss_index.bin data/faiss_metadata.json
git commit -m "data: rebuild warehouse with expanded narratives + updated FAISS index"
```

---

## Sprint 3: Interactive Charts

**Goal:** Add tooltips, hover states, click handlers, crosshairs, zoom/pan, and animations to all 10 chart types.

### Task 3.1: Add tooltips to bar charts (horizontal, grouped, stacked)

**Files:**
- Modify: `frontend/src/components/charts/HorizontalBarChart.tsx`

- [ ] **Step 1: Add Observable Plot tip() mark for hover tooltips**

Observable Plot supports the `tip` option on marks. Add to bar marks:

```typescript
Plot.barX(data, {
  x: "value",
  y: "label",
  fill: fillColor,
  tip: true,  // Enable native Observable Plot tooltip
  title: (d: Record<string, unknown>) =>
    `${d.label}\n${xLabel}: ${Number(d.value).toLocaleString()}`,
})
```

For grouped/stacked bars, include the series name in the tooltip.

- [ ] **Step 2: Add hover highlight effect**

Add CSS for `rect:hover` opacity change:

```css
.chart-container rect:hover {
  opacity: 0.8;
  filter: brightness(1.1);
  cursor: pointer;
}
```

- [ ] **Step 3: Test in browser**

Run: `cd frontend && npm run dev`
Navigate to any dimension page, hover over bar charts. Verify tooltips show value and label.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/components/charts/HorizontalBarChart.tsx
git commit -m "feat(charts): add tooltips + hover highlight to bar charts"
```

### Task 3.2: Add tooltips + crosshairs to scatter plots

**Files:**
- Modify: `frontend/src/components/charts/ScatterRegressionChart.tsx`
- Modify: `frontend/src/components/charts/ScatterClustersChart.tsx`

- [ ] **Step 1: Add tip mark to scatter regression**

```typescript
Plot.dot(data, {
  x: "x",
  y: "y",
  r: 3,
  fill: "#4f46e5",
  fillOpacity: 0.5,
  tip: true,
  title: (d: Record<string, unknown>) =>
    `${d.id || ''}\n${xLabel}: ${Number(d.x).toFixed(2)}\n${yLabel}: ${Number(d.y).toFixed(2)}`,
})
```

- [ ] **Step 2: Add crosshair rule marks**

Observable Plot `crosshair` mark:

```typescript
Plot.crosshairX(data, { x: "x", y: "y" }),
Plot.crosshairY(data, { x: "x", y: "y" }),
```

- [ ] **Step 3: Add tip to scatter clusters with cluster name**

```typescript
Plot.dot(data, {
  x: "x",
  y: "y",
  fill: "cluster",
  tip: true,
  title: (d: Record<string, unknown>) =>
    `Cluster: ${clusterLabels[d.cluster as number] || d.cluster}\n${xLabel}: ${Number(d.x).toFixed(2)}\n${yLabel}: ${Number(d.y).toFixed(2)}`,
})
```

- [ ] **Step 4: Commit**

```bash
git add frontend/src/components/charts/ScatterRegressionChart.tsx frontend/src/components/charts/ScatterClustersChart.tsx
git commit -m "feat(charts): add tooltips + crosshairs to scatter plots"
```

### Task 3.3: Add tooltips to Lorenz curve, SHAP bar, heatmap, box-violin

**Files:**
- Modify: `frontend/src/components/charts/LorenzCurveChart.tsx`
- Modify: `frontend/src/components/charts/ShapBarChart.tsx`
- Modify: `frontend/src/components/charts/HeatmapChart.tsx`
- Modify: `frontend/src/components/charts/BoxViolinChart.tsx`

- [ ] **Step 1: Lorenz curve — tooltip showing cumulative population % and service %**

```typescript
Plot.line(curvePoints, {
  x: "cum_pop",
  y: "cum_service",
  tip: true,
  title: (d: Record<string, unknown>) =>
    `Population: ${(Number(d.cum_pop) * 100).toFixed(1)}%\nService: ${(Number(d.cum_service) * 100).toFixed(1)}%`,
})
```

- [ ] **Step 2: SHAP bar — tooltip showing feature name and importance value**

```typescript
Plot.barX(features, {
  x: "importance",
  y: "name",
  tip: true,
  title: (d: Record<string, unknown>) => `${d.name}: ${Number(d.importance).toFixed(4)}`,
})
```

- [ ] **Step 3: Heatmap — cell hover tooltip with x-label, y-label, value**

```typescript
Plot.cell(cells, {
  x: "x",
  y: "y",
  fill: "value",
  tip: true,
  title: (d: Record<string, unknown>) =>
    `${d.x_label} × ${d.y_label}\nValue: ${Number(d.value).toFixed(2)}`,
})
```

- [ ] **Step 4: Box-violin — tooltip showing quartile stats on hover**

```typescript
// Add tip to the box rule marks
Plot.ruleY(groups, {
  y: "label",
  x1: "q1",
  x2: "q3",
  tip: true,
  title: (d: Record<string, unknown>) =>
    `${d.label}\nMin: ${Number(d.min).toFixed(1)}\nQ1: ${Number(d.q1).toFixed(1)}\nMedian: ${Number(d.median).toFixed(1)}\nQ3: ${Number(d.q3).toFixed(1)}\nMax: ${Number(d.max).toFixed(1)}`,
})
```

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/charts/LorenzCurveChart.tsx frontend/src/components/charts/ShapBarChart.tsx frontend/src/components/charts/HeatmapChart.tsx frontend/src/components/charts/BoxViolinChart.tsx
git commit -m "feat(charts): add tooltips to Lorenz, SHAP, heatmap, and box-violin charts"
```

### Task 3.4: Add zoom/pan to choropleth map + region hover popup

**Files:**
- Modify: `frontend/src/components/charts/ChoroplethMap.tsx`

- [ ] **Step 1: Enable scroll zoom + drag pan**

MapLibre GL supports this natively. Ensure the map init includes:

```typescript
const map = new maplibregl.Map({
  container: containerRef.current,
  style: mapStyle,
  center: [-1.5, 52.8],  // England center
  zoom: 5.5,
  scrollZoom: true,       // Enable scroll zoom
  dragPan: true,          // Enable drag pan
  doubleClickZoom: true,
})
```

- [ ] **Step 2: Add hover popup with region name + value**

```typescript
map.on("mousemove", "regions-fill", (e) => {
  if (e.features && e.features.length > 0) {
    const feature = e.features[0]
    const name = feature.properties?.area_name || ""
    const value = feature.properties?.value
    popup.setLngLat(e.lngLat).setHTML(
      `<strong>${name}</strong><br/>${metric}: ${Number(value).toLocaleString()}`
    ).addTo(map)
    map.getCanvas().style.cursor = "pointer"
  }
})

map.on("mouseleave", "regions-fill", () => {
  popup.remove()
  map.getCanvas().style.cursor = ""
})
```

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/charts/ChoroplethMap.tsx
git commit -m "feat(charts): add zoom/pan + hover popup to choropleth maps"
```

### Task 3.5: Add chart fade-in animations

**Files:**
- Modify: `frontend/src/components/charts/ChartRenderer.tsx`
- Modify: `frontend/src/index.css`

- [ ] **Step 1: Add fade-in animation CSS**

```css
@keyframes chart-fade-in {
  from { opacity: 0; transform: translateY(8px); }
  to { opacity: 1; transform: translateY(0); }
}
.chart-animate-in {
  animation: chart-fade-in 0.4s ease-out;
}
```

- [ ] **Step 2: Wrap chart output in animation div**

In `ChartRenderer.tsx`, wrap the rendered chart:

```typescript
return (
  <ChartErrorBoundary>
    <div className="chart-animate-in">
      <Suspense fallback={fallback}>{chart}</Suspense>
    </div>
  </ChartErrorBoundary>
)
```

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/charts/ChartRenderer.tsx frontend/src/index.css
git commit -m "feat(charts): add fade-in animation to all chart types"
```

---

### Task 3.6: Add vitest tests for chart interactivity

**Files:**
- Create: `frontend/src/components/charts/__tests__/ChartRenderer.test.tsx`

- [ ] **Step 1: Write component tests for chart rendering**

```typescript
// frontend/src/components/charts/__tests__/ChartRenderer.test.tsx
import { render, screen } from "@testing-library/react"
import { describe, it, expect } from "vitest"
import { ChartRenderer } from "../ChartRenderer"

describe("ChartRenderer", () => {
  it("renders null for empty chartData", () => {
    const { container } = render(<ChartRenderer chartData={{}} />)
    expect(container.firstChild).toBeNull()
  })

  it("renders DataTable for unknown chart type", () => {
    render(<ChartRenderer chartData={{ type: "unknown_type", data: [] }} />)
    // DataTable is the default fallback
    expect(screen.getByRole("table")).toBeTruthy()
  })

  it("renders chart-animate-in wrapper for valid types", () => {
    const { container } = render(
      <ChartRenderer chartData={{ type: "horizontal_bar", data: [{ label: "A", value: 1 }] }} />
    )
    expect(container.querySelector(".chart-animate-in")).toBeTruthy()
  })
})
```

- [ ] **Step 2: Run vitest**

Run: `cd frontend && npx vitest run src/components/charts/__tests__/ --reporter verbose`

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/charts/__tests__/
git commit -m "test(charts): add vitest tests for ChartRenderer dispatch and animation"
```

---

## Sprint 4: Auth & User System

**Goal:** Full Supabase auth, user profiles, conversation persistence, saved analyses, policy notes.

**Reference:** Transplant patterns from `/Users/souravamseekarmarti/Projects/bharat-alpha/`

### Task 4.1: Set up Supabase client and AuthContext

**Files:**
- Create: `frontend/src/integrations/supabase/client.ts`
- Create: `frontend/src/contexts/AuthContext.tsx`
- Create: `frontend/src/components/auth/ProtectedRoute.tsx`
- Modify: `frontend/package.json` (add @supabase/supabase-js)

- [ ] **Step 1: Install Supabase JS SDK**

```bash
cd frontend && npm install @supabase/supabase-js
```

- [ ] **Step 2: Create Supabase client**

```typescript
// frontend/src/integrations/supabase/client.ts
import { createClient } from "@supabase/supabase-js"

const supabaseUrl = import.meta.env.VITE_SUPABASE_URL
const supabaseKey = import.meta.env.VITE_SUPABASE_PUBLISHABLE_KEY

if (!supabaseUrl || !supabaseKey) {
  console.warn("Supabase credentials not configured — auth will be disabled")
}

export const supabase = createClient(
  supabaseUrl || "http://localhost:54321",
  supabaseKey || "placeholder",
)
```

- [ ] **Step 3: Create AuthContext (transplant from bharat-alpha)**

Copy the pattern from `/Users/souravamseekarmarti/Projects/bharat-alpha/src/contexts/AuthContext.tsx` — the structure is identical. Change imports only.

- [ ] **Step 4: Create ProtectedRoute**

```typescript
// frontend/src/components/auth/ProtectedRoute.tsx
import { Navigate } from "react-router-dom"
import { useAuth } from "@/contexts/AuthContext"

export function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const { user, loading } = useAuth()
  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="w-2 h-2 rounded-full bg-indigo-500 animate-pulse" />
      </div>
    )
  }
  if (!user) return <Navigate to="/auth" replace />
  return <>{children}</>
}
```

- [ ] **Step 5: Commit**

```bash
git add frontend/src/integrations/ frontend/src/contexts/ frontend/src/components/auth/ frontend/package.json frontend/package-lock.json
git commit -m "feat(auth): add Supabase client + AuthContext + ProtectedRoute"
```

### Task 4.2: Create Auth page

**Files:**
- Create: `frontend/src/pages/AuthPage.tsx`
- Modify: `frontend/src/App.tsx`

- [ ] **Step 1: Create AuthPage adapted from bharat-alpha**

Transplant from `/Users/souravamseekarmarti/Projects/bharat-alpha/src/pages/Auth.tsx`. Changes:
- Replace bharat-alpha branding with Aequitas branding
- Replace stock index metrics with policy headline stats (Gini, Palma, etc.)
- Replace "Research with Precision" → "Policy Intelligence with Evidence"
- Replace "Indian equity analysis" → "UK bus transport policy analytics"
- Replace "NOT INVESTMENT ADVICE" → "POLICY ANALYSIS TOOL — NOT OFFICIAL DfT GUIDANCE"
- Redirect to `/` not `/dashboard`
- Change accent color from orange to indigo

- [ ] **Step 2: Wire AuthPage into App.tsx routes**

Add route: `<Route path="/auth" element={<AuthPage />} />`
Wrap main routes with `<ProtectedRoute>` (except /auth and /landing).

- [ ] **Step 3: Test auth flow in browser**

Verify: unauthenticated users → /auth, Google OAuth works, email/password works, redirect to / on success.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/pages/AuthPage.tsx frontend/src/App.tsx
git commit -m "feat(auth): add sign-in page with Google OAuth + email/password"
```

### Task 4.3: Backend JWT validation

**Files:**
- Create: `src/aequitas/api/auth.py`
- Modify: `src/aequitas/api/config.py`
- Modify: `src/aequitas/api/routers/chat.py`

- [ ] **Step 1: Install python-jose**

```bash
cd /Users/souravamseekarmarti/Projects/aequitas/.worktrees/phase2-frontend-rag
.venv/bin/pip install python-jose[cryptography]
```

- [ ] **Step 2: Create auth.py (transplant from bharat-alpha)**

Copy from `/Users/souravamseekarmarti/Projects/bharat-alpha/backend/auth.py`. Change import path from `backend.config` to `aequitas.api.config`.

- [ ] **Step 3: Add SUPABASE_JWT_SECRET to config.py**

```python
# In config.py, add:
supabase_jwt_secret: str = ""  # Empty = dev mode (skip validation)
```

- [ ] **Step 4: Protect chat endpoint**

In `routers/chat.py`, add `user: dict = Depends(verify_supabase_jwt)` to the chat endpoint.

- [ ] **Step 5: Create conversations router and register in app.py**

Create `src/aequitas/api/routers/conversations.py` with CRUD endpoints:
- `GET /conversations` — list user's conversations
- `POST /conversations` — create new conversation
- `GET /conversations/{id}/messages` — get messages for a conversation
- `POST /conversations/{id}/messages` — add message to conversation
- `DELETE /conversations/{id}` — delete conversation

All endpoints require `user: dict = Depends(verify_supabase_jwt)`.

**Important:** Register ALL new routers in `app.py`:
```python
from aequitas.api.routers import conversations
app.include_router(conversations.router, prefix="/api")
```

- [ ] **Step 6: Commit**

```bash
git add src/aequitas/api/auth.py src/aequitas/api/config.py src/aequitas/api/routers/chat.py src/aequitas/api/routers/conversations.py src/aequitas/api/app.py
git commit -m "feat(auth): add backend JWT validation + conversations CRUD router"
```

### Task 4.4: Supabase migrations — tables + RLS

**Files:**
- Create: `supabase/config.toml`
- Create: `supabase/migrations/001_initial.sql`

- [ ] **Step 1: Create Supabase config**

```toml
# supabase/config.toml
[project]
id = "aequitas"
```

- [ ] **Step 2: Create initial migration**

```sql
-- supabase/migrations/001_initial.sql

-- Profiles (auto-created on signup)
CREATE TABLE IF NOT EXISTS public.profiles (
    id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    display_name TEXT,
    bio TEXT,
    policy_interests TEXT[] DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);
ALTER TABLE public.profiles ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Users can view own profile" ON public.profiles FOR SELECT USING (auth.uid() = id);
CREATE POLICY "Users can update own profile" ON public.profiles FOR UPDATE USING (auth.uid() = id);

-- Auto-create profile on signup
CREATE OR REPLACE FUNCTION public.handle_new_user()
RETURNS TRIGGER AS $$
BEGIN
    INSERT INTO public.profiles (id, display_name)
    VALUES (NEW.id, COALESCE(NEW.raw_user_meta_data->>'full_name', NEW.email));
    RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;
CREATE TRIGGER on_auth_user_created
    AFTER INSERT ON auth.users
    FOR EACH ROW EXECUTE FUNCTION public.handle_new_user();

-- Conversations
CREATE TABLE IF NOT EXISTS public.conversations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE NOT NULL,
    title TEXT,
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);
ALTER TABLE public.conversations ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Users can CRUD own conversations" ON public.conversations FOR ALL USING (auth.uid() = user_id);

-- Messages
CREATE TABLE IF NOT EXISTS public.messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    conversation_id UUID REFERENCES public.conversations(id) ON DELETE CASCADE NOT NULL,
    user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE NOT NULL,
    role TEXT NOT NULL CHECK (role IN ('user', 'assistant')),
    content TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT now()
);
ALTER TABLE public.messages ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Users can CRUD own messages" ON public.messages FOR ALL USING (auth.uid() = user_id);

-- Saved analyses (bookmarked narratives/chat responses)
CREATE TABLE IF NOT EXISTS public.saved_analyses (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE NOT NULL,
    title TEXT NOT NULL,
    content TEXT NOT NULL,
    section_id TEXT,
    dimension TEXT,
    tags TEXT[] DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT now()
);
ALTER TABLE public.saved_analyses ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Users can CRUD own saved analyses" ON public.saved_analyses FOR ALL USING (auth.uid() = user_id);

-- Policy notes (investment journal equivalent)
CREATE TABLE IF NOT EXISTS public.policy_notes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE NOT NULL,
    dimension TEXT NOT NULL,
    region TEXT DEFAULT 'all',
    stance TEXT CHECK (stance IN ('priority', 'monitor', 'adequate')),
    thesis TEXT NOT NULL,
    critique TEXT,
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);
ALTER TABLE public.policy_notes ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Users can CRUD own policy notes" ON public.policy_notes FOR ALL USING (auth.uid() = user_id);

-- Saved regions (watchlist equivalent)
CREATE TABLE IF NOT EXISTS public.saved_regions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE NOT NULL,
    region_code TEXT NOT NULL,
    region_name TEXT NOT NULL,
    notes TEXT,
    created_at TIMESTAMPTZ DEFAULT now()
);
ALTER TABLE public.saved_regions ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Users can CRUD own saved regions" ON public.saved_regions FOR ALL USING (auth.uid() = user_id);
```

- [ ] **Step 3: Commit**

```bash
git add supabase/
git commit -m "feat(db): add Supabase migrations — profiles, conversations, saved analyses, policy notes"
```

### Task 4.5: Frontend — UserMenu, Profile, ConversationSidebar

**Files:**
- Create: `frontend/src/components/layout/UserMenu.tsx`
- Create: `frontend/src/pages/ProfilePage.tsx`
- Create: `frontend/src/components/chat/ChatSidebar.tsx`
- Create: `frontend/src/lib/db.ts`
- Modify: `frontend/src/components/layout/Header.tsx`
- Modify: `frontend/src/components/chat/ChatDrawer.tsx`

- [ ] **Step 1: Create db.ts helper**

Supabase CRUD helpers for conversations, messages, saved analyses, policy notes. Pattern from bharat-alpha's `src/lib/db.ts`.

- [ ] **Step 2: Create UserMenu (transplant + rebrand)**

Avatar + dropdown with: Profile, Saved, Policy Notes, Sign Out. Pattern from bharat-alpha's `UserMenu.tsx`.

- [ ] **Step 3: Create ProfilePage**

Display name, bio, policy interests (8 dimension buttons). Pattern from bharat-alpha's `Profile.tsx`.

- [ ] **Step 4: Create ChatSidebar**

Conversation list with delete, resume, "new chat" button. Pattern from bharat-alpha's `ConversationSidebar.tsx`.

- [ ] **Step 5: Wire into Header and ChatDrawer**

Add UserMenu to Header. Add ChatSidebar toggle to ChatDrawer.

- [ ] **Step 6: Commit**

```bash
git add frontend/src/components/layout/UserMenu.tsx frontend/src/pages/ProfilePage.tsx frontend/src/components/chat/ChatSidebar.tsx frontend/src/lib/db.ts frontend/src/components/layout/Header.tsx frontend/src/components/chat/ChatDrawer.tsx
git commit -m "feat(auth): add user menu, profile page, conversation sidebar"
```

### Task 4.6: Add vitest tests for auth components

**Files:**
- Create: `frontend/src/components/auth/__tests__/ProtectedRoute.test.tsx`
- Create: `frontend/src/contexts/__tests__/AuthContext.test.tsx`

- [ ] **Step 1: Write ProtectedRoute test**

```typescript
import { render, screen } from "@testing-library/react"
import { describe, it, expect, vi } from "vitest"
import { MemoryRouter } from "react-router-dom"

// Mock useAuth to test both states
vi.mock("@/contexts/AuthContext", () => ({
  useAuth: vi.fn(),
}))

import { useAuth } from "@/contexts/AuthContext"
import { ProtectedRoute } from "../ProtectedRoute"

describe("ProtectedRoute", () => {
  it("shows loading spinner while auth is loading", () => {
    ;(useAuth as ReturnType<typeof vi.fn>).mockReturnValue({ user: null, loading: true })
    const { container } = render(
      <MemoryRouter><ProtectedRoute><div>Protected</div></ProtectedRoute></MemoryRouter>
    )
    expect(container.querySelector(".animate-pulse")).toBeTruthy()
  })

  it("renders children when authenticated", () => {
    ;(useAuth as ReturnType<typeof vi.fn>).mockReturnValue({ user: { id: "1" }, loading: false })
    render(
      <MemoryRouter><ProtectedRoute><div>Protected Content</div></ProtectedRoute></MemoryRouter>
    )
    expect(screen.getByText("Protected Content")).toBeTruthy()
  })
})
```

- [ ] **Step 2: Run vitest**

Run: `cd frontend && npx vitest run src/components/auth/__tests__/ --reporter verbose`

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/auth/__tests__/ frontend/src/contexts/__tests__/
git commit -m "test(auth): add vitest tests for ProtectedRoute and AuthContext"
```

### Task 4.7: Saved Analyses + Policy Notes + Saved Regions pages

**Files:**
- Create: `frontend/src/components/saved/SavedAnalyses.tsx`
- Create: `frontend/src/components/saved/PolicyNotes.tsx`
- Create: `frontend/src/components/saved/SavedRegions.tsx`
- Modify: `frontend/src/App.tsx`

- [ ] **Step 1: Create SavedAnalyses** — list bookmarked narratives/chat responses, expandable, deletable. Pattern from bharat-alpha's `/saved` page.

- [ ] **Step 2: Create PolicyNotes** — journal-style policy recommendations per dimension. Stance: priority/monitor/adequate. AI critique via chat endpoint. Pattern from bharat-alpha's `/journal`.

- [ ] **Step 3: Create SavedRegions** — tracked regions with key metrics. Pattern from bharat-alpha's `/watchlist`. Instead of stock prices, show region's Gini, SQI, evening isolation %.

- [ ] **Step 4: Add routes to App.tsx**

```typescript
<Route path="/saved" element={<ProtectedRoute><SavedAnalyses /></ProtectedRoute>} />
<Route path="/notes" element={<ProtectedRoute><PolicyNotes /></ProtectedRoute>} />
<Route path="/regions" element={<ProtectedRoute><SavedRegions /></ProtectedRoute>} />
<Route path="/profile" element={<ProtectedRoute><ProfilePage /></ProtectedRoute>} />
```

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/saved/ frontend/src/App.tsx
git commit -m "feat(user): add saved analyses, policy notes, and saved regions pages"
```

---

## Sprint 5: Landing & Polish

**Goal:** Landing page, about/disclaimer/contact, dark theme, status bar, metrics ticker, suggested questions, animations.

### Task 5.1: Landing page

**Files:**
- Create: `frontend/src/pages/LandingPage.tsx`
- Modify: `frontend/src/App.tsx`

- [ ] **Step 1: Create LandingPage**

Structure (adapted from bharat-alpha's landing page):
1. **Status bar** — "Aequitas Intelligence — Systems Online"
2. **Hero** — "Evidence-Based Policy Intelligence for UK Bus Transport"
3. **Metrics strip** — 4 headline stats: Gini 0.574, Palma 5.70, Evening Isolated 15.4%, Sunday Deserts 20.0%
4. **8 dimension cards** — one per policy dimension with icon + one-liner
5. **CTA** — "Start Exploring" button → /auth or / (if logged in)
6. **Footer** — About, Disclaimer, Contact links

- [ ] **Step 2: Add route**

```typescript
<Route path="/landing" element={<LandingPage />} />
```

- [ ] **Step 3: Commit**

```bash
git add frontend/src/pages/LandingPage.tsx frontend/src/App.tsx
git commit -m "feat(landing): add hero page with dimension cards + headline metrics"
```

### Task 5.2: About, Disclaimer, Contact pages

**Files:**
- Create: `frontend/src/pages/AboutPage.tsx`
- Create: `frontend/src/pages/DisclaimerPage.tsx`
- Create: `frontend/src/pages/ContactPage.tsx`

- [ ] **Step 1: Create AboutPage** — 8 dimensions explained, data sources (NaPTAN, BODS, ONS, IMD, NOMIS, DfT TAG, DESNZ), methodology summary.

- [ ] **Step 2: Create DisclaimerPage** — "Policy analysis tool — not official DfT guidance", data source caveats, AI-generated content warning, no liability.

- [ ] **Step 3: Create ContactPage** — Contact form + direct links. Pattern from bharat-alpha.

- [ ] **Step 4: Add routes and commit**

```bash
git add frontend/src/pages/AboutPage.tsx frontend/src/pages/DisclaimerPage.tsx frontend/src/pages/ContactPage.tsx frontend/src/App.tsx
git commit -m "feat(pages): add about, disclaimer, and contact pages"
```

### Task 5.3: Status bar + metrics ticker + footer

**Files:**
- Create: `frontend/src/components/layout/StatusBar.tsx`
- Create: `frontend/src/components/layout/MetricsTicker.tsx`
- Create: `frontend/src/components/layout/Footer.tsx`
- Modify: `frontend/src/components/layout/AppShell.tsx`

- [ ] **Step 1: Create StatusBar** — top bar with "Aequitas Intelligence" + current date + pulsing green dot. Style from bharat-alpha.

- [ ] **Step 2: Create headline metrics API endpoint first**

Move this from Sprint 6 — MetricsTicker needs a data source. Create `src/aequitas/api/routers/metrics.py`:

```python
router = APIRouter(tags=["metrics"])

@router.get("/metrics/ticker")
async def get_ticker_metrics(db=Depends(get_db)):
    """Return headline stats from pre-computed section_results."""
    # Query warehouse for key stats — NOT hardcoded values
    gini = db.execute("SELECT json_extract(stats, '$.gini') FROM section_results WHERE section_id='f1_gini' AND region='all' AND urban_rural='all'").fetchone()
    # ... similar for palma, evening_isolated, sunday_deserts, sqi
```

Register in `app.py`: `app.include_router(metrics.router, prefix="/api")`

- [ ] **Step 3: Create MetricsTicker** — scrolling headline stats fetched from `/api/metrics/ticker`. Show 4-6 key metrics: Gini, Palma, Concentration Index, Evening Isolated %, Sunday Desert %, Mean SQI.

- [ ] **Step 3: Create Footer** — navigation links (About, Disclaimer, Contact) + copyright.

- [ ] **Step 4: Wire into AppShell**

```typescript
<StatusBar />
<Header />
<MetricsTicker />
<Outlet />
<Footer />
```

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/layout/StatusBar.tsx frontend/src/components/layout/MetricsTicker.tsx frontend/src/components/layout/Footer.tsx frontend/src/components/layout/AppShell.tsx
git commit -m "feat(layout): add status bar, metrics ticker, and footer"
```

### Task 5.4: Chat enhancements — suggested questions, quick actions, auto-resize

**Files:**
- Create: `frontend/src/components/chat/SuggestedQuestions.tsx`
- Create: `frontend/src/components/chat/QuickActions.tsx`
- Modify: `frontend/src/components/chat/ChatDrawer.tsx`

- [ ] **Step 1: Create SuggestedQuestions** — dimension-aware question grid. Default questions + dimension-specific ones based on current page context:

```typescript
const SUGGESTIONS: Record<string, string[]> = {
  default: [
    "What are the most transport-deprived areas in England?",
    "How does bus service inequality compare to income inequality?",
    "Which regions should be prioritised for franchising under the Bus Services Act?",
    "What would happen if evening bus services were extended to 11pm?",
  ],
  equity: [
    "Explain the Gini coefficient for bus services",
    "Which regions have the highest Palma ratio?",
    "How does the Concentration Index show pro-rich bias?",
  ],
  // ... per dimension
}
```

- [ ] **Step 2: Create QuickActions** — 3 buttons: "Explore Inequity", "Compare Regions", "Ask About Policy". Each submits a pre-written prompt.

- [ ] **Step 3: Auto-resize chat textarea**

In ChatDrawer, replace fixed textarea with auto-sizing pattern:

```typescript
const textareaRef = useRef<HTMLTextAreaElement>(null)
const handleInput = () => {
  const el = textareaRef.current
  if (el) {
    el.style.height = "auto"
    el.style.height = Math.min(el.scrollHeight, 120) + "px"
  }
}
```

- [ ] **Step 4: Show SuggestedQuestions + QuickActions when chat is empty**

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/chat/SuggestedQuestions.tsx frontend/src/components/chat/QuickActions.tsx frontend/src/components/chat/ChatDrawer.tsx
git commit -m "feat(chat): add suggested questions, quick actions, and auto-resize input"
```

### Task 5.5: Dark theme + animations + empty states + logo

**Files:**
- Modify: `frontend/src/index.css`
- Create: `frontend/src/components/shared/EmptyState.tsx`
- Modify: `frontend/src/components/layout/Header.tsx`

- [ ] **Step 1: Add dark theme CSS variables**

Adapt bharat-alpha's Bloomberg-dark palette but with indigo primary:

```css
:root {
  --background: 228 15% 4%;        /* Ultra-dark */
  --card: 228 15% 7%;              /* Card surface */
  --muted: 228 15% 10%;            /* Muted background */
  --primary: 239 84% 67%;          /* Indigo-500 */
  --primary-foreground: 0 0% 100%;
  --foreground: 0 0% 95%;
  --border: 228 15% 15%;
  /* ... */
}
```

- [ ] **Step 2: Add animations**

```css
@keyframes fade-in { from { opacity: 0; transform: translateY(6px); } to { opacity: 1; transform: translateY(0); } }
@keyframes slide-in-right { from { opacity: 0; transform: translateX(-20px); } to { opacity: 1; transform: translateX(0); } }
@keyframes pulse-glow { 0%, 100% { opacity: 0.4; } 50% { opacity: 1; } }
.animate-fade-in { animation: fade-in 0.3s ease-out; }
.animate-slide-in { animation: slide-in-right 0.3s ease-out; }
.animate-pulse-glow { animation: pulse-glow 2s ease-in-out infinite; }
```

- [ ] **Step 3: Create consistent EmptyState component**

```typescript
// frontend/src/components/shared/EmptyState.tsx
interface Props {
  icon: React.ReactNode
  title: string
  description?: string
}
export function EmptyState({ icon, title, description }: Props) {
  return (
    <div className="flex flex-col items-center justify-center py-16 text-center">
      <div className="text-muted-foreground/20 mb-4">{icon}</div>
      <p className="text-xs uppercase tracking-widest text-muted-foreground">{title}</p>
      {description && <p className="text-xs text-muted-foreground/60 mt-2 max-w-xs">{description}</p>}
    </div>
  )
}
```

- [ ] **Step 4: Add logo to Header**

After generating the logo via Gemini, save as `frontend/public/logo.svg` and add to Header:

```typescript
<img src="/logo.svg" alt="Aequitas" className="w-7 h-7" />
<span className="font-bold text-sm tracking-tight">AEQUITAS</span>
```

- [ ] **Step 5: Commit**

```bash
git add frontend/src/index.css frontend/src/components/shared/EmptyState.tsx frontend/src/components/layout/Header.tsx frontend/public/logo.svg
git commit -m "feat(ui): add dark theme, animations, empty states, and logo"
```

---

## Sprint 6: Power Features

**Goal:** PDF export, compare mode, LSOA deep-dive, scenario builder, data provenance.

### Task 6.1: PDF export endpoint

**Files:**
- Create: `src/aequitas/api/routers/export.py`
- Modify: `src/aequitas/api/app.py`

- [ ] **Step 1: Install ReportLab**

```bash
.venv/bin/pip install reportlab
```

- [ ] **Step 2: Create export router**

```python
# src/aequitas/api/routers/export.py
"""PDF export of dimension reports."""
from fastapi import APIRouter, Query
from fastapi.responses import StreamingResponse
from io import BytesIO
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet

# NOTE: No prefix here — app.py adds /api when registering routers
router = APIRouter(tags=["export"])

@router.get("/{dimension}")
async def export_dimension_pdf(
    dimension: str,
    region: str = Query("all"),
    urban_rural: str = Query("all"),
):
    """Generate PDF report for a dimension + filter combination."""
    # 1. Query section_results for this dimension
    # 2. Build PDF with ReportLab: title, each section's stats + narrative
    # 3. Return as StreamingResponse with Content-Disposition
    ...
```

- [ ] **Step 3: Register router in app.py**

- [ ] **Step 4: Commit**

```bash
git add src/aequitas/api/routers/export.py src/aequitas/api/app.py
git commit -m "feat(export): add PDF generation endpoint for dimension reports"
```

### Task 6.2: Frontend PDF download button

**Files:**
- Modify: `frontend/src/components/dimension/DimensionPage.tsx`

- [ ] **Step 1: Add "Export PDF" button to DimensionPage header**

```typescript
<a
  href={`/api/export/${dimension}?region=${region}&urban_rural=${urbanRural}`}
  download
  className="flex items-center gap-2 px-3 py-1.5 text-xs border border-border rounded hover:bg-muted transition-colors"
>
  <Download className="w-3.5 h-3.5" />
  Export PDF
</a>
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/components/dimension/DimensionPage.tsx
git commit -m "feat(export): add PDF download button to dimension pages"
```

### Task 6.3: Compare mode — side-by-side regions

**Files:**
- Create: `frontend/src/pages/ComparePage.tsx`
- Modify: `frontend/src/App.tsx`

- [ ] **Step 1: Create ComparePage**

Two region pickers side by side. For each region, fetch `/api/sections?dimension=X&region=Y` and display stats + charts in parallel columns. Highlight differences.

- [ ] **Step 2: Add route**

```typescript
<Route path="/compare" element={<ProtectedRoute><ComparePage /></ProtectedRoute>} />
```

- [ ] **Step 3: Add "Compare" link to TabBar or Header**

- [ ] **Step 4: Commit**

```bash
git add frontend/src/pages/ComparePage.tsx frontend/src/App.tsx
git commit -m "feat(compare): add side-by-side region comparison page"
```

### Task 6.4: Data provenance panel

**Files:**
- Create: `frontend/src/components/dimension/ProvenancePanel.tsx`
- Modify: `frontend/src/components/dimension/SectionCard.tsx`

- [ ] **Step 1: Create ProvenancePanel**

Slide-out panel showing: metric formula, input values, source files, notebook cell reference. Fetches from `/api/provenance/{metric_id}`.

- [ ] **Step 2: Add "Show source" button to SectionCard**

Next to each key stat, add a small info icon that opens the ProvenancePanel.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/dimension/ProvenancePanel.tsx frontend/src/components/dimension/SectionCard.tsx
git commit -m "feat(provenance): add click-to-see-formula panel on section stats"
```

### Task 6.5: Scenario builder with interactive sliders

**Files:**
- Create: `frontend/src/components/dimension/ScenarioBuilder.tsx`
- Modify: `frontend/src/components/dimension/DimensionPage.tsx`

- [ ] **Step 1: Create ScenarioBuilder**

Interactive UI for the 4 policy scenarios (ps1-ps4). Sliders for:
- Frequency increase: 0-50% (step 5%)
- Last bus extension: 19:00-23:00 (step 30min)
- DRT coverage: 0-100% of rural LSOAs
- Franchise scope: None / Partial / Full

Each slider change recalculates estimated impact using pre-computed coefficients from the scenario tables.

- [ ] **Step 2: Show on /scenarios dimension page**

Render ScenarioBuilder above the standard section cards when dimension is "scenarios".

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/dimension/ScenarioBuilder.tsx frontend/src/components/dimension/DimensionPage.tsx
git commit -m "feat(scenarios): add interactive slider-based scenario builder"
```

### Task 6.6: ~~Headline metrics endpoint~~ MOVED TO SPRINT 5, Task 5.3 Step 2

The metrics endpoint was moved to Sprint 5 to avoid the MetricsTicker having no data source. See Sprint 5, Task 5.3.

---

## Sprint Dependencies

```
Sprint 1 (Data Foundation) ← START HERE
    ↓
Sprint 2 (Narratives)  ──┐
Sprint 3 (Charts)       ──┤  (can run in parallel after Sprint 1)
                          ↓
Sprint 4 (Auth & Users)
    ↓
Sprint 5 (Landing & Polish)
    ↓
Sprint 6 (Power Features)
```

## Verification Checklist

After all 6 sprints, verify:

- [ ] `/api/sections?dimension=equity&region=E12000007&urban_rural=urban` returns data (30 combos work)
- [ ] Chat responds with evidence-grounded answers (FAISS loaded)
- [ ] All 10 chart types render with tooltips on hover
- [ ] Narratives average 400+ chars, ≤20% suppressed
- [ ] Google OAuth sign-in works end-to-end
- [ ] Conversation history persists across sessions
- [ ] Landing page renders with headline stats
- [ ] PDF export downloads successfully
- [ ] Dark theme applied consistently
- [ ] All tests pass: `pytest tests/ -v` and `cd frontend && npm test`
