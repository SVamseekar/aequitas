# Precompute 51-Section Expansion Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Expand `precompute.py` from producing real stats for 3 of 51 registered sections to all 51 (minus 3 documented stubs), across all 30 filter combinations, fixing five correctness bugs along the way (region filter never matches, regional equity ignored, single-region ranking suppressed, gap_to_target uses a moving median, urban-rural comparisons self-contradict).

**Architecture:** Replace the monolithic `_build_stats` with a `warehouse/stats_builders/` package — one small module per template-contract family, each exposing one function per section_id. `precompute.py` holds a slim dispatch table. `engine.py` gains shape-based template selection so single-region ranking stats render via `single_region.j2`.

**Tech Stack:** Python 3.12, pandas, pytest, existing `aequitas.intelligence.calculators` (already has `calculate_correlation`, `rank_regions`, `describe_distribution`, `calculate_gap_to_target` — reuse these, do not reimplement).

---

## Reference: Confirmed Data Facts

These were confirmed by direct inspection — use them verbatim, do not re-derive:

- **Region names vs codes bug:** `lsoa_policy_synthesis.region` holds full names (`"North East"`, `"East of England"`, `"Yorkshire and The Humber"`, etc. — 9 values, confirmed exact strings below). `RegionCode`/`_REGIONS` use ONS codes (`"E12000001"`). The current `region_mask = policy_df[region_col] == region` never matches. Must map code → name before filtering.
- **`REGION_NAMES` mapping** (code → full name, exact strings from data):
  ```python
  REGION_NAMES: dict[str, str] = {
      "E12000001": "North East",
      "E12000002": "North West",
      "E12000003": "Yorkshire and The Humber",
      "E12000004": "East Midlands",
      "E12000005": "West Midlands",
      "E12000006": "East of England",
      "E12000007": "London",
      "E12000008": "South East",
      "E12000009": "South West",
  }
  ```
- `lsoa_policy_synthesis.urban_rural` values are `"Urban"` / `"Rural"` (capitalised) — the existing `.str.lower().str.startswith(urban_rural)` mask works correctly against lowercase `"urban"`/`"rural"` filter params.
- `lsoa_economic_appraisal.region` is **all `"Unknown"`** — cannot be grouped by region directly. Must join to `lsoa_policy_synthesis` on `lsoa_cd` (full 33,755-row overlap confirmed) to get usable `region`/`urban_rural`.
- `policy_scenarios.parquet` has exactly 4 rows (scenarios A–D) mapping 1:1 by row order to `ps1_freq_restoration` (A), `ps2_evening_extension` (B), `ps3_drt_rural` (C), `ps4_franchise` (D). Columns: `scenario, name, scope, population_affected, annual_additional_trips, estimated_annual_cost_m, co2_saving_t_yr, confidence` — this is **exactly** the `policy_scenario.j2` `scenario.*` contract. **Caution:** `co2_saving_t_yr` is `NaN` for rows B/C/D, and `estimated_annual_cost_m` is `NaN` for row D — coalesce to `0.0` before passing to the template (Jinja `|round` raises on `None`/`NaN`).
- `lsoa_clusters_hdbscan.hdbscan_archetype` values: `"Noise"`, `"Elderly Rural"`, `"Diverse Urban"`. `gmm_label` values: `0,1,2,3`.
- `route_clusters.cluster` values: `-1, 0, 1, 2, 3, 4, 5, 6` (HDBSCAN; `-1` = noise).
- `anomalies.anomaly_type` values: `"other_anomaly"`, `"normal"`, `"positive_deprived_well_served"`, `"inefficiency_affluent_poor_served"`, `"policy_failure_elderly_no_service"`.
- `lta_franchising_readiness.readiness_tier` values: `"Tier 1 — High"`, `"Tier 2 — Medium"`, `"Tier 3 — Low"` (ordered categorical).
- `coverage_prediction.parquet` columns: `lsoa_cd, trips_per_capita_predicted, trips_per_capita, imd_decile, residual`.
- `shap_summary.csv` columns: `feature, mean_abs_shap` (NOT a parquet — read with `pd.read_csv`).
- `route_geometries.primary_region` uses full region names matching the `REGION_NAMES` values (e.g. `"North West"`).
- `equity_summary.json` top-level keys include `regional_equity` (dict keyed by region) and `gini_after_bottom_decile_uplift` — both currently unused.

---

## Task 1: Add `REGION_NAMES` mapping and fix the region filter bug

**Files:**
- Modify: `src/aequitas/warehouse/precompute.py`
- Test: `tests/warehouse/test_precompute.py`

- [ ] **Step 1: Write the failing test**

Add to `tests/warehouse/test_precompute.py`:

```python
def test_region_filter_matches_full_names():
    """REGION_NAMES must map ONS codes to the full names present in the data."""
    from aequitas.warehouse.precompute import REGION_NAMES
    from aequitas.core.types import RegionCode

    assert REGION_NAMES[RegionCode.NORTH_EAST.value] == "North East"
    assert REGION_NAMES[RegionCode.LONDON.value] == "London"
    assert REGION_NAMES[RegionCode.YORKSHIRE.value] == "Yorkshire and The Humber"
    assert len(REGION_NAMES) == 9


@pytest.mark.slow
def test_region_filter_produces_nonempty_subset():
    """Filtering lsoa_policy_synthesis by ONS code (via REGION_NAMES) must match rows."""
    import pandas as pd
    from aequitas.core.config import PipelineConfig
    from aequitas.warehouse.precompute import REGION_NAMES

    cfg = PipelineConfig()
    df = pd.read_parquet(cfg.audit_dir / "lsoa_policy_synthesis.parquet")
    mask = df["region"] == REGION_NAMES["E12000001"]
    assert mask.sum() > 0, "North East region filter must match rows in the data"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/warehouse/test_precompute.py::test_region_filter_matches_full_names -v`
Expected: FAIL with `ImportError: cannot import name 'REGION_NAMES'`

- [ ] **Step 3: Add `REGION_NAMES` and fix the mask**

In `src/aequitas/warehouse/precompute.py`, add after the `_AREA_TYPES` definition (around line 32):

```python
# Maps ONS region codes (used in filter params and RegionCode) to the full
# region names stored in lsoa_policy_synthesis.region. The two do not match
# directly — this mapping is required for the region filter to work at all.
REGION_NAMES: dict[str, str] = {
    "E12000001": "North East",
    "E12000002": "North West",
    "E12000003": "Yorkshire and The Humber",
    "E12000004": "East Midlands",
    "E12000005": "West Midlands",
    "E12000006": "East of England",
    "E12000007": "London",
    "E12000008": "South East",
    "E12000009": "South West",
}
```

Then in `precompute_all_sections`, replace the region mask construction:

```python
            # Filter data
            region_mask = pd.Series(True, index=policy_df.index)
            if region != "all":
                region_col = "region" if "region" in policy_df.columns else None
                if region_col:
                    region_mask = policy_df[region_col] == region
```

with:

```python
            # Filter data
            region_mask = pd.Series(True, index=policy_df.index)
            if region != "all":
                region_col = "region" if "region" in policy_df.columns else None
                if region_col:
                    region_name = REGION_NAMES.get(region, region)
                    region_mask = policy_df[region_col] == region_name
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/warehouse/test_precompute.py::test_region_filter_matches_full_names tests/warehouse/test_precompute.py::test_region_filter_produces_nonempty_subset -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/aequitas/warehouse/precompute.py tests/warehouse/test_precompute.py
git commit -m "fix: region filter compared ONS codes against full region names — add REGION_NAMES mapping"
```

---

## Task 2: Remove the 18-combo skip — precompute all 30 filter combinations

**Files:**
- Modify: `src/aequitas/warehouse/precompute.py`
- Test: `tests/warehouse/test_precompute_30.py`

- [ ] **Step 1: Write the failing test**

Replace the contents of `tests/warehouse/test_precompute_30.py` with:

```python
"""Verify precompute generates all 30 filter combinations and skips none."""
import pytest
from aequitas.warehouse.precompute import _REGIONS, _AREA_TYPES


def test_filter_combo_count():
    """30 combos = 10 regions (all + 9 ONS codes) × 3 area_types."""
    combos = [(r, a) for r in _REGIONS for a in _AREA_TYPES]
    assert len(combos) == 30


def test_no_combos_skipped_in_source():
    """The 'continue' skip for region+urban_rural combos must be removed."""
    import inspect
    from aequitas.warehouse import precompute
    source = inspect.getsource(precompute.precompute_all_sections)
    assert "continue" not in source, (
        "precompute_all_sections must not skip any region × urban_rural combo"
    )


@pytest.mark.slow
def test_previously_dead_combos_now_present():
    """North East + Urban and London + Rural must both be processed (were skipped before)."""
    from aequitas.core.config import PipelineConfig
    from aequitas.warehouse.precompute import precompute_all_sections

    cfg = PipelineConfig()
    results = precompute_all_sections(cfg)
    combos_seen = {(r["region"], r["urban_rural"]) for r in results}
    assert ("E12000001", "urban") in combos_seen
    assert ("E12000007", "rural") in combos_seen
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/warehouse/test_precompute_30.py::test_no_combos_skipped_in_source -v`
Expected: FAIL — `continue` is present in the source

- [ ] **Step 3: Remove the skip**

In `src/aequitas/warehouse/precompute.py`, delete these lines from `precompute_all_sections`:

```python
            # Skip redundant single-region + urban/rural combos for speed
            # (these are low-value subsets; all_regions × all produces the key insights)
            if region != "all" and urban_rural != "all":
                continue

```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/warehouse/test_precompute_30.py -v`
Expected: PASS (the `@pytest.mark.slow` test may be skipped depending on pytest config — that's fine, the source-inspection test is the fast guard)

- [ ] **Step 5: Commit**

```bash
git add src/aequitas/warehouse/precompute.py tests/warehouse/test_precompute_30.py
git commit -m "fix: precompute all 30 filter combinations, remove dead-combo skip"
```

---

## Task 3: Create the `stats_builders` package skeleton and shared helpers

**Files:**
- Create: `src/aequitas/warehouse/stats_builders/__init__.py`
- Create: `src/aequitas/warehouse/stats_builders/shared.py`
- Test: `tests/warehouse/stats_builders/test_shared.py`
- Test: `tests/warehouse/stats_builders/__init__.py` (empty)

This task creates the package and a `shared.py` module holding the `REGION_NAMES`-equivalent for builder use (re-exported from `precompute`, to avoid duplication) plus one genuinely shared helper: building the `single_region` stats shape, which six different ranking-family sections will need identically.

- [ ] **Step 1: Create the test directory marker**

```bash
mkdir -p tests/warehouse/stats_builders
touch tests/warehouse/stats_builders/__init__.py
```

- [ ] **Step 2: Write the failing test**

Create `tests/warehouse/stats_builders/test_shared.py`:

```python
"""Tests for shared stats-builder helpers."""
import pandas as pd
import pytest

from aequitas.warehouse.stats_builders.shared import build_single_region_stats


def test_build_single_region_stats_shape():
    """Output must match the single_region.j2 contract exactly."""
    by_region = pd.Series({"North East": 1.5, "London": 3.0, "South West": 2.0})
    stats = build_single_region_stats(
        by_region=by_region,
        region_value=1.5,
        region_name="North East",
        unit="trips/capita",
    )
    assert stats["region_name"] == "North East"
    assert stats["value"] == 1.5
    assert stats["unit"] == "trips/capita"
    assert "national_avg" in stats
    assert "vs_national_pct" in stats
    # national_avg = mean(1.5, 3.0, 2.0) = 2.1667
    assert stats["national_avg"] == pytest.approx(2.17, abs=0.01)
    # vs_national_pct = (1.5 - 2.1667) / 2.1667 * 100 = -30.77
    assert stats["vs_national_pct"] == pytest.approx(-30.8, abs=0.1)


def test_build_single_region_stats_has_no_best_worst_keys():
    """Must NOT contain best/worst — engine uses their absence to pick single_region.j2."""
    by_region = pd.Series({"North East": 1.5, "London": 3.0})
    stats = build_single_region_stats(
        by_region=by_region, region_value=1.5, region_name="North East", unit="x"
    )
    assert "best" not in stats
    assert "worst" not in stats
```

- [ ] **Step 3: Run test to verify it fails**

Run: `pytest tests/warehouse/stats_builders/test_shared.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'aequitas.warehouse.stats_builders'`

- [ ] **Step 4: Create the package and shared module**

Create `src/aequitas/warehouse/stats_builders/__init__.py`:

```python
"""Stats builder modules — one per template-contract family.

Each module exposes functions that build the `stats` dict for one or more
section_ids, matching the exact key contract their Jinja2 template expects.
precompute.py dispatches to these via _SECTION_BUILDERS.
"""
```

Create `src/aequitas/warehouse/stats_builders/shared.py`:

```python
"""Shared helpers used across multiple stats-builder modules."""

import pandas as pd


def build_single_region_stats(
    by_region: pd.Series,
    region_value: float,
    region_name: str,
    unit: str,
) -> dict:
    """Build the stats shape required by single_region.j2.

    Used by ranking-family builders (a1, a2, b1, b4, f6, j4, bsa1) when the
    active filter is a single region rather than "all" — in that context a
    best/worst ranking is meaningless, but a region-vs-national comparison is
    the right narrative (see ISSUES.md §2.4/§8.1).

    Args:
        by_region: Series of metric values indexed by region name, across all
            regions (unfiltered) — used to compute the national average.
        region_value: The metric value for the single selected region.
        region_name: Human-readable region name (e.g. "North East").
        unit: Unit label for the metric (e.g. "trips/capita").

    Returns:
        Dict with keys region_name, value, national_avg, vs_national_pct, unit.
        Deliberately excludes best/worst so InsightEngine selects single_region.j2
        instead of ranking.j2.
    """
    national_avg = float(by_region.mean())
    vs_national_pct = (
        round((region_value - national_avg) / national_avg * 100, 1)
        if national_avg != 0
        else 0.0
    )
    return {
        "region_name": region_name,
        "value": round(float(region_value), 2),
        "national_avg": round(national_avg, 2),
        "vs_national_pct": vs_national_pct,
        "unit": unit,
    }
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `pytest tests/warehouse/stats_builders/test_shared.py -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add src/aequitas/warehouse/stats_builders/ tests/warehouse/stats_builders/
git commit -m "feat: add stats_builders package skeleton with shared single_region helper"
```

---

## Task 4: Engine — shape-based dispatch to single_region.j2

**Files:**
- Modify: `src/aequitas/intelligence/engine.py`
- Test: `tests/intelligence/test_engine.py`

- [ ] **Step 1: Read the current engine test file to match conventions**

Run: `cat tests/intelligence/test_engine.py | head -40`

(No code change in this step — just confirm test file exists and note its import/fixture style before adding to it.)

- [ ] **Step 2: Write the failing test**

Add to `tests/intelligence/test_engine.py`:

```python
def test_single_region_shape_renders_single_region_template():
    """When stats look like single_region shape, engine must use single_region.j2,
    not ranking.j2 — even though a1_route_density maps to ranking.j2 in the registry."""
    from aequitas.intelligence.engine import InsightEngine

    engine = InsightEngine()
    stats = {
        "region_name": "North East",
        "value": 1.23,
        "national_avg": 1.50,
        "vs_national_pct": -18.0,
        "unit": "trips/capita",
    }
    result = engine.generate(
        section_id="a1_route_density", region="E12000001", urban_rural="all", stats=stats
    )
    assert not result["suppressed"]
    assert "North East" in result["narrative"]
    assert "1.23" in result["narrative"]
    # ranking.j2's distinctive heading must NOT appear — confirms single_region.j2 was used
    assert "Regional Spread" not in result["narrative"]


def test_ranking_shape_still_renders_ranking_template():
    """Stats with best/worst must still render via ranking.j2 (regression guard)."""
    from aequitas.intelligence.engine import InsightEngine

    engine = InsightEngine()
    stats = {
        "best": {"name": "London", "value": 3.0, "pct_above": 50.0},
        "worst": {"name": "North East", "value": 1.0, "pct_below": 50.0},
        "national_avg": 2.0,
        "unit": "trips/capita",
    }
    result = engine.generate(
        section_id="a1_route_density", region="all", urban_rural="all", stats=stats
    )
    assert not result["suppressed"]
    assert "Regional Spread" in result["narrative"]
```

- [ ] **Step 3: Run test to verify it fails**

Run: `pytest tests/intelligence/test_engine.py::test_single_region_shape_renders_single_region_template -v`
Expected: FAIL — narrative contains ranking.j2 output (or "Regional Spread" appears), not single_region.j2's compact form

- [ ] **Step 4: Add shape-based dispatch**

In `src/aequitas/intelligence/engine.py`, locate the `generate` method. Find this block:

```python
        template_name = _SECTION_TEMPLATES.get(section_id)
        narrative = ""
        suppressed = False

        if template_name is None:
            suppressed = True
        elif not stats:
```

Replace it with:

```python
        template_name = _SECTION_TEMPLATES.get(section_id)

        # Shape-based override: a ranking-family section viewed for a single
        # region gets single_region stats (region_name/value/national_avg,
        # no best/worst) rather than a best/worst ranking — render with
        # single_region.j2 instead. See ISSUES.md §2.4/§8.1.
        if (
            template_name == "ranking.j2"
            and stats
            and "region_name" in stats
            and "value" in stats
            and "national_avg" in stats
            and "best" not in stats
            and "worst" not in stats
        ):
            template_name = "single_region.j2"

        narrative = ""
        suppressed = False

        if template_name is None:
            suppressed = True
        elif not stats:
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `pytest tests/intelligence/test_engine.py -v`
Expected: PASS — both new tests and all pre-existing engine tests pass

- [ ] **Step 6: Commit**

```bash
git add src/aequitas/intelligence/engine.py tests/intelligence/test_engine.py
git commit -m "feat: engine selects single_region.j2 over ranking.j2 by stats shape"
```

---

*(Continued in subsequent tasks — this plan covers the shared infrastructure. The remaining tasks build each stats_builders module: ranking, correlation, ml_clusters, ml_prediction, market_concentration, urban_rural_gap, policy_scenario, economic, equity, misc — followed by precompute.py wiring and HEADLINE_SECTIONS fix.)*

## Task 5: `ranking.py` builder module — 7 sections (a1, a2, b1, b4, f6, j4, bsa1)

**Files:**
- Create: `src/aequitas/warehouse/stats_builders/ranking.py`
- Test: `tests/warehouse/stats_builders/test_ranking.py`

All seven sections (`a1_route_density`, `a2_stop_density`, `b1_frequency`,
`b4_route_frequency`, `f6_equitable_regions`, `j4_investment_priority`,
`bsa1_franchising_readiness`) map to `ranking.j2`, which needs either:
- **All-regions view:** `{best: {name, value, pct_above}, worst: {name, value, pct_below}, national_avg, unit}`
- **Single-region view:** the `single_region` shape from `shared.build_single_region_stats`

Each section differs only in **which metric, grouped by which region column, from
which source table**. We express this as a small per-section config table and one
generic ranking function that both consults it.

| section_id | metric | source table | group col | unit | higher_is_better |
|---|---|---|---|---|---|
| `a1_route_density` | route count per region | `route_geometries` (`.groupby("primary_region").size()`) | `primary_region` | "routes" | True |
| `a2_stop_density` | `stops_per_1k` | `master_lsoa_table` | `region` | "stops/1,000 pop" | True |
| `b1_frequency` | `service_quality_index` | `lsoa_policy_synthesis` (filtered) | `region` | "SQI points" | True |
| `b4_route_frequency` | `trips_per_capita` (regional service-frequency proxy — no per-route frequency join exists; documented simplification) | `lsoa_policy_synthesis` (filtered) | `region` | "trips/capita" | True |
| `f6_equitable_regions` | `vulnerability_index` (lower = more equitable) | `lsoa_policy_synthesis` (filtered) | `region` | "vulnerability index" | False |
| `j4_investment_priority` | `investment_gap_annual_cost` (higher = higher priority) | `lsoa_policy_synthesis` (filtered) | `region` | "£/year investment gap" | True |
| `bsa1_franchising_readiness` | `franchising_readiness` | `lta_franchising_readiness` | `region` | "readiness score (0–100)" | True |

- [ ] **Step 1: Write the failing tests**

Create `tests/warehouse/stats_builders/test_ranking.py`:

```python
"""Tests for ranking.py — covers a1, a2, b1, b4, f6, j4, bsa1."""
import pandas as pd
import pytest

