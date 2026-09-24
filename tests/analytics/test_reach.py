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


def test_missing_input_writes_no_parquet(tmp_path):
    """PBF, GTFS, or destinations absent: no parquet, no invented counts."""
    from aequitas.analytics.reach import ReachConfig, write_reach

    origins = pd.DataFrame({"lsoa": ["E01000001"], "region_code": ["E12000005"]})
    origins.to_parquet(tmp_path / "master_lsoa_table.parquet", index=False)
    raw = tmp_path / "raw"
    raw.mkdir()
    out = write_reach(
        ReachConfig(processed_dir=tmp_path, raw_dir=raw, region="E12000005", country="england"),
        engine=None,
    )
    assert out is None
    assert not (tmp_path / "reach" / "lsoa_access_times.parquet").exists()


def test_missing_r5py_writes_no_parquet(tmp_path, monkeypatch):
    """Street and timetable files exist, r5py does not: still write nothing."""
    from aequitas.analytics import reach as reach_mod
    from aequitas.analytics.reach import ReachConfig, write_reach

    origins = pd.DataFrame(
        {"lsoa": ["E01000001"], "lat": [52.48], "lon": [-1.89], "region_code": ["E12000005"]}
    )
    origins.to_parquet(tmp_path / "master_lsoa_table.parquet", index=False)
    jobs = pd.DataFrame(
        {"dest_id": ["j1"], "dest_type": ["jobs"], "lat": [52.49], "lon": [-1.90]}
    )
    (tmp_path / "england").mkdir()
    jobs.to_parquet(tmp_path / "england" / "destinations_jobs.parquet", index=False)
    raw = tmp_path / "raw"
    (raw / "osm").mkdir(parents=True)
    (raw / "osm" / "england-latest.osm.pbf").write_bytes(b"not-a-pbf")
    (raw / "bods").mkdir(parents=True)
    (raw / "bods" / "bods_gtfs_all.zip").write_bytes(b"not-a-zip")

    def _no_r5(_pbf, _gtfs):
        raise RuntimeError("r5py is not installed")

    monkeypatch.setattr(reach_mod, "try_build_r5_engine", _no_r5)
    out = write_reach(
        ReachConfig(
            processed_dir=tmp_path,
            raw_dir=raw,
            region="E12000005",
            country="england",
            force=True,
        ),
        engine=None,
    )
    assert out is None
    assert not (tmp_path / "reach" / "lsoa_access_times.parquet").exists()


@pytest.mark.parametrize("country", ["ireland", "netherlands", "france"])
def test_api_reach_never_returns_england_lsoa_count(country: str):
    from fastapi.testclient import TestClient

    from aequitas.api.app import create_app

    client = TestClient(create_app())
    resp = client.get("/api/reach", params={"country": country, "dest_type": "jobs", "cutoff": 45})
    assert resp.status_code == 200
    body = resp.json()
    assert body["available"] is False
    assert body["n_areas"] == 0
    assert body["n_areas"] != 33755
    assert country in str(body.get("note") or "").lower()


@pytest.mark.requires_data
def test_full_england_reach_optional():
    from aequitas.analytics.reach import reach_output_path
    from aequitas.core.config import PipelineConfig

    path = reach_output_path(PipelineConfig().processed_dir)
    if not path.exists():
        pytest.skip("no precomputed reach pack")
    df = pd.read_parquet(path)
    assert "t_45" in df.columns
