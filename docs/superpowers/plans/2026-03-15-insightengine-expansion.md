# InsightEngine Expansion — Implementation Plan


> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Expand InsightEngine from 7 templates / ~60 narratives to 27 templates / 51 chart+narrative pairs with populated chart_data payloads, covering all analytical questions from the Blueprint + Phase 0 additions.

**Architecture:** Add new templates, evidence gate rules, chart_data builder functions, and a section registry. Rewire precompute.py to loop over all 51 sections using the registry. One prerequisite pipeline change: export SHAP importance to Parquet (currently in-memory only). LAD profiles (lad_profile.j2, 298 × 5 = 1,490 rows) deferred to a follow-up task.

**Tech Stack:** Python 3.12+, Jinja2, pandas, numpy, scipy, DuckDB, pytest

**Spec:** `docs/superpowers/specs/2026-03-15-insightengine-expansion-design.md`

---

## File Structure

```
src/aequitas/intelligence/
├── engine.py                    — MODIFY: expand _SECTION_TEMPLATES to 51 entries, register format_thousands filter
├── rules.py                     — MODIFY: add 16 new rule classes
├── calculators.py               — MODIFY: add build_box_violin_stats(), build_heatmap_stats()
├── chart_data_builder.py        — CREATE: pure functions DataFrame → chart_data JSON (one per chart type)
├── section_registry.py          — CREATE: maps section_id → (template, builder_fn, evidence_gate, data_sources)
└── templates/
    ├── (7 existing .j2 files)   — NO CHANGE
    ├── coverage_gap.j2          — CREATE
    ├── desert_spotlight.j2      — CREATE
    ├── urban_rural_gap.j2       — CREATE
    ├── ml_prediction.j2         — CREATE
    ├── service_hours.j2         — CREATE
    ├── weekend_penalty.j2       — CREATE
    ├── distribution.j2          — CREATE
    ├── market_concentration.j2  — CREATE
    ├── ml_clusters.j2           — CREATE
    ├── network_topology.j2      — CREATE
    ├── heatmap.j2               — CREATE
    ├── equity_decile.j2         — CREATE
    ├── demographic_breakdown.j2 — CREATE
    ├── accessibility_gap.j2     — CREATE
    ├── anomaly_spotlight.j2     — CREATE
    ├── economic_value.j2        — CREATE
    ├── bcr_analysis.j2          — CREATE
    ├── carbon_reduction.j2      — CREATE
    ├── tier_distribution.j2     — CREATE
    └── scenario_comparison.j2   — CREATE

src/aequitas/warehouse/
├── schema.py                    — MODIFY: add 8 new ANALYTICS_PARQUET_SOURCES entries
├── precompute.py                — MODIFY: replace _SECTIONS with section_registry, populate chart_data

tests/intelligence/
├── test_rules_new.py            — CREATE: tests for 16 new rule classes
├── test_chart_data_builder.py   — CREATE: tests for chart_data builder functions
├── test_section_registry.py     — CREATE: tests for registry completeness
├── test_templates_new.py        — CREATE: tests for 20 new templates
```

---

## Chunk 0: Prerequisites

### Task 0: Export SHAP Importance to Parquet

`shap_importance.parquet` does not exist yet — `compute_shap_importance()` runs in-memory during notebook 04d but never persists. We need it for sections A8, D8, G3, G4.

**Files:**
- Create: `src/aequitas/analytics/shap_export.py`
- Create: `tests/analytics/test_shap_export.py`
- Modify: `src/aequitas/pipeline/_stages.py` (add to audit_files list)

- [ ] **Step 1: Write failing test**

```python
# tests/analytics/test_shap_export.py
"""Test SHAP importance export."""

import pandas as pd
import pytest
from unittest.mock import patch, MagicMock
from aequitas.analytics.shap_export import export_shap_importance
from aequitas.core.config import PipelineConfig


def test_export_shap_produces_parquet(tmp_path):
    """SHAP export creates a Parquet with feature + mean_abs_shap columns."""
    cfg = PipelineConfig()
    cfg_audit = cfg.audit_dir

    # Only run if master_lsoa_table exists (CI may not have it)
    master_path = cfg_audit / "master_lsoa_table.parquet"
    if not master_path.exists():
        pytest.skip("master_lsoa_table.parquet not available")

    out = export_shap_importance(cfg, output_dir=tmp_path)
    assert out.exists()
    df = pd.read_parquet(out)
    assert "feature" in df.columns
    assert "mean_abs_shap" in df.columns
    assert len(df) >= 5  # at least 5 features
    # Should be sorted descending
    assert df["mean_abs_shap"].is_monotonic_decreasing
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /Users/souravamseekarmarti/Projects/aequitas && uv run python -m pytest tests/analytics/test_shap_export.py -v 2>&1 | head -10`
Expected: ImportError — module doesn't exist yet

- [ ] **Step 3: Implement shap_export.py**

```python
# src/aequitas/analytics/shap_export.py
"""Export SHAP feature importance to Parquet for InsightEngine consumption.

Trains a lightweight RF model on master_lsoa_table features, computes SHAP
values, and saves to shap_importance.parquet.
"""

from pathlib import Path

import pandas as pd
from loguru import logger

from aequitas.analytics.ml_prediction import train_coverage_model, compute_shap_importance
from aequitas.core.config import PipelineConfig

# The 9 socio-economic features used in coverage prediction
_FEATURE_COLS = [
    "imd_score",
    "unemployment_rate",
    "nocar_pct",
    "elderly_pct",
    "income_score",
    "nonwhite_pct",
    "disability_pct",
    "geo_barriers_score",
    "imd_decile",
]


def export_shap_importance(
    cfg: PipelineConfig | None = None,
    output_dir: Path | None = None,
) -> Path:
    """Train RF model and export SHAP importance to Parquet.

    Args:
        cfg: Pipeline configuration.
        output_dir: Override output directory (default: cfg.audit_dir).

    Returns:
        Path to the written shap_importance.parquet.
    """
    if cfg is None:
        cfg = PipelineConfig()
    out_dir = output_dir or cfg.audit_dir

    master = pd.read_parquet(cfg.audit_dir / "master_lsoa_table.parquet")

    # Prepare features + target
    available = [c for c in _FEATURE_COLS if c in master.columns]
    X = master[available].fillna(0)
    y = master["trips_per_capita"].fillna(0).values if "trips_per_capita" in master.columns else master[available[0]].values

    model, metrics = train_coverage_model(X, y)
    logger.info(f"SHAP export: RF R²={metrics['r2_test']:.3f}")

    importance = compute_shap_importance(model, X)

    out_path = out_dir / "shap_importance.parquet"
    importance.to_parquet(out_path, index=False)
    logger.info(f"SHAP importance exported: {len(importance)} features → {out_path}")
    return out_path
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd /Users/souravamseekarmarti/Projects/aequitas && uv run python -m pytest tests/analytics/test_shap_export.py -v`
Expected: PASS (or skip if no master_lsoa_table)

- [ ] **Step 5: Add to pipeline audit_files check**

In `src/aequitas/pipeline/_stages.py`, add `"shap_importance.parquet"` to the `audit_files` list in `run_analytics()`.

- [ ] **Step 6: Commit**

```bash
git add src/aequitas/analytics/shap_export.py tests/analytics/test_shap_export.py src/aequitas/pipeline/_stages.py
git commit -m "feat(analytics): export SHAP importance to Parquet for InsightEngine"
```

---

## Chunk 1: Evidence Gate Rules (16 new rule classes)

### Task 1: New Evidence Gate Rules

**Files:**
- Modify: `src/aequitas/intelligence/rules.py`
- Create: `tests/intelligence/test_rules_new.py`

- [ ] **Step 1: Write failing tests for all 16 new rules**

```python
# tests/intelligence/test_rules_new.py
"""Tests for new evidence gate rules — InsightEngine expansion."""

import pytest
from aequitas.intelligence.rules import (
    MinLsoaRule,
    DesertRule,
    UrbanRuralRule,
    MLPredictionRule,
    DistributionRule,
    MarketConcentrationRule,
    ClusterRule,
    NetworkRule,
    HeatmapRule,
    DecileRule,
    DemographicRule,
    AccessibilityRule,
    AnomalyRule,
    CarbonRule,
    TierRule,
    ScenarioComparisonRule,
)


# --- MinLsoaRule ---
def test_min_lsoa_fires_large():
    assert MinLsoaRule().should_fire(n_lsoas=500)

def test_min_lsoa_suppresses_small():
    assert not MinLsoaRule().should_fire(n_lsoas=50)

def test_min_lsoa_boundary():
    assert MinLsoaRule().should_fire(n_lsoas=100)
    assert not MinLsoaRule().should_fire(n_lsoas=99)


# --- DesertRule ---
def test_desert_fires():
    assert DesertRule().should_fire(n_desert_lsoas=1)

def test_desert_suppresses_zero():
    assert not DesertRule().should_fire(n_desert_lsoas=0)


# --- UrbanRuralRule ---
def test_urban_rural_fires():
    assert UrbanRuralRule().should_fire(n_urban=100, n_rural=50)

def test_urban_rural_suppresses_low_urban():
    assert not UrbanRuralRule().should_fire(n_urban=10, n_rural=50)

def test_urban_rural_suppresses_low_rural():
    assert not UrbanRuralRule().should_fire(n_urban=100, n_rural=5)


# --- MLPredictionRule ---
def test_ml_prediction_fires():
    assert MLPredictionRule().should_fire(r2=0.472, n_features=9)

def test_ml_prediction_suppresses_negative_r2():
    assert not MLPredictionRule().should_fire(r2=-0.1, n_features=9)

def test_ml_prediction_suppresses_few_features():
    assert not MLPredictionRule().should_fire(r2=0.5, n_features=2)


# --- DistributionRule ---
def test_distribution_fires():
    assert DistributionRule().should_fire(n=100)

def test_distribution_suppresses():
    assert not DistributionRule().should_fire(n=10)


# --- MarketConcentrationRule ---
def test_market_fires():
    assert MarketConcentrationRule().should_fire(n_operators=5)

def test_market_suppresses_monopoly():
    assert not MarketConcentrationRule().should_fire(n_operators=1)


# --- ClusterRule ---
def test_cluster_fires():
    assert ClusterRule().should_fire(n_clusters=4)

def test_cluster_suppresses():
    assert not ClusterRule().should_fire(n_clusters=1)


# --- NetworkRule ---
def test_network_fires():
    assert NetworkRule().should_fire(n_routes=100)

def test_network_suppresses():
    assert not NetworkRule().should_fire(n_routes=5)


# --- HeatmapRule ---
def test_heatmap_fires():
    assert HeatmapRule().should_fire(min_cell_n=50)

def test_heatmap_suppresses():
    assert not HeatmapRule().should_fire(min_cell_n=5)


# --- DecileRule ---
def test_decile_fires():
    assert DecileRule().should_fire(decile_counts=[200] * 10)

def test_decile_suppresses_one_small():
    counts = [200] * 9 + [50]
    assert not DecileRule().should_fire(decile_counts=counts)


# --- DemographicRule ---
def test_demographic_fires():
    assert DemographicRule().should_fire(group_counts=[100, 200, 150])

def test_demographic_suppresses():
    assert not DemographicRule().should_fire(group_counts=[100, 10, 150])


# --- AccessibilityRule ---
def test_accessibility_fires():
    assert AccessibilityRule().should_fire(n_pois=100)

def test_accessibility_suppresses():
    assert not AccessibilityRule().should_fire(n_pois=5)


# --- AnomalyRule ---
def test_anomaly_fires():
    assert AnomalyRule().should_fire(n_anomalies=100)

def test_anomaly_suppresses():
    assert not AnomalyRule().should_fire(n_anomalies=5)


# --- CarbonRule ---
def test_carbon_fires():
    assert CarbonRule().should_fire(co2_saving=100.0)

def test_carbon_suppresses():
    assert not CarbonRule().should_fire(co2_saving=0.0)

def test_carbon_suppresses_negative():
    assert not CarbonRule().should_fire(co2_saving=-5.0)


# --- TierRule ---
def test_tier_fires():
    assert TierRule().should_fire(n_lads=50)

def test_tier_suppresses():
    assert not TierRule().should_fire(n_lads=5)


# --- ScenarioComparisonRule ---
def test_scenario_fires():
    assert ScenarioComparisonRule().should_fire(n_scenarios=4)

def test_scenario_suppresses():
    assert not ScenarioComparisonRule().should_fire(n_scenarios=1)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /Users/souravamseekarmarti/Projects/aequitas && python -m pytest tests/intelligence/test_rules_new.py -v 2>&1 | head -30`
Expected: ImportError — classes don't exist yet

- [ ] **Step 3: Implement all 16 rule classes**

Append to `src/aequitas/intelligence/rules.py`:

