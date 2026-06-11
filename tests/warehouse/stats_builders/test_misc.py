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
        "total_weekday_departures": [0, 100, 0, 150, 300, 250],
        "total_sunday_departures": [0, 0, 0, 30, 100, 90],
        "sunday_desert": [True, True, True, False, False, False],
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
        "a3_walking_distance", region="all", region_name="all", urban_rural="all",
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
        "a3_walking_distance", region="E12000007", region_name="London", urban_rural="all",
        policy_df=_policy_df(), service_levels_df=None, service_quality_df=None,
        route_geometries_df=None, anomalies_df=None, lta_df=None,
    )
    assert "worst_region" not in stats


def test_a5_service_deserts_counts_zero_stop_lsoas():
    stats = build_misc_stats(
        "a5_service_deserts", region="all", region_name="all", urban_rural="all",
        policy_df=_policy_df(), service_levels_df=_service_levels_df(),
        service_quality_df=None, route_geometries_df=None, anomalies_df=None, lta_df=None,
    )
    assert stats["n_desert_lsoas"] == 2
    assert stats["pop_affected"] == pytest.approx(2000.0)
    assert stats["mean_imd_score"] == pytest.approx((35.0 + 20.0) / 2)


def test_b2_operating_hours_formats_hhmm_strings():
    stats = build_misc_stats(
        "b2_operating_hours", region="all", region_name="all", urban_rural="all",
        policy_df=_policy_df(), service_levels_df=None, service_quality_df=_service_quality_df(),
        route_geometries_df=None, anomalies_df=None, lta_df=None,
    )
    assert ":" in stats["median_first_service"]
    assert ":" in stats["median_last_service"]
    assert stats["n_evening_isolated"] == 2
    assert stats["pct_evening_isolated"] == pytest.approx(2 / 6 * 100)


def test_b3_weekend_penalty_computes_pct_drops():
    # NOTE: lsoa_service_levels.total_weekday_trips/total_sunday_trips are
    # zero-filled in production (see MEMORY.md Critical Data Traps), so this
    # builder reads from lsoa_service_quality (total_weekday_departures /
    # total_sunday_departures / sunday_desert) instead — no Saturday figure
    # exists in any audit table, so saturday_pct_drop is omitted.
    stats = build_misc_stats(
        "b3_weekend_penalty", region="all", region_name="all", urban_rural="all",
        policy_df=_policy_df(), service_levels_df=None,
        service_quality_df=_service_quality_df(), route_geometries_df=None, anomalies_df=None, lta_df=None,
    )
    weekday = 800.0
    sunday = 220.0
    assert stats["sunday_pct_drop"] == pytest.approx((1 - sunday / weekday) * 100)
    assert "saturday_pct_drop" not in stats
    assert stats["n_sunday_desert"] == 3


def test_c1_route_length_uses_describe_distribution():
    stats = build_misc_stats(
        "c1_route_length", region="E12000007", region_name="London", urban_rural="all",
        policy_df=_policy_df(), service_levels_df=None, service_quality_df=None,
        route_geometries_df=_route_geometries_df(), anomalies_df=None, lta_df=None,
    )
    assert stats["metric_name"] == "route length"
    assert stats["unit"] == "km"
    assert stats["median"] == pytest.approx(12.0)
    assert stats["skew_label"] in ("right-skewed (positive)", "left-skewed (negative)", "approximately symmetric")


def test_c2_stops_per_route_uses_stop_count():
    stats = build_misc_stats(
        "c2_stops_per_route", region="E12000007", region_name="London", urban_rural="all",
        policy_df=_policy_df(), service_levels_df=None, service_quality_df=None,
        route_geometries_df=_route_geometries_df(), anomalies_df=None, lta_df=None,
    )
    assert stats["metric_name"] == "stops per route"
    assert stats["median"] == pytest.approx(22.0)


def test_d7_deprivation_urban_rural_finds_worst_and_best_cells():
    stats = build_misc_stats(
        "d7_deprivation_urban_rural", region="all", region_name="all", urban_rural="all",
        policy_df=_policy_df(), service_levels_df=None, service_quality_df=None,
        route_geometries_df=None, anomalies_df=None, lta_df=None,
    )
    assert stats["worst_cell"]["value"] == pytest.approx(30.0)
    assert stats["best_cell"]["value"] == pytest.approx(90.0)
    assert "Decile" in stats["worst_cell"]["label"]


def test_f3_and_f4_are_stubbed():
    assert build_misc_stats("f3_ethnic_access", region="all", region_name="all", urban_rural="all", policy_df=_policy_df(), service_levels_df=None, service_quality_df=None, route_geometries_df=None, anomalies_df=None, lta_df=None) == {}
    assert build_misc_stats("f4_gender_accessibility", region="all", region_name="all", urban_rural="all", policy_df=_policy_df(), service_levels_df=None, service_quality_df=None, route_geometries_df=None, anomalies_df=None, lta_df=None) == {}


def test_g2_anomalies_counts_each_type():
    stats = build_misc_stats(
        "g2_anomalies", region="all", region_name="all", urban_rural="all",
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
        "bsa3_tier_distribution", region="all", region_name="all", urban_rural="all",
        policy_df=_policy_df(), service_levels_df=None, service_quality_df=None,
        route_geometries_df=None, anomalies_df=None, lta_df=_lta_df(),
    )
    assert stats["n_total"] == 4
    assert stats["n_tier1"] == 1
    assert stats["n_tier2"] == 2
    assert stats["n_tier3"] == 1
    assert stats["is_lad_level_unfiltered"] is False


@pytest.mark.parametrize("urban_rural", ["urban", "rural"])
def test_bsa3_tier_distribution_flags_lad_level_when_area_filtered(urban_rural: str):
    stats = build_misc_stats(
        "bsa3_tier_distribution", region="all", region_name="all", urban_rural=urban_rural,
        policy_df=_policy_df(), service_levels_df=None, service_quality_df=None,
        route_geometries_df=None, anomalies_df=None, lta_df=_lta_df(),
    )
    # LAD-grain data can't be subdivided — counts identical to "all".
    assert stats["n_total"] == 4
    assert stats["n_tier1"] == 1
    assert stats["n_tier2"] == 2
    assert stats["n_tier3"] == 1
    assert stats["is_lad_level_unfiltered"] is True


def test_empty_inputs_return_empty():
    empty = pd.DataFrame()
    assert build_misc_stats("a3_walking_distance", region="all", region_name="all", urban_rural="all", policy_df=empty, service_levels_df=None, service_quality_df=None, route_geometries_df=None, anomalies_df=None, lta_df=None) == {}
    assert build_misc_stats("g2_anomalies", region="all", region_name="all", urban_rural="all", policy_df=_policy_df(), service_levels_df=None, service_quality_df=None, route_geometries_df=None, anomalies_df=empty, lta_df=None) == {}
