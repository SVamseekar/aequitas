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
    return pd.DataFrame({"imd_score": x, "stops_per_1k": y})


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
    assert "stops" in stats["y_label"].lower()


def test_correlation_too_few_rows_returns_empty():
    df = pd.DataFrame({"imd_score": [1.0], "stops_per_1k": [2.0]})
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