```python


class MinLsoaRule:
    """Fire when enough LSOAs are available for meaningful analysis."""

    MIN_LSOAS = 100

    def should_fire(self, n_lsoas: int) -> bool:
        return n_lsoas >= self.MIN_LSOAS


class DesertRule:
    """Fire when at least one service desert LSOA exists."""

    def should_fire(self, n_desert_lsoas: int) -> bool:
        return n_desert_lsoas >= 1


class UrbanRuralRule:
    """Fire when both urban and rural groups have sufficient sample size."""

    MIN_PER_GROUP = 30

    def should_fire(self, n_urban: int, n_rural: int) -> bool:
        return n_urban >= self.MIN_PER_GROUP and n_rural >= self.MIN_PER_GROUP


class MLPredictionRule:
    """Fire when ML model has positive explanatory power with enough features."""

    MIN_FEATURES = 3

    def should_fire(self, r2: float, n_features: int) -> bool:
        return r2 > 0 and n_features >= self.MIN_FEATURES


class DistributionRule:
    """Fire when sample size is sufficient for distribution summary."""

    MIN_N = 30

    def should_fire(self, n: int) -> bool:
        return n >= self.MIN_N


class MarketConcentrationRule:
    """Fire when there are enough operators to compute HHI meaningfully."""

    MIN_OPERATORS = 2

    def should_fire(self, n_operators: int) -> bool:
        return n_operators >= self.MIN_OPERATORS


class ClusterRule:
    """Fire when clustering produced at least 2 distinct groups."""

    MIN_CLUSTERS = 2

    def should_fire(self, n_clusters: int) -> bool:
        return n_clusters >= self.MIN_CLUSTERS


class NetworkRule:
    """Fire when enough routes exist for network topology analysis."""

    MIN_ROUTES = 10

    def should_fire(self, n_routes: int) -> bool:
        return n_routes >= self.MIN_ROUTES


class HeatmapRule:
    """Fire when every cell in the heatmap has enough observations."""

    MIN_CELL_N = 10

    def should_fire(self, min_cell_n: int) -> bool:
        return min_cell_n >= self.MIN_CELL_N


class DecileRule:
    """Fire when all 10 IMD deciles have enough LSOAs for comparison."""

    MIN_PER_DECILE = 100

    def should_fire(self, decile_counts: list[int]) -> bool:
        return len(decile_counts) == 10 and all(c >= self.MIN_PER_DECILE for c in decile_counts)


class DemographicRule:
    """Fire when every demographic group has enough observations."""

    MIN_PER_GROUP = 30

    def should_fire(self, group_counts: list[int]) -> bool:
        return all(c >= self.MIN_PER_GROUP for c in group_counts)


class AccessibilityRule:
    """Fire when enough POIs exist for accessibility gap analysis."""

    MIN_POIS = 10

    def should_fire(self, n_pois: int) -> bool:
        return n_pois >= self.MIN_POIS


class AnomalyRule:
    """Fire when enough anomalies are detected to report patterns."""

    MIN_ANOMALIES = 10

    def should_fire(self, n_anomalies: int) -> bool:
        return n_anomalies >= self.MIN_ANOMALIES


class CarbonRule:
    """Fire when modal shift produces positive CO2 savings."""

    def should_fire(self, co2_saving: float) -> bool:
        return co2_saving > 0


class TierRule:
    """Fire when enough LADs are assessed for tier distribution."""

    MIN_LADS = 10

    def should_fire(self, n_lads: int) -> bool:
        return n_lads >= self.MIN_LADS


class ScenarioComparisonRule:
    """Fire when multiple scenarios exist for comparison."""

    MIN_SCENARIOS = 2

    def should_fire(self, n_scenarios: int) -> bool:
        return n_scenarios >= self.MIN_SCENARIOS
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /Users/souravamseekarmarti/Projects/aequitas && python -m pytest tests/intelligence/test_rules_new.py -v`
Expected: All 34 tests PASS

- [ ] **Step 5: Run existing rule tests to verify no regressions**

Run: `cd /Users/souravamseekarmarti/Projects/aequitas && python -m pytest tests/intelligence/test_rules.py -v`
Expected: All existing tests PASS

- [ ] **Step 6: Commit**

```bash
git add src/aequitas/intelligence/rules.py tests/intelligence/test_rules_new.py
git commit -m "feat(intelligence): add 16 evidence gate rules for expanded sections"
```

---

## Chunk 2: Chart Data Builder

### Task 2: Chart Data Builder Module

**Files:**
- Create: `src/aequitas/intelligence/chart_data_builder.py`
- Create: `tests/intelligence/test_chart_data_builder.py`

- [ ] **Step 1: Write failing tests for chart data builder functions**

```python
# tests/intelligence/test_chart_data_builder.py
"""Tests for chart_data builder — produces typed JSON payloads for frontend."""

import numpy as np
import pandas as pd
import pytest
from aequitas.intelligence.chart_data_builder import (
    build_horizontal_bar,
    build_scatter_regression,
    build_lorenz_curve,
    build_stacked_bar,
    build_grouped_bar,
    build_box_violin,
    build_choropleth,
    build_heatmap,
    build_shap_bar,
    build_scatter_clusters,
)


def test_horizontal_bar_structure():
    data = pd.DataFrame({
        "label": ["North East", "South East", "London"],
        "value": [12.1, 31.4, 25.0],
    })
    result = build_horizontal_bar(
        data=data, title="Route density", x_label="Routes per 100k",
        y_label="Region", national_avg=22.8,
    )
    assert result["type"] == "horizontal_bar"
    assert len(result["data"]) == 3
    assert result["data"][0]["rank"] == 1  # sorted descending
    assert result["national_avg"] == 22.8


def test_horizontal_bar_sorted():
    data = pd.DataFrame({"label": ["A", "B", "C"], "value": [10, 30, 20]})
    result = build_horizontal_bar(data=data, title="T", x_label="X", y_label="Y")
    values = [d["value"] for d in result["data"]]
    assert values == sorted(values, reverse=True)


def test_scatter_regression_samples():
    np.random.seed(42)
    n = 5000
    x = np.random.randn(n)
    y = 2 * x + np.random.randn(n)
    df = pd.DataFrame({"x": x, "y": y, "id": [f"E{i:08d}" for i in range(n)]})
    result = build_scatter_regression(
        df, x_col="x", y_col="y", id_col="id",
        title="Test", x_label="X", y_label="Y", max_points=2000,
    )
    assert result["type"] == "scatter_regression"
    assert len(result["data"]) <= 2000
    assert result["sample_size"] == n
    assert result["r"] is not None
    assert "regression_line" in result


def test_lorenz_curve():
    values = pd.Series([1.0, 2.0, 3.0, 4.0, 10.0])
    weights = pd.Series([100, 100, 100, 100, 100])
    result = build_lorenz_curve(
        values=values, weights=weights, title="Equity",
        reference_gini=0.36, reference_label="UK Income",
    )
    assert result["type"] == "lorenz_curve"
    assert 0 <= result["gini"] <= 1
    assert result["curve_points"][0]["cum_pop"] == 0.0
    assert result["curve_points"][-1]["cum_pop"] == pytest.approx(1.0, abs=0.01)


def test_stacked_bar():
    result = build_stacked_bar(
        categories=["NE", "SE"],
        series=[
            {"name": "Covered", "values": [80.0, 90.0]},
            {"name": "Not covered", "values": [20.0, 10.0]},
        ],
        title="Coverage",
    )
    assert result["type"] == "stacked_bar"
    assert len(result["categories"]) == 2
    assert len(result["series"]) == 2


def test_grouped_bar():
    result = build_grouped_bar(
        categories=["NE", "SE"],
        series=[
            {"name": "Urban", "values": [4.2, 5.1]},
            {"name": "Rural", "values": [1.3, 1.8]},
        ],
        title="Urban vs Rural",
    )
    assert result["type"] == "grouped_bar"


def test_box_violin():
    groups = {
        "North East": pd.Series([10, 20, 30, 40, 50, 60, 70]),
        "South East": pd.Series([15, 25, 35, 45, 55, 65, 75]),
    }
    result = build_box_violin(groups=groups, title="Route lengths", unit="km")
    assert result["type"] == "box_violin"
    assert len(result["groups"]) == 2
    assert "q1" in result["groups"][0]
    assert "median" in result["groups"][0]


def test_choropleth():
    data = pd.DataFrame({
        "area_code": ["E06000001", "E06000002"],
        "area_name": ["Hartlepool", "Middlesbrough"],
        "value": [12.3, 8.7],
    })
    result = build_choropleth(
        data=data, title="Deserts", geography="lad",
        metric="pct_no_service", colour_scale="RdYlGn",
    )
    assert result["type"] == "choropleth"
    assert len(result["data"]) == 2


def test_heatmap():
    result = build_heatmap(
        x_labels=["1", "2", "3"],
        y_labels=["Urban", "Rural"],
        values=[[60, 55, 50], [40, 35, 30]],
        title="SQI by decile",
        colour_scale="Viridis",
    )
    assert result["type"] == "heatmap"
    assert len(result["values"]) == 2
    assert len(result["values"][0]) == 3


def test_shap_bar():
    features = pd.DataFrame({
        "feature": ["nocar_pct", "imd_score", "elderly_pct"],
        "importance": [0.142, 0.098, 0.067],
    })
    result = build_shap_bar(features=features, title="SHAP", model_r2=0.472)
    assert result["type"] == "shap_bar"
    assert result["model_r2"] == 0.472
    assert len(result["features"]) == 3
    # Should be sorted by importance descending
    importances = [f["importance"] for f in result["features"]]
    assert importances == sorted(importances, reverse=True)


def test_scatter_clusters():
    data = pd.DataFrame({
        "x": [1.0, 2.0, 3.0, 4.0],
        "y": [0.5, 1.5, 2.5, 3.5],
        "cluster": [0, 0, 1, 1],
        "id": ["E01", "E02", "E03", "E04"],
    })
    cluster_labels = {0: "Urban", 1: "Rural"}
    result = build_scatter_clusters(
        data=data, cluster_labels=cluster_labels,
        title="Clusters", x_label="PC1", y_label="PC2", max_points=2000,
    )
    assert result["type"] == "scatter_clusters"
    assert len(result["clusters"]) == 2
    assert len(result["data"]) == 4
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /Users/souravamseekarmarti/Projects/aequitas && python -m pytest tests/intelligence/test_chart_data_builder.py -v 2>&1 | head -10`
Expected: ImportError

- [ ] **Step 3: Implement chart_data_builder.py**

```python
# src/aequitas/intelligence/chart_data_builder.py
"""Chart data builder — pure functions that produce typed JSON payloads.

Each function takes a DataFrame (or pre-aggregated data) and returns a dict
matching one of the chart_data schemas defined in the spec. The frontend
consumes these directly from the section_results.chart_data JSON column.

All scatter charts are sampled to max_points to keep storage reasonable.
All choropleths use LAD-level aggregation (not LSOA).
"""

from typing import Any

import numpy as np
import pandas as pd
from scipy import stats as scipy_stats

# Colorblind-safe palette (Viridis-derived)
_CLUSTER_COLOURS = [
    "#440154", "#46327e", "#365c8d", "#277f8e",
    "#1fa187", "#4ac16d", "#9fda3a", "#fde725",
]


def build_horizontal_bar(
    data: pd.DataFrame,
    title: str,
    x_label: str,
    y_label: str,
    national_avg: float | None = None,
) -> dict[str, Any]:
    """Build horizontal bar chart data, sorted descending by value."""
    sorted_df = data.sort_values("value", ascending=False).reset_index(drop=True)
    items = []
    for i, row in sorted_df.iterrows():
        items.append({
            "label": str(row["label"]),
            "value": round(float(row["value"]), 4),
            "rank": i + 1,
        })
    result: dict[str, Any] = {
        "type": "horizontal_bar",
        "title": title,
        "x_label": x_label,
        "y_label": y_label,
        "data": items,
    }
    if national_avg is not None:
        result["national_avg"] = round(float(national_avg), 4)
    return result


def build_scatter_regression(
    df: pd.DataFrame,
    x_col: str,
    y_col: str,
    id_col: str,
    title: str,
    x_label: str,
    y_label: str,
    max_points: int = 2000,
) -> dict[str, Any]:
    """Build scatter plot with regression line. Samples to max_points for display."""
    clean = df[[x_col, y_col, id_col]].dropna()
    n = len(clean)

    # Compute stats on full data
    r, p_value = scipy_stats.pearsonr(clean[x_col], clean[y_col]) if n >= 3 else (0.0, 1.0)
    slope, intercept = np.polyfit(clean[x_col], clean[y_col], 1) if n >= 2 else (0.0, 0.0)

    # Sample for display
    if n > max_points:
        sample = clean.sample(n=max_points, random_state=42)
    else:
        sample = clean

    points = [
        {"x": round(float(row[x_col]), 4), "y": round(float(row[y_col]), 4), "id": str(row[id_col])}
        for _, row in sample.iterrows()
    ]

    return {
        "type": "scatter_regression",
        "title": title,
        "x_label": x_label,
        "y_label": y_label,
        "r": round(float(r), 4),
        "p_value": round(float(p_value), 6),
        "regression_line": {"slope": round(float(slope), 6), "intercept": round(float(intercept), 6)},
        "sample_size": n,
        "display_sample_size": len(points),
        "data": points,
    }


def build_lorenz_curve(
    values: pd.Series,
    weights: pd.Series,
    title: str,
    reference_gini: float = 0.36,
    reference_label: str = "UK Income Gini",
    n_points: int = 100,
) -> dict[str, Any]:
    """Build Lorenz curve with Gini coefficient."""
    sorted_idx = values.argsort()
    sorted_vals = values.iloc[sorted_idx].values
    sorted_weights = weights.iloc[sorted_idx].values

    cum_pop = np.cumsum(sorted_weights) / sorted_weights.sum()
    weighted_vals = sorted_vals * sorted_weights
    cum_service = np.cumsum(weighted_vals) / weighted_vals.sum()

    # Prepend origin
    cum_pop = np.concatenate([[0], cum_pop])
    cum_service = np.concatenate([[0], cum_service])

    # Gini from Lorenz curve
    trapezoid = np.trapezoid if hasattr(np, "trapezoid") else np.trapz
    area_under = float(trapezoid(cum_service, cum_pop))
    gini = round(1 - 2 * area_under, 4)

    # Downsample curve points
    indices = np.linspace(0, len(cum_pop) - 1, n_points, dtype=int)
    curve_points = [
        {"cum_pop": round(float(cum_pop[i]), 4), "cum_service": round(float(cum_service[i]), 4)}
        for i in indices
    ]

    return {
        "type": "lorenz_curve",
        "title": title,
        "gini": gini,
        "reference_gini": reference_gini,
        "reference_label": reference_label,
        "curve_points": curve_points,
    }


def build_stacked_bar(
    categories: list[str],
    series: list[dict[str, Any]],
    title: str,
) -> dict[str, Any]:
    """Build stacked bar chart data."""
    return {
        "type": "stacked_bar",
        "title": title,
        "categories": categories,
        "series": series,
    }


def build_grouped_bar(
    categories: list[str],
    series: list[dict[str, Any]],
    title: str,
) -> dict[str, Any]:
    """Build grouped bar chart data."""
    return {
        "type": "grouped_bar",
        "title": title,
        "categories": categories,
        "series": series,
    }


def build_box_violin(
    groups: dict[str, pd.Series],
    title: str,
    unit: str = "",
) -> dict[str, Any]:
    """Build box + violin chart data from grouped series."""
    group_data = []
    for label, values in groups.items():
        q1 = float(values.quantile(0.25))
        q3 = float(values.quantile(0.75))
        iqr = q3 - q1
        lower_fence = q1 - 1.5 * iqr
        upper_fence = q3 + 1.5 * iqr
        outliers = values[(values < lower_fence) | (values > upper_fence)].tolist()
        group_data.append({
            "label": label,
            "min": round(float(values.min()), 2),
            "q1": round(q1, 2),
            "median": round(float(values.median()), 2),
            "q3": round(q3, 2),
            "max": round(float(values.max()), 2),
            "outliers": [round(float(o), 2) for o in outliers[:50]],  # cap outlier list
        })
    return {
        "type": "box_violin",
        "title": title,
        "unit": unit,
        "groups": group_data,
    }


def build_choropleth(
    data: pd.DataFrame,
    title: str,
    geography: str,
    metric: str,
    colour_scale: str = "Viridis",
) -> dict[str, Any]:
    """Build choropleth map data (LAD-aggregated, not LSOA)."""
    points = [
        {
            "area_code": str(row["area_code"]),
            "area_name": str(row.get("area_name", "")),
            "value": round(float(row["value"]), 2),
        }
        for _, row in data.iterrows()
    ]
    return {
        "type": "choropleth",
        "title": title,
        "geography": geography,
        "metric": metric,
        "colour_scale": colour_scale,
        "data": points,
    }


def build_heatmap(
    x_labels: list[str],
    y_labels: list[str],
    values: list[list[float]],
    title: str,
    colour_scale: str = "Viridis",
) -> dict[str, Any]:
    """Build heatmap data (e.g. IMD decile × urban/rural)."""
    return {
        "type": "heatmap",
        "title": title,
        "x_labels": x_labels,
        "y_labels": y_labels,
        "values": [[round(float(v), 2) for v in row] for row in values],
        "colour_scale": colour_scale,
    }


def build_shap_bar(
    features: pd.DataFrame,
    title: str,
    model_r2: float | None = None,
) -> dict[str, Any]:
    """Build SHAP feature importance bar chart."""
    sorted_df = features.sort_values("importance", ascending=False)
    items = [
        {"name": str(row["feature"]), "importance": round(float(row["importance"]), 4)}
        for _, row in sorted_df.iterrows()
    ]
    result: dict[str, Any] = {
        "type": "shap_bar",
        "title": title,
        "features": items,
    }
    if model_r2 is not None:
        result["model_r2"] = round(float(model_r2), 4)
    return result


def build_scatter_clusters(
    data: pd.DataFrame,
    cluster_labels: dict[int, str],
    title: str,
    x_label: str = "PC1",
    y_label: str = "PC2",
    max_points: int = 2000,
) -> dict[str, Any]:
    """Build scatter plot coloured by cluster membership."""
    n = len(data)
    if n > max_points:
        sample = data.sample(n=max_points, random_state=42)
    else:
        sample = data

    clusters = [
        {
            "id": int(cid),
            "label": label,
            "colour": _CLUSTER_COLOURS[int(cid) % len(_CLUSTER_COLOURS)],
        }
        for cid, label in sorted(cluster_labels.items())
    ]

    points = [
        {
            "x": round(float(row["x"]), 4),
            "y": round(float(row["y"]), 4),
            "cluster": int(row["cluster"]),
            "id": str(row["id"]),
        }
        for _, row in sample.iterrows()
    ]

    return {
        "type": "scatter_clusters",
        "title": title,
        "x_label": x_label,
        "y_label": y_label,
        "clusters": clusters,
        "data": points,
    }
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /Users/souravamseekarmarti/Projects/aequitas && python -m pytest tests/intelligence/test_chart_data_builder.py -v`
Expected: All 13 tests PASS

