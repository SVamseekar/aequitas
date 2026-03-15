"""Tests for validation gates."""

import pytest
from aequitas.validation.gates import (
    check_entity_counts,
    check_lsoa_count,
    check_match_rates,
    check_population_total,
)
from aequitas.core.constants import POPULATION_ENGLAND, LSOA_COUNT_ENGLAND


def test_population_gate_passes():
    assert check_population_total(56_490_056)


def test_population_gate_passes_within_tolerance():
    assert check_population_total(56_490_056 + 50)
    assert check_population_total(56_490_056 - 50)


def test_population_gate_fails():
    assert not check_population_total(50_000_000)


def test_lsoa_gate_passes():
    assert check_lsoa_count(33_755)


def test_lsoa_gate_fails():
    assert not check_lsoa_count(33_000)


def test_entity_count_sanity():
    assert check_entity_counts(stops=274_719, routes=13_099)


def test_entity_count_fails_bad_stops():
    assert not check_entity_counts(stops=1_000_000, routes=13_099)


def test_entity_count_allows_routes_drift():
    # BODS is a live feed — allow ±10%
    assert check_entity_counts(stops=274_719, routes=13_500)  # within 10%


def test_entity_count_fails_excessive_routes_drift():
    assert not check_entity_counts(stops=274_719, routes=25_000)  # too many


def test_match_rate_passes():
    assert check_match_rates(stop_lsoa_rate=0.9999)


def test_match_rate_fails_low():
    assert not check_match_rates(stop_lsoa_rate=0.98)


def test_match_rate_demographic_check():
    assert check_match_rates(0.9999, [0.97, 0.98, 0.99])
    assert not check_match_rates(0.9999, [0.97, 0.93, 0.99])  # 0.93 < 0.95
