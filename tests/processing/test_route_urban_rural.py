"""Tests for route urban/rural classification processing."""

import pandas as pd
import pytest

from aequitas.core.config import PipelineConfig
from aequitas.processing.route_urban_rural import _classify_route, compute_route_urban_rural


def test_classify_route_urban():
    group = pd.Series(["Urban"] * 9 + ["Rural"])
    assert _classify_route(group) == "urban"


def test_classify_route_rural():
    group = pd.Series(["Rural"] * 9 + ["Urban"])
    assert _classify_route(group) == "rural"


def test_classify_route_mixed():
    group = pd.Series(["Urban"] * 5 + ["Rural"] * 5)
    assert _classify_route(group) == "mixed"


def test_classify_route_handles_nan():
    # Stops outside England (no LSOA match) -> NaN urban_rural; majority
    # urban among matched stops should still classify as urban.
    group = pd.Series(["Urban"] * 9 + [None])
    assert _classify_route(group) == "urban"


@pytest.mark.slow
def test_compute_route_urban_rural_schema_and_coverage():
    cfg = PipelineConfig()
    result = compute_route_urban_rural(cfg)

    assert set(result.columns) == {"route_id", "urban_rural_classification", "primary_region"}
    # GT: route_stop_sequences.parquet has 13,640 unique routes.
    assert len(result) == 13_640
    assert result["urban_rural_classification"].isin(["urban", "rural", "mixed"]).all()
    # All three classifications should appear at this scale.
    assert set(result["urban_rural_classification"].unique()) == {"urban", "rural", "mixed"}