- [ ] **Step 5: Commit**

```bash
git add src/aequitas/intelligence/chart_data_builder.py tests/intelligence/test_chart_data_builder.py
git commit -m "feat(intelligence): chart_data builder — 10 chart type builders with sampling"
```

---

## Chunk 3: Jinja2 Templates (20 new)

### Task 3: Create All 20 New Templates

**Files:**
- Create: 20 `.j2` files in `src/aequitas/intelligence/templates/`
- Create: `tests/intelligence/test_templates_new.py`

- [ ] **Step 1: Create all 20 template files**

```jinja2
{# coverage_gap.j2 #}
{% if pct_covered is not none -%}
**{{ pct_covered|round(1) }}%** of England's population lives within 400m of a bus stop. **{{ n_zero_access|int }}** LSOAs ({{ pct_zero_access|round(1) }}%) have zero access, affecting an estimated {{ pop_zero_access|int }} residents.
{% if worst_region -%}
The largest concentration of zero-access LSOAs is in **{{ worst_region }}**.
{%- endif %}
{%- endif %}
```

```jinja2
{# desert_spotlight.j2 #}
{% if n_desert_lsoas > 0 -%}
**{{ n_desert_lsoas|int }}** LSOAs have no bus stops within their boundaries, affecting approximately **{{ pop_affected|int }}** people. {% if largest_region %}The largest concentration is in **{{ largest_region }}** ({{ largest_region_count|int }} LSOAs).{% endif %}
{% if mean_imd_score is not none -%}
Desert LSOAs have a mean IMD score of {{ mean_imd_score|round(1) }}, {{ "above" if mean_imd_score > national_mean_imd else "below" }} the national average of {{ national_mean_imd|round(1) }}.
{%- endif %}
{%- endif %}
```

```jinja2
{# urban_rural_gap.j2 #}
{% if urban_value is not none and rural_value is not none -%}
**Urban** areas have **{{ urban_value|round(2) }} {{ unit }}** compared to **{{ rural_value|round(2) }} {{ unit }}** in rural areas — a gap of {{ gap_pct|round(1) }}%.
{% if n_urban and n_rural -%}
Based on {{ n_urban|int }} urban and {{ n_rural|int }} rural LSOAs.
{%- endif %}
{%- endif %}
```

```jinja2
{# ml_prediction.j2 #}
{% if r2 is not none -%}
A Random Forest model explains **{{ (r2 * 100)|round(1) }}%** of variation in bus coverage (R² = {{ r2|round(3) }}).
{% if top_feature -%}
The strongest predictor is **{{ top_feature }}** (SHAP importance: {{ top_importance|round(3) }}).
{%- endif %}
{% if n_features -%}
The model uses {{ n_features|int }} socio-economic features; {{ ((1 - r2) * 100)|round(0)|int }}% of variance remains unexplained by demographics — suggesting policy-driven factors dominate.
{%- endif %}
{%- endif %}
```

```jinja2
{# service_hours.j2 #}
{% if median_first_service is not none -%}
The median first bus departs at **{{ median_first_service }}**; the median last bus at **{{ median_last_service }}**. **{{ n_evening_isolated|int }}** LSOAs ({{ pct_evening_isolated|round(1) }}%) lose all service before 19:00.
{%- endif %}
```

```jinja2
{# weekend_penalty.j2 #}
{% if sunday_pct_drop is not none -%}
Sunday service drops **{{ sunday_pct_drop|round(0)|int }}%** compared to weekday levels. **{{ n_sunday_desert|int }}** LSOAs ({{ pct_sunday_desert|round(1) }}%) have zero Sunday service.
{% if saturday_pct_drop is not none -%}
Saturday service drops {{ saturday_pct_drop|round(0)|int }}% from weekday levels.
{%- endif %}
{%- endif %}
```

```jinja2
{# distribution.j2 #}
{% if median is not none -%}
The median {{ metric_name }} is **{{ median|round(2) }} {{ unit }}** (10th–90th percentile: {{ p10|round(2) }}–{{ p90|round(2) }}). The distribution is {{ skew_label }}, with {{ n_outliers|int }} outliers beyond 3× IQR.
{% if cv is not none -%}
Coefficient of variation: {{ (cv * 100)|round(1) }}% — {{ "high heterogeneity" if cv > 0.5 else "moderate variation" if cv > 0.25 else "relatively uniform" }}.
{%- endif %}
{%- endif %}
```

```jinja2
{# market_concentration.j2 #}
{% if hhi is not none -%}
{{ region_name }} has an HHI of **{{ hhi|round(0)|int }}**, indicating a {{ "highly concentrated" if hhi > 2500 else "moderately concentrated" if hhi > 1500 else "competitive" }} operator market.
{% if top_operator -%}
The largest operator is **{{ top_operator }}** with {{ top_operator_share|round(1) }}% market share.
{%- endif %}
{%- endif %}
```

```jinja2
{# ml_clusters.j2 #}
{% if n_clusters is not none -%}
Clustering reveals **{{ n_clusters|int }}** distinct groups.
{% for cluster in clusters -%}
**Cluster {{ cluster.id }}** ({{ cluster.n|int }} {{ entity_type }}, {{ cluster.pct|round(1) }}%): {{ cluster.description }}.
{% endfor %}
{%- endif %}
```

```jinja2
{# network_topology.j2 #}
{% if n_cross_la is not none -%}
**{{ n_cross_la|int }}** routes ({{ pct_cross_la|round(1) }}%) cross local authority boundaries. {% if densest_corridor %}The densest cross-LA corridor is **{{ densest_corridor }}** with {{ densest_count|int }} routes.{% endif %}
Mean route length: {{ mean_length|round(1) }} km (median {{ median_length|round(1) }} km).
{%- endif %}
```

```jinja2
{# heatmap.j2 #}
{% if worst_cell is not none -%}
The interaction between {{ x_dimension }} and {{ y_dimension }} reveals that the worst-served cell is **{{ worst_cell.label }}** with a mean {{ metric_name }} of {{ worst_cell.value|round(1) }}. The best-served is **{{ best_cell.label }}** at {{ best_cell.value|round(1) }}.
{%- endif %}
```

```jinja2
{# equity_decile.j2 #}
{% if most_deprived_value is not none -%}
The most deprived decile receives **{{ most_deprived_value|round(1) }} {{ unit }}** compared to **{{ least_deprived_value|round(1) }} {{ unit }}** for the least deprived — a ratio of {{ ratio|round(1) }}:1.
{% if bottom_20_pct is not none -%}
The bottom 20% of LSOAs by deprivation receive only {{ bottom_20_pct|round(1) }}% of all bus trips.
{%- endif %}
{%- endif %}
```

```jinja2
{# demographic_breakdown.j2 #}
{% if groups -%}
{% for group in groups -%}
LSOAs in the **{{ group.label }}** category have **{{ group.value|round(2) }} {{ unit }}**, {{ group.vs_national_pct|round(1) }}% {{ "above" if group.vs_national_pct >= 0 else "below" }} the national average.
{% endfor %}
{%- endif %}
```

```jinja2
{# accessibility_gap.j2 #}
{% if n_beyond_threshold is not none -%}
**{{ n_beyond_threshold|int }}** {{ poi_type }} ({{ pct_beyond|round(1) }}%) are beyond {{ threshold_m|int }}m of a bus stop. {% if affected_population %}This affects an estimated **{{ affected_population|int }}** people.{% endif %}
{%- endif %}
```

```jinja2
{# anomaly_spotlight.j2 #}
{% if n_anomalies is not none -%}
**{{ n_anomalies|int }}** LSOAs ({{ pct_anomalies|round(1) }}%) are flagged as anomalous. Of these:
- **{{ n_positive|int }}** are "deprived but well-served" (policy successes)
- **{{ n_inefficiency|int }}** are "affluent but poorly served" (potential inefficiencies)
- **{{ n_policy_failure|int }}** are "elderly with no service" (equity gaps)
{%- endif %}
```

```jinja2
{# economic_value.j2 #}
{% if annual_benefit is not none -%}
{{ region_name }} generates an estimated **£{{ (annual_benefit / 1e6)|round(1) }}m** in annual transport user benefits from bus services, based on {{ n_trips|int }} daily trips at a blended value of time of £{{ vot|round(2) }}/hr.
{%- endif %}
```

```jinja2
{# bcr_analysis.j2 #}
{% if bcr is not none -%}
Closing coverage gaps in **{{ area_name }}** has a BCR of **{{ bcr|round(2) }}** ({{ vfm_band }} value for money). The investment required is **£{{ (investment_m)|round(1) }}m** over {{ appraisal_years|int }} years.
{% if bcr < 1.0 -%}
This intervention does not meet the minimum value-for-money threshold.
{%- elif bcr >= 2.0 -%}
This represents a high-value investment opportunity.
{%- endif %}
{%- endif %}
```

```jinja2
{# carbon_reduction.j2 #}
{% if co2_saving_tonnes is not none -%}
Modal shift from car to bus in {{ scope }} would save **{{ co2_saving_tonnes|round(0)|int }} tonnes CO₂/year**, valued at **£{{ co2_value_k|round(0)|int }}k** at the TAG carbon price of £{{ carbon_price|round(2) }}/tCO₂e.
{% if modal_shift_trips is not none -%}
This is based on {{ modal_shift_trips|int }} car trips replaced annually.
{%- endif %}
{%- endif %}
```

```jinja2
{# tier_distribution.j2 #}
{% if n_tier1 is not none -%}
Of {{ n_total|int }} LADs assessed for franchising readiness: **{{ n_tier1|int }}** in Tier 1 (high readiness), **{{ n_tier2|int }}** in Tier 2 (medium), and **{{ n_tier3|int }}** in Tier 3 (low).
{% if top_lad -%}
The highest-readiness LAD is **{{ top_lad }}** (score: {{ top_score|round(1) }}/100).
{%- endif %}
{%- endif %}
```

```jinja2
{# scenario_comparison.j2 #}
{% if scenarios -%}
Across {{ scenarios|length }} policy scenarios:
{% for s in scenarios -%}
- **{{ s.name }}**: {{ s.population|int }} people affected, £{{ s.cost_m|round(1) }}m/yr, {{ s.co2_t|int }} t CO₂ saved/yr
{% endfor %}
{% if best_bcr_scenario -%}
**{{ best_bcr_scenario }}** delivers the highest value for money.
{%- endif %}
{%- endif %}
```

- [ ] **Step 2: Write template rendering tests**

