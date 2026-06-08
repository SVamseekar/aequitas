"""Tests for equity.py — covers f1, a4, f2."""
import math

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


def test_zero_population_does_not_produce_nan():
    df = _equity_df()
    df["population"] = 0
    stats = build_equity_stats("f1_gini", equity_df=df)
    assert stats["concentration_index"] == 0.0
    assert stats["gini"] == 0.0
    assert stats["palma"] == 0.0
    assert not any(isinstance(v, float) and math.isnan(v) for v in stats.values())
