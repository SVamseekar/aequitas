"""The redesign's coverage layer must never relabel desert counts as percentages."""
import json

import duckdb
import pytest

from aequitas.api.services.score import map_areas_for_filter


def test_coverage_metric_uses_actual_coverage_not_desert_people() -> None:
    with duckdb.connect(":memory:") as db:
        db.execute("""CREATE TABLE section_results (
            region VARCHAR, urban_rural VARCHAR, section_id VARCHAR,
            stats VARCHAR, chart_data VARCHAR)
        """)
        for region, section, stats in [
            ("E12000002", "a3_walking_distance", {"pct_covered": 83.1}),
            ("E12000002", "a5_service_deserts", {"pop_affected": 583918}),
            ("E12000007", "a3_walking_distance", {"pct_covered": None}),
        ]:
            db.execute(
                "INSERT INTO section_results VALUES (?, 'all', ?, ?, '{}')",
                [region, section, json.dumps(stats)],
            )
        result = map_areas_for_filter(db, metric="coverage")
        assert result["metric_label"] == "LSOAs with non-zero access score (%)"
        assert result["data"] == [{
            "area_code": "E12000002", "area_name": "North West", "value": pytest.approx(83.1),
        }]
        assert not result["empty"]
        other = map_areas_for_filter(db, metric="coverage", country="ireland")
        assert other["metric_label"] == "People within 400 m of a stop (%)"
        assert other["data"] == result["data"]
        original = map_areas_for_filter(db)
        assert original['data'][0]['value'] == 583918
        assert original['metric_label'] == 'People with no nearby stop'


def test_missing_coverage_does_not_fall_back_to_desert_counts() -> None:
    with duckdb.connect(":memory:") as db:
        db.execute("""CREATE TABLE section_results (
            region VARCHAR, urban_rural VARCHAR, section_id VARCHAR,
            stats VARCHAR, chart_data VARCHAR)
        """)
        result = map_areas_for_filter(db, metric="coverage")
        assert result["empty"]
        assert result["data"] == []
