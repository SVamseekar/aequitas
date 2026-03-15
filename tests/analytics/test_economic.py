"""Tests for economic appraisal."""

import pytest
from aequitas.analytics.economic import (
    compute_bcr,
    compute_investment_gap,
    compute_modal_shift,
    pv_annuity,
)
from aequitas.core.constants import TAG


def test_pv_annuity():
    # 60-year annuity at 3.5% — Green Book formula
    pv = pv_annuity(annual=1000, rate=0.035, years=60)
    assert 24_000 < pv < 30_000


def test_pv_annuity_zero_rate():
    pv = pv_annuity(annual=1000, rate=0.0, years=10)
    assert pv == 10_000.0


def test_bcr_positive():
    t = TAG()
    bcr = compute_bcr(
        annual_benefit=1_000_000,
        annual_cost=800_000,
        rate=t.social_discount_rate,
        years=60,
    )
    assert bcr > 1.0


def test_bcr_below_one_if_cost_exceeds_benefit():
    bcr = compute_bcr(annual_benefit=500, annual_cost=1000, rate=0.035, years=60)
    assert bcr < 1.0


def test_modal_shift_co2_saving():
    result = compute_modal_shift(
        current_annual_trips=1_000_000,
        frequency_increase_pct=0.20,
        elasticity=0.55,
        modal_shift_fraction=0.25,
        avg_trip_distance_km=9.4,
    )
    assert result["co2_saved_tonnes"] > 0
    assert result["new_trips"] > 0
    assert result["modal_shift_trips"] < result["new_trips"]


def test_modal_shift_proportional_to_trips():
    r1 = compute_modal_shift(1_000_000, 0.20)
    r2 = compute_modal_shift(2_000_000, 0.20)
    assert abs(r2["new_trips"] / r1["new_trips"] - 2.0) < 0.01


def test_investment_gap_below_median():
    result = compute_investment_gap(
        current_trips_per_capita=10.0,
        national_median_trips_per_capita=30.0,
        population=5000,
        is_urban=False,
    )
    assert result["gap_trips"] > 0
    assert result["annual_cost_gbp"] > 0
    assert result["above_median"] is False


def test_investment_gap_above_median():
    result = compute_investment_gap(
        current_trips_per_capita=50.0,
        national_median_trips_per_capita=30.0,
        population=5000,
        is_urban=True,
    )
    assert result["gap_trips"] == 0.0
    assert result["above_median"] is True
