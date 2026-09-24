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


def test_delay_absent_leaves_late_null() -> None:
    obs = [
        TripObs(trip_id="v1", route_id="r1", delay_seconds=None),
        TripObs(trip_id="v2", route_id="r2", delay_seconds=None),
    ]
    body = build_rollup(
        country="england",
        observations=obs,
        n_entities=2,
        feeds=[],
        n_static_routes=13640,
        coverage_sentence="AVL",
    )
    assert body["n_with_delay"] == 0
    assert body["pct_late"] is None
    assert body["n_late"] == 0
    assert body["n_routes_with_update"] == 2


def test_delay_over_300_seconds_is_late() -> None:
    obs = [
        TripObs(trip_id="a", route_id="r1", delay_seconds=301),
        TripObs(trip_id="b", route_id="r1", delay_seconds=300),
        TripObs(trip_id="c", route_id="r2", delay_seconds=None),
    ]
    body = build_rollup(
        country="england",
        observations=obs,
        n_entities=3,
        feeds=[],
        n_static_routes=10,
        coverage_sentence="keyed",
    )
    assert body["n_with_delay"] == 2
    assert body["n_late"] == 1
    assert body["pct_late"] == 50.0
    assert body["late_threshold_seconds"] == 300


def test_siri_delay_element_counts_and_clocks_do_not() -> None:
    from aequitas.ops.collect import _england_coverage_sentence, _siri_vm_delay_obs

    xml = b"""
    <Siri><VehicleMonitoringDelivery>
      <VehicleActivity>
        <MonitoredVehicleJourney>
          <LineRef>42</LineRef>
          <DatedVehicleJourneyRef>trip-1</DatedVehicleJourneyRef>
          <Delay>PT6M</Delay>
        </MonitoredVehicleJourney>
      </VehicleActivity>
      <VehicleActivity>
        <MonitoredVehicleJourney>
          <LineRef>7</LineRef>
          <RecordedAtTime>2026-08-17T12:00:00Z</RecordedAtTime>
        </MonitoredVehicleJourney>
      </VehicleActivity>
    </VehicleMonitoringDelivery></Siri>
    """
    obs = _siri_vm_delay_obs(xml)
    assert len(obs) == 1
    assert obs[0].delay_seconds == 360
    assert obs[0].route_id == "42"
    sentence = _england_coverage_sentence(
        n_updates=2, n_routes=5351, n_static=13640, n_with_delay=0, key_set=False
    )
    assert "5351 of 13640" in sentence
    assert "n_with_delay = 0" in sentence
    assert "DfT punctuality" in sentence


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
