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
