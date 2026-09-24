"""Country-keyed destination Parquets — never load England files on IE/NL/FR."""

from pathlib import Path

import pandas as pd
import pytest

from aequitas.analytics.destinations import (
    DEST_TYPES,
    destination_path,
    load_destination_frames,
    resolve_destination_path,
    validate_destination_frame,
    write_destination_frame,
)
from aequitas.ingestion.destinations import (
    DestinationHit,
    destinations_from_points,
    omit_if_missing,
    write_country_destinations,
)


def _points(n: int = 3, *, dest_type: str = "gp", prefix: str = "ie") -> pd.DataFrame:
    return pd.DataFrame(
        {
            "dest_id": [f"{prefix}-{dest_type}-{i}" for i in range(n)],
            "dest_type": dest_type,
            "lat": [53.3 + i * 0.01 for i in range(n)],
            "lon": [-6.2 + i * 0.01 for i in range(n)],
            "name": [f"Place {i}" for i in range(n)],
            "area_id": [f"SA{i:05d}" for i in range(n)],
            "weight": [1.0] * n,
            "source": ["fixture"] * n,
        }
    )


def test_destination_path_is_country_keyed(tmp_path: Path) -> None:
    fr = destination_path(tmp_path, "france", "jobs")
    ie = destination_path(tmp_path, "ireland", "gp")
    nl = destination_path(tmp_path, "netherlands", "school")
    en = destination_path(tmp_path, "england", "jobs")
    assert fr == tmp_path / "france" / "destinations_jobs.parquet"
    assert ie == tmp_path / "ireland" / "destinations_gp.parquet"
    assert nl == tmp_path / "netherlands" / "destinations_school.parquet"
    assert en == tmp_path / "england" / "destinations_jobs.parquet"
    assert "lsoa" not in str(fr)


def test_france_load_ignores_england_root_parquet(tmp_path: Path) -> None:
    england = _points(4, dest_type="jobs", prefix="en")
    england["lat"] = [51.5, 51.51, 52.4, 53.4]
    (tmp_path / "destinations_jobs.parquet").parent.mkdir(parents=True, exist_ok=True)
    england.to_parquet(tmp_path / "destinations_jobs.parquet", index=False)

    frames = load_destination_frames(tmp_path, "france")
    assert frames == {}
    assert resolve_destination_path(tmp_path, "france", "jobs") is None


def test_england_may_read_legacy_flat_path(tmp_path: Path) -> None:
    england = _points(2, dest_type="gp", prefix="en")
    england.to_parquet(tmp_path / "destinations_gp.parquet", index=False)
    path = resolve_destination_path(tmp_path, "england", "gp")
    assert path == tmp_path / "destinations_gp.parquet"
    frames = load_destination_frames(tmp_path, "england", dest_types=("gp",))
    assert "gp" in frames
    assert len(frames["gp"]) == 2


def test_england_prefers_country_keyed_over_legacy(tmp_path: Path) -> None:
    keyed = _points(1, dest_type="school", prefix="en-new")
    legacy = _points(5, dest_type="school", prefix="en-old")
    write_destination_frame(keyed, tmp_path, "england", "school")
    legacy.to_parquet(tmp_path / "destinations_school.parquet", index=False)
    path = resolve_destination_path(tmp_path, "england", "school")
    assert path == destination_path(tmp_path, "england", "school")
    frames = load_destination_frames(tmp_path, "england", dest_types=("school",))
    assert len(frames["school"]) == 1


def test_validate_ireland_frame_does_not_require_lsoa() -> None:
    df = _points(dest_type="school", prefix="ie")
    issues = validate_destination_frame(df, country="ireland")
    assert issues == []
    assert "lsoa" not in df.columns


def test_validate_rejects_missing_coordinates() -> None:
    df = _points(dest_type="gp", prefix="nl")
    df = df.drop(columns=["lat"])
    issues = validate_destination_frame(df, country="netherlands")
    assert any("lat" in issue for issue in issues)


def test_write_destination_frame_is_country_keyed(tmp_path: Path) -> None:
    df = _points(dest_type="jobs", prefix="fr")
    path = write_destination_frame(df, tmp_path, "france", "jobs")
    assert path == tmp_path / "france" / "destinations_jobs.parquet"
    assert path.exists()
    loaded = pd.read_parquet(path)
    assert set(DEST_TYPES).issuperset(set(loaded["dest_type"].unique()))
    assert "lsoa_code" not in loaded.columns


