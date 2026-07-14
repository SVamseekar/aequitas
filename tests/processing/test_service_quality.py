"""Tests for service quality processing."""

import pytest
from aequitas.core.config import PipelineConfig
from aequitas.processing.service_quality import compute_service_quality

pytestmark = [pytest.mark.slow, pytest.mark.requires_data]


def test_sqi_mean():
    cfg = PipelineConfig()
    result = compute_service_quality(cfg)
    # ST-015: mean SQI = 65.4/100
    assert 60 < result["sqi"].mean() < 70


def test_evening_isolated_count():
    cfg = PipelineConfig()
    result = compute_service_quality(cfg)
    evening = result[result["evening_isolated"]].shape[0]
    # ST-013: 5,189 evening isolated LSOAs (±200 for BODS growth)
    assert abs(evening - 5189) < 500


def test_sunday_desert_count():
    cfg = PipelineConfig()
    result = compute_service_quality(cfg)
    sunday = result[result["sunday_desert"]].shape[0]
    # ST-014: 6,745 Sunday deserts (±200 for BODS growth)
    assert abs(sunday - 6745) < 500
