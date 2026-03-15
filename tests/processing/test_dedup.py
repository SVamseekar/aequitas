"""Tests for cross-region deduplication."""

import pandas as pd
import pytest
from aequitas.processing.dedup import deduplicate_stops, deduplicate_routes


def test_dedup_stops_removes_duplicates():
    df = pd.DataFrame({
        "stop_id": ["A", "B", "A", "C"],
        "stop_name": ["x", "y", "x", "z"],
    })
    result = deduplicate_stops(df)
    assert len(result) == 3
    assert result["stop_id"].nunique() == len(result)


def test_dedup_routes_merges_regions():
    df = pd.DataFrame({
        "route_id": ["R1", "R1", "R2"],
        "line_name": ["1A", "1A", "2B"],
        "region_code": ["E12000001", "E12000002", "E12000003"],
        "trips_per_day": [48, 52, 30],
    })
    result = deduplicate_routes(df)
    assert len(result) == 2
    r1 = result[result["route_id"] == "R1"].iloc[0]
    assert set(r1["regions_served"]) == {"E12000001", "E12000002"}
    assert r1["trips_per_day"] == 52  # max