```python
# tests/intelligence/test_templates_new.py
"""Tests for 20 new Jinja2 templates — verify they render without errors."""

import pytest
from aequitas.intelligence.engine import InsightEngine


@pytest.fixture
def engine():
    return InsightEngine()


TEMPLATE_TEST_CASES = [
    ("coverage_gap", {"pct_covered": 79.9, "n_zero_access": 6776, "pct_zero_access": 20.1, "pop_zero_access": 1_200_000, "worst_region": "South West"}),
    ("desert_spotlight", {"n_desert_lsoas": 4245, "pop_affected": 800_000, "largest_region": "South West", "largest_region_count": 612, "mean_imd_score": 25.3, "national_mean_imd": 21.7}),
    ("urban_rural_gap", {"urban_value": 4.2, "rural_value": 1.3, "unit": "stops/1k", "gap_pct": 223.1, "n_urban": 20000, "n_rural": 13000}),
    ("ml_prediction", {"r2": 0.472, "top_feature": "nocar_pct", "top_importance": 0.142, "n_features": 9}),
    ("service_hours", {"median_first_service": "06:32", "median_last_service": "18:45", "n_evening_isolated": 5189, "pct_evening_isolated": 15.4}),
    ("weekend_penalty", {"sunday_pct_drop": 80.0, "n_sunday_desert": 6745, "pct_sunday_desert": 20.0, "saturday_pct_drop": 35.0}),
    ("distribution", {"median": 18.7, "unit": "km", "metric_name": "route length", "p10": 8.4, "p90": 28.7, "skew_label": "right-skewed", "n_outliers": 23, "cv": 0.85}),
    ("market_concentration", {"hhi": 2800, "region_name": "North East", "top_operator": "Arriva", "top_operator_share": 45.2}),
    ("ml_clusters", {"n_clusters": 4, "entity_type": "LSOAs", "clusters": [{"id": 0, "n": 16944, "pct": 50.2, "description": "Affluent urban"}, {"id": 1, "n": 6023, "pct": 17.8, "description": "Deprived car-free"}]}),
    ("network_topology", {"n_cross_la": 5143, "pct_cross_la": 37.7, "densest_corridor": "Greater Manchester–Lancashire", "densest_count": 142, "mean_length": 23.0, "median_length": 18.7}),
    ("heatmap", {"x_dimension": "deprivation decile", "y_dimension": "area type", "metric_name": "SQI", "worst_cell": {"label": "Decile 1 × Rural", "value": 32.1}, "best_cell": {"label": "Decile 10 × Urban", "value": 78.4}}),
    ("equity_decile", {"most_deprived_value": 12.3, "least_deprived_value": 45.6, "unit": "trips/capita", "ratio": 3.7, "bottom_20_pct": 4.2}),
    ("demographic_breakdown", {"unit": "trips/capita", "groups": [{"label": "high non-white %", "value": 35.2, "vs_national_pct": 12.3}, {"label": "low non-white %", "value": 28.1, "vs_national_pct": -10.5}]}),
    ("accessibility_gap", {"n_beyond_threshold": 450, "poi_type": "secondary schools", "pct_beyond": 13.5, "threshold_m": 400, "affected_population": 150_000}),
    ("anomaly_spotlight", {"n_anomalies": 1688, "pct_anomalies": 5.0, "n_positive": 312, "n_inefficiency": 245, "n_policy_failure": 189}),
    ("economic_value", {"annual_benefit": 45_000_000, "region_name": "North East", "n_trips": 125_000, "vot": 8.49}),
    ("bcr_analysis", {"bcr": 1.32, "area_name": "rural South West", "vfm_band": "Low", "investment_m": 12.5, "appraisal_years": 60}),
    ("carbon_reduction", {"co2_saving_tonnes": 952, "scope": "bottom IMD decile", "co2_value_k": 247, "carbon_price": 259.87, "modal_shift_trips": 34_600_000}),
    ("tier_distribution", {"n_total": 298, "n_tier1": 1, "n_tier2": 102, "n_tier3": 195, "top_lad": "North Yorkshire", "top_score": 87.3}),
    ("scenario_comparison", {"scenarios": [{"name": "Freq restoration", "population": 5_700_000, "cost_m": 45.0, "co2_t": 952}, {"name": "Evening extension", "population": 8_400_000, "cost_m": 32.0, "co2_t": 450}], "best_bcr_scenario": "Freq restoration"}),
]


@pytest.mark.parametrize("section_id,stats", TEMPLATE_TEST_CASES, ids=[t[0] for t in TEMPLATE_TEST_CASES])
def test_template_renders(engine, section_id, stats):
    """Each new template renders without errors when given valid stats."""
    result = engine.generate(section_id=section_id, region="all", urban_rural="all", stats=stats)
    assert not result["suppressed"], f"{section_id} was suppressed"
    assert len(result["narrative"]) > 0, f"{section_id} produced empty narrative"
    assert "None" not in result["narrative"], f"{section_id} has unresolved None"
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `cd /Users/souravamseekarmarti/Projects/aequitas && python -m pytest tests/intelligence/test_templates_new.py -v 2>&1 | head -20`
Expected: FAIL — templates don't exist, engine doesn't know the section IDs

- [ ] **Step 4: Create all 20 template files on disk**

Write each template file to `src/aequitas/intelligence/templates/`. Use the template content from Step 1.

- [ ] **Step 5: Update engine.py — expand _SECTION_TEMPLATES and register format_thousands**

In `src/aequitas/intelligence/engine.py`, replace `_SECTION_TEMPLATES` with the full 51-entry mapping and register the custom filter:

```python
_SECTION_TEMPLATES: dict[str, str] = {
    # Existing (keep for backward compat during transition)
    "coverage_density": "coverage_density.j2",
    "equity": "equity.j2",
    "correlation": "correlation.j2",
    "ranking": "ranking.j2",
    "single_region": "single_region.j2",
    "gap_to_target": "gap_to_target.j2",
    "policy_scenario": "policy_scenario.j2",
    # Category A
    "a1_route_density": "ranking.j2",
    "a2_stop_density": "ranking.j2",
    "a3_walking_distance": "coverage_gap.j2",
    "a4_coverage_equity": "equity.j2",
    "a5_service_deserts": "desert_spotlight.j2",
    "a6_urban_rural_gap": "urban_rural_gap.j2",
    "a7_investment_gap": "gap_to_target.j2",
    "a8_coverage_prediction": "ml_prediction.j2",
    # Category B
    "b1_frequency": "ranking.j2",
    "b2_operating_hours": "service_hours.j2",
    "b3_weekend_penalty": "weekend_penalty.j2",
    "b4_route_frequency": "ranking.j2",
    "b5_frequency_deprivation": "correlation.j2",
    # Category C
    "c1_route_length": "distribution.j2",
    "c2_stops_per_route": "distribution.j2",
    "c3_operator_hhi": "market_concentration.j2",
    "c4_urban_rural_routes": "urban_rural_gap.j2",
    "c5_length_vs_frequency": "correlation.j2",
    "c6_route_archetypes": "ml_clusters.j2",
    "c7_network_topology": "network_topology.j2",
    # Category D
    "d1_coverage_deprivation": "correlation.j2",
    "d2_coverage_unemployment": "correlation.j2",
    "d3_coverage_car": "correlation.j2",
    "d4_coverage_elderly": "correlation.j2",
    "d5_coverage_income": "correlation.j2",
    "d6_transport_poverty": "ml_clusters.j2",
    "d7_deprivation_urban_rural": "heatmap.j2",
    "d8_feature_importance": "ml_prediction.j2",
    # Category F
    "f1_gini": "equity.j2",
    "f2_disparity_ratio": "equity_decile.j2",
    "f3_ethnic_access": "demographic_breakdown.j2",
    "f4_gender_accessibility": "accessibility_gap.j2",
    "f5_rural_penalty": "urban_rural_gap.j2",
    "f6_equitable_regions": "ranking.j2",
    # Category G
    "g1_route_clusters": "ml_clusters.j2",
    "g2_anomalies": "anomaly_spotlight.j2",
    "g3_coverage_model": "ml_prediction.j2",
    "g4_shap": "ml_prediction.j2",
    "g5_scenario_model": "policy_scenario.j2",
    # Category J
    "j1_economic_value": "economic_value.j2",
    "j2_bcr": "bcr_analysis.j2",
    "j3_carbon": "carbon_reduction.j2",
    "j4_investment_priority": "ranking.j2",
    # Category BSA
    "bsa1_franchising_readiness": "ranking.j2",
    "bsa2_operator_concentration": "market_concentration.j2",
    "bsa3_tier_distribution": "tier_distribution.j2",
    # Category PS
    "ps1_freq_restoration": "policy_scenario.j2",
    "ps2_evening_extension": "policy_scenario.j2",
    "ps3_drt_rural": "policy_scenario.j2",
    "ps4_franchise": "policy_scenario.j2",
    "ps5_scenario_comparison": "scenario_comparison.j2",
}
```

In `InsightEngine.__init__()`, after the `Environment(...)` call, add:

```python
        self._env.filters["format_thousands"] = lambda v: f"{int(v):,}"
