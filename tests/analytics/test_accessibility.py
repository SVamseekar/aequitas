"""Tests for 2SFCA accessibility."""

import numpy as np
import pytest
from aequitas.analytics.accessibility import compute_2sfca, normalise_scores


def test_2sfca_zero_access():
    """LSOA with no stops within catchment → score 0."""
    result = compute_2sfca(
        demand_points=np.array([[0.0, 0.0]]),
        demand_pop=np.array([1000.0]),
        supply_points=np.array([[100000.0, 100000.0]]),  # far away
        supply_capacity=np.array([50.0]),
        catchment_m=400,
    )
    assert result[0] == 0.0


def test_2sfca_positive_access():
    """LSOA with stops within catchment → positive score."""
    result = compute_2sfca(
        demand_points=np.array([[0.0, 0.0]]),
        demand_pop=np.array([1000.0]),
        supply_points=np.array([[200.0, 200.0]]),  # ~283m away
        supply_capacity=np.array([50.0]),
        catchment_m=400,
    )
    assert result[0] > 0


def test_2sfca_more_stops_higher_score():
    """More stops nearby → higher accessibility score."""
    result_one = compute_2sfca(
        demand_points=np.array([[0.0, 0.0]]),
        demand_pop=np.array([1000.0]),
        supply_points=np.array([[100.0, 0.0]]),
        supply_capacity=np.array([50.0]),
        catchment_m=400,
    )
    result_two = compute_2sfca(
        demand_points=np.array([[0.0, 0.0]]),
        demand_pop=np.array([1000.0]),
        supply_points=np.array([[100.0, 0.0], [0.0, 100.0]]),
        supply_capacity=np.array([50.0, 50.0]),
        catchment_m=400,
    )
    assert result_two[0] > result_one[0]


def test_2sfca_output_shape():
    """Output shape matches number of demand points."""
    n_demand, n_supply = 100, 50
    rng = np.random.default_rng(42)
    demand = rng.uniform(0, 10000, (n_demand, 2))
    supply = rng.uniform(0, 10000, (n_supply, 2))
    result = compute_2sfca(
        demand_points=demand,
        demand_pop=rng.uniform(100, 2000, n_demand),
        supply_points=supply,
        supply_capacity=rng.uniform(10, 200, n_supply),
        catchment_m=1000,
    )
    assert result.shape == (n_demand,)
    assert (result >= 0).all()


def test_normalise_scores():
    """Normalised scores are in [0, 100]."""
    scores = np.array([0.0, 0.001, 0.005, 0.01])
    norm = normalise_scores(scores)
    assert norm.max() == 100.0
    assert norm.min() == 0.0


def test_normalise_all_zero():
    """All-zero scores → all-zero output."""
    scores = np.zeros(10)
    norm = normalise_scores(scores)
    assert (norm == 0).all()
