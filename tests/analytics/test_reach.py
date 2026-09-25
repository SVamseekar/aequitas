"""Reach writer on a tiny mocked network — no England PBF in CI."""

from datetime import datetime, timezone

import pandas as pd
import pytest

from aequitas.analytics.reach import (
    R5_UNREACHABLE,
    StaticMinuteEngine,
    clip_destinations,
    count_within_cutoffs,
    counts_from_minute_values,
    validate_reach_frame,
    write_reach_from_engine,
)


def test_departure_from_gtfs_uses_feed_start_date(tmp_path):
    import zipfile

    from aequitas.analytics.reach import departure_from_gtfs

    gtfs = tmp_path / "feed.zip"
    with zipfile.ZipFile(gtfs, "w") as zf:
        zf.writestr(
            "feed_info.txt",
            "feed_publisher_name,feed_start_date,feed_end_date\nBODS,20260924,20270801\n",
        )
    dep = departure_from_gtfs(gtfs)
    assert dep is not None
    assert dep.year == 2026 and dep.month == 9 and dep.day == 24
    assert dep.hour == 8
    assert departure_from_gtfs(tmp_path / "missing.zip") is None


def test_clip_keeps_destination_inside_buffer_and_drops_outside():
    origins = pd.DataFrame({"lat": [52.5, 52.5], "lon": [-1.9, -1.9]})
    destinations = pd.DataFrame(
        {
            "dest_id": ["inside", "outside"],
            "lat": [52.5, 60.0],
            "lon": [-1.9, -1.9],
        }
    )
    kept = clip_destinations(destinations, origins, buffer_km=40)
    assert set(kept["dest_id"]) == {"inside"}


def test_counts_from_minute_values_drops_unreachable():
    counts = counts_from_minute_values([10, 20, 40, 50, R5_UNREACHABLE, -1])
    assert counts == {"t_15": 1, "t_30": 2, "t_45": 3}


def test_counts_from_minute_values_zeroes_matching_id():
    counts = counts_from_minute_values([90], dest_ids=["E1"], origin_id="E1")
    assert counts["t_15"] == 1


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


def test_itl1_code_filters_region_name(tmp_path):
    """E12000005 is the West Midlands name in the warehouse, not a region_code column."""
    from aequitas.analytics.reach import ReachConfig, StaticMinuteEngine, write_reach

    origins = pd.DataFrame(
        {
            "lsoa": ["E01000001", "E01000002"],
            "lat": [52.48, 51.50],
            "lon": [-1.89, -0.12],
            "region": ["West Midlands", "London"],
        }
    )
    origins.to_parquet(tmp_path / "master_lsoa_table.parquet", index=False)
    (tmp_path / "england").mkdir()
    pd.DataFrame(
        {"dest_id": ["j1"], "dest_type": ["jobs"], "lat": [52.49], "lon": [-1.90]}
    ).to_parquet(tmp_path / "england" / "destinations_jobs.parquet", index=False)
    matrix = pd.DataFrame(
        {
            "origin_id": ["E01000001", "E01000002"],
            "dest_id": ["j1", "j1"],
            "minutes": [10, 12],
        }
    )
    out = write_reach(
        ReachConfig(
            processed_dir=tmp_path,
            raw_dir=tmp_path / "raw",
            region="E12000005",
            country="england",
            dest_types=("jobs",),
            force=True,
        ),
        engine=StaticMinuteEngine(matrix),
    )
    assert out is not None
    written = pd.read_parquet(out)
    assert set(written["lsoa"]) == {"E01000001"}


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
