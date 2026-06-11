"""Tests for route trip frequency processing."""

import pandas as pd
import pytest

from aequitas.core.config import PipelineConfig
from aequitas.processing.route_trip_frequency import compute_route_trip_frequency


@pytest.mark.slow
def test_compute_route_trip_frequency_schema_and_coverage():
    cfg = PipelineConfig()
    result = compute_route_trip_frequency(cfg)

    assert set(result.columns) == {
        "route_id", "n_trips_per_day", "route_short_name", "agency_name", "primary_region",
    }
    # GT: BODS GTFS routes.txt has 13,099 unique bus routes (route_type==3).
    assert len(result) == 13_099

    # Genuine variation, not a degenerate constant.
    assert result["n_trips_per_day"].min() == 1
    assert result["n_trips_per_day"].max() > 1000
    assert result["n_trips_per_day"].nunique() > 100


@pytest.mark.slow
def test_n_trips_per_day_is_positive_integer():
    cfg = PipelineConfig()
    result = compute_route_trip_frequency(cfg)
    assert (result["n_trips_per_day"] >= 1).all()
    assert pd.api.types.is_integer_dtype(result["n_trips_per_day"])
