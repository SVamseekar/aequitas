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
