"""Tests for TAG v2.03fc and DESNZ 2025 constants."""

import pytest
from aequitas.core.constants import TAG, DESNZ, POPULATION_ENGLAND, LSOA_COUNT_ENGLAND


def test_population_denominator():
    assert POPULATION_ENGLAND == 56_490_056


def test_lsoa_count():
    assert LSOA_COUNT_ENGLAND == 33_755


def test_tag_vot_commuting():
    assert TAG().vot_commuting_2014 == pytest.approx(11.21, abs=0.01)


def test_tag_vot_leisure():
    assert TAG().vot_leisure_2014 == pytest.approx(5.12, abs=0.01)


def test_tag_carbon_central_2025():
    assert TAG().carbon_value_central_2025 == pytest.approx(259.87, abs=0.01)


def test_tag_discount_rate():
    assert TAG().social_discount_rate == pytest.approx(0.035, abs=0.001)


def test_desnz_bus_co2():
    assert DESNZ().bus_co2_avg_local == pytest.approx(0.10385, abs=0.0001)


def test_desnz_car_co2():
    assert DESNZ().car_co2_avg_diesel == pytest.approx(0.17304, abs=0.0001)


def test_desnz_modal_shift_saving():
    assert DESNZ().modal_shift_car_to_bus == pytest.approx(0.00779, abs=0.0001)