def test_destinations_from_points_normalises_schema() -> None:
    raw = pd.DataFrame(
        {
            "id": ["a", "b"],
            "latitude": [48.85, 45.75],
            "longitude": [2.35, 4.85],
            "label": ["Paris GP", "Lyon GP"],
        }
    )
    out = destinations_from_points(raw, dest_type="gp", source="INSEE BPE fixture", country="france")
    issues = validate_destination_frame(out, country="france")
    assert issues == []
    assert list(out["dest_type"].unique()) == ["gp"]
    assert out["source"].iloc[0] == "INSEE BPE fixture"


def test_omit_if_missing_does_not_invent_rows() -> None:
    hit = DestinationHit(url="https://example.invalid/missing.csv", status=404, bytes=0, rows=0)
    result = omit_if_missing(hit, dest_type="gp", country="ireland")
    assert result.written is None
    assert result.omit is True
    assert result.rows == 0
    assert "404" in result.reason


def test_jobs_from_area_centroids() -> None:
    from aequitas.ingestion.destinations import jobs_from_area_centroids

    areas = pd.DataFrame(
        {
            "sa_code": ["SA00001", "SA00002", "SA00003"],
            "lat": [53.3, 51.9, None],
            "lon": [-6.2, -8.5, -9.0],
            "workers": [100.0, 40.0, 10.0],
        }
    )
    out = jobs_from_area_centroids(
        areas,
        country="ireland",
        source="CSO workplace fixture",
        id_col="sa_code",
        weight_col="workers",
    )
    assert len(out) == 2
    assert set(out["dest_type"]) == {"jobs"}
    assert "lsoa" not in out.columns
    assert validate_destination_frame(out, country="ireland") == []


def test_ingest_country_destinations_from_local_csv(tmp_path: Path) -> None:
    from aequitas.ingestion.destinations import ingest_country_destinations

    local = tmp_path / "raw" / "france" / "destinations"
    local.mkdir(parents=True)
    _points(3, dest_type="school", prefix="fr").to_csv(local / "school.csv", index=False)
    report = ingest_country_destinations(
        country="france",
        processed_dir=tmp_path / "processed",
        raw_dir=tmp_path / "raw",
        probe=False,
    )
    assert "school" in report.written
    assert destination_path(tmp_path / "processed", "france", "school").exists()
    assert any(o.dest_type == "gp" and o.omit for o in report.omits)
    assert resolve_destination_path(tmp_path / "processed", "england", "school") is None


def test_write_country_destinations_writes_only_present_types(tmp_path: Path) -> None:
    frames = {"gp": _points(3, dest_type="gp", prefix="nl"), "school": None, "jobs": None}
    written = write_country_destinations(tmp_path, "netherlands", frames)
    assert set(written) == {"gp"}
    assert destination_path(tmp_path, "netherlands", "gp").exists()
    assert resolve_destination_path(tmp_path, "netherlands", "school") is None
    assert resolve_destination_path(tmp_path, "netherlands", "jobs") is None
    assert resolve_destination_path(tmp_path, "england", "gp") is None


def test_write_reach_france_skips_when_only_england_dests_exist(tmp_path: Path) -> None:
    from aequitas.analytics.reach import ReachConfig, StaticMinuteEngine, write_reach

    england_jobs = _points(8, dest_type="jobs", prefix="en")
    england_jobs.to_parquet(tmp_path / "destinations_jobs.parquet", index=False)
    pd.DataFrame({"lsoa": ["IRIS1"], "lat": [48.85], "lon": [2.35]}).to_parquet(
        tmp_path / "master_lsoa_table.parquet", index=False
    )
    matrix = pd.DataFrame({"origin_id": ["IRIS1"], "dest_id": ["en-jobs-0"], "minutes": [10]})
    out = write_reach(
        ReachConfig(
            processed_dir=tmp_path,
            raw_dir=tmp_path / "raw",
            country="france",
            dest_types=("jobs",),
            force=True,
        ),
        engine=StaticMinuteEngine(matrix),
    )
    assert out is None


