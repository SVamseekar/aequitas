"""Reach writer on a tiny mocked network — no England PBF in CI."""

from datetime import datetime, timezone

import pandas as pd
import pytest

from aequitas.analytics.reach import (
    StaticMinuteEngine,
    count_within_cutoffs,
    validate_reach_frame,
    write_reach_from_engine,
)


def test_count_within_cutoffs():
    s = pd.Series([5, 15, 30, 45, 90, None, -1])
    c = count_within_cutoffs(s)
    assert c["t_15"] == 2
    assert c["t_30"] == 3
    assert c["t_45"] == 4


def test_write_reach_tiny_fixture(tmp_path):
    origins = pd.DataFrame({"lsoa": ["E01000001", "E01000002", "E01000003"]})
    dests = pd.DataFrame({"dest_id": ["j1", "j2", "j3"]})
    matrix = pd.DataFrame(
        {
            "origin_id": [
                "E01000001",
                "E01000001",
                "E01000001",
                "E01000002",
                "E01000002",
                "E01000002",
                "E01000003",
                "E01000003",
                "E01000003",
            ],
            "dest_id": ["j1", "j2", "j3"] * 3,
            "minutes": [10, 20, 40, 12, 35, 80, 50, 55, 60],
        }
    )
    out = write_reach_from_engine(
        origins,
        dests,
        StaticMinuteEngine(matrix),
        dest_type="jobs",
        region="E12000005",
        departure=datetime(2024, 6, 11, 8, 0, tzinfo=timezone.utc),
    )
    assert len(out) == 3
    row1 = out.set_index("lsoa").loc["E01000001"]
    assert int(row1["t_15"]) == 1
    assert int(row1["t_30"]) == 2
    assert int(row1["t_45"]) == 3
    issues = validate_reach_frame(out, expected_lsoas=3)
    assert issues == []
    path = tmp_path / "lsoa_access_times.parquet"
    out.to_parquet(path, index=False)
    assert path.exists()


@pytest.mark.requires_data
def test_full_england_reach_optional():
    from aequitas.analytics.reach import reach_output_path
    from aequitas.core.config import PipelineConfig

    path = reach_output_path(PipelineConfig().processed_dir)
    if not path.exists():
        pytest.skip("no precomputed reach pack")
    df = pd.read_parquet(path)
    assert "t_45" in df.columns