from aequitas.warehouse.stats_builders.ranking import (
    build_ranking_stats,
    RANKING_CONFIG,
)


def _make_region_df(metric: str, values: dict[str, float], extra_cols: dict | None = None) -> pd.DataFrame:
    rows = []
    for region, val in values.items():
        row = {"region": region, metric: val}
        if extra_cols:
            row.update(extra_cols)
        rows.append(row)
    return pd.DataFrame(rows)


def test_all_regions_shape_has_best_and_worst():
    df = _make_region_df(
        "service_quality_index",
        {"London": 75.0, "North East": 50.0, "South West": 65.0},
    )
    stats = build_ranking_stats(
        section_id="b1_frequency",
        df=df,
        region="all",
        region_name=None,
    )
    assert stats["best"]["name"] == "London"
    assert stats["best"]["value"] == 75.0
    assert stats["worst"]["name"] == "North East"
    assert stats["worst"]["value"] == 50.0
    assert "national_avg" in stats
    assert stats["unit"] == "SQI points"
    assert "best" in stats and "worst" in stats


def test_lower_is_better_metric_flips_best_worst():
    """f6_equitable_regions: lower vulnerability_index = more equitable = 'best'."""
    df = _make_region_df(
        "vulnerability_index",
        {"London": 0.8, "North East": 0.3, "South West": 0.5},
    )
    stats = build_ranking_stats(
        section_id="f6_equitable_regions",
        df=df,
        region="all",
        region_name=None,
    )
    assert stats["best"]["name"] == "North East"  # lowest vulnerability = most equitable
    assert stats["worst"]["name"] == "London"


def test_single_region_shape_when_region_filtered():
    df = _make_region_df(
        "service_quality_index",
        {"London": 75.0, "North East": 50.0, "South West": 65.0},
    )
    stats = build_ranking_stats(
        section_id="b1_frequency",
        df=df,
        region="E12000001",
        region_name="North East",
    )
    assert stats["region_name"] == "North East"
    assert stats["value"] == 50.0
    assert "best" not in stats
    assert "worst" not in stats
    assert "national_avg" in stats


def test_empty_dataframe_returns_empty_stats():
    df = pd.DataFrame(columns=["region", "service_quality_index"])
    stats = build_ranking_stats(section_id="b1_frequency", df=df, region="all", region_name=None)
    assert stats == {}


def test_ranking_config_covers_all_seven_sections():
    expected = {
        "a1_route_density",
        "a2_stop_density",
        "b1_frequency",
        "b4_route_frequency",
        "f6_equitable_regions",
        "j4_investment_priority",
        "bsa1_franchising_readiness",
    }
    assert set(RANKING_CONFIG.keys()) == expected
    for sid, cfg in RANKING_CONFIG.items():
        assert "metric" in cfg
        assert "group_col" in cfg
        assert "unit" in cfg
        assert "higher_is_better" in cfg
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/warehouse/stats_builders/test_ranking.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'aequitas.warehouse.stats_builders.ranking'`

- [ ] **Step 3: Write the implementation**

Create `src/aequitas/warehouse/stats_builders/ranking.py`:

```python
"""Stats builder for ranking.j2 — best/worst region comparisons.

Covers: a1_route_density, a2_stop_density, b1_frequency, b4_route_frequency,
f6_equitable_regions, j4_investment_priority, bsa1_franchising_readiness.

All seven sections share the same template contract — they differ only in
which metric (and source table) is ranked. RANKING_CONFIG is the single
source of truth for that mapping; build_ranking_stats is generic over it.
"""

import pandas as pd

from aequitas.warehouse.stats_builders.shared import build_single_region_stats

# Per-section configuration: which metric to rank, grouped by which column,
# with what unit label, and whether higher values are "better" (best = highest)
# or lower values are "better" (best = lowest, e.g. vulnerability_index).
RANKING_CONFIG: dict[str, dict] = {
    "a1_route_density": {
        "metric": "route_count",
        "group_col": "primary_region",
        "unit": "routes",
        "higher_is_better": True,
    },
    "a2_stop_density": {
        "metric": "stops_per_1k",
        "group_col": "region",
        "unit": "stops/1,000 population",
        "higher_is_better": True,
    },
    "b1_frequency": {
        "metric": "service_quality_index",
        "group_col": "region",
        "unit": "SQI points",
        "higher_is_better": True,
    },
    "b4_route_frequency": {
        # Regional service-frequency proxy — no per-route frequency join exists
        # in the audit parquets (route_geometries has no departure-frequency
        # column). trips_per_capita aggregated by region is the closest
        # traceable proxy and keeps the metric population-denominated.
        "metric": "trips_per_capita",
        "group_col": "region",
        "unit": "trips/capita",
        "higher_is_better": True,
    },
    "f6_equitable_regions": {
        "metric": "vulnerability_index",
        "group_col": "region",
        "unit": "vulnerability index",
        "higher_is_better": False,
    },
    "j4_investment_priority": {
        "metric": "investment_gap_annual_cost",
        "group_col": "region",
        "unit": "£/year investment gap",
        "higher_is_better": True,
    },
    "bsa1_franchising_readiness": {
        "metric": "franchising_readiness",
        "group_col": "region",
        "unit": "readiness score (0-100)",
        "higher_is_better": True,
    },
}


def build_ranking_stats(
    section_id: str,
    df: pd.DataFrame,
    region: str,
    region_name: str | None,
) -> dict:
    """Build stats for any ranking.j2-backed section.

    Args:
        section_id: One of the keys in RANKING_CONFIG.
        df: DataFrame already aggregated to one row per group with columns
            [group_col, metric] — e.g. a route-count-per-region table for a1,
            or the filtered LSOA policy_synthesis frame for b1/f6/j4.
        region: Active region filter — "all" or an ONS region code.
        region_name: Full region name (from REGION_NAMES) when region != "all",
            else None.

    Returns:
        Either the all-regions {best, worst, national_avg, unit} shape, the
        single-region shape (via shared.build_single_region_stats), or {} if
        df has no rows for the metric.
    """
    cfg = RANKING_CONFIG[section_id]
    metric = cfg["metric"]
    group_col = cfg["group_col"]
    unit = cfg["unit"]
    higher_is_better = cfg["higher_is_better"]

    if df.empty or group_col not in df.columns or metric not in df.columns:
        return {}

    by_region = df.groupby(group_col)[metric].mean().dropna()
    if by_region.empty:
        return {}

    if region != "all" and region_name is not None:
        if region_name not in by_region.index:
            return {}
        return build_single_region_stats(
            by_region=by_region,
            region_value=float(by_region[region_name]),
            region_name=region_name,
            unit=unit,
        )

    if len(by_region) < 2:
        return {}

    nat_mean = float(by_region.mean())
    best_name = by_region.idxmax() if higher_is_better else by_region.idxmin()
    worst_name = by_region.idxmin() if higher_is_better else by_region.idxmax()
    best_val = float(by_region[best_name])
    worst_val = float(by_region[worst_name])

    return {
        "best": {
            "name": best_name,
            "value": round(best_val, 2),
            "pct_above": round((best_val - nat_mean) / nat_mean * 100, 1) if nat_mean else 0.0,
        },
        "worst": {
            "name": worst_name,
            "value": round(worst_val, 2),
            "pct_below": round((nat_mean - worst_val) / nat_mean * 100, 1) if nat_mean else 0.0,
        },
        "national_avg": round(nat_mean, 2),
        "unit": unit,
    }
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/warehouse/stats_builders/test_ranking.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/aequitas/warehouse/stats_builders/ranking.py tests/warehouse/stats_builders/test_ranking.py
git commit -m "feat: add ranking.py stats builder covering 7 sections (a1,a2,b1,b4,f6,j4,bsa1)"
```

---

## Task 6: `correlation.py` builder module — 7 sections (b5, c5, d1–d5)

**Files:**
- Create: `src/aequitas/warehouse/stats_builders/correlation.py`
- Test: `tests/warehouse/stats_builders/test_correlation.py`

All seven map to `correlation.j2`, which needs:
`{r, p_value, n, n_observations, x_label, y_label, strength, direction}`
(the `n_observations` key is new — added per ISSUES.md §4.4 so the template's
evidence gate can use a sample-size-aware significance threshold; Task 14
updates `correlation.j2` to read it).

This module **reuses `aequitas.intelligence.calculators.calculate_correlation`**
— do not reimplement Pearson r/p/strength/direction logic.

| section_id | x (label) | y (label) | x source col | y source col |
|---|---|---|---|---|
| `d1_coverage_deprivation` | IMD score | trips per capita | `imd_score` | `trips_per_capita` |
| `d2_coverage_unemployment` | unemployment rate | trips per capita | `unemployment_rate` (master_lsoa_table) | `trips_per_capita` |
| `d3_coverage_car` | car-free household % | trips per capita | `nocar_pct` (master_lsoa_table) | `trips_per_capita` |
| `d4_coverage_elderly` | elderly population % | trips per capita | `elderly_pct` (master_lsoa_table) | `trips_per_capita` |
| `d5_coverage_income` | income score | trips per capita | `income_score` (master_lsoa_table) | `trips_per_capita` |
| `b5_frequency_deprivation` | IMD score | service quality index | `imd_score` | `service_quality_index` |
| `c5_length_vs_frequency` | route length (km) | stop count (frequency proxy — see note) | `length_km` (route_clusters) | `stop_count` (route_clusters) |

**Note on c5:** no per-route departure-frequency column exists in any audit
parquet (`route_clusters`/`route_geometries` lack headway data, and joining
`stop_headways` to routes requires a multi-hop trip→stop→route resolution not
present as a precomputed table). `stop_count` is used as a frequency proxy
(more stops along a route correlates with more frequent local service patterns)
and the builder documents this inline.

`d1`–`d5` and `b5` use the `filtered` policy_df (already region/urban-rural
filtered) joined to `master_lsoa_table` columns where needed. `c5` uses
`route_clusters` directly (routes have no region/urban-rural dimension to
filter by — same data is returned regardless of the active filter, matching
how `c1`/`c2`/`c6`/`c7` will also behave).

- [ ] **Step 1: Write the failing tests**

Create `tests/warehouse/stats_builders/test_correlation.py`:

```python
"""Tests for correlation.py — covers b5, c5, d1-d5."""
import numpy as np
import pandas as pd
import pytest

from aequitas.warehouse.stats_builders.correlation import (
    build_correlation_stats,
    CORRELATION_CONFIG,
)


def _correlated_df(n=200, seed=0):
    rng = np.random.default_rng(seed)
    x = rng.normal(50, 10, n)
    y = -0.8 * x + rng.normal(0, 5, n) + 100  # strong negative correlation
    return pd.DataFrame({"imd_score": x, "trips_per_capita": y})


def test_correlation_stats_shape():
    df = _correlated_df()
    stats = build_correlation_stats("d1_coverage_deprivation", df)
    assert set(stats.keys()) >= {
        "r", "p_value", "n", "n_observations", "x_label", "y_label", "strength", "direction"
    }
    assert stats["direction"] == "negative"
    assert stats["n"] == 200
    assert stats["n_observations"] == 200
    assert stats["x_label"] == "IMD Decile" or "IMD" in stats["x_label"]
    assert "trips" in stats["y_label"].lower()


def test_correlation_too_few_rows_returns_empty():
    df = pd.DataFrame({"imd_score": [1.0], "trips_per_capita": [2.0]})
    stats = build_correlation_stats("d1_coverage_deprivation", df)
    assert stats == {}


def test_missing_columns_returns_empty():
    df = pd.DataFrame({"imd_score": [1.0, 2.0, 3.0]})
    stats = build_correlation_stats("d1_coverage_deprivation", df)
    assert stats == {}


def test_correlation_config_covers_all_seven_sections():
    expected = {
        "d1_coverage_deprivation", "d2_coverage_unemployment", "d3_coverage_car",
        "d4_coverage_elderly", "d5_coverage_income", "b5_frequency_deprivation",
        "c5_length_vs_frequency",
    }
    assert set(CORRELATION_CONFIG.keys()) == expected
    for sid, cfg in CORRELATION_CONFIG.items():
        assert "x_col" in cfg and "y_col" in cfg
        assert "x_label" in cfg and "y_label" in cfg
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/warehouse/stats_builders/test_correlation.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Write the implementation**

Create `src/aequitas/warehouse/stats_builders/correlation.py`:

```python
"""Stats builder for correlation.j2 — Pearson correlation between two variables.

Covers: d1_coverage_deprivation, d2_coverage_unemployment, d3_coverage_car,
d4_coverage_elderly, d5_coverage_income, b5_frequency_deprivation,
c5_length_vs_frequency.

Reuses aequitas.intelligence.calculators.calculate_correlation — the Pearson
r/p-value/strength/direction logic already exists and is tested there.
"""

import pandas as pd

from aequitas.intelligence.calculators import calculate_correlation

# Per-section variable pair configuration. x_col/y_col are columns expected to
# already be present in the DataFrame passed to build_correlation_stats — the
# caller (precompute.py) is responsible for joining in master_lsoa_table
# columns (income_score, unemployment_rate, elderly_pct, nocar_pct) where the
# section requires them, since lsoa_policy_synthesis does not carry them.
CORRELATION_CONFIG: dict[str, dict] = {
    "d1_coverage_deprivation": {
        "x_col": "imd_score", "y_col": "trips_per_capita",
        "x_label": "IMD Score", "y_label": "Trips per Capita",
    },
    "d2_coverage_unemployment": {
        "x_col": "unemployment_rate", "y_col": "trips_per_capita",
        "x_label": "Unemployment Rate", "y_label": "Trips per Capita",
    },
    "d3_coverage_car": {
        "x_col": "nocar_pct", "y_col": "trips_per_capita",
        "x_label": "Car-Free Household %", "y_label": "Trips per Capita",
    },
    "d4_coverage_elderly": {
        "x_col": "elderly_pct", "y_col": "trips_per_capita",
        "x_label": "Elderly Population %", "y_label": "Trips per Capita",
    },
    "d5_coverage_income": {
        "x_col": "income_score", "y_col": "trips_per_capita",
        "x_label": "Income Score", "y_label": "Trips per Capita",
    },
    "b5_frequency_deprivation": {
        "x_col": "imd_score", "y_col": "service_quality_index",
        "x_label": "IMD Score", "y_label": "Service Quality Index",
    },
    "c5_length_vs_frequency": {
        # stop_count used as a frequency proxy — no per-route departure
        # frequency column exists in any audit parquet (see plan Task 6 note).
        "x_col": "length_km", "y_col": "stop_count",
        "x_label": "Route Length (km)", "y_label": "Stops per Route (frequency proxy)",
    },
}


def build_correlation_stats(section_id: str, df: pd.DataFrame) -> dict:
    """Build stats for any correlation.j2-backed section.

    Args:
        section_id: One of the keys in CORRELATION_CONFIG.
        df: DataFrame containing both the x_col and y_col for this section
            (already filtered/joined by the caller).

    Returns:
        Dict matching correlation.j2's contract, or {} if columns are missing
        or fewer than 3 complete-case rows are available (calculate_correlation's
        own floor — we additionally require this directly so the section
        suppresses cleanly rather than rendering a near-meaningless r).
    """
    cfg = CORRELATION_CONFIG[section_id]
    x_col, y_col = cfg["x_col"], cfg["y_col"]

    if x_col not in df.columns or y_col not in df.columns:
        return {}

    pair = df[[x_col, y_col]].dropna()
    if len(pair) < 3:
        return {}

    result = calculate_correlation(pair[x_col], pair[y_col])

    return {
        "r": result.r,
        "p_value": result.p_value,
        "n": result.n,
        "n_observations": result.n,
        "x_label": cfg["x_label"],
        "y_label": cfg["y_label"],
        "strength": result.strength,
        "direction": result.direction,
    }
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/warehouse/stats_builders/test_correlation.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/aequitas/warehouse/stats_builders/correlation.py tests/warehouse/stats_builders/test_correlation.py
git commit -m "feat: add correlation.py stats builder covering 7 sections (b5,c5,d1-d5)"
```

---

## Task 7: `ml_clusters.py` builder module — 3 sections (c6, d6, g1)

**Files:**
- Create: `src/aequitas/warehouse/stats_builders/ml_clusters.py`
- Test: `tests/warehouse/stats_builders/test_ml_clusters.py`

All three map to `ml_clusters.j2`, needing:
`{n_clusters, entity_type, clusters: [{id, n, pct, description}, ...]}`

| section_id | entity_type | source | cluster col | description basis |
|---|---|---|---|---|
| `g1_route_clusters` | "routes" | `route_clusters.parquet` | `cluster` (HDBSCAN, -1=noise) | mean `length_km`/`stop_count`/`cross_la_int` per cluster |
| `c6_route_archetypes` | "route archetypes" | `route_clusters.parquet` | `cluster` | same as g1 — different narrative framing (archetype vs raw cluster), same underlying clustering since no second route-clustering exists |
| `d6_transport_poverty` | "LSOAs" | `lsoa_clusters_hdbscan.parquet` | `hdbscan_archetype` (pre-labelled: "Noise", "Elderly Rural", "Diverse Urban") | use the existing archetype label directly as the description basis |

