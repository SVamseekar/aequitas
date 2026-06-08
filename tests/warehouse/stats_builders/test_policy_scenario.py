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


def test_ps2_coalesces_nan_co2_to_zero():
    stats = build_policy_scenario_stats("ps2_evening_extension", scenarios_df=_scenarios_df())
    assert stats["scenario"]["co2_saving_t_yr"] == 0.0


def test_ps4_coalesces_nan_cost_to_zero():
    stats = build_policy_scenario_stats("ps4_franchise", scenarios_df=_scenarios_df())
    assert stats["scenario"]["estimated_annual_cost_m"] == 0.0
    assert stats["scenario"]["co2_saving_t_yr"] == 0.0


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
    assert stats["scenarios"][3]["cost_m"] == 0.0  # row D NaN coalesced
    # cost-per-beneficiary: A=12.78, B=13.92, C=20.81, D=excluded (no cost)
    assert stats["best_bcr_scenario"] == "Frequency restoration — bottom IMD decile"


def test_empty_scenarios_returns_empty():
    assert build_policy_scenario_stats("ps1_freq_restoration", scenarios_df=pd.DataFrame()) == {}
    assert build_policy_scenario_stats("ps5_scenario_comparison", scenarios_df=pd.DataFrame()) == {}
