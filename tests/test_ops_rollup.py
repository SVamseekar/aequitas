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


def test_ireland_without_key_names_401_and_404(monkeypatch) -> None:
    from aequitas.ops.collect import NTA_TRIP, NTA_VP, collect_ireland
    from aequitas.ops.fetch import FetchHit

    def fake_fetch(url, **kwargs):
        if url == NTA_TRIP:
            return FetchHit(url, 401, 152, 10, "TripUpdates (NTA)", "none", error="HTTP 401"), None
        if url == NTA_VP:
            return FetchHit(url, 404, 54, 8, "VehiclePositions (NTA)", "none", error="HTTP 404"), None
        raise AssertionError(url)

    monkeypatch.setattr("aequitas.ops.collect.fetch_bytes", fake_fetch)
    monkeypatch.delenv("NTA_API_KEY", raising=False)
    monkeypatch.delenv("NTA_GTFSR_KEY", raising=False)
    body = collect_ireland()
    assert body["empty"] is True
    assert body["pct_late"] is None
    reason = body["empty_reason"]
    assert "TripUpdates HTTP 401" in reason
    assert "VehiclePositions HTTP 404" in reason
    assert "Dublin Bus" in reason
    assert "Bus Éireann" in reason
    assert "Go-Ahead Ireland" in reason
    assert "BODS" not in reason
    assert "IMD" not in reason
    assert "LSOA" not in reason


def test_ireland_protobuf_drops_agencies_outside_three() -> None:
    from google.transit import gtfs_realtime_pb2

    from aequitas.ops.collect import split_nta_scope
    from aequitas.ops.proto import parse_feed_message

    feed = gtfs_realtime_pb2.FeedMessage()
    feed.header.gtfs_realtime_version = "2.0"
    dublin = feed.entity.add()
    dublin.id = "Dublin Bus"
    dublin.trip_update.trip.trip_id = "db-1"
    dublin.trip_update.trip.route_id = "46A"
    dublin.trip_update.stop_time_update.add().arrival.delay = 301
    luas = feed.entity.add()
    luas.id = "Luas"
    luas.trip_update.trip.trip_id = "luas-1"
    luas.trip_update.trip.route_id = "green"
    luas.trip_update.stop_time_update.add().arrival.delay = 900
    obs, n = parse_feed_message(feed.SerializeToString())
    assert n == 2
    kept, dropped = split_nta_scope(obs)
    assert [o.trip_id for o in kept] == ["db-1"]
    assert kept[0].delay_seconds == 301
    assert dropped == ["Luas"]


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


def _fr_feed(trip_id: str, route_id: str) -> bytes:
    from google.transit import gtfs_realtime_pb2

    feed = gtfs_realtime_pb2.FeedMessage()
    feed.header.gtfs_realtime_version = "2.0"
    ent = feed.entity.add()
    ent.id = trip_id
    ent.trip_update.trip.trip_id = trip_id
    ent.trip_update.trip.route_id = route_id
    ent.trip_update.stop_time_update.add().arrival.delay = 301
    return feed.SerializeToString()


def test_france_cap_skips_the_rest_and_prefixes_dataset_id(monkeypatch) -> None:
    from aequitas.ops import collect
    from aequitas.ops.fetch import FetchHit

    catalog = {
        "data": [
            {
                "id": "ds-ok",
                "title": "Metro bus",
                "resources": [{"format": "gtfs-rt", "url": "https://example.test/ok", "title": "rt"}],
            },
            {
                "id": "ds-cap",
                "title": "Second metro",
                "resources": [{"format": "gtfs-rt", "url": "https://example.test/capped", "title": "rt"}],
            },
            {
                "id": "ds-dom",
                "title": "Guadeloupe bus",
                "resources": [{"format": "gtfs-rt", "url": "https://example.test/dom", "title": "rt"}],
            },
        ]
    }
    calls: list[str] = []

    def fake_fetch(url, **kwargs):
        calls.append(url)
        if url == collect.NAP_DATASETS:
            body = __import__("json").dumps(catalog).encode()
            return FetchHit(url, 200, len(body), 5, "catalog", "none"), body
        if url.endswith("/ok"):
            body = _fr_feed("trip-1", "route-1")
            return FetchHit(url, 200, len(body), 5, "rt", "none"), body
        raise AssertionError(url)

    prefixed: list[str] = []
    real_prefix = collect._prefix_france_ids

    def spy(obs, dataset_id):
        real_prefix(obs, dataset_id)
        prefixed.extend(o.trip_id or "" for o in obs)

    monkeypatch.setattr(collect, "FR_RT_SAMPLE_CAP", 1)
    monkeypatch.setattr(collect, "fetch_bytes", fake_fetch)
    monkeypatch.setattr(collect, "_prefix_france_ids", spy)
    body = collect.collect_france()
    assert body["n_gtfs_rt_listed"] == 3
    assert body["n_sampled"] == 1
    assert body["skipped_reasons"]["not harvested this wave (cap)"] == 1
    assert body["skipped_reasons"]["DOM out"] == 1
    assert "3 listed / 1 sampled" in body["coverage_sentence"]
    assert "not a national AOM" in body["coverage_sentence"].lower() or "Not a national AOM" in body["coverage_sentence"]
    assert body["n_routes_with_update"] == 1
    assert calls == [collect.NAP_DATASETS, "https://example.test/ok"]
    assert prefixed == ["ds-ok:trip-1"]
    assert body["coverage_pct"] is None
    # The kept observation is inside the rollup only as a route count. Re-parse via a direct prefix check:
    from aequitas.ops.collect import _prefix_france_ids
    from aequitas.ops.proto import TripObs, parse_feed_message

    obs, _n = parse_feed_message(_fr_feed("trip-1", "route-1"))
    _prefix_france_ids(obs, "ds-ok")
    assert obs[0].trip_id == "ds-ok:trip-1"
    assert obs[0].route_id == "ds-ok:route-1"


def test_france_403_is_not_retried(monkeypatch) -> None:
    from aequitas.ops import collect
    from aequitas.ops.fetch import FetchHit

    catalog = {
        "data": [
            {
                "id": "lio",
                "title": "liO Occitanie",
                "resources": [{"format": "gtfs-rt", "url": "https://example.test/lio", "title": "rt"}],
            }
        ]
    }
    calls: list[str] = []

    def fake_fetch(url, **kwargs):
        calls.append(url)
        if url == collect.NAP_DATASETS:
            body = __import__("json").dumps(catalog).encode()
            return FetchHit(url, 200, len(body), 5, "catalog", "none"), body
        return FetchHit(url, 403, 12, 5, "rt", "none", error="HTTP 403"), None

    monkeypatch.setattr(collect, "fetch_bytes", fake_fetch)
    body = collect.collect_france()
    assert calls == [collect.NAP_DATASETS, "https://example.test/lio"]
    assert body["n_sampled"] == 1
    assert body["skipped_reasons"]["HTTP 403"] == 1
    assert body["empty"] is True
    assert "Not a national AOM figure" in body["coverage_sentence"]
    assert "BODS" not in body["coverage_sentence"]
    assert "IMD" not in body["coverage_sentence"]
    assert "LSOA" not in body["coverage_sentence"]
