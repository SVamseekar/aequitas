"""Tests for equity analytics."""

import pytest
import numpy as np
from aequitas.analytics.equity import (
    compute_gini,
    compute_palma_ratio,
    compute_concentration_index,
    compute_vulnerability_index,
    identify_triple_deprived,
)


def test_gini_perfect_equality():
    values = np.ones(100)
    weights = np.ones(100)
    assert compute_gini(values, weights) == pytest.approx(0.0, abs=0.01)


def test_gini_maximum_inequality():
    values = np.zeros(99)
    values = np.append(values, 100.0)
    weights = np.ones(100)
    assert compute_gini(values, weights) > 0.9


def test_palma_ratio():
    # Bottom 40% gets 10, top 10% gets 57 → Palma = 5.7
    values = np.array([10] * 40 + [20] * 50 + [57] * 10)
    weights = np.ones(100)
    ratio = compute_palma_ratio(values, weights)
    assert ratio == pytest.approx(5.7, abs=0.1)


def test_gini_zero_total_service_is_zero_by_convention():
    values = np.zeros(10)
    weights = np.ones(10)
    assert compute_gini(values, weights) == pytest.approx(0.0, abs=1e-9)


def test_gini_rejects_mismatched_lengths():
    with pytest.raises(ValueError):
        compute_gini(np.array([1.0, 2.0]), np.array([1.0, 2.0, 3.0]))


def test_gini_rejects_negative_weight():
    with pytest.raises(ValueError):
        compute_gini(np.array([1.0, 2.0]), np.array([1.0, -1.0]))


def test_gini_rejects_all_zero_weights():
    with pytest.raises(ValueError):
        compute_gini(np.array([1.0, 2.0]), np.array([0.0, 0.0]))


def test_gini_rejects_non_finite_input():
    with pytest.raises(ValueError):
        compute_gini(np.array([1.0, np.nan]), np.array([1.0, 1.0]))


def test_gini_allows_individual_zero_weight():
    # An unpopulated LSOA (population=0) contributes nothing and should not
    # be rejected — only a negative weight or an all-zero total is invalid.
    with_zero = compute_gini(np.array([1.0, 2.0, 5.0]), np.array([1.0, 0.0, 3.0]))
    without_zero = compute_gini(np.array([1.0, 5.0]), np.array([1.0, 3.0]))
    assert with_zero == pytest.approx(without_zero, abs=1e-9)


def test_palma_ratio_splits_boundary_area_proportionally():
    values = np.array([1.0, 10.0, 2.0, 2.0])
    weights = np.array([30.0, 10.0, 30.0, 30.0])
    # bottom 40 population units: all of the first area (30) + 10 of the second (2.0)
    # bottom_mean = (1.0*30 + 2.0*10) / 40 = 1.25
    assert compute_palma_ratio(values, weights) == pytest.approx(10.0 / 1.25, rel=1e-9)


def test_palma_ratio_is_order_invariant_for_tied_values():
    values = np.array([1.0, 1.0, 5.0, 5.0])
    weights = np.array([20.0, 40.0, 20.0, 20.0])
    order = [1, 0, 3, 2]
    palma_a = compute_palma_ratio(values, weights)
    palma_b = compute_palma_ratio(values[order], weights[order])
    assert palma_a == pytest.approx(palma_b, abs=1e-9)


def test_concentration_index_is_order_invariant_for_tied_ranks():
    service = np.array([10.0, 2.0, 5.0])
    rank = np.array([1, 1, 2])
    population = np.array([50.0, 150.0, 200.0])
    order = [1, 0, 2]
    ci_a = compute_concentration_index(service, rank, population)
    ci_b = compute_concentration_index(service[order], rank[order], population[order])
    assert ci_a == pytest.approx(ci_b, abs=1e-9)


def test_vulnerability_index_range():
    import pandas as pd
    df = pd.DataFrame({
        "imd_score": [80, 10, 50],
        "nocar_pct": [60, 10, 30],
        "elderly_pct": [30, 5, 15],
        "disability_pct": [25, 8, 12],
        "unemployment_rate": [15, 3, 8],
    })
    result = compute_vulnerability_index(df)
    assert result.between(0, 100).all()


def test_triple_deprived_count(master_lsoa_table):
    result = identify_triple_deprived(master_lsoa_table)
    # ST-021: 612 triple-deprived LSOAs (1.8%)
    assert abs(result.sum() - 612) < 50