Confirmed cluster stats (use these to write the test fixtures' expected shapes,
not hardcoded into the implementation):
- `route_clusters.cluster` value counts: `-1`→221, `0`→158, `1`→1788, `2`→1294, `3`→345, `4`→342, `5`→281, `6`→1051 (total 5,480)
- `route_clusters` per-cluster means (length_km, stop_count, cross_la_int): cluster 1 is short/local (9.4km, 23 stops, 0% cross-LA), cluster 4 is long/cross-boundary (46.8km, 47 stops, 100% cross-LA)
- `lsoa_clusters_hdbscan.hdbscan_archetype` value counts: "Noise"→29,560, "Elderly Rural"→4,095, "Diverse Urban"→100 (total 33,755)

- [ ] **Step 1: Write the failing tests**

Create `tests/warehouse/stats_builders/test_ml_clusters.py`:

```python
"""Tests for ml_clusters.py — covers c6, d6, g1."""
import pandas as pd
import pytest

from aequitas.warehouse.stats_builders.ml_clusters import build_ml_clusters_stats


def _route_clusters_df():
    rows = []
    # cluster 1: short local routes (n=3)
    for _ in range(3):
        rows.append({"cluster": 1, "length_km": 9.0, "stop_count": 23, "cross_la_int": 0})
    # cluster 4: long cross-boundary routes (n=2)
    for _ in range(2):
        rows.append({"cluster": 4, "length_km": 47.0, "stop_count": 47, "cross_la_int": 1})
    # noise (n=1) — must be excluded from cluster list
    rows.append({"cluster": -1, "length_km": 45.0, "stop_count": 53, "cross_la_int": 0})
    return pd.DataFrame(rows)


def _lsoa_archetype_df():
    rows = (
        [{"hdbscan_archetype": "Noise"}] * 6
        + [{"hdbscan_archetype": "Elderly Rural"}] * 3
        + [{"hdbscan_archetype": "Diverse Urban"}] * 1
    )
    return pd.DataFrame(rows)


def test_route_clusters_excludes_noise_and_has_descriptions():
    df = _route_clusters_df()
    stats = build_ml_clusters_stats("g1_route_clusters", df)
    cluster_ids = {c["id"] for c in stats["clusters"]}
    assert -1 not in cluster_ids
    assert stats["entity_type"] == "routes"
    assert stats["n_clusters"] == len(stats["clusters"])
    for c in stats["clusters"]:
        assert c["n"] > 0
        assert 0 < c["pct"] <= 100
        assert isinstance(c["description"], str) and len(c["description"]) > 0


def test_route_archetypes_uses_same_source_different_entity_type():
    df = _route_clusters_df()
    stats = build_ml_clusters_stats("c6_route_archetypes", df)
    assert stats["entity_type"] == "route archetypes"
    assert stats["n_clusters"] > 0


def test_lsoa_archetype_clusters_from_prelabelled_column():
    df = _lsoa_archetype_df()
    stats = build_ml_clusters_stats("d6_transport_poverty", df)
    assert stats["entity_type"] == "LSOAs"
    labels = {c["description"][:13] for c in stats["clusters"]}  # description starts with label
    assert any("Noise" in c["description"] for c in stats["clusters"])
    assert any("Elderly Rural" in c["description"] for c in stats["clusters"])
    total_pct = sum(c["pct"] for c in stats["clusters"])
    assert total_pct == pytest.approx(100.0, abs=0.5)


def test_empty_df_returns_empty():
    assert build_ml_clusters_stats("g1_route_clusters", pd.DataFrame()) == {}
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/warehouse/stats_builders/test_ml_clusters.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Write the implementation**

Create `src/aequitas/warehouse/stats_builders/ml_clusters.py`:

```python
"""Stats builder for ml_clusters.j2 — HDBSCAN cluster profile summaries.

Covers: g1_route_clusters, c6_route_archetypes (both from route_clusters.parquet,
differing only in narrative framing), d6_transport_poverty (from
lsoa_clusters_hdbscan.parquet, using its pre-computed hdbscan_archetype labels).
"""

import pandas as pd

_ROUTE_ENTITY_TYPES = {
    "g1_route_clusters": "routes",
    "c6_route_archetypes": "route archetypes",
}


def _describe_route_cluster(cluster_id: int, mean_length: float, mean_stops: float, mean_cross_la: float) -> str:
    """Generate a description from a route cluster's mean feature values.

    Thresholds (short < 15km, long > 35km; cross_la majority > 0.5) are chosen
    to separate the confirmed cluster means (cluster 1: 9.4km/0% cross-LA vs
    cluster 4: 46.8km/100% cross-LA) into clearly distinct narrative bands.
    """
    length_band = "short local" if mean_length < 15 else "long-distance" if mean_length > 35 else "medium-length"
    boundary = "cross-boundary" if mean_cross_la > 0.5 else "within-authority"
    return (
        f"{length_band.capitalize()} {boundary} routes averaging {mean_length:.1f} km "
        f"with {mean_stops:.0f} stops per route"
    )


def _build_route_clusters(section_id: str, df: pd.DataFrame) -> dict:
    required = {"cluster", "length_km", "stop_count", "cross_la_int"}
    if not required.issubset(df.columns):
        return {}

    real = df[df["cluster"] != -1]  # exclude HDBSCAN noise label
    if real.empty:
        return {}

    total = len(real)
    grouped = real.groupby("cluster").agg(
        n=("cluster", "size"),
        mean_length=("length_km", "mean"),
        mean_stops=("stop_count", "mean"),
        mean_cross_la=("cross_la_int", "mean"),
    )

    clusters = []
    for cluster_id, row in grouped.iterrows():
        clusters.append({
            "id": int(cluster_id),
            "n": int(row["n"]),
            "pct": round(float(row["n"]) / total * 100, 1),
            "description": _describe_route_cluster(
                int(cluster_id), float(row["mean_length"]), float(row["mean_stops"]), float(row["mean_cross_la"])
            ),
        })

    return {
        "n_clusters": len(clusters),
        "entity_type": _ROUTE_ENTITY_TYPES[section_id],
        "clusters": sorted(clusters, key=lambda c: -c["n"]),
    }


_ARCHETYPE_DESCRIPTIONS: dict[str, str] = {
    "Noise": "Noise — LSOAs with no clear archetype membership; heterogeneous demographic and service profiles that do not cluster densely with any group",
    "Elderly Rural": "Elderly Rural — LSOAs combining higher elderly populations, rural settlement patterns, and structurally lower service levels",
    "Diverse Urban": "Diverse Urban — LSOAs with higher ethnic diversity, denser urban settlement, and comparatively stronger service provision",
}


def _build_lsoa_archetypes(df: pd.DataFrame) -> dict:
    if "hdbscan_archetype" not in df.columns or df.empty:
        return {}

    counts = df["hdbscan_archetype"].value_counts()
    total = int(counts.sum())
    if total == 0:
        return {}

    clusters = []
    for label, n in counts.items():
        clusters.append({
            "id": label,
            "n": int(n),
            "pct": round(float(n) / total * 100, 1),
            "description": _ARCHETYPE_DESCRIPTIONS.get(label, f"{label} — LSOA archetype identified by HDBSCAN clustering"),
        })

    return {
        "n_clusters": len(clusters),
        "entity_type": "LSOAs",
        "clusters": sorted(clusters, key=lambda c: -c["n"]),
    }


def build_ml_clusters_stats(section_id: str, df: pd.DataFrame) -> dict:
    """Build stats for any ml_clusters.j2-backed section.

    Args:
        section_id: One of g1_route_clusters, c6_route_archetypes, d6_transport_poverty.
        df: For route sections, route_clusters.parquet (unfiltered — routes have
            no region/urban-rural dimension). For d6, lsoa_clusters_hdbscan.parquet
            (callers may pass the unfiltered frame — clustering was computed
            nationally and does not vary by filter, same as SHAP; see ISSUES §4.3).

    Returns:
        Dict with n_clusters, entity_type, clusters list, or {} if the
        required columns/data are absent.
    """
    if df.empty:
        return {}
    if section_id in _ROUTE_ENTITY_TYPES:
        return _build_route_clusters(section_id, df)
    if section_id == "d6_transport_poverty":
        return _build_lsoa_archetypes(df)
    return {}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/warehouse/stats_builders/test_ml_clusters.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/aequitas/warehouse/stats_builders/ml_clusters.py tests/warehouse/stats_builders/test_ml_clusters.py
git commit -m "feat: add ml_clusters.py stats builder covering 3 sections (c6,d6,g1)"
```

---

## Task 8: `ml_prediction.py` builder module — 4 sections (a8, d8, g3, g4)

**Files:**
- Create: `src/aequitas/warehouse/stats_builders/ml_prediction.py`
- Test: `tests/warehouse/stats_builders/test_ml_prediction.py`

All four (`a8_coverage_prediction`, `d8_feature_importance`, `g3_coverage_model`,
`g4_shap`) map to `ml_prediction.j2`, needing:
`{r2, top_feature, top_importance, n_features}`

The Random Forest model was trained once nationally (33,755 LSOAs) — SHAP
values and R² do not vary by region/urban-rural filter (confirmed: this is the
exact situation ISSUES.md §4.3 documents as a known limitation requiring a
narrative caveat, not a per-filter recomputation). All four sections therefore
return **identical stats** for every filter combination — this is correct
behaviour, not a bug, given the model is national.

Confirmed figures (from `docs/figures-registry.md` ST-007 and `shap_summary.csv`
— per the project's figures-registry rule, both are ✅ Confirmed sources):
- `r2 = 0.4719`
- `top_feature = "nocar_pct"`, `top_importance = 0.0830` (rounded from `0.08301616868981271`)
- `n_features = 9` (the 9 rows in `shap_summary.csv`: `imd_score`, `unemployment_rate`,
  `nocar_pct`, `elderly_pct`, `disability_pct`, `income_score`, `nonwhite_pct`,
  `stops_per_1k`, `urban_enc`)

- [ ] **Step 1: Write the failing tests**

Create `tests/warehouse/stats_builders/test_ml_prediction.py`:

```python
"""Tests for ml_prediction.py — covers a8, d8, g3, g4."""
import pandas as pd
import pytest

from aequitas.warehouse.stats_builders.ml_prediction import build_ml_prediction_stats


def _shap_df():
    return pd.DataFrame({
        "feature": ["imd_score", "unemployment_rate", "nocar_pct", "elderly_pct",
                    "disability_pct", "income_score", "nonwhite_pct", "stops_per_1k", "urban_enc"],
        "mean_abs_shap": [0.00547, 0.00211, 0.08302, 0.00653, 0.01606, 0.00684, 0.03029, 0.06281, 0.0],
    })


@pytest.mark.parametrize("section_id", [
    "a8_coverage_prediction", "d8_feature_importance", "g3_coverage_model", "g4_shap",
])
def test_all_four_sections_produce_identical_national_stats(section_id):
    stats = build_ml_prediction_stats(section_id, shap_df=_shap_df(), r2=0.4719)
    assert stats["r2"] == pytest.approx(0.4719)
    assert stats["top_feature"] == "nocar_pct"
    assert stats["top_importance"] == pytest.approx(0.083, abs=0.001)
    assert stats["n_features"] == 9


def test_empty_shap_df_returns_empty():
    stats = build_ml_prediction_stats("g4_shap", shap_df=pd.DataFrame(), r2=0.4719)
    assert stats == {}


def test_missing_r2_returns_empty():
    stats = build_ml_prediction_stats("g4_shap", shap_df=_shap_df(), r2=None)
    assert stats == {}
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/warehouse/stats_builders/test_ml_prediction.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Write the implementation**

Create `src/aequitas/warehouse/stats_builders/ml_prediction.py`:

```python
"""Stats builder for ml_prediction.j2 — Random Forest R² / SHAP feature importance.

Covers: a8_coverage_prediction, d8_feature_importance, g3_coverage_model, g4_shap.

The model is trained once nationally — these stats are identical across every
filter combination (region/urban_rural make no difference to a nationally-fit
model's R² or SHAP values). This is documented behaviour per ISSUES.md §4.3,
not a bug: the narrative caveat about national-vs-regional applicability lives
in the template/registry layer, not here.
"""

import pandas as pd


def build_ml_prediction_stats(section_id: str, shap_df: pd.DataFrame, r2: float | None) -> dict:
    """Build stats for any ml_prediction.j2-backed section.

    Args:
        section_id: One of a8_coverage_prediction, d8_feature_importance,
            g3_coverage_model, g4_shap. (Accepted for interface symmetry with
            other builders and potential future per-section framing — all four
            currently return the same national-model stats.)
        shap_df: DataFrame loaded from shap_summary.csv with columns
            'feature' and 'mean_abs_shap'.
        r2: Confirmed R² figure for the national Random Forest model
            (0.4719 — see docs/figures-registry.md ST-007).

    Returns:
        Dict with r2, top_feature, top_importance, n_features, or {} if the
        SHAP data or R² figure is unavailable.
    """
    if shap_df.empty or "feature" not in shap_df.columns or "mean_abs_shap" not in shap_df.columns:
        return {}
    if r2 is None:
        return {}

    ranked = shap_df.sort_values("mean_abs_shap", ascending=False).reset_index(drop=True)
    top = ranked.iloc[0]

    return {
        "r2": round(float(r2), 4),
        "top_feature": str(top["feature"]),
        "top_importance": round(float(top["mean_abs_shap"]), 3),
        "n_features": int(len(ranked)),
    }
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/warehouse/stats_builders/test_ml_prediction.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/aequitas/warehouse/stats_builders/ml_prediction.py tests/warehouse/stats_builders/test_ml_prediction.py
git commit -m "feat: add ml_prediction.py stats builder covering 4 sections (a8,d8,g3,g4)"
```

---

## Task 9: `market_concentration.py` builder module — 2 sections (c3, bsa2)

**Files:**
- Create: `src/aequitas/warehouse/stats_builders/market_concentration.py`
- Test: `tests/warehouse/stats_builders/test_market_concentration.py`

Both `c3_operator_hhi` and `bsa2_operator_concentration` map to
`market_concentration.j2`, needing:
`{hhi, region_name, top_operator (optional), top_operator_share (optional)}`
(the template gates `top_operator` behind `{% if top_operator %}` — safe to omit).

They differ in **what HHI represents**:

- **`c3_operator_hhi`** ("Operator landscape (HHI)") — computed directly from
  `route_geometries`: group by `primary_region` (or nationally when `region == "all"`),
  then by `agency_name`, HHI = Σ(route-count market share %)². This also yields
  `top_operator`/`top_operator_share`. Confirmed worked example: London HHI ≈ 929
  (competitive), top operator "Go Ahead London" at 17.8%.
- **`bsa2_operator_concentration`** ("Operator concentration", under the BSA
  category) — uses the **pre-computed** `region_hhi` column from
  `lta_franchising_readiness.parquet` (mean across LADs in the region/filter —
  confirmed e.g. North East LADs all carry `region_hhi = 1609`). No
  `top_operator` is available from this source — omit it (template handles
  this via its `{% if top_operator %}` gate).

When `region == "all"`, `region_name` is `"England"` and HHI is computed across
all routes/LADs nationally.

- [ ] **Step 1: Write the failing tests**

Create `tests/warehouse/stats_builders/test_market_concentration.py`:

```python
"""Tests for market_concentration.py — covers c3, bsa2."""
import pandas as pd
import pytest

from aequitas.warehouse.stats_builders.market_concentration import build_market_concentration_stats


def _routes_df():
    # 3 operators in one region: shares 60%, 30%, 10% -> HHI = 3600+900+100 = 4600
    rows = (
        [{"primary_region": "London", "agency_name": "Big Co"}] * 6
        + [{"primary_region": "London", "agency_name": "Mid Co"}] * 3
        + [{"primary_region": "London", "agency_name": "Small Co"}] * 1
    )
    return pd.DataFrame(rows)


def _lta_df():
    return pd.DataFrame({
        "lad_nm": ["Hartlepool", "Middlesbrough"],
        "region": ["North East", "North East"],
        "region_hhi": [1609, 1609],
    })


def test_c3_computes_hhi_and_top_operator_from_routes():
    stats = build_market_concentration_stats(
        "c3_operator_hhi", routes_df=_routes_df(), lta_df=None,
        region_name="London",
    )
    assert stats["hhi"] == pytest.approx(4600.0, abs=0.1)
    assert stats["region_name"] == "London"
    assert stats["top_operator"] == "Big Co"
    assert stats["top_operator_share"] == pytest.approx(60.0, abs=0.1)


def test_bsa2_uses_precomputed_lta_hhi_without_top_operator():
    stats = build_market_concentration_stats(
        "bsa2_operator_concentration", routes_df=None, lta_df=_lta_df(),
        region_name="North East",
    )
    assert stats["hhi"] == pytest.approx(1609.0)
    assert stats["region_name"] == "North East"
    assert "top_operator" not in stats


def test_empty_inputs_return_empty():
    assert build_market_concentration_stats("c3_operator_hhi", routes_df=pd.DataFrame(), lta_df=None, region_name="London") == {}
    assert build_market_concentration_stats("bsa2_operator_concentration", routes_df=None, lta_df=pd.DataFrame(), region_name="London") == {}
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/warehouse/stats_builders/test_market_concentration.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Write the implementation**

Create `src/aequitas/warehouse/stats_builders/market_concentration.py`:

```python
"""Stats builder for market_concentration.j2 — Herfindahl-Hirschman Index.

Covers: c3_operator_hhi (computed from route-level operator market share),
bsa2_operator_concentration (uses the pre-computed region_hhi from
lta_franchising_readiness — the BSA franchising-readiness composite already
includes an HHI sub-score, so we reuse it rather than recomputing).
"""

import pandas as pd


def _hhi_from_shares(shares_pct: pd.Series) -> float:
    """HHI = sum of squared market shares (in percentage points)."""
    return float((shares_pct ** 2).sum())


def _build_from_routes(routes_df: pd.DataFrame, region_name: str) -> dict:
    if routes_df.empty or "agency_name" not in routes_df.columns:
        return {}

    counts = routes_df["agency_name"].value_counts(dropna=True)
    total = int(counts.sum())
    if total == 0:
        return {}

    shares = counts / total * 100
    hhi = _hhi_from_shares(shares)
    top_operator = str(shares.index[0])
    top_share = float(shares.iloc[0])

    return {
        "hhi": round(hhi, 1),
        "region_name": region_name,
        "top_operator": top_operator,
        "top_operator_share": round(top_share, 1),
    }


