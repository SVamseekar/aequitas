"""Tests for urban_rural_gap.py — covers a6, c4, f5."""
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


def _route_urban_rural_df():
    return pd.DataFrame({
        "route_id": [1, 2, 3, 4, 5, 6, 7, 8, 9, 10],
        "urban_rural_classification": [
            "urban", "urban", "urban", "urban", "urban",
            "urban", "urban", "rural", "rural", "mixed",
        ],
        "primary_region": ["North West"] * 10,
    })


def _route_geometries_df():
    return pd.DataFrame({
        "route_id": [1, 2, 3, 4, 5, 6, 7, 8, 9, 10],
        "primary_region": ["North West"] * 10,
        "cross_la": [True, False, False, False, True, False, False, True, False, False],
    })


def test_c4_computes_urban_rural_mixed_split_for_region():
    stats = build_urban_rural_gap_stats(
        "c4_urban_rural_routes",
        region_df=_region_df(),
        urban_rural="all",
        route_urban_rural_df=_route_urban_rural_df(),
        route_geometries_df=_route_geometries_df(),
        region_name="North West",
        region="E12000002",
    )
    assert stats["urban_value"] == pytest.approx(70.0)
    assert stats["rural_value"] == pytest.approx(20.0)
    assert stats["n_urban"] == 7
    assert stats["n_rural"] == 2
    assert stats["n_mixed"] == 1
    assert stats["unit"] == "% of routes"
    assert stats["gap_pct"] == pytest.approx((70.0 - 20.0) / 70.0 * 100)
    # cross_la: 3 of 10 routes
    assert stats["n_cross_la"] == 3
    assert stats["pct_cross_la"] == pytest.approx(30.0)


def test_c4_filters_to_classification_when_urban_rural_active():
    stats = build_urban_rural_gap_stats(
        "c4_urban_rural_routes",
        region_df=_region_df(),
        urban_rural="rural",
        route_urban_rural_df=_route_urban_rural_df(),
        route_geometries_df=_route_geometries_df(),
        region_name="North West",
        region="E12000002",
    )
    # n_cross_la restricted to the 2 rural routes (8, 9) -> route 8 is cross_la
    assert stats["n_cross_la"] == 1
    assert stats["pct_cross_la"] == pytest.approx(50.0)


def test_c4_empty_route_urban_rural_returns_empty():
    assert build_urban_rural_gap_stats(
        "c4_urban_rural_routes",
        region_df=_region_df(),
        urban_rural="all",
        route_urban_rural_df=pd.DataFrame(),
        route_geometries_df=pd.DataFrame(),
        region_name="England",
        region="all",
    ) == {}


def test_c4_filters_by_region():
    df = pd.concat([
        _route_urban_rural_df(),
        pd.DataFrame({
            "route_id": [11, 12],
            "urban_rural_classification": ["rural", "rural"],
            "primary_region": ["London", "London"],
        }),
    ], ignore_index=True)
    stats = build_urban_rural_gap_stats(
        "c4_urban_rural_routes",
        region_df=_region_df(),
        urban_rural="all",
        route_urban_rural_df=df,
        route_geometries_df=_route_geometries_df(),
        region_name="London",
        region="E12000007",
    )
    # urban_pct is 0 for London-only rural routes — insufficient_data sentinel,
    # not {}, so the section still renders n_rural/n_mixed.
    assert stats == {
        "insufficient_data": True, "n_lsoas": 2, "n_urban": 0, "n_rural": 2, "n_mixed": 0,
    }


def test_empty_region_df_returns_insufficient_data():
    """A17: an empty region_df returns the insufficient_data sentinel, not {}."""
    assert build_urban_rural_gap_stats("a6_urban_rural_gap", region_df=pd.DataFrame(), urban_rural="all") == {
        "insufficient_data": True, "n_lsoas": 0,
    }


def test_no_rural_lsoas_returns_insufficient_data():
    """A17: a region with zero Rural LSOAs (e.g. London) returns a sentinel, not {}."""
    df = pd.DataFrame({
        "urban_rural": ["Urban", "Urban"],
        "trips_per_capita": [4.0, 5.0],
        "service_quality_index": [40.0, 50.0],
    })
    stats = build_urban_rural_gap_stats("a6_urban_rural_gap", region_df=df, urban_rural="rural")
    assert stats == {"insufficient_data": True, "n_lsoas": 2, "n_urban": 2, "n_rural": 0}


def test_zero_urban_value_returns_insufficient_data():
    df = pd.DataFrame({
        "urban_rural": ["Urban", "Rural"],
        "trips_per_capita": [0.0, 4.0],
        "service_quality_index": [0.0, 40.0],
    })
    stats = build_urban_rural_gap_stats("a6_urban_rural_gap", region_df=df, urban_rural="all")
    assert stats == {"insufficient_data": True, "n_lsoas": 2, "n_urban": 1, "n_rural": 1}
