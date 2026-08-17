"""Targeted Wave 8 ops tests — no full pytest suite."""

from __future__ import annotations

from pathlib import Path

from aequitas.ops.proto import LATE_THRESHOLD_SECONDS, TripObs
from aequitas.ops.rollup import build_rollup
from aequitas.ops.store import load_latest_rollup, write_rollup


def test_rollup_late_threshold_is_five_minutes() -> None:
    assert LATE_THRESHOLD_SECONDS == 300
    obs = [
        TripObs(trip_id="a", route_id="r1", delay_seconds=301),
        TripObs(trip_id="b", route_id="r1", delay_seconds=10),
        TripObs(trip_id="c", route_id="r2", delay_seconds=-400),
        TripObs(trip_id="d", route_id="r2", skipped=True),
    ]
    body = build_rollup(
        country="england",
        observations=obs,
        n_entities=4,
        feeds=[],
        n_static_routes=100,
        coverage_sentence="test",
    )
    assert body["n_late"] == 1
    assert body["n_early"] == 1
    assert body["n_on_time"] == 1
    assert body["n_skipped"] == 1
    assert body["n_routes_with_update"] == 2
    assert body["coverage_pct"] == 2.0
    assert body["pct_late"] == 33.33


def test_empty_ireland_does_not_copy_england_pct(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("AEQUITAS_OPS_DIR", str(tmp_path))
    write_rollup(
        "england",
        build_rollup(
            country="england",
            observations=[TripObs("t", "r", delay_seconds=900)],
            n_entities=1,
            feeds=[],
            n_static_routes=10,
            coverage_sentence="en",
        ),
        project_root=tmp_path,
    )
    write_rollup(
        "ireland",
        build_rollup(
            country="ireland",
            observations=[],
            n_entities=0,
            feeds=[],
            n_static_routes=None,
            coverage_sentence="NTA key missing",
            empty=True,
            empty_reason="NTA key missing — Dublin Bus, Bus Éireann, Go-Ahead only.",
        ),
        project_root=tmp_path,
    )
    ie = load_latest_rollup("ireland", project_root=tmp_path)
    en = load_latest_rollup("england", project_root=tmp_path)
    assert ie is not None and en is not None
    assert ie["empty"] is True
    assert ie["pct_late"] is None
    assert en["pct_late"] == 100.0
    assert "BODS" not in (ie["empty_reason"] or "")
    assert "IMD" not in (ie["empty_reason"] or "")
