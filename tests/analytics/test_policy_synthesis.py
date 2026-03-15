"""Tests for policy synthesis analytics."""

import pytest
from aequitas.core.config import PipelineConfig
from aequitas.analytics.policy_synthesis import (
    compute_priority_matrix,
    compute_lta_readiness,
    compute_policy_scenarios,
)


@pytest.mark.slow
def test_q1_priority_count():
    cfg = PipelineConfig()
    result = compute_priority_matrix(cfg)
    q1 = result[result["priority_quadrant"] == "Q1: High vulnerability, Low access (PRIORITY)"]
    # ST-031: 6,091 Q1 priority LSOAs
    assert abs(len(q1) - 6091) < 200


@pytest.mark.slow
def test_priority_matrix_covers_all_lsoas():
    cfg = PipelineConfig()
    result = compute_priority_matrix(cfg)
    # All 33,755 England LSOAs classified
    assert abs(len(result) - 33755) < 10
    assert result["priority_quadrant"].notna().all()


@pytest.mark.slow
def test_lta_readiness_lad_count():
    cfg = PipelineConfig()
    result = compute_lta_readiness(cfg)
    # 298 LADs ranked
    assert abs(len(result) - 298) < 10


@pytest.mark.slow
def test_lta_readiness_has_score():
    cfg = PipelineConfig()
    result = compute_lta_readiness(cfg)
    assert "franchising_readiness" in result.columns
    assert result["franchising_readiness"].between(0, 100).all()


@pytest.mark.slow
def test_policy_scenarios_count():
    cfg = PipelineConfig()
    result = compute_policy_scenarios(cfg)
    assert len(result) == 4
