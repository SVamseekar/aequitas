"""Tests for economic.py — covers j1, j2, j3."""
import pandas as pd
import pytest

from aequitas.warehouse.stats_builders.economic import build_economic_stats


def _appraisal_df():
    return pd.DataFrame({
        "lsoa_cd": ["E01000001", "E01000002"],
        "annual_time_benefit": [100_000.0, 200_000.0],
        "annual_additional_trips": [5_000.0, 7_000.0],
        "pv_benefits": [6_000_000.0, 6_000_000.0],
        "pv_costs": [2_000_000.0, 1_000_000.0],
        "modal_shift_co2_net_saving_kg": [50_000.0, 70_000.0],
        "modal_shift_car_trips_replaced": [1_000.0, 1_500.0],
    })


def test_j1_economic_value_uses_blended_vot_constant():
    stats = build_economic_stats("j1_economic_value", appraisal_df=_appraisal_df(), region_name="London")
    assert stats["region_name"] == "London"
    assert stats["annual_benefit"] == pytest.approx(300_000.0)
    assert stats["n_trips"] == pytest.approx(12_000.0)
    assert stats["vot"] == pytest.approx(8.49)


def test_j2_bcr_uses_pv_ratio_and_60_year_appraisal():
    stats = build_economic_stats("j2_bcr", appraisal_df=_appraisal_df(), region_name="London")
    assert stats["bcr"] == pytest.approx(4.0)
    assert stats["vfm_band"] == "Very High"
    assert stats["area_name"] == "London"
    assert stats["investment_m"] == pytest.approx(3.0)
    assert stats["appraisal_years"] == 60


def test_j2_returns_empty_when_no_cost_data():
    df = _appraisal_df()
    df["pv_costs"] = 0.0
    assert build_economic_stats("j2_bcr", appraisal_df=df, region_name="London") == {}


def test_j3_carbon_uses_tag_2025_carbon_price():
    stats = build_economic_stats("j3_carbon", appraisal_df=_appraisal_df(), region_name="London")
    assert stats["co2_saving_tonnes"] == pytest.approx(120.0)
    assert stats["carbon_price"] == pytest.approx(259.87)
    assert stats["co2_value_k"] == pytest.approx(120.0 * 259.87 / 1000)
    assert stats["modal_shift_trips"] == pytest.approx(2_500.0)
    assert stats["scope"] == "London"


def test_empty_appraisal_df_returns_empty():
    empty = pd.DataFrame()
    assert build_economic_stats("j1_economic_value", appraisal_df=empty, region_name="London") == {}
    assert build_economic_stats("j2_bcr", appraisal_df=empty, region_name="London") == {}
    assert build_economic_stats("j3_carbon", appraisal_df=empty, region_name="London") == {}