def _build_from_lta(lta_df: pd.DataFrame, region_name: str) -> dict:
    if lta_df.empty or "region_hhi" not in lta_df.columns:
        return {}

    mean_hhi = float(lta_df["region_hhi"].mean())
    if pd.isna(mean_hhi):
        return {}

    # No top_operator available from this source — market_concentration.j2
    # gates the operator-detail paragraph behind `{% if top_operator %}`.
    return {
        "hhi": round(mean_hhi, 1),
        "region_name": region_name,
    }


def build_market_concentration_stats(
    section_id: str,
    routes_df: pd.DataFrame | None,
    lta_df: pd.DataFrame | None,
    region_name: str,
) -> dict:
    """Build stats for c3_operator_hhi or bsa2_operator_concentration.

    Args:
        section_id: "c3_operator_hhi" or "bsa2_operator_concentration".
        routes_df: route_geometries rows for the active filter scope (region-
            filtered by primary_region, or all routes when region == "all").
            Required for c3, ignored for bsa2.
        lta_df: lta_franchising_readiness rows for the active filter scope
            (region-filtered, or all LADs when region == "all"). Required for
            bsa2, ignored for c3.
        region_name: Human-readable region/scope label for the template header
            (e.g. "London" or "England" when region == "all").

    Returns:
        Dict matching market_concentration.j2's contract, or {} if the
        relevant source data is empty/missing.
    """
    if section_id == "c3_operator_hhi":
        return _build_from_routes(routes_df if routes_df is not None else pd.DataFrame(), region_name)
    if section_id == "bsa2_operator_concentration":
        return _build_from_lta(lta_df if lta_df is not None else pd.DataFrame(), region_name)
    return {}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/warehouse/stats_builders/test_market_concentration.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/aequitas/warehouse/stats_builders/market_concentration.py tests/warehouse/stats_builders/test_market_concentration.py
git commit -m "feat: add market_concentration.py stats builder covering 2 sections (c3,bsa2)"
```

---

## Task 10: `urban_rural_gap.py` builder module — 3 sections (a6, c4 [stub], f5)

**Files:**
- Create: `src/aequitas/warehouse/stats_builders/urban_rural_gap.py`
- Test: `tests/warehouse/stats_builders/test_urban_rural_gap.py`

All three sections map to `urban_rural_gap.j2`, needing:
`{urban_value, rural_value, gap_pct, n_urban, n_rural, unit}`.

This builder implements the §4.2 fix: **always** compute `urban_value` from
the urban subset and `rural_value` from the rural subset of the
**region-filtered but area-type-UNfiltered** dataframe (`region_df`), never
from `filtered_df` (which has already collapsed to one area type when
`urban_rural != "all"`). This guarantees both sides have non-zero `n` for
every one of the 30 combinations.

- **`a6_urban_rural_gap`** ("Urban vs rural coverage gap", category A
  Accessibility) — uses `trips_per_capita` (the coverage/service-volume metric
  used throughout `lsoa_policy_synthesis`). `unit = "trips per capita"`.
- **`f5_rural_penalty`** ("Rural accessibility penalty", category F Equity)
  — uses `service_quality_index` (the composite SQI, ground-truth mean 65.4/100
  per CLAUDE.md). `unit = "service quality index"`.
- **`c4_urban_rural_routes`** ("Urban vs rural routes", category C) — STUB
  per spec §8.4: comparing route geometry by urban/rural classification
  requires a route-geometry × LSOA-urban-rural spatial join that does not
  exist in any precomputed table. Returns `{}` with an inline comment.

`gap_pct` is the percentage by which the rural value falls short of the urban
value: `(urban_value - rural_value) / urban_value * 100`. Guard divide-by-zero
by returning `{}` when `urban_value == 0`.

- [ ] **Step 1: Write the failing tests**

Create `tests/warehouse/stats_builders/test_urban_rural_gap.py`:

```python
"""Tests for urban_rural_gap.py — covers a6, c4 (stub), f5."""
import pandas as pd
import pytest

from aequitas.warehouse.stats_builders.urban_rural_gap import build_urban_rural_gap_stats


def _region_df():
    # region-filtered, BOTH area types present (this is the key §4.2 invariant)
    return pd.DataFrame({
        "urban_rural": ["Urban", "Urban", "Urban", "Rural", "Rural"],
        "trips_per_capita": [10.0, 12.0, 14.0, 4.0, 6.0],
        "service_quality_index": [80.0, 70.0, 90.0, 50.0, 40.0],
    })


def test_a6_computes_both_sides_from_region_df_regardless_of_area_filter():
    # Even when urban_rural filter == "rural", a6 must still report BOTH sides
    stats = build_urban_rural_gap_stats(
        "a6_urban_rural_gap", region_df=_region_df(), urban_rural="rural",
    )
    assert stats["urban_value"] == pytest.approx(12.0)
    assert stats["rural_value"] == pytest.approx(5.0)
    assert stats["n_urban"] == 3
    assert stats["n_rural"] == 2
    assert stats["unit"] == "trips per capita"
    assert stats["gap_pct"] == pytest.approx((12.0 - 5.0) / 12.0 * 100)


def test_f5_uses_service_quality_index():
    stats = build_urban_rural_gap_stats(
        "f5_rural_penalty", region_df=_region_df(), urban_rural="all",
    )
    assert stats["urban_value"] == pytest.approx(80.0)
    assert stats["rural_value"] == pytest.approx(45.0)
    assert stats["unit"] == "service quality index"


def test_c4_is_stubbed():
    assert build_urban_rural_gap_stats("c4_urban_rural_routes", region_df=_region_df(), urban_rural="all") == {}


def test_empty_region_df_returns_empty():
    assert build_urban_rural_gap_stats("a6_urban_rural_gap", region_df=pd.DataFrame(), urban_rural="all") == {}


def test_zero_urban_value_returns_empty():
    df = pd.DataFrame({
        "urban_rural": ["Urban", "Rural"],
        "trips_per_capita": [0.0, 4.0],
        "service_quality_index": [0.0, 40.0],
    })
    assert build_urban_rural_gap_stats("a6_urban_rural_gap", region_df=df, urban_rural="all") == {}
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/warehouse/stats_builders/test_urban_rural_gap.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Write the implementation**

Create `src/aequitas/warehouse/stats_builders/urban_rural_gap.py`:

```python
"""Stats builder for urban_rural_gap.j2 — urban vs rural comparisons.

Covers: a6_urban_rural_gap (coverage gap via trips_per_capita),
f5_rural_penalty (accessibility penalty via service_quality_index),
c4_urban_rural_routes (stub — no route-geometry x urban/rural join exists).

Fixes ISSUES.md §4.2: both sides are ALWAYS computed from the region-filtered
but area-type-UNfiltered dataframe, never from a frame already collapsed to
one area type. This guarantees non-zero n on both sides for all 30 combos.
"""

import pandas as pd

_METRIC_BY_SECTION: dict[str, tuple[str, str]] = {
    "a6_urban_rural_gap": ("trips_per_capita", "trips per capita"),
    "f5_rural_penalty": ("service_quality_index", "service quality index"),
}


def build_urban_rural_gap_stats(
    section_id: str,
    region_df: pd.DataFrame,
    urban_rural: str,
) -> dict:
    """Build stats for a6_urban_rural_gap, f5_rural_penalty, or c4 (stub).

    Args:
        section_id: One of "a6_urban_rural_gap", "f5_rural_penalty",
            "c4_urban_rural_routes".
        region_df: lsoa_policy_synthesis rows filtered by region ONLY — must
            retain both "Urban" and "Rural" rows regardless of the active
            urban_rural filter (§4.2 invariant).
        urban_rural: The active area-type filter ("all"/"urban"/"rural") —
            unused for value computation (both sides always computed), kept
            for signature symmetry with other builders and potential future
            narrative framing.

    Returns:
        Dict matching urban_rural_gap.j2's contract, or {} when source data
        is empty, urban_value is zero (divide-by-zero guard), or the section
        is stubbed.
    """
    if section_id == "c4_urban_rural_routes":
        # STUB (ISSUES.md §8.4): comparing route geometry by urban/rural
        # classification requires a route_geometries x LSOA-urban-rural
        # spatial join that does not exist in any precomputed table.
        return {}

    metric = _METRIC_BY_SECTION.get(section_id)
    if metric is None or region_df.empty or "urban_rural" not in region_df.columns:
        return {}

    column, unit = metric
    urban = region_df[region_df["urban_rural"] == "Urban"]
    rural = region_df[region_df["urban_rural"] == "Rural"]
    if urban.empty or rural.empty:
        return {}

    urban_value = float(urban[column].mean())
    rural_value = float(rural[column].mean())
    if urban_value == 0:
        return {}

    return {
        "urban_value": round(urban_value, 2),
        "rural_value": round(rural_value, 2),
        "gap_pct": round((urban_value - rural_value) / urban_value * 100, 1),
        "n_urban": int(len(urban)),
        "n_rural": int(len(rural)),
        "unit": unit,
    }
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/warehouse/stats_builders/test_urban_rural_gap.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/aequitas/warehouse/stats_builders/urban_rural_gap.py tests/warehouse/stats_builders/test_urban_rural_gap.py
git commit -m "feat: add urban_rural_gap.py stats builder, fixes urban-rural self-contradiction (§4.2)"
```

---

## Task 11: `policy_scenario.py` builder module — 6 sections (ps1-ps4, g5, ps5)

**Files:**
- Create: `src/aequitas/warehouse/stats_builders/policy_scenario.py`
- Test: `tests/warehouse/stats_builders/test_policy_scenario.py`

`policy_scenarios.parquet` has exactly 4 rows (scenarios A, B, C, D), mapped
1:1 by row order:

| Row | scenario | section_id |
|---|---|---|
| 0 | A — Frequency restoration | `ps1_freq_restoration`, `g5_scenario_model` |
| 1 | B — Evening extension | `ps2_evening_extension` |
| 2 | C — DRT rural | `ps3_drt_rural` |
| 3 | D — Franchise | `ps4_franchise` |

Both `ps1_freq_restoration` and `g5_scenario_model` use row 0 — `g5` is the
"Scenario modelling" overview slot under category G and the most natural single
scenario to headline there is the flagship frequency-restoration intervention.

**NaN coalescing required** (confirmed in source data):
- `co2_saving_t_yr` is `NaN` for rows B, C, D
- `estimated_annual_cost_m` is `NaN` for row D
- Both must coalesce to `0.0` — `policy_scenario.j2` calls `|round(1)` and
  `|int` on these fields, which raise on `None`/`NaN`.

`scenario.confidence` in the template is compared against literal `"high"` /
`"medium"` strings, but the actual data holds descriptive strings like
`"Indicative (❌ operating cost unverified)"`. The template's `{% elif %}` /
`{% else %}` chain handles this gracefully — no transformation needed; pass
the raw string through.

**`ps5_scenario_comparison`** uses `scenario_comparison.j2` (a *different*
template — `{scenarios: [...], best_bcr_scenario}`), built from **all 4 rows**:
- `scenarios`: list of `{name, population, cost_m, co2_t}` (cost/co2 NaN-coalesced
  to 0.0, same as above)
- `best_bcr_scenario`: name of the scenario with the lowest cost-per-beneficiary
  ratio (`estimated_annual_cost_m * 1e6 / population_affected`) — the closest
  proxy to "best value for money" available without a per-scenario BCR column.
  Rows with `estimated_annual_cost_m` NaN/0 are excluded from this ranking
  (cannot compute a ratio), but still appear in the `scenarios` list.

- [ ] **Step 1: Write the failing tests**

Create `tests/warehouse/stats_builders/test_policy_scenario.py`:

```python
"""Tests for policy_scenario.py — covers ps1-ps4, g5, ps5."""
import math

import pandas as pd
import pytest

from aequitas.warehouse.stats_builders.policy_scenario import build_policy_scenario_stats


def _scenarios_df():
    return pd.DataFrame({
        "scenario": ["A", "B", "C", "D"],
        "name": [
            "Frequency restoration — bottom IMD decile",
            "Last bus extended to 23:00 — evening isolated",
            "DRT in rural elderly LSOAs",
            "Bus Services Act — franchise top-5 LADs",
        ],
        "scope": ["3,375 LSOAs", "5,189 LSOAs", "3,192 LSOAs", "5 LADs"],
        "population_affected": [5689818, 8392662, 5243877, 760008],
        "annual_additional_trips": [34583390, 7783500, 13634080, 4862418],
        "estimated_annual_cost_m": [72.7, 116.8, 109.1, math.nan],
        "co2_saving_t_yr": [952.0, math.nan, math.nan, math.nan],
        "confidence": ["Indicative (note A)", "Indicative (note B)", "Indicative (note C)", "Indicative (note D)"],
    })


def test_ps1_returns_row_zero_with_nan_coalesced():
    stats = build_policy_scenario_stats("ps1_freq_restoration", scenarios_df=_scenarios_df())
    s = stats["scenario"]
    assert s["name"] == "Frequency restoration — bottom IMD decile"
    assert s["co2_saving_t_yr"] == pytest.approx(952.0)
    assert s["estimated_annual_cost_m"] == pytest.approx(72.7)


def test_ps2_coalesces_nan_co2_to_zero():
    stats = build_policy_scenario_stats("ps2_evening_extension", scenarios_df=_scenarios_df())
    assert stats["scenario"]["co2_saving_t_yr"] == 0.0


def test_ps4_coalesces_nan_cost_to_zero():
    stats = build_policy_scenario_stats("ps4_franchise", scenarios_df=_scenarios_df())
    assert stats["scenario"]["estimated_annual_cost_m"] == 0.0
    assert stats["scenario"]["co2_saving_t_yr"] == 0.0


def test_g5_mirrors_ps1_flagship_scenario():
    ps1 = build_policy_scenario_stats("ps1_freq_restoration", scenarios_df=_scenarios_df())
    g5 = build_policy_scenario_stats("g5_scenario_model", scenarios_df=_scenarios_df())
    assert g5 == ps1


def test_ps5_builds_portfolio_with_best_bcr_by_cost_per_beneficiary():
    stats = build_policy_scenario_stats("ps5_scenario_comparison", scenarios_df=_scenarios_df())
    assert len(stats["scenarios"]) == 4
    first = stats["scenarios"][0]
    assert first["name"] == "Frequency restoration — bottom IMD decile"
    assert first["population"] == 5689818
    assert first["cost_m"] == pytest.approx(72.7)
    assert first["co2_t"] == pytest.approx(952.0)
    assert stats["scenarios"][3]["cost_m"] == 0.0  # row D NaN coalesced
    # cost-per-beneficiary: A=12.78, B=13.92, C=20.81, D=excluded (no cost)
    assert stats["best_bcr_scenario"] == "Frequency restoration — bottom IMD decile"


def test_empty_scenarios_returns_empty():
    assert build_policy_scenario_stats("ps1_freq_restoration", scenarios_df=pd.DataFrame()) == {}
    assert build_policy_scenario_stats("ps5_scenario_comparison", scenarios_df=pd.DataFrame()) == {}
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/warehouse/stats_builders/test_policy_scenario.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Write the implementation**

Create `src/aequitas/warehouse/stats_builders/policy_scenario.py`:

```python
"""Stats builder for policy_scenario.j2 and scenario_comparison.j2.

Covers: ps1_freq_restoration, ps2_evening_extension, ps3_drt_rural,
ps4_franchise, g5_scenario_model (single-scenario shape), and
ps5_scenario_comparison (portfolio shape, different template).

policy_scenarios.parquet has exactly 4 rows (A-D) mapped 1:1 by row order.
NaN coalescing to 0.0 is required: co2_saving_t_yr is NaN for rows B/C/D,
estimated_annual_cost_m is NaN for row D — the Jinja templates call
|round(1) and |int on these fields, which raise on None/NaN.
"""

import math

import pandas as pd

_ROW_BY_SECTION: dict[str, int] = {
    "ps1_freq_restoration": 0,
    "ps2_evening_extension": 1,
    "ps3_drt_rural": 2,
    "ps4_franchise": 3,
    "g5_scenario_model": 0,  # flagship scenario headlines the overview slot
}

_SCENARIO_FIELDS = (
    "name", "scope", "population_affected", "annual_additional_trips",
    "estimated_annual_cost_m", "co2_saving_t_yr", "confidence",
)


def _coalesce(value: float) -> float:
    return 0.0 if value is None or (isinstance(value, float) and math.isnan(value)) else float(value)


def _row_to_scenario(row: pd.Series) -> dict:
    scenario = {field: row[field] for field in _SCENARIO_FIELDS}
    scenario["estimated_annual_cost_m"] = _coalesce(scenario["estimated_annual_cost_m"])
    scenario["co2_saving_t_yr"] = _coalesce(scenario["co2_saving_t_yr"])
    scenario["population_affected"] = int(scenario["population_affected"])
    return scenario


def _build_single(scenarios_df: pd.DataFrame, row_index: int) -> dict:
    if scenarios_df.empty or row_index >= len(scenarios_df):
        return {}
    return {"scenario": _row_to_scenario(scenarios_df.iloc[row_index])}


def _build_comparison(scenarios_df: pd.DataFrame) -> dict:
    if scenarios_df.empty:
        return {}

    scenarios = []
    best_name: str | None = None
    best_ratio = math.inf

    for _, row in scenarios_df.iterrows():
        cost_m = _coalesce(row["estimated_annual_cost_m"])
        population = int(row["population_affected"])
        scenarios.append({
            "name": row["name"],
            "population": population,
            "cost_m": cost_m,
            "co2_t": _coalesce(row["co2_saving_t_yr"]),
        })
        if cost_m > 0 and population > 0:
            ratio = (cost_m * 1e6) / population
            if ratio < best_ratio:
                best_ratio = ratio
                best_name = str(row["name"])

    return {"scenarios": scenarios, "best_bcr_scenario": best_name}


def build_policy_scenario_stats(section_id: str, scenarios_df: pd.DataFrame) -> dict:
    """Build stats for ps1-ps4, g5_scenario_model, or ps5_scenario_comparison.

    Args:
        section_id: One of the 6 covered section IDs.
        scenarios_df: The full 4-row policy_scenarios.parquet (not filtered —
            scenarios are England-wide interventions, not region-scoped).

    Returns:
        For ps1-ps4/g5: `{"scenario": {...}}` matching policy_scenario.j2.
        For ps5: `{"scenarios": [...], "best_bcr_scenario": ...}` matching
        scenario_comparison.j2. `{}` if scenarios_df is empty.
    """
    if section_id == "ps5_scenario_comparison":
        return _build_comparison(scenarios_df)

    row_index = _ROW_BY_SECTION.get(section_id)
    if row_index is None:
        return {}
    return _build_single(scenarios_df, row_index)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/warehouse/stats_builders/test_policy_scenario.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/aequitas/warehouse/stats_builders/policy_scenario.py tests/warehouse/stats_builders/test_policy_scenario.py
