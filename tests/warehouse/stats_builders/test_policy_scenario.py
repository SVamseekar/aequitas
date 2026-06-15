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


def test_ps2_preserves_nan_co2_as_none():
    stats = build_policy_scenario_stats("ps2_evening_extension", scenarios_df=_scenarios_df())
    assert stats["scenario"]["co2_saving_t_yr"] is None


def test_ps4_preserves_nan_cost_and_co2_as_none():
    stats = build_policy_scenario_stats("ps4_franchise", scenarios_df=_scenarios_df())
    assert stats["scenario"]["estimated_annual_cost_m"] is None
    assert stats["scenario"]["co2_saving_t_yr"] is None


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
    assert stats["scenarios"][3]["cost_m"] is None  # row D not modeled, not coalesced to 0
    # cost-per-beneficiary: A=12.78, B=13.92, C=20.81, D=excluded (no cost)
    assert stats["best_bcr_scenario"] == "Frequency restoration — bottom IMD decile"


def test_empty_scenarios_returns_empty():
    assert build_policy_scenario_stats("ps1_freq_restoration", scenarios_df=pd.DataFrame()) == {}
    assert build_policy_scenario_stats("ps5_scenario_comparison", scenarios_df=pd.DataFrame()) == {}


def _elderly_df():
    """Tiny 6-LSOA stand-in for sources.correlation_df (region-filtered)."""
    return pd.DataFrame({
        "lsoa_cd": ["L1", "L2", "L3", "L4", "L5", "L6"],
        "imd_decile": [1, 1, 5, 10, 1, 3],
        "evening_isolated": [True, False, True, False, True, False],
        "urban_rural": ["Rural", "Urban", "Rural", "Rural", "Rural", "Urban"],
        "elderly_pct": [30.0, 10.0, 26.0, 20.0, 25.0, 5.0],
        "population": [1000, 2000, 1500, 1200, 900, 800],
    })


def test_ps1_without_elderly_df_falls_back_to_national_constant():
    stats = build_policy_scenario_stats("ps1_freq_restoration", scenarios_df=_scenarios_df())
    assert stats["scenario"]["population_affected"] == 5689818


def test_ps1_recomputes_population_from_imd_decile_1():
    stats = build_policy_scenario_stats(
        "ps1_freq_restoration", scenarios_df=_scenarios_df(), elderly_df=_elderly_df(),
    )
    # imd_decile == 1: L1 (1000) + L2 (2000) + L5 (900) = 3900
    assert stats["scenario"]["population_affected"] == 3900
    # smaller than the national constant
    assert stats["scenario"]["population_affected"] < 5689818
    # trips scaled proportionally
    expected_trips = round(34583390 * (3900 / 5689818))
    assert stats["scenario"]["annual_additional_trips"] == expected_trips


def test_ps2_recomputes_population_from_evening_isolated():
    stats = build_policy_scenario_stats(
        "ps2_evening_extension", scenarios_df=_scenarios_df(), elderly_df=_elderly_df(),
    )
    # evening_isolated == True: L1 (1000) + L3 (1500) + L5 (900) = 3400
    assert stats["scenario"]["population_affected"] == 3400
    assert stats["scenario"]["population_affected"] < 8392662


def test_ps3_recomputes_population_from_rural_and_elderly_threshold():
    stats = build_policy_scenario_stats(
        "ps3_drt_rural", scenarios_df=_scenarios_df(), elderly_df=_elderly_df(),
    )
    # Rural AND elderly_pct > 24.7: L1 (30.0, 1000) + L3 (26.0, 1500) + L5 (25.0, 900) = 3400
    # L4 is Rural but elderly_pct=20.0 (below threshold) -> excluded
    assert stats["scenario"]["population_affected"] == 3400
    assert stats["scenario"]["population_affected"] < 5243877


def test_ps4_stays_at_national_constant_regardless_of_filter():
    stats = build_policy_scenario_stats(
        "ps4_franchise", scenarios_df=_scenarios_df(), elderly_df=_elderly_df(),
    )
    # ps4 is LAD-level — top-5 LADs doesn't decompose by region
    assert stats["scenario"]["population_affected"] == 760008
    assert stats["scenario"]["annual_additional_trips"] == 4862418


def test_empty_elderly_df_returns_zero_population():
    stats = build_policy_scenario_stats(
        "ps1_freq_restoration", scenarios_df=_scenarios_df(), elderly_df=pd.DataFrame(),
    )
    assert stats["scenario"]["population_affected"] == 5689818  # falls back, empty -> national


def test_ps5_aggregates_recomputed_per_scenario_figures():
    stats = build_policy_scenario_stats(
        "ps5_scenario_comparison", scenarios_df=_scenarios_df(), elderly_df=_elderly_df(),
    )
    populations = {s["name"]: s["population"] for s in stats["scenarios"]}
    assert populations["Frequency restoration — bottom IMD decile"] == 3900
    assert populations["Last bus extended to 23:00 — evening isolated"] == 3400
    assert populations["DRT in rural elderly LSOAs"] == 3400
    assert populations["Bus Services Act — franchise top-5 LADs"] == 760008  # ps4 unchanged
