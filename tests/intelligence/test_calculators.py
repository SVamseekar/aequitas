"""Tests for InsightEngine calculators."""

import numpy as np
import pandas as pd
import pytest
from aequitas.intelligence.calculators import (
    calculate_correlation,
    calculate_gap_to_target,
    describe_distribution,
    rank_regions,
)


def test_rank_regions():
    data = pd.DataFrame({
        "region": ["A", "B", "C"],
        "value": [10, 30, 20],
        "population": [1000, 2000, 1500],
    })
    ranked = rank_regions(data, metric="value", higher_is_better=True)
    assert ranked.iloc[0]["region"] == "B"  # rank 1
    assert ranked.iloc[0]["rank"] == 1


def test_rank_regions_lower_is_better():
    data = pd.DataFrame({
        "region": ["A", "B", "C"],
        "value": [10, 30, 20],
    })
    ranked = rank_regions(data, metric="value", higher_is_better=False)
    assert ranked.iloc[0]["region"] == "A"  # lowest value = rank 1


def test_rank_regions_vs_national():
    data = pd.DataFrame({"region": ["A", "B"], "value": [50.0, 150.0]})
    ranked = rank_regions(data, metric="value", higher_is_better=True)
    # national mean = 100, A is -50% below, B is +50% above
    assert ranked[ranked["region"] == "A"]["vs_national_pct"].values[0] == -50.0


def test_describe_distribution():
    values = pd.Series([1, 2, 3, 4, 5, 100])
    desc = describe_distribution(values)
    assert hasattr(desc, "mean")
    assert hasattr(desc, "median")
    assert desc.outliers > 0  # 100 is an outlier


def test_describe_distribution_no_outliers():
    values = pd.Series(range(100))
    desc = describe_distribution(values)
    assert desc.outliers == 0


def test_correlation_significant():
    np.random.seed(42)
    x = np.arange(100, dtype=float)
    y = x * 2 + np.random.randn(100) * 5
    result = calculate_correlation(pd.Series(x), pd.Series(y))
    assert result.r > 0.9
    assert result.p_value < 0.05
    assert result.significant is True
    assert result.direction == "positive"


def test_correlation_negative():
    x = pd.Series(range(100), dtype=float)
    y = pd.Series(range(99, -1, -1), dtype=float)
    result = calculate_correlation(x, y)
    assert result.r < -0.99
    assert result.direction == "negative"


def test_correlation_insufficient_data():
    result = calculate_correlation(pd.Series([1.0, 2.0]), pd.Series([2.0, 4.0]))
    assert result.significant is False


def test_gap_to_target():
    values = pd.Series([10.0, 20.0, 30.0, 40.0, 50.0])
    gap = calculate_gap_to_target(values, target=25.0)
    assert gap.n_below_target == 2
    assert gap.pct_below_target == 40.0
    assert gap.mean_gap == 10.0  # gaps are (15, 5), mean=10


def test_gap_all_above_target():
    values = pd.Series([100.0, 200.0, 300.0])
    gap = calculate_gap_to_target(values, target=50.0)
    assert gap.n_below_target == 0
    assert gap.total_gap == 0.0
