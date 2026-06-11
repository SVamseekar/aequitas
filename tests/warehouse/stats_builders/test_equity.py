"""Tests for equity.py — covers f1, a4, f2."""
import math

import pandas as pd
import pytest

from aequitas.warehouse.stats_builders.equity import build_equity_stats


def _equity_df():
    # 30 LSOAs, three per IMD decile, trips_per_capita increasing with affluence
    # (decile 1 = most deprived -> lowest trips; decile 10 = least deprived -> highest)
    deciles = [d for d in range(1, 11) for _ in range(3)]
    return pd.DataFrame({
        "lsoa_cd": [f"E01{i:06d}" for i in range(1, 31)],
        "imd_decile": deciles,
        "trips_per_capita": [float(d) for d in deciles],
        "population": [1000] * 30,
    })


def test_f1_gini_computes_live_distribution_stats():
    stats = build_equity_stats("f1_gini", equity_df=_equity_df())
    assert 0.0 < stats["gini"] < 1.0
    assert stats["palma"] > 0
    assert isinstance(stats["concentration_index"], float)
    assert stats["n_lsoas"] == 30


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


def test_f2_disparity_ratio_undefined_when_p10_is_zero():
    """A15: zero baseline in the most-deprived decile must not produce ratio=0."""
    df = _equity_df()
    df.loc[df["imd_decile"] == 1, "trips_per_capita"] = 0.0
    stats = build_equity_stats("f2_disparity_ratio", equity_df=df)
    assert stats["most_deprived_value"] == pytest.approx(0.0)
    assert stats["ratio"] is None
    assert stats["ratio_undefined"] is True


def test_f1_gini_insufficient_data_below_minimum_lsoa_count():
    """A18: small samples (n < 30) must not produce an out-of-range Gini."""
    df = pd.DataFrame({
        "lsoa_cd": [f"E0100000{i}" for i in range(1, 11)],
        "imd_decile": list(range(1, 11)),
        "trips_per_capita": [10.0, 1.0, 9.0, 2.0, 8.0, 3.0, 7.0, 4.0, 6.0, 5.0],
        "population": [1000] * 10,
    })
    stats = build_equity_stats("f1_gini", equity_df=df)
    assert stats == {"insufficient_data": True, "n_lsoas": 10}


def test_f1_gini_normal_case_unaffected_by_min_lsoa_guard():
    """Sanity: n >= 30, p10 > 0 still returns full distribution stats as before."""
    df = pd.DataFrame({
        "lsoa_cd": [f"E0100{i:04d}" for i in range(30)],
        "imd_decile": [(i % 10) + 1 for i in range(30)],
        "trips_per_capita": [float((i % 10) + 1) for i in range(30)],
        "population": [1000] * 30,
    })
    stats = build_equity_stats("f1_gini", equity_df=df)
    assert "insufficient_data" not in stats
    assert 0.0 <= stats["gini"] <= 1.0
    assert stats["n_lsoas"] == 30
