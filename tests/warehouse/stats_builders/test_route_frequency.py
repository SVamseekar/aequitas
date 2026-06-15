"""Tests for route_frequency.py — covers b4_route_frequency."""

import pandas as pd
import pytest

from aequitas.warehouse.stats_builders.route_frequency import build_route_frequency_stats


def _route_freq_df():
    return pd.DataFrame({
        "route_id": [1, 2, 3, 4, 5, 6, 7],
        "n_trips_per_day": [100, 80, 60, 40, 20, 10, 5],
        "route_short_name": ["A", "B", "C", "D", "E", "F", "G"],
        "agency_name": ["Op1"] * 7,
        "primary_region": ["London", "London", "London", "South East", "South East", "South East", "South East"],
    })


def _urban_rural_df():
    return pd.DataFrame({
        "route_id": [1, 2, 3, 4, 5, 6, 7],
        "urban_rural_classification": ["urban", "urban", "rural", "urban", "rural", "rural", "mixed"],
        "primary_region": ["London", "London", "London", "South East", "South East", "South East", "South East"],
    })


def test_all_regions_top_and_bottom():
    stats = build_route_frequency_stats(
        route_trip_frequency_df=_route_freq_df(),
        route_urban_rural_df=_urban_rural_df(),
        region="all",
        region_name="England",
        urban_rural="all",
    )
    assert stats["n_routes"] == 7
    assert stats["scope_label"] == "England"
    assert stats["unit"] == "trips/day"
    assert [r["route_short_name"] for r in stats["top_routes"]] == ["A", "B", "C", "D", "E"]
    # bottom_routes excludes routes already shown in top_routes (no overlap)
    assert [r["route_short_name"] for r in stats["bottom_routes"]] == ["G", "F"]
    assert stats["top_routes"][0]["n_trips_per_day"] == 100
    assert stats["top_routes"][0]["agency_name"] == "Op1"


def test_region_filter():
    stats = build_route_frequency_stats(
        route_trip_frequency_df=_route_freq_df(),
        route_urban_rural_df=_urban_rural_df(),
        region="E1",
        region_name="South East",
        urban_rural="all",
    )
    assert stats["n_routes"] == 4
    assert all(r["primary_region"] == "South East" for r in stats["top_routes"])
    assert stats["top_routes"][0]["route_short_name"] == "D"
    assert stats["scope_label"] == "South East"


def test_urban_rural_filter():
    stats = build_route_frequency_stats(
        route_trip_frequency_df=_route_freq_df(),
        route_urban_rural_df=_urban_rural_df(),
        region="all",
        region_name="England",
        urban_rural="urban",
    )
    # routes 1, 2, 4 are urban
    assert stats["n_routes"] == 3
    assert {r["route_short_name"] for r in stats["top_routes"]} == {"A", "B", "D"}
    assert stats["scope_label"] == "England (urban)"


def test_small_n_returns_available_routes_without_overlap():
    df = _route_freq_df().head(2)
    stats = build_route_frequency_stats(
        route_trip_frequency_df=df,
        route_urban_rural_df=_urban_rural_df(),
        region="all",
        region_name="England",
        urban_rural="all",
    )
    assert stats["n_routes"] == 2
    assert len(stats["top_routes"]) == 2
    # All routes already appear in top_routes — bottom_routes is empty to
    # avoid showing the same routes as both "busiest" and "least busy".
    assert stats["bottom_routes"] == []


def test_no_routes_after_filter_returns_empty():
    stats = build_route_frequency_stats(
        route_trip_frequency_df=_route_freq_df(),
        route_urban_rural_df=_urban_rural_df(),
        region="E2",
        region_name="North East",
        urban_rural="all",
    )
    assert stats == {}


def test_empty_input_returns_empty():
    stats = build_route_frequency_stats(
        route_trip_frequency_df=pd.DataFrame(),
        route_urban_rural_df=pd.DataFrame(),
        region="all",
        region_name="England",
        urban_rural="all",
    )
    assert stats == {}