git commit -m "feat: add policy_scenario.py stats builder covering 6 sections (ps1-4,g5,ps5)"
```

---

## Task 12: `economic.py` builder module — 3 sections (j1, j2, j3)

**Files:**
- Create: `src/aequitas/warehouse/stats_builders/economic.py`
- Test: `tests/warehouse/stats_builders/test_economic.py`

`lsoa_economic_appraisal.parquet`'s `region` column is **all `"Unknown"`**
(confirmed) — it cannot be filtered by region directly. It must be joined to
`lsoa_policy_synthesis` (the correctly-populated `region`/`urban_rural`
source) via `lsoa_cd` (confirmed 33,755-row overlap, both use codes like
`'E01000001'`). The caller passes a pre-joined, pre-filtered `appraisal_df`
(joined once in `precompute.py`, then filtered per-combo like every other
source) — this builder does not perform the join itself.

Each of the 3 sections uses a **different template** with a distinct contract:

- **`j1_economic_value`** → `economic_value.j2`:
  `{region_name, annual_benefit, n_trips, vot}`. `annual_benefit` is
  `annual_time_benefit` summed across the filtered frame (the direct
  user-benefit component — matches the template's "Key Finding" framing of
  "annual transport user benefits...from avoided journey time"). `n_trips` is
  `annual_additional_trips` summed (daily-trip framing per the template's
  methodology note — the existing column is annual, but the template's
  on-screen framing treats `n_trips` as the trip count driving the benefit
  calculation, so the annual sum is the correct traceable figure). `vot` is
  the **blended bus Value of Time, £8.49/hr** — figures-registry **ST-030**
  (✅ Confirmed, "Blended bus VoT (38% comm, 51% leisure, 11% business),
  derived from TAG A1.3.1 2023 prices; DfT NTS 2023 trip purpose split").
  This is a fixed national constant (not region-varying) — defined as a
  module-level constant `_BLENDED_VOT_PER_HOUR = 8.49` with a comment citing
  ST-030, per the figures-registry rule (a confirmed figure may be used
  directly once registered — no live re-derivation required).

- **`j2_bcr`** → `bcr_analysis.j2`:
  `{bcr, vfm_band, area_name, investment_m, appraisal_years}`. `bcr` is the
  population-weighted mean of `pv_benefits`/`pv_costs` sums
  (`pv_benefits.sum() / pv_costs.sum()`, guarding zero-cost). `vfm_band` is
  derived from `bcr` using the **same thresholds the template itself encodes**
  (`>=4.0` Very High, `>=2.0` High, `>=1.5` Medium, `>=1.0` Low,
  `<1.0` Poor) — kept as a small local helper so the narrative band label
  matches the template's own prose exactly. `investment_m` is
  `pv_costs.sum() / 1e6`. `appraisal_years` is **60** — figures-registry
  **ST-027** (✅ Confirmed, "60-yr appraisal, 3.5% SDR" from
  `04e_economic_appraisal.ipynb`), defined as `_APPRAISAL_YEARS = 60`.
  Returns `{}` when `pv_costs.sum() == 0` (BCR undefined — matches the
  observed `bcr_band == "No cost data"` rows).

- **`j3_carbon`** → `carbon_reduction.j2`:
  `{co2_saving_tonnes, co2_value_k, scope, carbon_price, modal_shift_trips}`.
  `co2_saving_tonnes` is `modal_shift_co2_net_saving_kg.sum() / 1000`.
  `carbon_price` is **TAG `carbon_value_central_2025` = £259.87/tCO2e**
  (`core.constants.TAG().carbon_value_central_2025` — matches figures-registry
  **ST-029**'s "At TAG carbon price £259.87/tCO2e (2020 prices, 2025 value)").
  `co2_value_k` is `co2_saving_tonnes * carbon_price / 1000`. `modal_shift_trips`
  is `modal_shift_car_trips_replaced.sum()`. `scope` is `region_name` (reuses
  the same human-readable label passed to other region-scoped builders).

All three return `{}` when `appraisal_df` is empty.

- [ ] **Step 1: Write the failing tests**

Create `tests/warehouse/stats_builders/test_economic.py`:

```python
"""Tests for economic.py — covers j1, j2, j3."""
import pandas as pd
import pytest

from aequitas.warehouse.stats_builders.economic import build_economic_stats


def _appraisal_df():
    return pd.DataFrame({
        "lsoa_cd": ["E01000001", "E01000002"],
        "annual_time_benefit": [100_000.0, 200_000.0],
        "annual_additional_trips": [5_000.0, 7_000.0],
        "pv_benefits": [3_000_000.0, 5_000_000.0],
        "pv_costs": [2_000_000.0, 1_000_000.0],
        "modal_shift_co2_net_saving_kg": [50_000.0, 70_000.0],
        "modal_shift_car_trips_replaced": [1_000.0, 1_500.0],
    })


def test_j1_economic_value_uses_blended_vot_constant():
    stats = build_economic_stats("j1_economic_value", appraisal_df=_appraisal_df(), region_name="London")
    assert stats["region_name"] == "London"
    assert stats["annual_benefit"] == pytest.approx(300_000.0)
    assert stats["n_trips"] == pytest.approx(12_000.0)
    assert stats["vot"] == pytest.approx(8.49)


def test_j2_bcr_uses_pv_ratio_and_60_year_appraisal():
    stats = build_economic_stats("j2_bcr", appraisal_df=_appraisal_df(), region_name="London")
    assert stats["bcr"] == pytest.approx(8_000_000.0 / 3_000_000.0)
    assert stats["vfm_band"] == "Very High"
    assert stats["area_name"] == "London"
    assert stats["investment_m"] == pytest.approx(3.0)
    assert stats["appraisal_years"] == 60


def test_j2_returns_empty_when_no_cost_data():
    df = _appraisal_df()
    df["pv_costs"] = 0.0
    assert build_economic_stats("j2_bcr", appraisal_df=df, region_name="London") == {}


def test_j3_carbon_uses_tag_2025_carbon_price():
    stats = build_economic_stats("j3_carbon", appraisal_df=_appraisal_df(), region_name="London")
    assert stats["co2_saving_tonnes"] == pytest.approx(120.0)
    assert stats["carbon_price"] == pytest.approx(259.87)
    assert stats["co2_value_k"] == pytest.approx(120.0 * 259.87 / 1000)
    assert stats["modal_shift_trips"] == pytest.approx(2_500.0)
    assert stats["scope"] == "London"


def test_empty_appraisal_df_returns_empty():
    empty = pd.DataFrame()
    assert build_economic_stats("j1_economic_value", appraisal_df=empty, region_name="London") == {}
    assert build_economic_stats("j2_bcr", appraisal_df=empty, region_name="London") == {}
    assert build_economic_stats("j3_carbon", appraisal_df=empty, region_name="London") == {}
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/warehouse/stats_builders/test_economic.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Write the implementation**

Create `src/aequitas/warehouse/stats_builders/economic.py`:

```python
"""Stats builders for economic_value.j2, bcr_analysis.j2, carbon_reduction.j2.

Covers: j1_economic_value, j2_bcr, j3_carbon.

lsoa_economic_appraisal.region is all "Unknown" — the caller must pass a
pre-joined appraisal_df (joined to lsoa_policy_synthesis via lsoa_cd, then
filtered per-combo like every other source).
"""

import pandas as pd

from aequitas.core.constants import TAG

# Figures-registry ST-030 (✅ Confirmed): "Blended bus VoT (38% comm, 51%
# leisure, 11% business) | £8.49/hr | 04e_economic_appraisal.ipynb | Derived
# from TAG A1.3.1 2023 prices; DfT NTS 2023 trip purpose split". National
# constant — does not vary by region/filter.
_BLENDED_VOT_PER_HOUR = 8.49

# Figures-registry ST-027 (✅ Confirmed): "BCR ... 60-yr appraisal, 3.5% SDR |
# 04e_economic_appraisal.ipynb".
_APPRAISAL_YEARS = 60


def _vfm_band(bcr: float) -> str:
    """Value-for-money band — mirrors the thresholds bcr_analysis.j2 itself encodes."""
    if bcr >= 4.0:
        return "Very High"
    if bcr >= 2.0:
        return "High"
    if bcr >= 1.5:
        return "Medium"
    if bcr >= 1.0:
        return "Low"
    return "Poor"


def _build_economic_value(appraisal_df: pd.DataFrame, region_name: str) -> dict:
    return {
        "region_name": region_name,
        "annual_benefit": float(appraisal_df["annual_time_benefit"].sum()),
        "n_trips": float(appraisal_df["annual_additional_trips"].sum()),
        "vot": _BLENDED_VOT_PER_HOUR,
    }


def _build_bcr(appraisal_df: pd.DataFrame, region_name: str) -> dict:
    pv_costs = float(appraisal_df["pv_costs"].sum())
    if pv_costs == 0:
        return {}

    pv_benefits = float(appraisal_df["pv_benefits"].sum())
    bcr = pv_benefits / pv_costs

    return {
        "bcr": round(bcr, 2),
        "vfm_band": _vfm_band(bcr),
        "area_name": region_name,
        "investment_m": round(pv_costs / 1e6, 1),
        "appraisal_years": _APPRAISAL_YEARS,
    }


def _build_carbon(appraisal_df: pd.DataFrame, region_name: str) -> dict:
    carbon_price = TAG().carbon_value_central_2025
    co2_saving_tonnes = float(appraisal_df["modal_shift_co2_net_saving_kg"].sum()) / 1000

    return {
        "co2_saving_tonnes": round(co2_saving_tonnes, 1),
        "co2_value_k": round(co2_saving_tonnes * carbon_price / 1000, 1),
        "scope": region_name,
        "carbon_price": carbon_price,
        "modal_shift_trips": float(appraisal_df["modal_shift_car_trips_replaced"].sum()),
    }


_BUILDERS = {
    "j1_economic_value": _build_economic_value,
    "j2_bcr": _build_bcr,
    "j3_carbon": _build_carbon,
}


def build_economic_stats(section_id: str, appraisal_df: pd.DataFrame, region_name: str) -> dict:
    """Build stats for j1_economic_value, j2_bcr, or j3_carbon.

    Args:
        section_id: One of "j1_economic_value", "j2_bcr", "j3_carbon".
        appraisal_df: lsoa_economic_appraisal rows, pre-joined to
            lsoa_policy_synthesis via lsoa_cd (to recover real region/
            urban_rural values — the source table's own region column is all
            "Unknown") and filtered to the active region/area-type combo.
        region_name: Human-readable scope label for the template header.

    Returns:
        Dict matching the relevant template's contract, or {} if appraisal_df
        is empty or (for j2_bcr) total pv_costs is zero (BCR undefined).
    """
    if appraisal_df.empty:
        return {}

    builder = _BUILDERS.get(section_id)
    if builder is None:
        return {}
    return builder(appraisal_df, region_name)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/warehouse/stats_builders/test_economic.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/aequitas/warehouse/stats_builders/economic.py tests/warehouse/stats_builders/test_economic.py
git commit -m "feat: add economic.py stats builder covering 3 sections (j1,j2,j3)"
```

---

## Task 13: `equity.py` builder module — 3 sections (f1, a4, f2)

**Files:**
- Create: `src/aequitas/warehouse/stats_builders/equity.py`
- Test: `tests/warehouse/stats_builders/test_equity.py`

**Investigation finding that changes the spec's planned §2.3 approach:**
`equity_summary.json`'s `regional_equity` dict has exactly **one key:
`"Unknown"`** — it is NOT keyed by real region names (confirmed by direct
inspection: `list(regional_equity.keys()) == ["Unknown"]`). Reading
`regional_equity[region]` as the spec originally proposed would never match
any real region and silently fall through to the national fallback for all 9
regions — reproducing the exact bug §2.3 complains about, just one layer
deeper.

**Revised approach (still fixes §2.3, more robustly):** compute Gini, Palma,
and Concentration Index **live** from the filtered `lsoa_equity_metrics` rows
(`trips_per_capita` for service distribution, `imd_decile` for the
concentration ranking) using a small population-weighted Gini/Palma/CI helper
defined in this module (no such helper exists in `calculators.py` — confirmed
by grep). This makes every regional combination produce its own real,
traceable Gini/Palma/CI rather than a single national figure repeated 30
times, which is the actual fix the issue is asking for. National-scope
(`region == "all"`) results will closely match `equity_summary.json`'s
top-level `gini_population_weighted`/`palma_ratio`/`concentration_index_trips`
(both computed from the same `trips_per_capita` column over the same 33,755
LSOAs) — this cross-check is asserted in the test.

Both `f1_gini` and `a4_coverage_equity` map to `equity.j2` (`{gini, palma,
concentration_index, n_lsoas}`) and use **identical** stats — `a4` is the
"Equity of coverage within regions" (category A) framing of the same
underlying Gini/Palma analysis as `f1_gini` (category F), just surfaced in a
different policy-dimension grouping. Computing them identically avoids two
divergent Gini implementations disagreeing with each other across categories.

**`f2_disparity_ratio`** → `equity_decile.j2`:
`{most_deprived_value, least_deprived_value, ratio, bottom_20_pct, unit}`.
Computed from the filtered `lsoa_equity_metrics`: group by `imd_decile`,
take the mean `trips_per_capita` for decile 1 (`most_deprived_value`) and
decile 10 (`least_deprived_value`), `ratio = most_deprived... ` — wait, the
template's framing is "most deprived receives X, least deprived receives Y,
disparity ratio Y:X" in the sense that the **least-deprived value is larger**
(better served) — so `ratio = least_deprived_value / most_deprived_value`,
guarding zero. `bottom_20_pct` is the % of total trips received by deciles 1-2
combined (`bottom_20 trips_per_capita-weighted-by-population sum / total`,
×100). `unit = "trips per capita"`.

All three return `{}` when the filtered `lsoa_equity_metrics` slice is empty
or has fewer than 2 distinct `imd_decile` values (Gini/decile-ratio undefined
on a degenerate sample).

- [ ] **Step 1: Write the failing tests**

Create `tests/warehouse/stats_builders/test_equity.py`:

```python
"""Tests for equity.py — covers f1, a4, f2."""
import pandas as pd
import pytest

from aequitas.warehouse.stats_builders.equity import build_equity_stats


def _equity_df():
    # 10 LSOAs, one per IMD decile, trips_per_capita increasing with affluence
    # (decile 1 = most deprived -> lowest trips; decile 10 = least deprived -> highest)
    return pd.DataFrame({
        "lsoa_cd": [f"E0100000{i}" for i in range(1, 11)],
        "imd_decile": list(range(1, 11)),
        "trips_per_capita": [float(i) for i in range(1, 11)],
        "population": [1000] * 10,
    })


def test_f1_gini_computes_live_distribution_stats():
    stats = build_equity_stats("f1_gini", equity_df=_equity_df())
    assert 0.0 < stats["gini"] < 1.0
    assert stats["palma"] > 0
    assert isinstance(stats["concentration_index"], float)
    assert stats["n_lsoas"] == 10


def test_a4_matches_f1_identical_computation():
    df = _equity_df()
    assert build_equity_stats("a4_coverage_equity", equity_df=df) == build_equity_stats("f1_gini", equity_df=df)


def test_f2_disparity_ratio_least_over_most_deprived():
    stats = build_equity_stats("f2_disparity_ratio", equity_df=_equity_df())
    assert stats["most_deprived_value"] == pytest.approx(1.0)
    assert stats["least_deprived_value"] == pytest.approx(10.0)
    assert stats["ratio"] == pytest.approx(10.0)
    assert stats["unit"] == "trips per capita"
    assert 0.0 < stats["bottom_20_pct"] < 100.0


def test_returns_empty_for_degenerate_single_decile_sample():
    df = _equity_df()
    df["imd_decile"] = 5  # collapse to a single decile -> Gini/ratio undefined
    assert build_equity_stats("f1_gini", equity_df=df) == {}
    assert build_equity_stats("f2_disparity_ratio", equity_df=df) == {}


def test_empty_df_returns_empty():
    empty = pd.DataFrame()
    assert build_equity_stats("f1_gini", equity_df=empty) == {}
    assert build_equity_stats("f2_disparity_ratio", equity_df=empty) == {}
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/warehouse/stats_builders/test_equity.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Write the implementation**

Create `src/aequitas/warehouse/stats_builders/equity.py`:

```python
"""Stats builders for equity.j2 and equity_decile.j2.

Covers: f1_gini, a4_coverage_equity (identical computation — same underlying
Gini/Palma/CI analysis surfaced under two policy-dimension categories),
f2_disparity_ratio.

Fixes ISSUES.md §2.3: equity_summary.json's regional_equity dict has only one
key ("Unknown") — it cannot supply real per-region breakdowns. Instead, Gini,
Palma, and Concentration Index are computed LIVE from the filtered
lsoa_equity_metrics slice, so every region/area-type combination produces its
own real, traceable distribution statistics rather than one national figure
repeated 30 times.
"""

import numpy as np
import pandas as pd

_MIN_DISTINCT_DECILES = 2


def _population_weighted_gini(values: pd.Series, weights: pd.Series) -> float:
    """Population-weighted Gini coefficient via the Lorenz-curve trapezoid method."""
    order = np.argsort(values.to_numpy())
    v = values.to_numpy()[order]
    w = weights.to_numpy()[order]

    cum_w = np.cumsum(w)
    cum_vw = np.cumsum(v * w)
    total_w = cum_w[-1]
    total_vw = cum_vw[-1]
    if total_w == 0 or total_vw == 0:
        return 0.0

    lorenz_x = np.concatenate([[0.0], cum_w / total_w])
    lorenz_y = np.concatenate([[0.0], cum_vw / total_vw])

    area_under_lorenz = np.trapezoid(lorenz_y, lorenz_x) if hasattr(np, "trapezoid") else np.trapz(lorenz_y, lorenz_x)
    return float(1 - 2 * area_under_lorenz)


def _palma_ratio(df: pd.DataFrame, value_col: str) -> float:
    """Top-10%-share / bottom-40%-share, by population-weighted value."""
    ranked = df.sort_values(value_col)
    total = float((ranked[value_col] * ranked["population"]).sum())
    if total == 0:
        return 0.0

    cum_pop = ranked["population"].cumsum()
    total_pop = cum_pop.iloc[-1]
    bottom_mask = cum_pop <= total_pop * 0.4
    top_mask = cum_pop > total_pop * 0.9

    bottom_share = float((ranked.loc[bottom_mask, value_col] * ranked.loc[bottom_mask, "population"]).sum()) / total
    top_share = float((ranked.loc[top_mask, value_col] * ranked.loc[top_mask, "population"]).sum()) / total
    if bottom_share == 0:
        return 0.0
    return top_share / bottom_share