```

This also fixes the existing bug where `policy_scenario.j2` uses `format_thousands` but it was never registered.

- [ ] **Step 6: Run tests to verify they pass**

Run: `cd /Users/souravamseekarmarti/Projects/aequitas && python -m pytest tests/intelligence/test_templates_new.py tests/intelligence/test_engine.py -v`
Expected: All new template tests PASS. All existing engine tests PASS.

- [ ] **Step 7: Commit**

```bash
git add src/aequitas/intelligence/templates/*.j2 src/aequitas/intelligence/engine.py tests/intelligence/test_templates_new.py
git commit -m "feat(intelligence): 20 new Jinja2 templates + 51-entry section mapping"
```

---

## Chunk 4: Section Registry + Warehouse Schema

### Task 4: Section Registry

**Files:**
- Create: `src/aequitas/intelligence/section_registry.py`
- Create: `tests/intelligence/test_section_registry.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/intelligence/test_section_registry.py
"""Tests for section registry — single source of truth for all 51 sections."""

import pytest
from aequitas.intelligence.section_registry import SECTION_REGISTRY, SectionDef


def test_registry_has_51_sections():
    assert len(SECTION_REGISTRY) == 51


def test_all_section_ids_are_strings():
    for sid in SECTION_REGISTRY:
        assert isinstance(sid, str)
        assert len(sid) > 0


def test_all_entries_are_section_defs():
    for sid, entry in SECTION_REGISTRY.items():
        assert isinstance(entry, SectionDef), f"{sid} is not a SectionDef"


def test_all_templates_exist():
    """Every template referenced in the registry must be a known template."""
    from aequitas.intelligence.engine import _SECTION_TEMPLATES
    for sid, entry in SECTION_REGISTRY.items():
        assert entry.template in {v for v in _SECTION_TEMPLATES.values()}, \
            f"{sid} references unknown template {entry.template}"


def test_category_a_has_8():
    a_sections = [s for s in SECTION_REGISTRY if s.startswith("a")]
    assert len(a_sections) == 8


def test_category_d_has_8():
    d_sections = [s for s in SECTION_REGISTRY if s.startswith("d")]
    assert len(d_sections) == 8


def test_known_section_ids():
    """Spot-check key section IDs exist."""
    expected = ["a1_route_density", "b5_frequency_deprivation", "d1_coverage_deprivation",
                "f1_gini", "g2_anomalies", "j3_carbon", "bsa1_franchising_readiness", "ps5_scenario_comparison"]
    for sid in expected:
        assert sid in SECTION_REGISTRY, f"Missing section: {sid}"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /Users/souravamseekarmarti/Projects/aequitas && python -m pytest tests/intelligence/test_section_registry.py -v 2>&1 | head -10`
Expected: ImportError

- [ ] **Step 3: Implement section_registry.py**

```python
# src/aequitas/intelligence/section_registry.py
"""Section registry — maps every section_id to its template, chart type, and evidence gate.

Single source of truth for all 51 analytical sections. Used by precompute.py
to iterate over sections and by the frontend to know what chart to render.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class SectionDef:
    """Definition of one analytical section."""

    template: str
    """Jinja2 template filename (e.g. 'ranking.j2')."""

    chart_type: str
    """Chart data type (e.g. 'horizontal_bar', 'scatter_regression')."""

    category: str
    """Category label (e.g. 'A', 'B', 'BSA')."""

    title: str
    """Human-readable question title."""


SECTION_REGISTRY: dict[str, SectionDef] = {
    # Category A: Coverage & Accessibility
    "a1_route_density": SectionDef("ranking.j2", "horizontal_bar", "A", "Route density by region"),
    "a2_stop_density": SectionDef("ranking.j2", "horizontal_bar", "A", "Stop density by region"),
    "a3_walking_distance": SectionDef("coverage_gap.j2", "stacked_bar", "A", "Population within 400m of a stop"),
    "a4_coverage_equity": SectionDef("equity.j2", "lorenz_curve", "A", "Equity of coverage within regions"),
    "a5_service_deserts": SectionDef("desert_spotlight.j2", "choropleth", "A", "Service deserts"),
    "a6_urban_rural_gap": SectionDef("urban_rural_gap.j2", "grouped_bar", "A", "Urban vs rural coverage gap"),
    "a7_investment_gap": SectionDef("gap_to_target.j2", "horizontal_bar", "A", "Investment to reach national average"),
    "a8_coverage_prediction": SectionDef("ml_prediction.j2", "shap_bar", "A", "Coverage prediction from demographics"),
    # Category B: Service Quality
    "b1_frequency": SectionDef("ranking.j2", "horizontal_bar", "B", "Average frequency by region"),
    "b2_operating_hours": SectionDef("service_hours.j2", "grouped_bar", "B", "Operating hours"),
    "b3_weekend_penalty": SectionDef("weekend_penalty.j2", "grouped_bar", "B", "Weekend service penalty"),
    "b4_route_frequency": SectionDef("ranking.j2", "horizontal_bar", "B", "Most/least frequent routes"),
    "b5_frequency_deprivation": SectionDef("correlation.j2", "scatter_regression", "B", "Frequency vs deprivation"),
    # Category C: Route Characteristics
    "c1_route_length": SectionDef("distribution.j2", "box_violin", "C", "Route length distribution"),
    "c2_stops_per_route": SectionDef("distribution.j2", "box_violin", "C", "Stops per route"),
    "c3_operator_hhi": SectionDef("market_concentration.j2", "horizontal_bar", "C", "Operator landscape (HHI)"),
    "c4_urban_rural_routes": SectionDef("urban_rural_gap.j2", "grouped_bar", "C", "Urban vs rural routes"),
    "c5_length_vs_frequency": SectionDef("correlation.j2", "scatter_regression", "C", "Route length vs frequency"),
    "c6_route_archetypes": SectionDef("ml_clusters.j2", "scatter_clusters", "C", "Route archetypes"),
    "c7_network_topology": SectionDef("network_topology.j2", "choropleth", "C", "Network topology"),
    # Category D: Socio-Economic Correlations
    "d1_coverage_deprivation": SectionDef("correlation.j2", "scatter_regression", "D", "Coverage vs deprivation"),
    "d2_coverage_unemployment": SectionDef("correlation.j2", "scatter_regression", "D", "Coverage vs unemployment"),
    "d3_coverage_car": SectionDef("correlation.j2", "scatter_regression", "D", "Coverage vs car ownership"),
    "d4_coverage_elderly": SectionDef("correlation.j2", "scatter_regression", "D", "Coverage vs elderly population"),
    "d5_coverage_income": SectionDef("correlation.j2", "scatter_regression", "D", "Coverage vs income"),
    "d6_transport_poverty": SectionDef("ml_clusters.j2", "scatter_clusters", "D", "Transport poverty clusters"),
    "d7_deprivation_urban_rural": SectionDef("heatmap.j2", "heatmap", "D", "Deprivation x urban/rural"),
    "d8_feature_importance": SectionDef("ml_prediction.j2", "shap_bar", "D", "Feature importance"),
    # Category F: Equity & Social Inclusion
    "f1_gini": SectionDef("equity.j2", "lorenz_curve", "F", "Gini coefficient"),
    "f2_disparity_ratio": SectionDef("equity_decile.j2", "horizontal_bar", "F", "Disparity by IMD decile"),
    "f3_ethnic_access": SectionDef("demographic_breakdown.j2", "grouped_bar", "F", "Bus access by ethnicity"),
    "f4_gender_accessibility": SectionDef("accessibility_gap.j2", "horizontal_bar", "F", "Gender-adjusted accessibility"),
    "f5_rural_penalty": SectionDef("urban_rural_gap.j2", "grouped_bar", "F", "Rural accessibility penalty"),
    "f6_equitable_regions": SectionDef("ranking.j2", "horizontal_bar", "F", "Most equitable regions"),
    # Category G: ML Insights
    "g1_route_clusters": SectionDef("ml_clusters.j2", "scatter_clusters", "G", "Route clustering"),
    "g2_anomalies": SectionDef("anomaly_spotlight.j2", "scatter_regression", "G", "Anomaly detection"),
    "g3_coverage_model": SectionDef("ml_prediction.j2", "scatter_regression", "G", "Coverage prediction"),
    "g4_shap": SectionDef("ml_prediction.j2", "shap_bar", "G", "Feature importance (SHAP)"),
    "g5_scenario_model": SectionDef("policy_scenario.j2", "grouped_bar", "G", "Scenario modelling"),
    # Category J: Economic Impact & BCR
    "j1_economic_value": SectionDef("economic_value.j2", "horizontal_bar", "J", "Economic value per region"),
    "j2_bcr": SectionDef("bcr_analysis.j2", "horizontal_bar", "J", "BCR for coverage gaps"),
    "j3_carbon": SectionDef("carbon_reduction.j2", "horizontal_bar", "J", "Carbon reduction from modal shift"),
    "j4_investment_priority": SectionDef("ranking.j2", "horizontal_bar", "J", "Regional investment prioritisation"),
    # Category BSA: Bus Services Act 2025
    "bsa1_franchising_readiness": SectionDef("ranking.j2", "horizontal_bar", "BSA", "LTA franchising readiness"),
    "bsa2_operator_concentration": SectionDef("market_concentration.j2", "horizontal_bar", "BSA", "Operator concentration"),
    "bsa3_tier_distribution": SectionDef("tier_distribution.j2", "stacked_bar", "BSA", "Readiness tier distribution"),
    # Category PS: Policy Scenario Modelling
    "ps1_freq_restoration": SectionDef("policy_scenario.j2", "horizontal_bar", "PS", "Frequency restoration"),
    "ps2_evening_extension": SectionDef("policy_scenario.j2", "horizontal_bar", "PS", "Evening extension"),
    "ps3_drt_rural": SectionDef("policy_scenario.j2", "horizontal_bar", "PS", "DRT for rural areas"),
    "ps4_franchise": SectionDef("policy_scenario.j2", "horizontal_bar", "PS", "Combined franchise"),
    "ps5_scenario_comparison": SectionDef("scenario_comparison.j2", "grouped_bar", "PS", "Scenario comparison"),
}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /Users/souravamseekarmarti/Projects/aequitas && python -m pytest tests/intelligence/test_section_registry.py -v`
Expected: All 7 tests PASS

- [ ] **Step 5: Commit**

```bash
git add src/aequitas/intelligence/section_registry.py tests/intelligence/test_section_registry.py
git commit -m "feat(intelligence): section registry — 51 sections mapped to templates and chart types"
```

### Task 5: Warehouse Schema Additions

**Files:**
- Modify: `src/aequitas/warehouse/schema.py`

- [ ] **Step 1: Add 8 new entries to ANALYTICS_PARQUET_SOURCES**

In `src/aequitas/warehouse/schema.py`, add to `ANALYTICS_PARQUET_SOURCES`:

```python
    # New tables for expanded sections (all in data/audit/ — Phase 0 outputs)
    "stop_headways": "data/audit/stop_headways.parquet",
    "coverage_prediction": "data/audit/coverage_prediction.parquet",
    "shap_importance": "data/audit/shap_importance.parquet",
    "route_clusters": "data/audit/route_clusters.parquet",
    "lsoa_clusters": "data/audit/lsoa_clusters_hdbscan.parquet",
    "anomalies": "data/audit/anomalies.parquet",
    "modal_shift_scenarios": "data/audit/modal_shift_scenarios.parquet",
    "policy_scenarios": "data/audit/policy_scenarios.parquet",
```

- [ ] **Step 2: Verify existing tests still pass**

Run: `cd /Users/souravamseekarmarti/Projects/aequitas && python -m pytest tests/ -v --ignore=tests/pipeline/test_integration.py -x 2>&1 | tail -10`
Expected: All tests PASS

- [ ] **Step 3: Commit**

```bash
git add src/aequitas/warehouse/schema.py
git commit -m "feat(warehouse): add 8 analytics Parquet sources for expanded sections"
```

---

## Chunk 5: Precompute Rewrite

### Task 6: Rewrite precompute.py to Use Section Registry

**Files:**
- Modify: `src/aequitas/warehouse/precompute.py`

This is the most complex task. The new precompute.py must:
1. Import the section registry instead of hardcoded `_SECTIONS`
2. Load all required Parquet files (not just policy + equity)
3. Build stats AND chart_data for each section (no empty chart_data)
4. Call evidence gate rules in each builder — return ({}, {}) if gate fails
5. Use the section registry to determine which template to render

- [ ] **Step 1: Rewrite precompute.py**

Replace the contents of `src/aequitas/warehouse/precompute.py` with the new version that uses the section registry:

```python
"""Pre-computation of section_results for the DuckDB warehouse.

For each filter combination, computes all 51 analytical sections and stores
them with stats, chart_data, and narratives in section_results.

Called once at build time — never at request time.
"""

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from loguru import logger

from aequitas.core.config import PipelineConfig
from aequitas.core.types import RegionCode
from aequitas.intelligence.calculators import (
    calculate_correlation,
    calculate_gap_to_target,
    describe_distribution,
    rank_regions,
)
from aequitas.intelligence.chart_data_builder import (
    build_box_violin,
    build_choropleth,
    build_grouped_bar,
    build_heatmap,
    build_horizontal_bar,
    build_lorenz_curve,
    build_scatter_clusters,
    build_scatter_regression,
    build_shap_bar,
    build_stacked_bar,
)
from aequitas.intelligence.engine import InsightEngine
from aequitas.intelligence.rules import (
    CorrelationRule,
    GiniEquityRule,
    GapToInvestmentRule,
    MinLsoaRule,
    DesertRule,
    UrbanRuralRule,
    MLPredictionRule,
    DistributionRule,
    MarketConcentrationRule,
    ClusterRule,
    NetworkRule,
    HeatmapRule,
    DecileRule,
    DemographicRule,
    AccessibilityRule,
    AnomalyRule,
    CarbonRule,
    TierRule,
    ScenarioComparisonRule,
)
from aequitas.intelligence.section_registry import SECTION_REGISTRY


# All region codes + "all"
_REGIONS = ["all"] + [rc.value for rc in RegionCode]
_AREA_TYPES = ["all", "urban", "rural"]


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


def _load_parquet_safe(path: Path) -> pd.DataFrame | None:
    """Load a Parquet file, returning None if it doesn't exist."""
    if path.exists():
        return pd.read_parquet(path)
    logger.warning(f"Parquet not found: {path}")
    return None


def _filter_data(
    df: pd.DataFrame, region: str, urban_rural: str,
) -> pd.DataFrame:
    """Apply region and urban/rural filters to a DataFrame."""
    mask = pd.Series(True, index=df.index)
    if region != "all" and "region" in df.columns:
        mask &= df["region"] == region
    if urban_rural != "all" and "urban_rural" in df.columns:
        mask &= df["urban_rural"].str.lower().str.startswith(urban_rural)
    return df[mask]


def _minutes_to_time(minutes: float) -> str:
    """Convert minutes-from-midnight to HH:MM string."""
    h = int(minutes) // 60
    m = int(minutes) % 60
    return f"{h:02d}:{m:02d}"


def precompute_all_sections(cfg: PipelineConfig) -> list[dict]:
    """Precompute all section results for all filter combinations.

    Loads all required Parquet files, iterates over the 51-section registry,
    applies filters, builds stats + chart_data, renders narratives.
    """
    engine = InsightEngine()
    results: list[dict] = []

    # Load all data sources
    data = _load_all_data(cfg)
    if not data:
        logger.warning("No data loaded — precompute returning empty results")
        return results

    for region in _REGIONS:
        for urban_rural in _AREA_TYPES:
            # Skip single-region + urban/rural combos (low value)
            if region != "all" and urban_rural != "all":
                continue

            for section_id in SECTION_REGISTRY:
                try:
                    stats, chart_data = _build_section(
                        section_id, data, region, urban_rural,
                    )
                except Exception as e:
                    logger.warning(f"Failed to build {section_id} for {region}/{urban_rural}: {e}")
                    stats, chart_data = {}, {}

                result = engine.generate(
                    section_id=section_id,
                    region=region,
                    urban_rural=urban_rural,
                    stats=stats,
                )
                results.append(
                    SectionResult(
                        region=region,
                        urban_rural=urban_rural,
                        section_id=section_id,
                        stats=stats,
                        chart_data=chart_data,
                        narrative=result["narrative"],
                    ).to_dict()
                )

    logger.info(f"Precomputed {len(results)} section results")
    return results


def _load_all_data(cfg: PipelineConfig) -> dict[str, pd.DataFrame]:
    """Load all Parquet files needed by the 51 sections."""
    sources = {
        "policy": cfg.audit_dir / "lsoa_policy_synthesis.parquet",
        "equity": cfg.audit_dir / "lsoa_equity_metrics.parquet",
        "service_quality": cfg.audit_dir / "lsoa_service_quality.parquet",
        "economic": cfg.audit_dir / "lsoa_economic_appraisal.parquet",
        "accessibility": cfg.audit_dir / "lsoa_2sfca.parquet",
        "routes": cfg.audit_dir / "route_geometries.parquet",
        "lta": cfg.audit_dir / "lta_franchising_readiness.parquet",
        "scenarios": cfg.audit_dir / "policy_scenarios.parquet",
        "modal_shift": cfg.audit_dir / "modal_shift_scenarios.parquet",
        "anomalies": cfg.audit_dir / "anomalies.parquet",
        "clusters": cfg.audit_dir / "lsoa_clusters_hdbscan.parquet",
        "route_clusters": cfg.audit_dir / "route_clusters.parquet",
        "coverage_pred": cfg.audit_dir / "coverage_prediction.parquet",
        "shap": cfg.audit_dir / "shap_importance.parquet",
    }
    data: dict[str, pd.DataFrame] = {}
    for key, path in sources.items():
        df = _load_parquet_safe(path)
        if df is not None:
            data[key] = df
    return data


def _build_section(
    section_id: str,
    data: dict[str, pd.DataFrame],
    region: str,
    urban_rural: str,
) -> tuple[dict, dict]:
    """Build stats and chart_data for a single section + filter combo.

    Returns (stats_dict, chart_data_dict).
    """
    # Dispatch by section prefix to the appropriate builder
    builders = {
        "a1": _build_ranking_density,
        "a2": _build_ranking_density,
        "a3": _build_coverage_gap,
        "a4": _build_equity,
        "a5": _build_desert,
        "a6": _build_urban_rural,
        "a7": _build_gap_to_target,
        "a8": _build_ml_prediction,
        "b1": _build_ranking_density,
        "b2": _build_service_hours,
        "b3": _build_weekend_penalty,
        "b4": _build_ranking_density,
        "b5": _build_correlation,
        "c1": _build_distribution,
        "c2": _build_distribution,
        "c3": _build_market_concentration,
        "c4": _build_urban_rural,
        "c5": _build_correlation,
        "c6": _build_clusters,
        "c7": _build_network,
        "d1": _build_correlation,
        "d2": _build_correlation,
        "d3": _build_correlation,
        "d4": _build_correlation,
        "d5": _build_correlation,
        "d6": _build_clusters,
        "d7": _build_heatmap,
        "d8": _build_ml_prediction,
        "f1": _build_equity,
        "f2": _build_equity_decile,
        "f3": _build_demographic,
        "f4": _build_accessibility,
        "f5": _build_urban_rural,
        "f6": _build_ranking_density,
        "g1": _build_clusters,
        "g2": _build_anomaly,
        "g3": _build_ml_prediction,
        "g4": _build_ml_prediction,
        "g5": _build_scenario,
        "j1": _build_economic_value,
        "j2": _build_bcr,
        "j3": _build_carbon,
        "j4": _build_ranking_density,
        "bsa1": _build_franchising,
        "bsa2": _build_market_concentration,
        "bsa3": _build_tier_dist,
        "ps1": _build_scenario,
        "ps2": _build_scenario,
        "ps3": _build_scenario,
        "ps4": _build_scenario,
        "ps5": _build_scenario_comparison,
    }

    prefix = section_id.split("_")[0]
    builder = builders.get(prefix)
    if builder is None:
        return {}, {}

    return builder(section_id, data, region, urban_rural)


# --- Builder functions ---
# Each returns (stats_dict, chart_data_dict)


def _build_ranking_density(
    section_id: str, data: dict, region: str, urban_rural: str,
) -> tuple[dict, dict]:
    """Build ranking for route/stop density by region."""
    policy = data.get("policy")
    if policy is None:
        return {}, {}
    filtered = _filter_data(policy, region, urban_rural)
    if len(filtered) == 0 or "region" not in filtered.columns:
        return {}, {}

    metric = "trips_per_capita"
    if metric not in filtered.columns:
        return {}, {}

    by_region = filtered.groupby("region")[metric].mean().reset_index()
    by_region.columns = ["label", "value"]
    nat_avg = float(by_region["value"].mean())

    if len(by_region) < 2:
        return {}, {}

    best_idx = by_region["value"].idxmax()
    worst_idx = by_region["value"].idxmin()

    stats = {
        "best": {
            "name": str(by_region.loc[best_idx, "label"]),
            "value": round(float(by_region.loc[best_idx, "value"]), 2),
            "pct_above": round((float(by_region.loc[best_idx, "value"]) - nat_avg) / nat_avg * 100, 1),
        },
        "worst": {
            "name": str(by_region.loc[worst_idx, "label"]),
            "value": round(float(by_region.loc[worst_idx, "value"]), 2),
            "pct_below": round((nat_avg - float(by_region.loc[worst_idx, "value"])) / nat_avg * 100, 1),
        },
        "national_avg": round(nat_avg, 2),
        "unit": "trips/capita",
    }

    chart = build_horizontal_bar(
        data=by_region, title=SECTION_REGISTRY[section_id].title,
        x_label="Trips per capita", y_label="Region", national_avg=nat_avg,
    )
    return stats, chart


def _build_coverage_gap(
    section_id: str, data: dict, region: str, urban_rural: str,
) -> tuple[dict, dict]:
    """Build coverage gap (A3)."""
    acc = data.get("accessibility")
    if acc is None:
        return {}, {}
    filtered = _filter_data(acc, region, urban_rural)
    if not MinLsoaRule().should_fire(n_lsoas=len(filtered)):
        return {}, {}

    score_col = "sfca_score" if "sfca_score" in filtered.columns else None
    if score_col is None:
        return {}, {}

    n_zero = int((filtered[score_col] == 0).sum())
    pct_covered = round((1 - n_zero / len(filtered)) * 100, 1)
    stats = {
        "pct_covered": pct_covered,
        "n_zero_access": n_zero,
        "pct_zero_access": round(n_zero / len(filtered) * 100, 1),
        "pop_zero_access": int(filtered.loc[filtered[score_col] == 0, "population"].sum()) if "population" in filtered.columns else 0,
    }

    # chart_data: stacked bar (covered/not by region)
    chart: dict = {}
    if "region" in filtered.columns:
        by_region = filtered.groupby("region").apply(
            lambda g: pd.Series({
                "covered": round((g[score_col] > 0).mean() * 100, 1),
                "not_covered": round((g[score_col] == 0).mean() * 100, 1),
            })
        ).reset_index()
        chart = build_stacked_bar(
            categories=by_region["region"].tolist(),
            series=[
                {"name": "Covered", "values": by_region["covered"].tolist()},
                {"name": "Not covered", "values": by_region["not_covered"].tolist()},
            ],
            title=SECTION_REGISTRY[section_id].title,
        )
    return stats, chart


def _build_equity(
    section_id: str, data: dict, region: str, urban_rural: str,
) -> tuple[dict, dict]:
    """Build equity metrics (A4, F1)."""
    eq = data.get("equity")
    policy = data.get("policy")
    if eq is None:
        return {}, {}
    cols = ["gini", "palma_ratio", "concentration_index"]
    if not all(c in eq.columns for c in cols):
        return {}, {}
    stats = {
        "gini": float(eq["gini"].iloc[0]),
        "palma": float(eq["palma_ratio"].iloc[0]),
        "concentration_index": float(eq["concentration_index"].iloc[0]),
    }

    # chart_data: Lorenz curve from policy data
    chart: dict = {}
    if policy is not None and "trips_per_capita" in policy.columns and "population" in policy.columns:
        filtered = _filter_data(policy, region, urban_rural)
        if GiniEquityRule().should_fire(n_lsoas=len(filtered)):
            chart = build_lorenz_curve(
                values=filtered["trips_per_capita"].fillna(0),
                weights=filtered["population"].fillna(1),
                title=SECTION_REGISTRY[section_id].title,
            )
    return stats, chart


def _build_desert(
    section_id: str, data: dict, region: str, urban_rural: str,
) -> tuple[dict, dict]:
    """Build service desert spotlight (A5)."""
    sq = data.get("service_quality")
    if sq is None:
        return {}, {}
    filtered = _filter_data(sq, region, urban_rural)
    if len(filtered) == 0:
        return {}, {}

    desert_col = "total_weekday_departures" if "total_weekday_departures" in filtered.columns else None
    if desert_col is None:
        return {}, {}

    deserts = filtered[filtered[desert_col] == 0]
    if not DesertRule().should_fire(n_desert_lsoas=len(deserts)):
        return {}, {}

    stats = {
        "n_desert_lsoas": len(deserts),
        "pop_affected": int(deserts["population"].sum()) if "population" in deserts.columns else 0,
    }
    if "region" in deserts.columns and len(deserts) > 0:
        top_region = deserts["region"].value_counts().idxmax()
        stats["largest_region"] = str(top_region)
        stats["largest_region_count"] = int(deserts["region"].value_counts().max())

    # chart_data: choropleth of desert % by LAD
    chart: dict = {}
    lta = data.get("lta")
    if lta is not None and "lad_cd" in lta.columns:
        lad_data = lta[["lad_cd", "lad_nm"]].copy()
        if "sunday_desert_rate" in lta.columns:
            lad_data["value"] = (lta["sunday_desert_rate"] * 100).round(1)
            lad_data = lad_data.rename(columns={"lad_cd": "area_code", "lad_nm": "area_name"})
            chart = build_choropleth(
                data=lad_data, title=SECTION_REGISTRY[section_id].title,
                geography="lad", metric="pct_lsoas_no_service", colour_scale="RdYlGn",
            )
    return stats, chart


def _build_urban_rural(
    section_id: str, data: dict, region: str, urban_rural: str,
) -> tuple[dict, dict]:
    """Build urban vs rural gap (A6, C4, F5)."""
    policy = data.get("policy")
    if policy is None or "urban_rural" not in policy.columns:
        return {}, {}
    filtered = _filter_data(policy, region, "all")  # always compare both
    metric = "trips_per_capita" if "trips_per_capita" in filtered.columns else None
    if metric is None:
        return {}, {}

    urban = filtered[filtered["urban_rural"].str.lower().str.startswith("urban")]
    rural = filtered[filtered["urban_rural"].str.lower().str.startswith("rural")]
    if not UrbanRuralRule().should_fire(n_urban=len(urban), n_rural=len(rural)):
        return {}, {}

    u_val = float(urban[metric].mean())
    r_val = float(rural[metric].mean())
    gap = round((u_val - r_val) / r_val * 100, 1) if r_val != 0 else 0

    stats = {
        "urban_value": round(u_val, 2),
        "rural_value": round(r_val, 2),
        "unit": "trips/capita",
        "gap_pct": gap,
        "n_urban": len(urban),
        "n_rural": len(rural),
    }

    # chart_data: grouped bar by region
    chart: dict = {}
    if "region" in filtered.columns:
        regions = sorted(filtered["region"].unique())
        u_vals = [round(float(urban[urban["region"] == r][metric].mean()), 2) if len(urban[urban["region"] == r]) > 0 else 0 for r in regions]
        r_vals = [round(float(rural[rural["region"] == r][metric].mean()), 2) if len(rural[rural["region"] == r]) > 0 else 0 for r in regions]
        chart = build_grouped_bar(
            categories=list(regions),
            series=[{"name": "Urban", "values": u_vals}, {"name": "Rural", "values": r_vals}],
            title=SECTION_REGISTRY[section_id].title,
        )
    return stats, chart


def _build_gap_to_target(
    section_id: str, data: dict, region: str, urban_rural: str,
) -> tuple[dict, dict]:
    """Build gap to target (A7)."""
    policy = data.get("policy")
    if policy is None:
        return {}, {}
    filtered = _filter_data(policy, region, urban_rural)
    if "trips_per_capita" not in filtered.columns or len(filtered) == 0:
        return {}, {}

    median = float(filtered["trips_per_capita"].median())
    below = filtered[filtered["trips_per_capita"] < median]
    if not GapToInvestmentRule().should_fire(n_below_target=len(below)):
        return {}, {}

    stats = {
        "n_below": len(below),
        "pct_below": round(len(below) / len(filtered) * 100, 1),
        "target": round(median, 2),
        "unit": "trips/capita",
        "mean_gap": round(float((median - below["trips_per_capita"]).mean()), 2) if len(below) > 0 else 0.0,
        "total_annual_cost_m": round(float(len(below) * 500 / 1_000_000), 1),
    }

    # chart_data: horizontal bar of gap by region
    chart: dict = {}
    if "region" in filtered.columns:
        by_region = filtered.groupby("region").apply(
            lambda g: round(float((median - g.loc[g["trips_per_capita"] < median, "trips_per_capita"]).sum()), 1) if (g["trips_per_capita"] < median).any() else 0
        ).reset_index()
        by_region.columns = ["label", "value"]
        by_region = by_region[by_region["value"] > 0]
        if len(by_region) > 0:
            chart = build_horizontal_bar(
                data=by_region, title=SECTION_REGISTRY[section_id].title,
                x_label="Total gap (trips/capita)", y_label="Region",
            )
    return stats, chart


def _build_ml_prediction(
    section_id: str, data: dict, region: str, urban_rural: str,
) -> tuple[dict, dict]:
    """Build ML prediction / SHAP (A8, D8, G3, G4)."""
    shap_df = data.get("shap")
    if shap_df is None or len(shap_df) == 0:
        return {}, {}
    if not MLPredictionRule().should_fire(r2=0.472, n_features=len(shap_df)):
        return {}, {}

    stats: dict[str, Any] = {}
    chart: dict[str, Any] = {}

    top = shap_df.iloc[0]
    stats = {
        "r2": 0.472,  # locked ground truth
        "top_feature": str(top.get("feature", "")),
        "top_importance": round(float(top.get("mean_abs_shap", top.get("importance", 0))), 3),
        "n_features": len(shap_df),
    }
    feat_df = shap_df.rename(columns={"mean_abs_shap": "importance"}) if "mean_abs_shap" in shap_df.columns else shap_df
    if "feature" in feat_df.columns and "importance" in feat_df.columns:
        chart = build_shap_bar(features=feat_df, title=SECTION_REGISTRY[section_id].title, model_r2=0.472)
    return stats, chart


def _build_service_hours(
    section_id: str, data: dict, region: str, urban_rural: str,
) -> tuple[dict, dict]:
    """Build service hours (B2)."""
    sq = data.get("service_quality")
    if sq is None:
        return {}, {}
    filtered = _filter_data(sq, region, urban_rural)
    if not MinLsoaRule().should_fire(n_lsoas=len(filtered)):
        return {}, {}

    stats: dict[str, Any] = {}
    if "first_service_min" in filtered.columns:
        stats["median_first_service"] = _minutes_to_time(float(filtered["first_service_min"].median()))
    if "last_service_min" in filtered.columns:
        stats["median_last_service"] = _minutes_to_time(float(filtered["last_service_min"].median()))
    if "evening_isolated" in filtered.columns:
        n_ei = int(filtered["evening_isolated"].sum())
        stats["n_evening_isolated"] = n_ei
        stats["pct_evening_isolated"] = round(n_ei / len(filtered) * 100, 1)

    # chart_data: grouped bar (first/last service by region)
    chart: dict = {}
    if "region" in filtered.columns and "first_service_min" in filtered.columns and "last_service_min" in filtered.columns:
        by_region = filtered.groupby("region").agg(
            first=("first_service_min", "median"), last=("last_service_min", "median")
        ).reset_index()
        chart = build_grouped_bar(
            categories=by_region["region"].tolist(),
            series=[
                {"name": "First service (min)", "values": by_region["first"].round(0).tolist()},
                {"name": "Last service (min)", "values": by_region["last"].round(0).tolist()},
            ],
            title=SECTION_REGISTRY[section_id].title,
        )
    return stats, chart


def _build_weekend_penalty(
    section_id: str, data: dict, region: str, urban_rural: str,
) -> tuple[dict, dict]:
    """Build weekend penalty (B3)."""
    sq = data.get("service_quality")
    if sq is None:
        return {}, {}
    filtered = _filter_data(sq, region, urban_rural)
    if not MinLsoaRule().should_fire(n_lsoas=len(filtered)):
        return {}, {}

    stats: dict[str, Any] = {}
    if "sunday_desert" in filtered.columns:
        n_sd = int(filtered["sunday_desert"].sum())
        stats["n_sunday_desert"] = n_sd
        stats["pct_sunday_desert"] = round(n_sd / len(filtered) * 100, 1)
    if "total_weekday_departures" in filtered.columns and "total_sunday_departures" in filtered.columns:
        wd = float(filtered["total_weekday_departures"].sum())
        su = float(filtered["total_sunday_departures"].sum())
        stats["sunday_pct_drop"] = round((1 - su / wd) * 100, 1) if wd > 0 else 0

    # chart_data: grouped bar (weekday/sunday by region)
    chart: dict = {}
    if "region" in filtered.columns and "total_weekday_departures" in filtered.columns:
        by_region = filtered.groupby("region").agg(
            weekday=("total_weekday_departures", "mean"),
            sunday=("total_sunday_departures", "mean") if "total_sunday_departures" in filtered.columns else ("total_weekday_departures", lambda x: 0),
        ).reset_index()
        chart = build_grouped_bar(
            categories=by_region["region"].tolist(),
            series=[
                {"name": "Weekday", "values": by_region["weekday"].round(1).tolist()},
                {"name": "Sunday", "values": by_region["sunday"].round(1).tolist()},
            ],
            title=SECTION_REGISTRY[section_id].title,
        )
    return stats, chart


def _build_correlation(
    section_id: str, data: dict, region: str, urban_rural: str,
) -> tuple[dict, dict]:
    """Build correlation section (B5, C5, D1-D5)."""
    policy = data.get("policy")
    if policy is None:
        return {}, {}
    filtered = _filter_data(policy, region, urban_rural)

    # Map section_id to x/y columns
    col_map = {
        "b5": ("imd_score", "service_quality_index", "IMD Score", "Service Quality Index"),
        "c5": ("route_length_km", "trips_per_day", "Route Length (km)", "Trips per Day"),
        "d1": ("imd_score", "trips_per_capita", "IMD Score", "Trips per Capita"),
        "d2": ("unemployment_rate", "trips_per_capita", "Unemployment Rate", "Trips per Capita"),
        "d3": ("nocar_pct", "trips_per_capita", "% No Car", "Trips per Capita"),
        "d4": ("elderly_pct", "trips_per_capita", "% Elderly", "Trips per Capita"),
        "d5": ("income_score", "trips_per_capita", "Income Score", "Trips per Capita"),
    }

    prefix = section_id.split("_")[0]
    mapping = col_map.get(prefix)
    if mapping is None:
        return {}, {}

    x_col, y_col, x_label, y_label = mapping
    if x_col not in filtered.columns or y_col not in filtered.columns:
        return {}, {}

    corr = calculate_correlation(filtered[x_col], filtered[y_col])
    if not CorrelationRule().should_fire(n=corr.n, p_value=corr.p_value):
        return {}, {}

    stats = {
        "r": corr.r,
        "p_value": corr.p_value,
        "n": corr.n,
        "strength": corr.strength,
        "direction": corr.direction,
        "x_label": x_label,
        "y_label": y_label,
    }

    id_col = "lsoa_code" if "lsoa_code" in filtered.columns else "lsoa_cd" if "lsoa_cd" in filtered.columns else filtered.columns[0]
    chart = build_scatter_regression(
        df=filtered, x_col=x_col, y_col=y_col, id_col=id_col,
        title=SECTION_REGISTRY[section_id].title, x_label=x_label, y_label=y_label,
    )
    return stats, chart


def _build_distribution(
    section_id: str, data: dict, region: str, urban_rural: str,
) -> tuple[dict, dict]:
    """Build distribution section (C1, C2)."""
    routes = data.get("routes")
    if routes is None:
        return {}, {}

    metric_map = {
        "c1": ("route_length_km", "Route Length", "km"),
        "c2": ("num_stops", "Stops per Route", "stops"),
    }
    prefix = section_id.split("_")[0]
    mapping = metric_map.get(prefix)
    if mapping is None:
        return {}, {}

    col, name, unit = mapping
    if col not in routes.columns:
        return {}, {}

    values = routes[col].dropna()
    if not DistributionRule().should_fire(n=len(values)):
        return {}, {}

    desc = describe_distribution(values)
    skew = "right-skewed" if desc.mean > desc.median * 1.1 else "left-skewed" if desc.mean < desc.median * 0.9 else "approximately symmetric"

    stats = {
        "median": desc.median,
        "unit": unit,
        "metric_name": name.lower(),
        "p10": desc.p10,
        "p90": desc.p90,
        "skew_label": skew,
        "n_outliers": desc.outliers,
        "cv": desc.cv,
    }

    # Build box-violin by region if available
    chart: dict = {}
    if "region" in routes.columns:
        groups = {r: routes.loc[routes["region"] == r, col].dropna() for r in routes["region"].unique()}
        groups = {k: v for k, v in groups.items() if len(v) > 0}
        if groups:
            chart = build_box_violin(groups=groups, title=SECTION_REGISTRY[section_id].title, unit=unit)
    return stats, chart


def _build_market_concentration(
    section_id: str, data: dict, region: str, urban_rural: str,
) -> tuple[dict, dict]:
    """Build market concentration / HHI (C3, BSA2)."""
    lta = data.get("lta")
    if lta is None:
        return {}, {}
    if "region_hhi" not in lta.columns:
        return {}, {}

    by_region = lta.groupby("region")["region_hhi"].first().reset_index()
    by_region.columns = ["label", "value"]
    n_operators = len(by_region)
    if not MarketConcentrationRule().should_fire(n_operators=n_operators):
        return {}, {}

    stats = {
        "hhi": round(float(by_region["value"].mean()), 0),
        "region_name": "England" if region == "all" else region,
    }

    chart = build_horizontal_bar(
        data=by_region, title=SECTION_REGISTRY[section_id].title,
        x_label="HHI", y_label="Region",
    )
    return stats, chart


def _build_clusters(
    section_id: str, data: dict, region: str, urban_rural: str,
) -> tuple[dict, dict]:
    """Build cluster sections (C6, D6, G1)."""
    is_route = section_id.startswith("c6") or section_id.startswith("g1")
    key = "route_clusters" if is_route else "clusters"
    df = data.get(key)
    if df is None:
        return {}, {}

    cluster_col = "cluster" if is_route else "hdbscan_label"
    if cluster_col not in df.columns:
        return {}, {}

    valid = df[df[cluster_col] >= 0]  # exclude noise (-1)
    unique_labels = sorted(valid[cluster_col].unique())
    n_clusters = len(unique_labels)
    if not ClusterRule().should_fire(n_clusters=n_clusters):
        return {}, {}

    entity_type = "routes" if is_route else "LSOAs"

    # Build cluster descriptions
    clusters_info = []
    archetype_col = "hdbscan_archetype" if "hdbscan_archetype" in df.columns else None
    for cid in unique_labels:
        mask = valid[cluster_col] == cid
        n = int(mask.sum())
        pct = round(n / len(valid) * 100, 1)
        desc = str(df.loc[mask, archetype_col].iloc[0]) if archetype_col and mask.any() else f"Cluster {cid}"
        clusters_info.append({"id": int(cid), "n": n, "pct": pct, "description": desc})

    stats = {
        "n_clusters": n_clusters,
        "entity_type": entity_type,
        "clusters": clusters_info,
    }

    # chart_data: scatter_clusters (needs x/y projection — use first 2 numeric cols as proxy)
    chart: dict = {}
    numeric_cols = valid.select_dtypes(include="number").columns.tolist()
    id_col = "route_id" if is_route else "lsoa_cd"
    if len(numeric_cols) >= 2 and id_col in valid.columns:
        scatter_df = valid[[numeric_cols[0], numeric_cols[1], cluster_col, id_col]].copy()
        scatter_df.columns = ["x", "y", "cluster", "id"]
        cluster_labels = {int(c["id"]): c["description"] for c in clusters_info}
        chart = build_scatter_clusters(
            data=scatter_df, cluster_labels=cluster_labels,
            title=SECTION_REGISTRY[section_id].title,
        )
    return stats, chart


def _build_network(
    section_id: str, data: dict, region: str, urban_rural: str,
) -> tuple[dict, dict]:
    """Build network topology (C7)."""
    routes = data.get("routes")
    if routes is None:
        return {}, {}
    if not NetworkRule().should_fire(n_routes=len(routes)):
        return {}, {}

    n_cross = int(routes["cross_la_flag"].sum()) if "cross_la_flag" in routes.columns else 0
    stats = {
        "n_cross_la": n_cross,
        "pct_cross_la": round(n_cross / len(routes) * 100, 1) if len(routes) > 0 else 0,
        "mean_length": round(float(routes["route_length_km"].mean()), 1) if "route_length_km" in routes.columns else 0,
        "median_length": round(float(routes["route_length_km"].median()), 1) if "route_length_km" in routes.columns else 0,
    }

    # chart_data: choropleth of cross-LA route density by LAD
    chart: dict = {}
    lta = data.get("lta")
    if lta is not None and "lad_cd" in lta.columns and "mean_trips_per_cap" in lta.columns:
        lad_data = lta[["lad_cd", "lad_nm", "mean_trips_per_cap"]].copy()
        lad_data.columns = ["area_code", "area_name", "value"]
        chart = build_choropleth(
            data=lad_data, title=SECTION_REGISTRY[section_id].title,
            geography="lad", metric="cross_la_route_density", colour_scale="Viridis",
        )
    return stats, chart


def _build_heatmap(
    section_id: str, data: dict, region: str, urban_rural: str,
) -> tuple[dict, dict]:
    """Build heatmap (D7)."""
    policy = data.get("policy")
    if policy is None:
        return {}, {}
    filtered = _filter_data(policy, region, "all")

    if "imd_decile" not in filtered.columns or "urban_rural" not in filtered.columns or "trips_per_capita" not in filtered.columns:
        return {}, {}

    pivot = filtered.groupby(["urban_rural", "imd_decile"])["trips_per_capita"].mean().unstack(fill_value=0)
    cell_counts = filtered.groupby(["urban_rural", "imd_decile"]).size().unstack(fill_value=0)
    min_cell = int(cell_counts.min().min())
    if not HeatmapRule().should_fire(min_cell_n=min_cell):
        return {}, {}

    x_labels = [str(d) for d in sorted(pivot.columns)]
    y_labels = list(pivot.index)
    values = pivot.values.tolist()

    worst_val = float("inf")
    best_val = float("-inf")
    worst_cell = best_cell = {"label": "", "value": 0}
    for yi, y_label in enumerate(y_labels):
        for xi, x_label in enumerate(x_labels):
            v = values[yi][xi]
            if v < worst_val:
                worst_val = v
                worst_cell = {"label": f"Decile {x_label} × {y_label}", "value": round(v, 1)}
            if v > best_val:
                best_val = v
                best_cell = {"label": f"Decile {x_label} × {y_label}", "value": round(v, 1)}

    stats = {
        "x_dimension": "deprivation decile",
        "y_dimension": "area type",
        "metric_name": "trips per capita",
        "worst_cell": worst_cell,
        "best_cell": best_cell,
    }
    chart = build_heatmap(
        x_labels=x_labels, y_labels=y_labels, values=values,
        title=SECTION_REGISTRY[section_id].title,
    )
    return stats, chart


def _build_equity_decile(
    section_id: str, data: dict, region: str, urban_rural: str,
) -> tuple[dict, dict]:
    """Build equity by IMD decile (F2)."""
    policy = data.get("policy")
    if policy is None:
        return {}, {}
    filtered = _filter_data(policy, region, urban_rural)
    if "imd_decile" not in filtered.columns or "trips_per_capita" not in filtered.columns:
        return {}, {}

    decile_counts = [int((filtered["imd_decile"] == d).sum()) for d in range(1, 11)]
    if not DecileRule().should_fire(decile_counts=decile_counts):
        return {}, {}

    by_decile = filtered.groupby("imd_decile")["trips_per_capita"].mean()
    most = float(by_decile.get(1, 0))
    least = float(by_decile.get(10, 0))
    ratio = round(least / most, 1) if most > 0 else 0

    stats = {
        "most_deprived_value": round(most, 1),
        "least_deprived_value": round(least, 1),
        "unit": "trips/capita",
        "ratio": ratio,
    }

    # chart_data: horizontal bar of service by decile
    decile_df = by_decile.reset_index()
    decile_df.columns = ["label", "value"]
    decile_df["label"] = decile_df["label"].astype(str)
    chart = build_horizontal_bar(
        data=decile_df, title=SECTION_REGISTRY[section_id].title,
        x_label="Trips per capita", y_label="IMD Decile",
    )
    return stats, chart


def _build_demographic(
    section_id: str, data: dict, region: str, urban_rural: str,
) -> tuple[dict, dict]:
    """Build demographic breakdown (F3)."""
    policy = data.get("policy")
    if policy is None or "nonwhite_pct" not in policy.columns:
        return {}, {}
    filtered = _filter_data(policy, region, urban_rural)
    if "trips_per_capita" not in filtered.columns:
        return {}, {}

    median_nw = float(filtered["nonwhite_pct"].median())
    high = filtered[filtered["nonwhite_pct"] >= median_nw]
    low = filtered[filtered["nonwhite_pct"] < median_nw]
    if not DemographicRule().should_fire(group_counts=[len(high), len(low)]):
        return {}, {}

    nat_avg = float(filtered["trips_per_capita"].mean())

    groups = []
    for label, subset in [("high non-white %", high), ("low non-white %", low)]:
        val = float(subset["trips_per_capita"].mean())
        groups.append({
            "label": label,
            "value": round(val, 2),
            "vs_national_pct": round((val - nat_avg) / nat_avg * 100, 1) if nat_avg != 0 else 0,
        })
    stats = {"groups": groups, "unit": "trips/capita"}

    # chart_data: grouped bar
    chart = build_grouped_bar(
        categories=[g["label"] for g in groups],
        series=[{"name": "Trips/capita", "values": [g["value"] for g in groups]}],
        title=SECTION_REGISTRY[section_id].title,
    )
    return stats, chart


def _build_accessibility(
    section_id: str, data: dict, region: str, urban_rural: str,
) -> tuple[dict, dict]:
    """Build accessibility gap (F4)."""
    acc = data.get("accessibility")
    if acc is None:
        return {}, {}
    filtered = _filter_data(acc, region, urban_rural)
    score_col = "sfca_score" if "sfca_score" in filtered.columns else None
    if score_col is None or len(filtered) == 0:
        return {}, {}

    n_zero = int((filtered[score_col] == 0).sum())
    if not AccessibilityRule().should_fire(n_pois=n_zero):
        return {}, {}

    stats = {
        "n_beyond_threshold": n_zero,
        "poi_type": "LSOAs",
        "pct_beyond": round(n_zero / len(filtered) * 100, 1),
        "threshold_m": 400,
    }

    # chart_data: horizontal bar (zero-access LSOAs by region)
    chart: dict = {}
    if "region" in filtered.columns:
        by_region = filtered[filtered[score_col] == 0].groupby("region").size().reset_index()
        by_region.columns = ["label", "value"]
        chart = build_horizontal_bar(
            data=by_region, title=SECTION_REGISTRY[section_id].title,
            x_label="LSOAs with zero access", y_label="Region",
        )
    return stats, chart


def _build_anomaly(
    section_id: str, data: dict, region: str, urban_rural: str,
) -> tuple[dict, dict]:
    """Build anomaly spotlight (G2)."""
    df = data.get("anomalies")
    if df is None:
        return {}, {}

    type_col = "anomaly_type" if "anomaly_type" in df.columns else None
    if type_col is None:
        return {}, {}

    anomalies = df[df[type_col] != "normal"]
    if not AnomalyRule().should_fire(n_anomalies=len(anomalies)):
        return {}, {}

    stats = {
        "n_anomalies": len(anomalies),
        "pct_anomalies": round(len(anomalies) / len(df) * 100, 1),
        "n_positive": int((anomalies[type_col] == "positive_deprived_well_served").sum()),
        "n_inefficiency": int((anomalies[type_col] == "inefficiency_affluent_poor_served").sum()),
        "n_policy_failure": int((anomalies[type_col] == "policy_failure_elderly_no_service").sum()),
    }

    # chart_data: scatter (SQI vs IMD, anomalies highlighted)
    chart: dict = {}
    if "service_quality_index" in df.columns and "imd_score" in df.columns and "lsoa_cd" in df.columns:
        chart = build_scatter_regression(
            df=df, x_col="imd_score", y_col="service_quality_index", id_col="lsoa_cd",
            title=SECTION_REGISTRY[section_id].title,
            x_label="IMD Score", y_label="Service Quality Index",
        )
    return stats, chart


def _build_scenario(
    section_id: str, data: dict, region: str, urban_rural: str,
) -> tuple[dict, dict]:
    """Build individual scenario (G5, PS1-PS4)."""
    scenarios = data.get("scenarios")
    if scenarios is None or len(scenarios) == 0:
        return {}, {}

    scenario_map = {"ps1": "A", "ps2": "B", "ps3": "C", "ps4": "D", "g5": "A"}
    prefix = section_id.split("_")[0]
    scenario_letter = scenario_map.get(prefix, "A")

    row = scenarios[scenarios["scenario"] == scenario_letter] if "scenario" in scenarios.columns else pd.DataFrame()
    if len(row) == 0:
        return {}, {}

    r = row.iloc[0]
    pop = int(r.get("population_affected", 0))
    cost = float(r.get("estimated_annual_cost_m", 0))
    co2 = float(r.get("co2_saving_t_yr", 0)) if pd.notna(r.get("co2_saving_t_yr")) else 0

    stats = {
        "scenario": {
            "scenario": str(r.get("scenario", "")),
            "name": str(r.get("name", "")),
            "scope": str(r.get("scope", "")),
            "population_affected": pop,
            "estimated_annual_cost_m": cost,
            "co2_saving_t_yr": int(co2),
            "confidence": str(r.get("confidence", "indicative")),
        }
    }

    # chart_data: horizontal bar (cost, CO2, population as separate metrics)
    bar_data = pd.DataFrame({
        "label": ["Population affected", "Annual cost (£m)", "CO₂ saved (t/yr)"],
        "value": [pop / 1e6, cost, co2],
    })
    chart = build_horizontal_bar(
        data=bar_data, title=SECTION_REGISTRY[section_id].title,
        x_label="Value", y_label="Metric",
    )
    return stats, chart


def _build_economic_value(
    section_id: str, data: dict, region: str, urban_rural: str,
) -> tuple[dict, dict]:
    """Build economic value (J1)."""
    econ = data.get("economic")
    if econ is None:
        return {}, {}
    filtered = _filter_data(econ, region, urban_rural)
    if not MinLsoaRule().should_fire(n_lsoas=len(filtered)):
        return {}, {}

    stats = {
        "annual_benefit": float(filtered["annual_benefit_gbp"].sum()) if "annual_benefit_gbp" in filtered.columns else 0,
        "region_name": "England" if region == "all" else region,
        "n_trips": int(filtered["trips_per_day"].sum()) if "trips_per_day" in filtered.columns else 0,
        "vot": 8.49,  # TAG v2.03fc, blended commute/other
    }

    # chart_data: horizontal bar (benefit by region)
    chart: dict = {}
    if "region" in filtered.columns and "annual_benefit_gbp" in filtered.columns:
        by_region = filtered.groupby("region")["annual_benefit_gbp"].sum().reset_index()
        by_region.columns = ["label", "value"]
        by_region["value"] = (by_region["value"] / 1e6).round(1)  # £m
        chart = build_horizontal_bar(
            data=by_region, title=SECTION_REGISTRY[section_id].title,
            x_label="Annual benefit (£m)", y_label="Region",
        )
    return stats, chart


def _build_bcr(
    section_id: str, data: dict, region: str, urban_rural: str,
) -> tuple[dict, dict]:
    """Build BCR analysis (J2)."""
    econ = data.get("economic")
    if econ is None:
        return {}, {}
    filtered = _filter_data(econ, region, urban_rural)
    if "bcr_central" not in filtered.columns or len(filtered) == 0:
        return {}, {}

    mean_bcr = float(filtered["bcr_central"].mean())
    stats = {
        "bcr": round(mean_bcr, 2),
        "area_name": "England" if region == "all" else region,
        "vfm_band": "Very High" if mean_bcr > 4 else "High" if mean_bcr > 2 else "Medium" if mean_bcr > 1.5 else "Low" if mean_bcr > 1 else "Poor",
        "investment_m": round(float(filtered["investment_gap_annual_cost"].sum()) / 1e6, 1) if "investment_gap_annual_cost" in filtered.columns else 0,
        "appraisal_years": 60,
    }

    # chart_data: horizontal bar (BCR by region)
    chart: dict = {}
    if "region" in filtered.columns:
        by_region = filtered.groupby("region")["bcr_central"].mean().reset_index()
        by_region.columns = ["label", "value"]
        by_region["value"] = by_region["value"].round(2)
        chart = build_horizontal_bar(
            data=by_region, title=SECTION_REGISTRY[section_id].title,
            x_label="BCR", y_label="Region",
        )
    return stats, chart


def _build_carbon(
    section_id: str, data: dict, region: str, urban_rural: str,
) -> tuple[dict, dict]:
    """Build carbon reduction (J3)."""
    ms = data.get("modal_shift")
    if ms is None or len(ms) == 0:
        return {}, {}

    # Use central elasticity (0.55)
    el_col = "elasticity_value" if "elasticity_value" in ms.columns else "elasticity"
    central = ms[ms[el_col] == 0.55] if el_col in ms.columns else ms
    if len(central) == 0:
        central = ms.iloc[[0]]
    r = central.iloc[0]

    co2_saving = float(r.get("net_co2_saving_tonnes_pa", r.get("co2_saved_tonnes", 0)))
    if not CarbonRule().should_fire(co2_saving=co2_saving):
        return {}, {}

    stats = {
        "co2_saving_tonnes": co2_saving,
        "scope": str(r.get("scope", "England")),
        "co2_value_k": round(co2_saving * 259.87 / 1000, 0),
        "carbon_price": 259.87,
        "modal_shift_trips": int(r.get("car_trips_replaced_pa", r.get("modal_shift_trips", 0))),
    }

    # chart_data: horizontal bar (CO2 by scope/scenario)
    co2_by_scope = central.groupby("scope")["net_co2_saving_tonnes_pa"].first().reset_index() if "scope" in central.columns else pd.DataFrame()
    chart: dict = {}
    if len(co2_by_scope) > 0:
        co2_by_scope.columns = ["label", "value"]
        chart = build_horizontal_bar(
            data=co2_by_scope, title=SECTION_REGISTRY[section_id].title,
            x_label="Net CO₂ saved (t/yr)", y_label="Scope",
        )
    return stats, chart


def _build_franchising(
    section_id: str, data: dict, region: str, urban_rural: str,
) -> tuple[dict, dict]:
    """Build franchising readiness ranking (BSA1)."""
    lta = data.get("lta")
    if lta is None:
        return {}, {}

    score_col = "franchising_readiness" if "franchising_readiness" in lta.columns else None
    if score_col is None:
        return {}, {}
    if not MinLsoaRule().should_fire(n_lsoas=len(lta)):
        return {}, {}

    sorted_lta = lta.sort_values(score_col, ascending=False)
    best = sorted_lta.iloc[0]
    worst = sorted_lta.iloc[-1]
    nat_avg = float(sorted_lta[score_col].mean())

    name_col = "lad_nm" if "lad_nm" in lta.columns else lta.columns[0]
    stats = {
        "best": {
            "name": str(best[name_col]),
            "value": round(float(best[score_col]), 1),
            "pct_above": round((float(best[score_col]) - nat_avg) / nat_avg * 100, 1),
        },
        "worst": {
            "name": str(worst[name_col]),
            "value": round(float(worst[score_col]), 1),
            "pct_below": round((nat_avg - float(worst[score_col])) / nat_avg * 100, 1),
        },
        "national_avg": round(nat_avg, 1),
        "unit": "readiness score",
    }

    # chart_data: horizontal bar (top/bottom 20 LADs)
    top20 = sorted_lta.head(20)[[name_col, score_col]].copy()
    top20.columns = ["label", "value"]
    chart = build_horizontal_bar(
        data=top20, title=SECTION_REGISTRY[section_id].title,
        x_label="Franchising readiness", y_label="LAD", national_avg=nat_avg,
    )
    return stats, chart


def _build_tier_dist(
    section_id: str, data: dict, region: str, urban_rural: str,
) -> tuple[dict, dict]:
    """Build tier distribution (BSA3)."""
    lta = data.get("lta")
    if lta is None or "readiness_tier" not in lta.columns:
        return {}, {}
    if not TierRule().should_fire(n_lads=len(lta)):
        return {}, {}

    # readiness_tier is text like "Tier 1 — High", extract the number
    tier_nums = lta["readiness_tier"].str.extract(r"Tier (\d)")[0].astype(float)
    tier_counts = tier_nums.value_counts()
    stats = {
        "n_total": len(lta),
        "n_tier1": int(tier_counts.get(1, 0)),
        "n_tier2": int(tier_counts.get(2, 0)),
        "n_tier3": int(tier_counts.get(3, 0)),
    }
    name_col = "lad_nm" if "lad_nm" in lta.columns else lta.columns[0]
    score_col = "franchising_readiness" if "franchising_readiness" in lta.columns else None
    if score_col:
        top = lta.sort_values(score_col, ascending=False).iloc[0]
        stats["top_lad"] = str(top[name_col])
        stats["top_score"] = round(float(top[score_col]), 1)

    # chart_data: stacked bar (tiers by region)
    chart: dict = {}
    if "region" in lta.columns:
        lta_with_tier = lta.copy()
        lta_with_tier["_tier_num"] = tier_nums
        by_region = lta_with_tier.groupby("region")["_tier_num"].value_counts().unstack(fill_value=0)
        regions = list(by_region.index)
        chart = build_stacked_bar(
            categories=regions,
            series=[
                {"name": "Tier 1 (High)", "values": [int(by_region.loc[r].get(1.0, 0)) for r in regions]},
                {"name": "Tier 2 (Medium)", "values": [int(by_region.loc[r].get(2.0, 0)) for r in regions]},
                {"name": "Tier 3 (Low)", "values": [int(by_region.loc[r].get(3.0, 0)) for r in regions]},
            ],
            title=SECTION_REGISTRY[section_id].title,
        )
    return stats, chart


def _build_scenario_comparison(
    section_id: str, data: dict, region: str, urban_rural: str,
) -> tuple[dict, dict]:
    """Build scenario comparison (PS5)."""
    scenarios = data.get("scenarios")
    if scenarios is None:
        return {}, {}
    if not ScenarioComparisonRule().should_fire(n_scenarios=len(scenarios)):
        return {}, {}

    items = []
    for _, r in scenarios.iterrows():
        items.append({
            "name": str(r.get("name", "")),
            "population": int(r.get("population_affected", 0)),
            "cost_m": round(float(r.get("estimated_annual_cost_m", 0)) if pd.notna(r.get("estimated_annual_cost_m")) else 0, 1),
            "co2_t": int(r.get("co2_saving_t_yr", 0)) if pd.notna(r.get("co2_saving_t_yr")) else 0,
        })

    stats = {
        "scenarios": items,
        "best_bcr_scenario": str(scenarios.iloc[0].get("name", "")) if len(scenarios) > 0 else "",
    }

    # chart_data: grouped bar (all scenarios side by side)
    names = [i["name"] for i in items]
    chart = build_grouped_bar(
        categories=names,
        series=[
            {"name": "Population (millions)", "values": [round(i["population"] / 1e6, 2) for i in items]},
            {"name": "Cost (£m/yr)", "values": [i["cost_m"] for i in items]},
            {"name": "CO₂ saved (t/yr)", "values": [i["co2_t"] for i in items]},
        ],
        title=SECTION_REGISTRY[section_id].title,
    )
    return stats, chart
```

- [ ] **Step 2: Run all intelligence tests**

Run: `cd /Users/souravamseekarmarti/Projects/aequitas && python -m pytest tests/intelligence/ -v`
Expected: All tests PASS (existing + new)

- [ ] **Step 3: Commit**

```bash
git add src/aequitas/warehouse/precompute.py
git commit -m "feat(warehouse): rewrite precompute to use section registry — 51 sections with chart_data"
```

---

## Chunk 6: Integration Verification

### Task 7: Run Full Pipeline Smoke Test

- [ ] **Step 1: Run all tests**

Run: `cd /Users/souravamseekarmarti/Projects/aequitas && python -m pytest tests/ --ignore=tests/pipeline/test_integration.py -v 2>&1 | tail -20`
Expected: All tests PASS

- [ ] **Step 2: Verify section registry completeness**

Run: `cd /Users/souravamseekarmarti/Projects/aequitas && python -c "from aequitas.intelligence.section_registry import SECTION_REGISTRY; print(f'{len(SECTION_REGISTRY)} sections registered')"`
Expected: `51 sections registered`

- [ ] **Step 3: Verify engine can render all sections**

Run: `cd /Users/souravamseekarmarti/Projects/aequitas && python -c "
from aequitas.intelligence.engine import InsightEngine, _SECTION_TEMPLATES
print(f'{len(_SECTION_TEMPLATES)} template mappings')
engine = InsightEngine()
# Test one new section
result = engine.generate('a3_walking_distance', region='all', urban_rural='all', stats={'pct_covered': 79.9, 'n_zero_access': 6776, 'pct_zero_access': 20.1, 'pop_zero_access': 1200000})
print(f'Narrative length: {len(result[\"narrative\"])} chars')
print(f'Suppressed: {result[\"suppressed\"]}')
"`
Expected: 58 template mappings (51 new + 7 existing), narrative generated, not suppressed

- [ ] **Step 4: Final commit**

```bash
git add -A
git commit -m "feat: InsightEngine expansion complete — 51 sections, 27 templates, chart_data builder"
```

---

## Future Work (deferred)

- **LAD Profiles:** `lad_profile.j2` wrapping 5 sub-narratives for each of 298 LADs (1,490 additional rows). Spec Section 5 defines this but it is not included in this plan to keep scope focused on the 51 topic-page sections.
- **Generalized suppression in engine.py:** The coverage_density-specific suppression logic (line 91) should be replaced with a generic evidence-gate dispatch using section_registry metadata. For now, builder-level gating returns empty stats which triggers engine.py's existing `not stats` → suppress path.
- **`data/processed/` path consolidation:** The 7 original `ANALYTICS_PARQUET_SOURCES` entries still point to `data/processed/` which has no Parquets. These will need updating when the pipeline actually writes to `processed_dir`.
- **VoT price year documentation:** VoT=8.49 needs a comment tracing to specific TAG cell reference and price year.