def test_write_reach_uses_country_dest_paths_not_england_root(tmp_path: Path) -> None:
    from datetime import datetime, timezone

    from aequitas.analytics.reach import ReachConfig, StaticMinuteEngine, write_reach

    england_jobs = _points(8, dest_type="jobs", prefix="en")
    england_jobs.to_parquet(tmp_path / "destinations_jobs.parquet", index=False)

    fr_jobs = _points(2, dest_type="jobs", prefix="fr")
    write_destination_frame(fr_jobs, tmp_path, "france", "jobs")

    origins = pd.DataFrame(
        {
            "lsoa": ["IRIS1", "IRIS2"],
            "lat": [48.85, 48.86],
            "lon": [2.35, 2.36],
        }
    )
    origins.to_parquet(tmp_path / "master_lsoa_table.parquet", index=False)

    matrix = pd.DataFrame(
        {
            "origin_id": ["IRIS1", "IRIS1", "IRIS2", "IRIS2"],
            "dest_id": ["fr-jobs-0", "fr-jobs-1", "fr-jobs-0", "fr-jobs-1"],
            "minutes": [10, 20, 12, 40],
        }
    )
    cfg = ReachConfig(
        processed_dir=tmp_path,
        raw_dir=tmp_path / "raw",
        country="france",
        dest_types=("jobs",),
        force=True,
    )
    out = write_reach(cfg, engine=StaticMinuteEngine(matrix), departure=datetime(2024, 6, 11, 8, 0, tzinfo=timezone.utc))
    assert out is not None
    written = pd.read_parquet(out)
    assert set(written["lsoa"]) == {"IRIS1", "IRIS2"}
    assert len(written) == 2


def test_query_reach_france_does_not_load_england_dest(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from aequitas.analytics.reach import reach_output_path as real_reach_path
    from aequitas.api.services import reach_query as reach_query_mod

    england_reach = pd.DataFrame(
        {
            "lsoa": [f"E01{i:06d}" for i in range(5)],
            "dest_type": ["jobs"] * 5,
            "t_15": [10] * 5,
            "t_30": [20] * 5,
            "t_45": [30] * 5,
            "region": ["E12000005"] * 5,
        }
    )
    reach_dir = tmp_path / "reach"
    reach_dir.mkdir()
    england_reach.to_parquet(reach_dir / "lsoa_access_times.parquet", index=False)
    england_jobs = _points(20, dest_type="jobs", prefix="en")
    england_jobs.to_parquet(tmp_path / "destinations_jobs.parquet", index=False)

    def _path(_processed_dir: Path, country: str = "england") -> Path:
        return real_reach_path(tmp_path, country)

    monkeypatch.setattr(reach_query_mod, "reach_output_path", _path)
    payload = reach_query_mod.query_reach("jobs", 45, "all", "all", country="france")
    assert payload["available"] is False
    assert payload["n_areas"] == 0
    assert payload.get("median") is None
    note = str(payload.get("note") or "").lower()
    assert "france" in note
    assert payload["n_areas"] != 33755


def test_api_reach_france_never_returns_england_lsoa_count() -> None:
    from fastapi.testclient import TestClient

    from aequitas.api.app import create_app

    client = TestClient(create_app())
    resp = client.get("/api/reach", params={"country": "france", "dest_type": "jobs", "cutoff": 45})
    assert resp.status_code == 200
    body = resp.json()
    assert body["available"] is False
    assert body["n_areas"] == 0
    assert body["n_areas"] != 33755
    assert "france" in str(body.get("note") or "").lower()


def test_api_destinations_france_does_not_report_england_files(tmp_path: Path) -> None:
    from fastapi.testclient import TestClient

    from aequitas.analytics.destinations import destinations_inventory, write_destination_frame
    from aequitas.api.app import create_app

    write_destination_frame(_points(6, dest_type="gp", prefix="en"), tmp_path, "england", "gp")
    inv = destinations_inventory(tmp_path, "france")
    assert inv["destinations"]["gp"]["available"] is False
    assert inv["destinations"]["gp"]["rows"] == 0
    client = TestClient(create_app())
    resp = client.get("/api/destinations", params={"country": "france"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["country"] == "france"
    assert body["destinations"]["jobs"]["rows"] != 33755