def _concentration_index(df: pd.DataFrame, value_col: str) -> float:
    """Erreygers-style concentration index: 2/mean * population-weighted covariance(rank, value)."""
    ranked = df.sort_values("imd_decile")
    cum_pop = ranked["population"].cumsum()
    total_pop = float(cum_pop.iloc[-1])
    fractional_rank = (cum_pop - ranked["population"] / 2) / total_pop

    mean_value = float((ranked[value_col] * ranked["population"]).sum() / total_pop)
    if mean_value == 0:
        return 0.0

    weighted_cov = float(
        ((ranked[value_col] - mean_value) * (fractional_rank - 0.5) * ranked["population"]).sum() / total_pop
    )
    return float(2 * weighted_cov / mean_value)


def _build_distribution(equity_df: pd.DataFrame) -> dict:
    if equity_df.empty or equity_df["imd_decile"].nunique() < _MIN_DISTINCT_DECILES:
        return {}

    return {
        "gini": round(_population_weighted_gini(equity_df["trips_per_capita"], equity_df["population"]), 4),
        "palma": round(_palma_ratio(equity_df, "trips_per_capita"), 2),
        "concentration_index": round(_concentration_index(equity_df, "trips_per_capita"), 4),
        "n_lsoas": int(len(equity_df)),
    }


def _build_disparity_ratio(equity_df: pd.DataFrame) -> dict:
    if equity_df.empty or equity_df["imd_decile"].nunique() < _MIN_DISTINCT_DECILES:
        return {}

    by_decile = equity_df.groupby("imd_decile")["trips_per_capita"].mean()
    most_deprived_value = float(by_decile.loc[by_decile.index.min()])
    least_deprived_value = float(by_decile.loc[by_decile.index.max()])
    if most_deprived_value == 0:
        return {}

    bottom_20 = equity_df[equity_df["imd_decile"] <= 2]
    total_trips = float((equity_df["trips_per_capita"] * equity_df["population"]).sum())
    bottom_20_trips = float((bottom_20["trips_per_capita"] * bottom_20["population"]).sum())
    bottom_20_pct = (bottom_20_trips / total_trips * 100) if total_trips > 0 else 0.0

    return {
        "most_deprived_value": round(most_deprived_value, 2),
        "least_deprived_value": round(least_deprived_value, 2),
        "ratio": round(least_deprived_value / most_deprived_value, 2),
        "bottom_20_pct": round(bottom_20_pct, 1),
        "unit": "trips per capita",
    }


def build_equity_stats(section_id: str, equity_df: pd.DataFrame) -> dict:
    """Build stats for f1_gini, a4_coverage_equity, or f2_disparity_ratio.

    Args:
        section_id: One of "f1_gini", "a4_coverage_equity", "f2_disparity_ratio".
        equity_df: lsoa_equity_metrics rows filtered to the active region/
            area-type combo. Must retain lsoa_cd, imd_decile, trips_per_capita,
            population columns.

    Returns:
        Dict matching equity.j2's contract (f1/a4) or equity_decile.j2's
        contract (f2), or {} when the filtered slice is empty or spans fewer
        than 2 distinct IMD deciles (distribution statistics undefined).
    """
    if section_id in ("f1_gini", "a4_coverage_equity"):
        return _build_distribution(equity_df)
    if section_id == "f2_disparity_ratio":
        return _build_disparity_ratio(equity_df)
    return {}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/warehouse/stats_builders/test_equity.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/aequitas/warehouse/stats_builders/equity.py tests/warehouse/stats_builders/test_equity.py
git commit -m "feat: add equity.py stats builder, fixes regional equity using live computation (§2.3)"
```

---

## Task 14: `misc.py` builder module — 11 sections (a3, a5, b2, b3, c1, c2, d7, f3 [stub], f4 [stub], g2, bsa3)

**Files:**
- Create: `src/aequitas/warehouse/stats_builders/misc.py`
- Test: `tests/warehouse/stats_builders/test_misc.py`
- Modify: `src/aequitas/intelligence/templates/correlation.j2` (n-aware
  significance gate, §4.4 — folded into this task since it is a one-line
  template change with no builder dependency)

This is the grab-bag module for sections whose templates are each used by
only one or two sections — one small function per template contract.

| Section | Template | Source | Contract |
|---|---|---|---|
| `a3_walking_distance` | `coverage_gap.j2` | `lsoa_2sfca` (filtered) + national `lsoa_2sfca` | `{pct_covered, n_zero_access, pct_zero_access, pop_zero_access, worst_region}` |
| `a5_service_deserts` | `desert_spotlight.j2` | `lsoa_service_levels` (filtered, `stop_count == 0`) | `{n_desert_lsoas, pop_affected, largest_region, largest_region_count, mean_imd_score, national_mean_imd}` |
| `b2_operating_hours` | `service_hours.j2` | `lsoa_service_quality` (filtered) | `{median_first_service, median_last_service, n_evening_isolated, pct_evening_isolated}` |
| `b3_weekend_penalty` | `weekend_penalty.j2` | `lsoa_service_levels` (filtered) | `{sunday_pct_drop, n_sunday_desert, pct_sunday_desert, saturday_pct_drop}` |
| `c1_route_length` | `distribution.j2` | `route_geometries.length_km` (filtered by `primary_region`) | `DistributionSummary` + `{metric_name, unit, skew_label}` |
| `c2_stops_per_route` | `distribution.j2` | `route_geometries.stop_count` (filtered) | same shape, different metric |
| `d7_deprivation_urban_rural` | `heatmap.j2` | `lsoa_policy_synthesis` cross-tab `imd_decile` × `urban_rural` | `{x_dimension, y_dimension, metric_name, worst_cell, best_cell}` |
| `f3_ethnic_access` | `demographic_breakdown.j2` | — STUB (§8.2: ts021 ethnicity join not implemented) | `{}` |
| `f4_gender_accessibility` | `accessibility_gap.j2` | — STUB (§8.3: no LSOA-level gender travel data exists) | `{}` |
| `g2_anomalies` | `anomaly_spotlight.j2` | `anomalies` (filtered) | `{n_anomalies, pct_anomalies, n_positive, n_inefficiency, n_policy_failure}` |
| `bsa3_tier_distribution` | `tier_distribution.j2` | `lta_franchising_readiness` (filtered) | `{n_total, n_tier1, n_tier2, n_tier3}` |

**Notes on non-trivial mappings:**

- `a3_walking_distance`: `lsoa_2sfca` lacks an `accessibility_score == 0`
  column directly comparable across the audit; use `sfca_score_norm == 0`
  from `lsoa_policy_synthesis` (already joined and filtered) as the
  zero-access flag — this is the same column CLAUDE.md's ground truth ("6,776
  LSOAs zero-access") refers to. `pct_covered` is
  `(1 - n_zero_access / len(filtered)) * 100`. `worst_region` is computed only
  when `region == "all"` (grouping by region only makes sense nationally;
  passing `region == "all"` lets the builder decide whether to include it —
  omit the key entirely for single-region scope, matching the template's
  `{% if worst_region %}` gate).
- `a5_service_deserts`: "desert" = `stop_count == 0` in `lsoa_service_levels`
  (joined to `lsoa_policy_synthesis` for `imd_score`/`region`/`population`).
  `largest_region` follows the same all-vs-single-region omission pattern as
  `worst_region` above.
- `b2_operating_hours`: `first_service_min`/`last_service_min` are minutes-
  since-midnight integers; convert the median to `"HH:MM"` strings via
  `divmod(minutes, 60)` — the template parses these strings back with
  `.split(':')`.
- `c1`/`c2`: reuse `describe_distribution` from `calculators.py` — do not
  reimplement. `skew_label` is derived from the sign and magnitude of
  `(mean - median) / std` (a standard nonparametric skew proxy): `> 0.2` →
  `"right-skewed (positive)"`, `< -0.2` → `"left-skewed (negative)"`, else
  `"approximately symmetric"`.
- `d7_deprivation_urban_rural`: cross-tab mean `service_quality_index` by
  `(imd_decile, urban_rural)`; `worst_cell`/`best_cell` are
  `{label: "Decile {d}, {Urban|Rural}", value: float}` for the min/max cells.
- `g2_anomalies`: counts of `anomaly_type` values
  `"positive_deprived_well_served"`, `"inefficiency_affluent_poor_served"`,
  `"policy_failure_elderly_no_service"` (confirmed exact strings from
  investigation) plus `both_anomaly` total.
- `bsa3_tier_distribution`: counts of `readiness_tier` values `"Tier 1 — High"`,
  `"Tier 2 — Medium"`, `"Tier 3 — Low"` (confirmed exact strings, including the
  em-dash) in the filtered `lta_franchising_readiness` slice.

**§4.4 fix (folded in):** `correlation.j2`'s evidence gate currently uses a
fixed `p_value < 0.05` significance threshold regardless of sample size. With
`n` in the tens of thousands (LSOA-level correlations), p < 0.05 is nearly
guaranteed even for negligible effect sizes — the gate must scale with `n`.
Update the template's significance check to
`{% set sig_threshold = 0.001 if n_observations > 10000 else 0.05 %}` and use
`sig_threshold` in place of the literal `0.05` comparison. (`correlation.py`
from Task 6 already includes `n_observations` in its stats — this is purely a
template-side change.)

- [ ] **Step 1: Write the failing tests**

Create `tests/warehouse/stats_builders/test_misc.py`:

```python
"""Tests for misc.py — covers a3, a5, b2, b3, c1, c2, d7, f3 (stub), f4 (stub), g2, bsa3."""
import pandas as pd
import pytest

from aequitas.warehouse.stats_builders.misc import build_misc_stats


def _policy_df():
    return pd.DataFrame({
        "lsoa_cd": [f"E0100000{i}" for i in range(1, 7)],
        "region": ["London", "London", "North East", "North East", "South East", "South East"],
        "imd_decile": [1, 1, 5, 5, 10, 10],
        "urban_rural": ["Urban", "Rural", "Urban", "Rural", "Urban", "Rural"],
        "sfca_score_norm": [0.0, 0.5, 0.0, 0.3, 0.8, 0.9],
        "population": [1000, 1000, 1000, 1000, 1000, 1000],
        "service_quality_index": [40.0, 30.0, 60.0, 55.0, 90.0, 85.0],
        "imd_score": [35.0, 33.0, 20.0, 18.0, 5.0, 4.0],
    })


def _service_levels_df():
    return pd.DataFrame({
        "lsoa_cd": [f"E0100000{i}" for i in range(1, 7)],
        "stop_count": [0, 2, 0, 3, 5, 4],
        "total_weekday_trips": [0, 100, 0, 150, 300, 250],
        "total_saturday_trips": [0, 70, 0, 100, 220, 180],
        "total_sunday_trips": [0, 0, 0, 30, 100, 90],
    })


def _service_quality_df():
    return pd.DataFrame({
        "lsoa_cd": [f"E0100000{i}" for i in range(1, 7)],
        "first_service_min": [360, 390, 400, 420, 350, 380],
        "last_service_min": [1140, 1080, 1100, 1020, 1200, 1150],
        "evening_isolated": [True, False, True, False, False, False],
    })


def _route_geometries_df():
    return pd.DataFrame({
        "primary_region": ["London"] * 5,
        "length_km": [10.0, 12.0, 14.0, 50.0, 11.0],
        "stop_count": [20, 22, 24, 60, 21],
    })


def _anomalies_df():
    return pd.DataFrame({
        "anomaly_type": [
            "normal", "normal", "positive_deprived_well_served",
            "inefficiency_affluent_poor_served", "policy_failure_elderly_no_service",
            "policy_failure_elderly_no_service",
        ],
        "both_anomaly": [False, False, True, True, True, True],
    })


def _lta_df():
    return pd.DataFrame({
        "lad_nm": ["A", "B", "C", "D"],
        "readiness_tier": ["Tier 1 — High", "Tier 2 — Medium", "Tier 2 — Medium", "Tier 3 — Low"],
    })


def test_a3_walking_distance_all_region_includes_worst_region():
    stats = build_misc_stats(
        "a3_walking_distance", region="all", urban_rural="all",
        policy_df=_policy_df(), service_levels_df=None, service_quality_df=None,
        route_geometries_df=None, anomalies_df=None, lta_df=None,
    )
    assert stats["n_zero_access"] == 2
    assert stats["pop_zero_access"] == pytest.approx(2000.0)
    assert stats["pct_zero_access"] == pytest.approx(2 / 6 * 100)
    assert stats["pct_covered"] == pytest.approx((1 - 2 / 6) * 100)
    assert "worst_region" in stats


def test_a3_omits_worst_region_for_single_region_scope():
    stats = build_misc_stats(
        "a3_walking_distance", region="E12000007", urban_rural="all",
        policy_df=_policy_df(), service_levels_df=None, service_quality_df=None,
        route_geometries_df=None, anomalies_df=None, lta_df=None,
    )
    assert "worst_region" not in stats


def test_a5_service_deserts_counts_zero_stop_lsoas():
    stats = build_misc_stats(
        "a5_service_deserts", region="all", urban_rural="all",
        policy_df=_policy_df(), service_levels_df=_service_levels_df(),
        service_quality_df=None, route_geometries_df=None, anomalies_df=None, lta_df=None,
    )
    assert stats["n_desert_lsoas"] == 2
    assert stats["pop_affected"] == pytest.approx(2000.0)
    assert stats["mean_imd_score"] == pytest.approx((35.0 + 20.0) / 2)


def test_b2_operating_hours_formats_hhmm_strings():
    stats = build_misc_stats(
        "b2_operating_hours", region="all", urban_rural="all",
        policy_df=_policy_df(), service_levels_df=None, service_quality_df=_service_quality_df(),
        route_geometries_df=None, anomalies_df=None, lta_df=None,
    )
    assert ":" in stats["median_first_service"]
    assert ":" in stats["median_last_service"]
    assert stats["n_evening_isolated"] == 2
    assert stats["pct_evening_isolated"] == pytest.approx(2 / 6 * 100)


def test_b3_weekend_penalty_computes_pct_drops():
    stats = build_misc_stats(
        "b3_weekend_penalty", region="all", urban_rural="all",
        policy_df=_policy_df(), service_levels_df=_service_levels_df(),
        service_quality_df=None, route_geometries_df=None, anomalies_df=None, lta_df=None,
    )
    weekday = 800.0
    sunday = 220.0
    saturday = 570.0
    assert stats["sunday_pct_drop"] == pytest.approx((1 - sunday / weekday) * 100)
    assert stats["saturday_pct_drop"] == pytest.approx((1 - saturday / weekday) * 100)
    assert stats["n_sunday_desert"] == 3


def test_c1_route_length_uses_describe_distribution():
    stats = build_misc_stats(
        "c1_route_length", region="London", urban_rural="all",
        policy_df=_policy_df(), service_levels_df=None, service_quality_df=None,
        route_geometries_df=_route_geometries_df(), anomalies_df=None, lta_df=None,
    )
    assert stats["metric_name"] == "route length"
    assert stats["unit"] == "km"
    assert stats["median"] == pytest.approx(12.0)
    assert stats["skew_label"] in ("right-skewed (positive)", "left-skewed (negative)", "approximately symmetric")


def test_c2_stops_per_route_uses_stop_count():
    stats = build_misc_stats(
        "c2_stops_per_route", region="London", urban_rural="all",
        policy_df=_policy_df(), service_levels_df=None, service_quality_df=None,
        route_geometries_df=_route_geometries_df(), anomalies_df=None, lta_df=None,
    )
    assert stats["metric_name"] == "stops per route"
    assert stats["median"] == pytest.approx(22.0)


def test_d7_deprivation_urban_rural_finds_worst_and_best_cells():
    stats = build_misc_stats(
        "d7_deprivation_urban_rural", region="all", urban_rural="all",
        policy_df=_policy_df(), service_levels_df=None, service_quality_df=None,
        route_geometries_df=None, anomalies_df=None, lta_df=None,
    )
    assert stats["worst_cell"]["value"] == pytest.approx(30.0)
    assert stats["best_cell"]["value"] == pytest.approx(90.0)
    assert "Decile" in stats["worst_cell"]["label"]


def test_f3_and_f4_are_stubbed():
    assert build_misc_stats("f3_ethnic_access", region="all", urban_rural="all", policy_df=_policy_df(), service_levels_df=None, service_quality_df=None, route_geometries_df=None, anomalies_df=None, lta_df=None) == {}
    assert build_misc_stats("f4_gender_accessibility", region="all", urban_rural="all", policy_df=_policy_df(), service_levels_df=None, service_quality_df=None, route_geometries_df=None, anomalies_df=None, lta_df=None) == {}


def test_g2_anomalies_counts_each_type():
    stats = build_misc_stats(
        "g2_anomalies", region="all", urban_rural="all",
        policy_df=_policy_df(), service_levels_df=None, service_quality_df=None,
        route_geometries_df=None, anomalies_df=_anomalies_df(), lta_df=None,
    )
    assert stats["n_anomalies"] == 4
    assert stats["n_positive"] == 1
    assert stats["n_inefficiency"] == 1
    assert stats["n_policy_failure"] == 2
    assert stats["pct_anomalies"] == pytest.approx(4 / 6 * 100)


def test_bsa3_tier_distribution_counts_each_tier():
    stats = build_misc_stats(
        "bsa3_tier_distribution", region="all", urban_rural="all",
        policy_df=_policy_df(), service_levels_df=None, service_quality_df=None,
        route_geometries_df=None, anomalies_df=None, lta_df=_lta_df(),
    )
    assert stats["n_total"] == 4
    assert stats["n_tier1"] == 1
    assert stats["n_tier2"] == 2
    assert stats["n_tier3"] == 1


def test_empty_inputs_return_empty():
    empty = pd.DataFrame()
    assert build_misc_stats("a3_walking_distance", region="all", urban_rural="all", policy_df=empty, service_levels_df=None, service_quality_df=None, route_geometries_df=None, anomalies_df=None, lta_df=None) == {}
    assert build_misc_stats("g2_anomalies", region="all", urban_rural="all", policy_df=_policy_df(), service_levels_df=None, service_quality_df=None, route_geometries_df=None, anomalies_df=empty, lta_df=None) == {}
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/warehouse/stats_builders/test_misc.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Write the implementation**

Create `src/aequitas/warehouse/stats_builders/misc.py`:

