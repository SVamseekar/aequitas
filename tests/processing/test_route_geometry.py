"""Tests for route geometry processing."""

import pytest
from aequitas.core.config import PipelineConfig
from aequitas.processing.route_geometry import compute_route_geometries


@pytest.mark.slow
def test_routes_with_geometry_count():
    cfg = PipelineConfig()
    result = compute_route_geometries(cfg)
    has_geom = result[result["has_geometry"]]
    # GT-027: 7,241 routes with geometry (±50 allowed for live BODS drift)
    assert abs(len(has_geom) - 7241) < 100


@pytest.mark.slow
def test_mean_route_length():
    cfg = PipelineConfig()
    result = compute_route_geometries(cfg)
    has_geom = result[result["has_geometry"]]
    mean_km = has_geom["length_km"].mean()
    # ST-010: mean 23.0 km
    assert 20.0 < mean_km < 26.0


@pytest.mark.slow
def test_cross_la_routes():
    cfg = PipelineConfig()
    result = compute_route_geometries(cfg)
    cross_la = result[result["n_las"] > 1]
    # ST-011: 5,143 cross-LA at Phase 0. BODS is a live feed — allow ±500 for dataset growth.
    assert abs(len(cross_la) - 5143) < 500
