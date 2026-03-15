"""Tests for spatial join processing."""

import pytest
from aequitas.core.config import PipelineConfig
from aequitas.ingestion.naptan import load_naptan
from aequitas.ingestion.boundaries import load_lsoa_boundaries
from aequitas.processing.spatial import assign_stops_to_lsoa


@pytest.fixture(scope="module")
def cfg():
    return PipelineConfig()


def test_stop_lsoa_match_rate(cfg, ground_truth):
    stops = load_naptan(cfg.raw_dir / "naptan" / "Stops.csv")
    lsoa_gdf = load_lsoa_boundaries(cfg.raw_dir / "boundaries")
    result = assign_stops_to_lsoa(stops, lsoa_gdf)
    match_rate = result["lsoa_code"].notna().mean()
    expected = ground_truth["joins"]["stop_to_lsoa_match_rate_pct"] / 100
    assert match_rate >= expected - 0.001


def test_all_lsoa_codes_valid(cfg):
    stops = load_naptan(cfg.raw_dir / "naptan" / "Stops.csv")
    lsoa_gdf = load_lsoa_boundaries(cfg.raw_dir / "boundaries")
    result = assign_stops_to_lsoa(stops, lsoa_gdf)
    matched = result[result["lsoa_code"].notna()]
    assert matched["lsoa_code"].str.match(r"^E0[12]\d{6}$").all()