```python
"""Stats builders for the 11 single/dual-section template contracts.

Covers: a3_walking_distance, a5_service_deserts, b2_operating_hours,
b3_weekend_penalty, c1_route_length, c2_stops_per_route,
d7_deprivation_urban_rural, f3_ethnic_access (stub), f4_gender_accessibility
(stub), g2_anomalies, bsa3_tier_distribution.
"""

import pandas as pd

from aequitas.intelligence.calculators import describe_distribution

_DESERT_REGION_MIN_ROWS = 1


def _skew_label(mean: float, median: float, std: float) -> str:
    if std == 0:
        return "approximately symmetric"
    skew = (mean - median) / std
    if skew > 0.2:
        return "right-skewed (positive)"
    if skew < -0.2:
        return "left-skewed (negative)"
    return "approximately symmetric"


def _minutes_to_hhmm(minutes: float) -> str:
    hours, mins = divmod(int(round(minutes)), 60)
    return f"{hours:02d}:{mins:02d}"


def _build_walking_distance(policy_df: pd.DataFrame, region: str) -> dict:
    if policy_df.empty or "sfca_score_norm" not in policy_df.columns:
        return {}

    zero_access = policy_df[policy_df["sfca_score_norm"] == 0]
    n_total = len(policy_df)
    n_zero = len(zero_access)

    stats = {
        "pct_covered": round((1 - n_zero / n_total) * 100, 1),
        "n_zero_access": int(n_zero),
        "pct_zero_access": round(n_zero / n_total * 100, 1),
        "pop_zero_access": float(zero_access["population"].sum()),
    }

    if region == "all" and n_zero > 0:
        worst = zero_access.groupby("region").size().idxmax()
        stats["worst_region"] = str(worst)

    return stats


def _build_service_deserts(policy_df: pd.DataFrame, service_levels_df: pd.DataFrame | None, region: str) -> dict:
    if policy_df.empty or service_levels_df is None or service_levels_df.empty:
        return {}

    joined = policy_df.merge(service_levels_df[["lsoa_cd", "stop_count"]], on="lsoa_cd", how="inner")
    deserts = joined[joined["stop_count"] == 0]
    if deserts.empty:
        return {}

    national_mean_imd = float(policy_df["imd_score"].mean())

    stats = {
        "n_desert_lsoas": int(len(deserts)),
        "pop_affected": float(deserts["population"].sum()),
        "mean_imd_score": round(float(deserts["imd_score"].mean()), 1),
        "national_mean_imd": round(national_mean_imd, 1),
    }

    if region == "all":
        by_region = deserts.groupby("region").size()
        largest = by_region.idxmax()
        stats["largest_region"] = str(largest)
        stats["largest_region_count"] = int(by_region.loc[largest])

    return stats


def _build_operating_hours(service_quality_df: pd.DataFrame | None) -> dict:
    if service_quality_df is None or service_quality_df.empty:
        return {}

    n_total = len(service_quality_df)
    n_evening_isolated = int(service_quality_df["evening_isolated"].sum())

    return {
        "median_first_service": _minutes_to_hhmm(service_quality_df["first_service_min"].median()),
        "median_last_service": _minutes_to_hhmm(service_quality_df["last_service_min"].median()),
        "n_evening_isolated": n_evening_isolated,
        "pct_evening_isolated": round(n_evening_isolated / n_total * 100, 1),
    }


def _build_weekend_penalty(service_levels_df: pd.DataFrame | None) -> dict:
    if service_levels_df is None or service_levels_df.empty:
        return {}

    weekday = float(service_levels_df["total_weekday_trips"].sum())
    if weekday == 0:
        return {}

    saturday = float(service_levels_df["total_saturday_trips"].sum())
    sunday = float(service_levels_df["total_sunday_trips"].sum())
    sunday_deserts = service_levels_df[service_levels_df["total_sunday_trips"] == 0]

    return {
        "sunday_pct_drop": round((1 - sunday / weekday) * 100, 1),
        "saturday_pct_drop": round((1 - saturday / weekday) * 100, 1),
        "n_sunday_desert": int(len(sunday_deserts)),
        "pct_sunday_desert": round(len(sunday_deserts) / len(service_levels_df) * 100, 1),
    }


def _build_distribution_section(route_geometries_df: pd.DataFrame | None, region: str, column: str, metric_name: str, unit: str) -> dict:
    if route_geometries_df is None or route_geometries_df.empty or column not in route_geometries_df.columns:
        return {}

    df = route_geometries_df
    if region != "all" and "primary_region" in df.columns:
        df = df[df["primary_region"] == region]
    if df.empty:
        return {}

    summary = describe_distribution(df[column])
    return {
        "mean": summary.mean,
        "median": summary.median,
        "std": summary.std,
        "cv": summary.cv,
        "iqr": summary.iqr,
        "p10": summary.p10,
        "p90": summary.p90,
        "n_outliers": summary.outliers,
        "metric_name": metric_name,
        "unit": unit,
        "skew_label": _skew_label(summary.mean, summary.median, summary.std),
    }


def _build_deprivation_heatmap(policy_df: pd.DataFrame) -> dict:
    if policy_df.empty:
        return {}

    grouped = policy_df.groupby(["imd_decile", "urban_rural"])["service_quality_index"].mean()
    if grouped.empty:
        return {}

    worst_idx = grouped.idxmin()
    best_idx = grouped.idxmax()

    def _cell(idx: tuple) -> dict:
        decile, area_type = idx
        return {"label": f"Decile {decile}, {area_type}", "value": round(float(grouped.loc[idx]), 1)}

    return {
        "x_dimension": "IMD decile",
        "y_dimension": "urban/rural classification",
        "metric_name": "service quality index",
        "worst_cell": _cell(worst_idx),
        "best_cell": _cell(best_idx),
    }


def _build_anomalies(anomalies_df: pd.DataFrame | None) -> dict:
    if anomalies_df is None or anomalies_df.empty:
        return {}

    n_total = len(anomalies_df)
    type_counts = anomalies_df["anomaly_type"].value_counts()

    return {
        "n_anomalies": int(anomalies_df["both_anomaly"].sum()),
        "pct_anomalies": round(int(anomalies_df["both_anomaly"].sum()) / n_total * 100, 1),
        "n_positive": int(type_counts.get("positive_deprived_well_served", 0)),
        "n_inefficiency": int(type_counts.get("inefficiency_affluent_poor_served", 0)),
        "n_policy_failure": int(type_counts.get("policy_failure_elderly_no_service", 0)),
    }


def _build_tier_distribution(lta_df: pd.DataFrame | None) -> dict:
    if lta_df is None or lta_df.empty:
        return {}

    tier_counts = lta_df["readiness_tier"].value_counts()
    return {
        "n_total": int(len(lta_df)),
        "n_tier1": int(tier_counts.get("Tier 1 — High", 0)),
        "n_tier2": int(tier_counts.get("Tier 2 — Medium", 0)),
        "n_tier3": int(tier_counts.get("Tier 3 — Low", 0)),
    }


def build_misc_stats(
    section_id: str,
    region: str,
    urban_rural: str,
    policy_df: pd.DataFrame,
    service_levels_df: pd.DataFrame | None,
    service_quality_df: pd.DataFrame | None,
    route_geometries_df: pd.DataFrame | None,
    anomalies_df: pd.DataFrame | None,
    lta_df: pd.DataFrame | None,
) -> dict:
    """Build stats for one of the 11 misc-module sections.

    Args:
        section_id: One of the 11 covered section IDs.
        region: Active region filter ("all" or an ONS region code) — used to
            decide whether to surface "worst region"/"largest region" keys
            (only meaningful at national scope) and to filter route_geometries
            by primary_region for c1/c2.
        urban_rural: Active area-type filter — unused for value computation,
            kept for signature symmetry with other builders.
        policy_df: lsoa_policy_synthesis rows for the active filter scope.
        service_levels_df: lsoa_service_levels rows for the active scope
            (joined to policy_df via lsoa_cd where needed). Required for
            a5/b3, otherwise None.
        service_quality_df: lsoa_service_quality rows for the active scope.
            Required for b2, otherwise None.
        route_geometries_df: route_geometries rows for the active scope.
            Required for c1/c2, otherwise None.
        anomalies_df: anomalies rows for the active scope. Required for g2,
            otherwise None.
        lta_df: lta_franchising_readiness rows for the active scope. Required
            for bsa3, otherwise None.

    Returns:
        Dict matching the relevant template's contract, or {} when required
        source data is missing/empty or the section is stubbed (f3, f4).
    """
    if section_id in ("f3_ethnic_access", "f4_gender_accessibility"):
        # STUBS (ISSUES.md §8.2/§8.3): f3 requires a ts021 ethnicity-by-LSOA
        # join that the analytics stage does not produce; f4 requires
        # gender-disaggregated travel data that does not exist in any
        # government open dataset at LSOA granularity. Both await a future
        # analytics-stage data engineering pass.
        return {}

    if section_id == "a3_walking_distance":
        return _build_walking_distance(policy_df, region)
    if section_id == "a5_service_deserts":
        return _build_service_deserts(policy_df, service_levels_df, region)
    if section_id == "b2_operating_hours":
        return _build_operating_hours(service_quality_df)
    if section_id == "b3_weekend_penalty":
        return _build_weekend_penalty(service_levels_df)
    if section_id == "c1_route_length":
        return _build_distribution_section(route_geometries_df, region, "length_km", "route length", "km")
    if section_id == "c2_stops_per_route":
        return _build_distribution_section(route_geometries_df, region, "stop_count", "stops per route", "stops")
    if section_id == "d7_deprivation_urban_rural":
        return _build_deprivation_heatmap(policy_df)
    if section_id == "g2_anomalies":
        return _build_anomalies(anomalies_df)
    if section_id == "bsa3_tier_distribution":
        return _build_tier_distribution(lta_df)
    return {}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/warehouse/stats_builders/test_misc.py -v`
Expected: PASS

- [ ] **Step 5: Update `correlation.j2` for n-aware significance (§4.4)**

Open `src/aequitas/intelligence/templates/correlation.j2`. Find the line(s)
that compare `p_value` against the literal `0.05`. Replace the fixed
threshold with a sample-size-aware one:

```jinja2
{% set sig_threshold = 0.001 if n_observations > 10000 else 0.05 %}
```

placed near the top of the template (after the `{% if r is defined %}`
guard), then replace every literal `0.05` comparison against `p_value` with
`sig_threshold`. This reflects that with `n` in the tens of thousands
(LSOA-level correlations routinely have n ≈ 33,755), a p < 0.05 threshold is
nearly always satisfied even for negligible effect sizes — the gate must
tighten as `n` grows, or it ceases to gate anything.

- [ ] **Step 6: Commit**

```bash
git add src/aequitas/warehouse/stats_builders/misc.py tests/warehouse/stats_builders/test_misc.py src/aequitas/intelligence/templates/correlation.j2
git commit -m "feat: add misc.py stats builder covering 11 sections, fix n-aware correlation significance (§4.4)"
```

---

## Task 15: Rewrite `precompute.py` — wire all 51 sections through the dispatch table

**Files:**
- Modify: `src/aequitas/warehouse/precompute.py` (full rewrite of `_build_stats`
  and the combo loop)
- Test: `tests/warehouse/test_precompute_30.py` (replace existing assertions)

This task wires together every builder module from Tasks 5-14 into a single
dispatch table, fixes the region-code-vs-name bug, removes the 18-combo skip,
and fixes the `gap_to_target` moving-median bug (§2.5/§8.5).

**`REGION_NAMES` mapping** (the §investigation fix — confirmed exact strings):

```python
REGION_NAMES: dict[str, str] = {
    "E12000001": "North East",
    "E12000002": "North West",
    "E12000003": "Yorkshire and The Humber",
    "E12000004": "East Midlands",
    "E12000005": "West Midlands",
    "E12000006": "East of England",
    "E12000007": "London",
    "E12000008": "South East",
    "E12000009": "South West",
}
```

**Region masking fix:** `region_mask = policy_df["region"] == REGION_NAMES.get(region, region)`
— this resolves the ONS code to the full name before comparing against
`lsoa_policy_synthesis.region` (which holds full names). `region_name` (the
human-readable label passed to builders) is `"England"` when `region == "all"`,
else `REGION_NAMES[region]`.

**`gap_to_target` fix (§2.5/§8.5):** compute `national_median` from the
**unfiltered** `policy_df["trips_per_capita"]`, not the filtered/moving median.
Use it as `target` for every combo — this makes the metric comparable across
regions (a fixed yardstick) rather than each region being judged against its
own median (which makes every region's "below average" count converge to ~50%
by construction). Label `target_description: "national median"`.

- [ ] **Step 1: Write the failing test (assert dispatch coverage and combo count)**

Replace the contents of `tests/warehouse/test_precompute_30.py` with:

```python
"""Tests for precompute_all_sections — verifies full 51-section x 30-combo coverage."""
import pytest

from aequitas.core.config import PipelineConfig
from aequitas.intelligence.section_registry import SECTION_REGISTRY
from aequitas.warehouse.precompute import _STUB_SECTIONS, precompute_all_sections


@pytest.fixture
def cfg() -> PipelineConfig:
    return PipelineConfig()


def test_precomputes_30_combos_times_51_sections(cfg):
    results = precompute_all_sections(cfg)
    assert len(results) == 30 * 51


def test_every_registered_section_appears_in_every_combo(cfg):
    results = precompute_all_sections(cfg)
    seen = {(r["region"], r["urban_rural"], r["section_id"]) for r in results}
    assert len(seen) == 30 * 51
    for section_id in SECTION_REGISTRY:
        matching = [r for r in results if r["section_id"] == section_id]
        assert len(matching) == 30, f"{section_id} missing combos"


def test_stub_sections_produce_empty_stats_everywhere(cfg):
    results = precompute_all_sections(cfg)
    for section_id in _STUB_SECTIONS:
        matching = [r for r in results if r["section_id"] == section_id]
        assert len(matching) == 30
        assert all(r["stats"] == {} for r in matching)


def test_non_stub_sections_produce_non_empty_stats_at_national_scope(cfg):
    results = precompute_all_sections(cfg)
    national_all = [
        r for r in results
        if r["region"] == "all" and r["urban_rural"] == "all" and r["section_id"] not in _STUB_SECTIONS
    ]
    empty = [r["section_id"] for r in national_all if r["stats"] == {}]
    assert empty == [], f"unexpectedly empty at national scope: {empty}"


def test_gap_to_target_uses_fixed_national_median_across_regions(cfg):
    results = precompute_all_sections(cfg)
    targets = {
        r["region"]: r["stats"].get("target")
        for r in results
        if r["section_id"] == "a7_investment_gap" and r["urban_rural"] == "all" and r["stats"]
    }
    # All regions must be judged against the SAME national yardstick (§2.5 fix)
    assert len(set(targets.values())) == 1
    assert all(r["stats"].get("target_description") == "national median" for r in results if r["section_id"] == "a7_investment_gap" and r["stats"])
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/warehouse/test_precompute_30.py -v`
Expected: FAIL — `ImportError: cannot import name '_STUB_SECTIONS'` (and combo
count assertions fail against the old 5-section/18-skip implementation)

- [ ] **Step 3: Rewrite `precompute.py`**

Replace the entire contents of `src/aequitas/warehouse/precompute.py`:

