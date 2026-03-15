"""Tests for BODS GTFS ingestion."""

import pytest
from aequitas.core.config import PipelineConfig
from aequitas.ingestion.bods import load_bods_routes, load_bods_trips, load_bods_stops, load_bods_calendar


@pytest.fixture(scope="module")
def cfg():
    return PipelineConfig()


@pytest.fixture(scope="module")
def bods_zip(cfg):
    return cfg.raw_dir / "bods" / "bods_gtfs_all.zip"


def test_routes_count(bods_zip, ground_truth):
    routes = load_bods_routes(bods_zip)
    # BODS is a live feed — allow ±10% drift from the Phase 0 snapshot count
    expected = ground_truth["bods"]["raw_route_rows"]
    assert abs(len(routes) - expected) / expected < 0.10, (
        f"Routes count {len(routes)} deviates >10% from Phase 0 ground truth {expected}"
    )


def test_routes_unique_ids(bods_zip):
    routes = load_bods_routes(bods_zip)
    assert routes["route_id"].nunique() == len(routes)


def test_trips_count(bods_zip, ground_truth):
    trips = load_bods_trips(bods_zip)
    assert len(trips) == ground_truth["bods"]["total_trips"]


def test_stops_count(bods_zip, ground_truth):
    stops = load_bods_stops(bods_zip)
    assert stops["stop_id"].nunique() == ground_truth["bods"]["bods_unique_stop_ids"]


def test_calendar_loads(bods_zip):
    cal = load_bods_calendar(bods_zip)
    assert "service_id" in cal.columns
    assert len(cal) > 0