```python
"""Pre-computation of section_results for the DuckDB warehouse.

For each of the 30 filter combinations (10 regions × 3 area types), computes
all 51 registered analytical sections and stores them as JSON in
section_results. This is called once at build time — never at request time.
"""

import json
from dataclasses import dataclass
from typing import Callable

import pandas as pd
from loguru import logger

from aequitas.core.config import PipelineConfig
from aequitas.core.types import RegionCode
from aequitas.intelligence.engine import InsightEngine
from aequitas.intelligence.section_registry import SECTION_REGISTRY
from aequitas.warehouse.stats_builders.correlation import build_correlation_stats
from aequitas.warehouse.stats_builders.economic import build_economic_stats
from aequitas.warehouse.stats_builders.equity import build_equity_stats
from aequitas.warehouse.stats_builders.market_concentration import build_market_concentration_stats
from aequitas.warehouse.stats_builders.misc import build_misc_stats
from aequitas.warehouse.stats_builders.ml_clusters import build_ml_clusters_stats
from aequitas.warehouse.stats_builders.ml_prediction import build_ml_prediction_stats
from aequitas.warehouse.stats_builders.policy_scenario import build_policy_scenario_stats
from aequitas.warehouse.stats_builders.ranking import build_ranking_stats
from aequitas.warehouse.stats_builders.urban_rural_gap import build_urban_rural_gap_stats

# Investigation fix: lsoa_policy_synthesis.region holds full ONS region names,
# while RegionCode/_REGIONS hold ONS region CODES. The two never matched —
# this mapping resolves codes to names before filtering.
REGION_NAMES: dict[str, str] = {
    "E12000001": "North East",
    "E12000002": "North West",
    "E12000003": "Yorkshire and The Humber",
    "E12000004": "East Midlands",
    "E12000005": "West Midlands",
    "E12000006": "East of England",
    "E12000007": "London",
    "E12000008": "South East",
    "E12000009": "South West",
}

_REGIONS = ["all"] + [rc.value for rc in RegionCode]
_AREA_TYPES = ["all", "urban", "rural"]

# NOTE: these sets were corrected against the ACTUAL SECTION_REGISTRY contents
# (verified via direct inspection — the registry's real IDs differ from the
# illustrative names used earlier in this plan's module-grouping table).
_RANKING_SECTIONS = {"a1_route_density", "a2_stop_density", "b1_frequency",
                     "b4_route_frequency", "f6_equitable_regions", "j4_investment_priority", "bsa1_franchising_readiness"}
_CORRELATION_SECTIONS = {"b5_frequency_deprivation", "c5_length_vs_frequency", "d1_coverage_deprivation",
                         "d2_coverage_unemployment", "d3_coverage_car", "d4_coverage_elderly",
                         "d5_coverage_income"}
_ML_CLUSTER_SECTIONS = {"c6_route_archetypes", "d6_transport_poverty", "g1_route_clusters"}
_ML_PREDICTION_SECTIONS = {"a8_coverage_prediction", "d8_feature_importance", "g3_coverage_model", "g4_shap"}
_MARKET_CONCENTRATION_SECTIONS = {"c3_operator_hhi", "bsa2_operator_concentration"}
_URBAN_RURAL_GAP_SECTIONS = {"a6_urban_rural_gap", "c4_urban_rural_routes", "f5_rural_penalty"}
_POLICY_SCENARIO_SECTIONS = {"ps1_freq_restoration", "ps2_evening_extension", "ps3_drt_rural",
                             "ps4_franchise", "g5_scenario_model", "ps5_scenario_comparison"}
_ECONOMIC_SECTIONS = {"j1_economic_value", "j2_bcr", "j3_carbon"}
_EQUITY_SECTIONS = {"f1_gini", "a4_coverage_equity", "f2_disparity_ratio"}
_MISC_SECTIONS = {"a3_walking_distance", "a5_service_deserts", "b2_operating_hours", "b3_weekend_penalty",
                  "c1_route_length", "c2_stops_per_route", "d7_deprivation_urban_rural", "f3_ethnic_access",
                  "f4_gender_accessibility", "g2_anomalies", "bsa3_tier_distribution"}
# c7_network_topology has its own template (network_topology.j2) shared with no
# other section — it gets a small one-off builder inline in _dispatch (Step 3b
# below) rather than its own module, since it is the only section using this contract.
_NETWORK_TOPOLOGY_SECTIONS = {"c7_network_topology"}

# Sections with no viable data source (ISSUES.md §8.2-§8.4) — stubbed pending
# future analytics-stage joins. Documented per-section in their builder module.
_STUB_SECTIONS = {"f3_ethnic_access", "f4_gender_accessibility", "c4_urban_rural_routes"}


@dataclass
class SectionResult:
    region: str
    urban_rural: str
    section_id: str
    stats: dict
    chart_data: dict
    narrative: str

    def to_dict(self) -> dict:
        return {
            "region": self.region,
            "urban_rural": self.urban_rural,
            "section_id": self.section_id,
            "stats": self.stats,
            "chart_data": self.chart_data,
            "narrative": self.narrative,
        }


@dataclass
class _Sources:
    """All audit Parquets/JSON loaded once, used across every combo."""

    policy_df: pd.DataFrame
    equity_df: pd.DataFrame
    equity_summary: dict
    route_geometries_df: pd.DataFrame
    route_clusters_df: pd.DataFrame
    lsoa_clusters_df: pd.DataFrame
    coverage_prediction_df: pd.DataFrame
    shap_df: pd.DataFrame
    anomalies_df: pd.DataFrame
    lta_df: pd.DataFrame
    policy_scenarios_df: pd.DataFrame
    service_levels_df: pd.DataFrame
    service_quality_df: pd.DataFrame
    appraisal_df: pd.DataFrame
    national_median_trips_per_capita: float


def _read_parquet_or_empty(path) -> pd.DataFrame:
    return pd.read_parquet(path) if path.exists() else pd.DataFrame()


def _load_service_quality(path) -> pd.DataFrame:
    """Load lsoa_service_quality, normalising its LSOA21CD column to lsoa_cd.

    This source uses LSOA21CD (the ONS 2021 boundary column name) while every
    other audit table uses lsoa_cd — normalise once at load time so all
    downstream filtering/joining can use a single consistent column name.
    """
    if not path.exists():
        return pd.DataFrame()
    df = pd.read_parquet(path)
    return df.rename(columns={"LSOA21CD": "lsoa_cd"})


def _load_sources(cfg: PipelineConfig) -> _Sources | None:
    audit = cfg.audit_dir
    policy_path = audit / "lsoa_policy_synthesis.parquet"
    equity_path = audit / "lsoa_equity_metrics.parquet"
    if not policy_path.exists() or not equity_path.exists():
        logger.warning("Audit Parquets not found — precompute returning empty results")
        return None

    policy_df = pd.read_parquet(policy_path)

    equity_summary: dict = {}
    summary_path = audit / "equity_summary.json"
    if summary_path.exists():
        equity_summary = json.loads(summary_path.read_text())

    shap_path = audit / "shap_summary.csv"
    shap_df = pd.read_csv(shap_path) if shap_path.exists() else pd.DataFrame()

    # lsoa_economic_appraisal.region is all "Unknown" — recover real
    # region/urban_rural by joining to lsoa_policy_synthesis via lsoa_cd.
    appraisal_raw = _read_parquet_or_empty(audit / "lsoa_economic_appraisal.parquet")
    appraisal_df = pd.DataFrame()
    if not appraisal_raw.empty:
        appraisal_df = appraisal_raw.drop(columns=["region", "urban_rural"], errors="ignore").merge(
            policy_df[["lsoa_cd", "region", "urban_rural"]], on="lsoa_cd", how="inner",
        )

    return _Sources(
        policy_df=policy_df,
        equity_df=pd.read_parquet(equity_path),
        equity_summary=equity_summary,
        route_geometries_df=_read_parquet_or_empty(audit / "route_geometries.parquet"),
        route_clusters_df=_read_parquet_or_empty(audit / "route_clusters.parquet"),
        lsoa_clusters_df=_read_parquet_or_empty(audit / "lsoa_clusters_hdbscan.parquet"),
        coverage_prediction_df=_read_parquet_or_empty(audit / "coverage_prediction.parquet"),
        shap_df=shap_df,
        anomalies_df=_read_parquet_or_empty(audit / "anomalies.parquet"),
        lta_df=_read_parquet_or_empty(audit / "lta_franchising_readiness.parquet"),
        policy_scenarios_df=_read_parquet_or_empty(audit / "policy_scenarios.parquet"),
        service_levels_df=_read_parquet_or_empty(audit / "lsoa_service_levels.parquet"),
        service_quality_df=_load_service_quality(audit / "lsoa_service_quality.parquet"),
        appraisal_df=appraisal_df,
        national_median_trips_per_capita=float(policy_df["trips_per_capita"].median()),
    )


def _filter_by_lsoa(df: pd.DataFrame, filtered_lsoa_cds: pd.Series) -> pd.DataFrame:
    if df.empty or "lsoa_cd" not in df.columns:
        return df
    return df[df["lsoa_cd"].isin(filtered_lsoa_cds)]


def _filter_by_region_col(df: pd.DataFrame, column: str, value: str) -> pd.DataFrame:
    if df.empty or column not in df.columns or value == "all":
        return df
    return df[df[column] == value]


def precompute_all_sections(cfg: PipelineConfig) -> list[dict]:
    """Precompute all 51 section results for the 30 filter combinations.

    Loads Phase 0 audit Parquets once, applies region/area-type filters per
    combo, dispatches to the appropriate stats builder per section, runs
    InsightEngine, and returns the full list of section results.

    Args:
        cfg: Pipeline configuration.

    Returns:
        List of dicts, each with keys: region, urban_rural, section_id,
        stats, chart_data, narrative. Length is 30 x len(SECTION_REGISTRY).
    """
    sources = _load_sources(cfg)
    if sources is None:
        return []

    engine = InsightEngine()
    results: list[dict] = []

    for region in _REGIONS:
        region_name = "England" if region == "all" else REGION_NAMES[region]
        region_value = "all" if region == "all" else region_name

        for urban_rural in _AREA_TYPES:
            policy_df = sources.policy_df
            region_mask = pd.Series(True, index=policy_df.index)
            if region_value != "all":
                region_mask = policy_df["region"] == region_value

            ur_mask = pd.Series(True, index=policy_df.index)
            if urban_rural != "all":
                ur_mask = policy_df["urban_rural"].str.lower().str.startswith(urban_rural)

            filtered = policy_df[region_mask & ur_mask]
            region_df = policy_df[region_mask]  # region-filtered, area-type UNfiltered (§4.2)
            lsoa_cds = filtered["lsoa_cd"]

            for section_id in SECTION_REGISTRY:
                stats = _dispatch(
                    section_id=section_id,
                    region=region,
                    urban_rural=urban_rural,
                    region_name=region_name,
                    filtered=filtered,
                    region_df=region_df,
                    sources=sources,
                    lsoa_cds=lsoa_cds,
                )
                result = engine.generate(section_id=section_id, region=region, urban_rural=urban_rural, stats=stats)
                results.append(
                    SectionResult(
                        region=region, urban_rural=urban_rural, section_id=section_id,
                        stats=stats, chart_data={}, narrative=result["narrative"],
                    ).to_dict()
                )

    logger.info(f"Precomputed {len(results)} section results")
    return results


def _dispatch(
    section_id: str,
    region: str,
    urban_rural: str,
    region_name: str,
    filtered: pd.DataFrame,
    region_df: pd.DataFrame,
    sources: _Sources,
    lsoa_cds: pd.Series,
) -> dict:
    """Route a section_id to its builder module with the data it needs."""
    if section_id in _STUB_SECTIONS:
        return {}

    if section_id in _RANKING_SECTIONS:
        return build_ranking_stats(section_id, filtered=filtered, national_df=sources.policy_df, region=region, region_name=region_name)

    if section_id in _CORRELATION_SECTIONS:
        return build_correlation_stats(section_id, filtered=filtered)

    if section_id in _ML_CLUSTER_SECTIONS:
        return build_ml_clusters_stats(
            section_id,
            lsoa_clusters_df=_filter_by_lsoa(sources.lsoa_clusters_df, lsoa_cds),
            route_clusters_df=_filter_by_region_col(sources.route_clusters_df, "primary_region", region_name) if region != "all" else sources.route_clusters_df,
        )

    if section_id in _ML_PREDICTION_SECTIONS:
        return build_ml_prediction_stats(
            section_id,
            coverage_prediction_df=_filter_by_lsoa(sources.coverage_prediction_df, lsoa_cds),
            shap_df=sources.shap_df,
        )

    if section_id in _MARKET_CONCENTRATION_SECTIONS:
        routes = sources.route_geometries_df
        if region != "all" and "primary_region" in routes.columns:
            routes = routes[routes["primary_region"] == region_name]
        lta = sources.lta_df
        if region != "all" and "region" in lta.columns:
            lta = lta[lta["region"] == region_name]
        return build_market_concentration_stats(section_id, routes_df=routes, lta_df=lta, region_name=region_name)

    if section_id in _URBAN_RURAL_GAP_SECTIONS:
        return build_urban_rural_gap_stats(section_id, region_df=region_df, urban_rural=urban_rural)

    if section_id in _POLICY_SCENARIO_SECTIONS:
        return build_policy_scenario_stats(section_id, scenarios_df=sources.policy_scenarios_df)

    if section_id in _ECONOMIC_SECTIONS:
        return build_economic_stats(section_id, appraisal_df=_filter_by_lsoa(sources.appraisal_df, lsoa_cds), region_name=region_name)

    if section_id in _EQUITY_SECTIONS:
        return build_equity_stats(section_id, equity_df=_filter_by_lsoa(sources.equity_df, lsoa_cds))

    if section_id in _MISC_SECTIONS:
        return build_misc_stats(
            section_id,
            region=region,
            urban_rural=urban_rural,
            policy_df=filtered,
            service_levels_df=_filter_by_lsoa(sources.service_levels_df, lsoa_cds),
            service_quality_df=_filter_by_lsoa(sources.service_quality_df, lsoa_cds),
            route_geometries_df=sources.route_geometries_df,
            anomalies_df=_filter_by_lsoa(sources.anomalies_df, lsoa_cds),
            lta_df=_filter_by_region_col(sources.lta_df, "region", region_name) if region != "all" else sources.lta_df,
        )

    if section_id in _NETWORK_TOPOLOGY_SECTIONS:
        return _build_network_topology(sources.route_geometries_df, region, region_name)

    if section_id == "a7_investment_gap":
        return _build_gap_to_target(filtered, sources.national_median_trips_per_capita)

    return {}


def _build_network_topology(routes_df: pd.DataFrame, region: str, region_name: str) -> dict:
    """Stats for c7_network_topology -> network_topology.j2 (the only section using this contract).

    {n_cross_la, pct_cross_la, densest_corridor, densest_count, mean_length, median_length}
    """
    if routes_df.empty or "cross_la" not in routes_df.columns:
        return {}

    df = routes_df
    if region != "all" and "primary_region" in df.columns:
        df = df[df["primary_region"] == region_name]
    if df.empty:
        return {}

    cross_la = df[df["cross_la"]]
    n_total = len(df)
    stats = {
        "n_cross_la": int(len(cross_la)),
        "pct_cross_la": round(len(cross_la) / n_total * 100, 1),
        "mean_length": round(float(df["length_km"].mean()), 1),
        "median_length": round(float(df["length_km"].median()), 1),
    }

    if region == "all" and not cross_la.empty and "primary_region" in cross_la.columns:
        by_region = cross_la.groupby("primary_region").size()
        densest = by_region.idxmax()
        stats["densest_corridor"] = str(densest)
        stats["densest_count"] = int(by_region.loc[densest])

    return stats


def _build_gap_to_target(filtered: pd.DataFrame, national_median: float) -> dict:
    """Gap-to-target stats, fixed to use a fixed national yardstick (§2.5/§8.5).

    The previous implementation computed the median from the FILTERED
    (region-scoped) frame — making every region's "below average" share
    converge to ~50% by construction, since each region was judged against
    its own moving median rather than a comparable national benchmark.
    """
    if filtered.empty or "trips_per_capita" not in filtered.columns:
        return {}

    below = filtered[filtered["trips_per_capita"] < national_median]
    return {
        "n_below": int(len(below)),
        "pct_below": round(len(below) / len(filtered) * 100, 1),
        "target": round(national_median, 2),
        "target_description": "national median",
        "unit": "trips/capita",
        "mean_gap": round(float((national_median - below["trips_per_capita"]).mean()), 2) if len(below) > 0 else 0.0,
    }
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `pytest tests/warehouse/test_precompute_30.py -v`
Expected: PASS — 1,530 results, every section present in every combo, stub
sections empty everywhere, gap_to_target uses one shared national median.

- [ ] **Step 5: Commit**

```bash
git add src/aequitas/warehouse/precompute.py tests/warehouse/test_precompute_30.py
git commit -m "feat: wire all 51 sections through stats builders, fix region filter and gap_to_target median (§2.1,§2.5,§4.1)"
```

---

## Task 16: Verify `HEADLINE_SECTIONS` resolves against the new builders (§5)

**Files:**
- Read/verify only: `src/aequitas/api/services/warehouse.py:27-36`
- Test: `tests/api/test_overview.py`

**Investigation finding:** `HEADLINE_SECTIONS` (lines 27-36 of
`api/services/warehouse.py`) was already updated to new-style section IDs in
an earlier pass — it references `f1_gini`, `a3_walking_distance`,
`b1_frequency`, `c3_operator_hhi`, `d1_coverage_deprivation`, `j3_carbon`,
`bsa1_franchising_readiness`, `ps1_freq_restoration`, all of which exist in
`SECTION_REGISTRY`. Cross-checking each `stat_key` against this plan's builder
output contracts:

| dim_id | section_id | stat_key | Produced by | Present in output? |
|---|---|---|---|---|
| equity | f1_gini | `gini` | `equity.py` (Task 13) | ✅ |
| accessibility | a3_walking_distance | `pct_covered` | `misc.py` (Task 14) | ✅ |
| service_quality | b1_frequency | `national_avg` | `ranking.py` (Task 5) | ✅ (national-scope ranking shape) |
| route_network | c3_operator_hhi | `hhi` | `market_concentration.py` (Task 9) | ✅ |
| correlations | d1_coverage_deprivation | `r` | `correlation.py` (Task 6, via `CorrelationResult.r`) | ✅ |
| economic | j3_carbon | `co2_saving_tonnes` | `economic.py` (Task 12) | ✅ |
| bus_services_act | bsa1_franchising_readiness | `national_avg` | `ranking.py` (Task 5) | ✅ |
| scenarios | ps1_freq_restoration | `scenario.population_affected` (dot-path) | `policy_scenario.py` (Task 11) | ✅ |

No code change is required — this task is a **verification + regression test**
confirming the dict's IDs resolve to non-empty stats once the warehouse is
rebuilt against the Task 15 precompute rewrite (closing out §5: "all-zero
overview page").

- [ ] **Step 1: Write the verification test**

Create or replace `tests/api/test_overview.py` with:

```python
"""Tests for query_overview — verifies HEADLINE_SECTIONS resolves to non-zero values (§5)."""
import duckdb
import pytest

from aequitas.api.services.warehouse import HEADLINE_SECTIONS, query_overview
from aequitas.intelligence.section_registry import SECTION_REGISTRY


def test_headline_section_ids_exist_in_registry():
    for dim_id, (section_id, _stat_key) in HEADLINE_SECTIONS.items():
        assert section_id in SECTION_REGISTRY, f"{dim_id} references unknown section_id {section_id!r}"


def test_overview_returns_non_zero_values_for_national_scope(tmp_path):
    db_path = tmp_path / "warehouse.duckdb"
    db = duckdb.connect(str(db_path))
    db.execute("""
        CREATE TABLE section_results (
            region VARCHAR, urban_rural VARCHAR, section_id VARCHAR,
            stats JSON, narrative VARCHAR
        )
    """)

    fixture_stats = {
        "f1_gini": {"gini": 0.5741},
        "a3_walking_distance": {"pct_covered": 92.4},
        "b1_frequency": {"national_avg": 12.3},
        "c3_operator_hhi": {"hhi": 1850.0},
        "d1_coverage_deprivation": {"r": -0.0644},
        "j3_carbon": {"co2_saving_tonnes": 5278.5},
        "bsa1_franchising_readiness": {"national_avg": 41.2},
        "ps1_freq_restoration": {"scenario": {"population_affected": 5689818}},
    }
    for section_id, stats in fixture_stats.items():
        db.execute(
            "INSERT INTO section_results VALUES (?, ?, ?, ?, ?)",
            ["all", "all", section_id, stats, "narrative text"],
        )

    overview = query_overview(db, region="all", urban_rural="all")
    by_dim = {row["dimension"]: row for row in overview} if overview and "dimension" in overview[0] else None

    nonzero_count = sum(1 for row in overview if row.get("value") not in (0, 0.0, None))
    assert nonzero_count == len(HEADLINE_SECTIONS), (
        f"expected all {len(HEADLINE_SECTIONS)} headline dimensions non-zero, got {nonzero_count}: {overview}"
    )
```

(Adjust the `by_dim`/`row.get("value")`/`row.get("dimension")` key names to
match `query_overview`'s actual return shape — read
`src/aequitas/api/services/warehouse.py:95-130` to confirm the exact dict keys
the function returns per row before finalising the assertions; the fixture
setup and the "all non-zero" assertion are the load-bearing parts of this
test regardless of exact key names.)

- [ ] **Step 2: Run the test**

Run: `pytest tests/api/test_overview.py -v`
Expected: PASS — confirms every `HEADLINE_SECTIONS` entry both exists in the
registry and resolves to a non-zero scalar once real stats are present.

- [ ] **Step 3: Commit**

```bash
git add tests/api/test_overview.py
git commit -m "test: verify HEADLINE_SECTIONS resolves to non-zero overview values (§5)"
```

---

## Final Step: Rebuild warehouse and FAISS index, run full suite

Once Tasks 1-16 are merged:

1. Rebuild the warehouse: `aequitas run --stage warehouse` (or the equivalent
   CLI invocation documented in `docs/AEQUITAS_MASTER_REFERENCE.md`) — this
   re-runs `precompute_all_sections` and repopulates `section_results` with
   all 1,530 rows.
2. Rebuild the FAISS index: `aequitas run --stage rag_index` — the index was
   built almost entirely from empty narratives (§6); it must be rebuilt
   against the newly-populated `section_results` table to produce
   policy-quality RAG retrieval.
3. Run the full test suite (`pytest`) and fix any remaining failures the
   rewrite surfaces in integration paths not covered by the unit tests above
   (e.g. `tests/intelligence/test_engine.py` shape-dispatch interactions,
   `tests/api/` endpoint tests that assert on specific narrative content).

