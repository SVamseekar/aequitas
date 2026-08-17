"""Parse GTFS-RT protobuf without FastAPI (D01 — collectors only)."""

from __future__ import annotations

from dataclasses import dataclass, field

from google.transit import gtfs_realtime_pb2

LATE_THRESHOLD_SECONDS = 300  # 5 minutes; cited in every rollup


@dataclass
class TripObs:
    trip_id: str | None
    route_id: str | None
    stop_ids: list[str] = field(default_factory=list)
    delay_seconds: int | None = None
    skipped: bool = False
    cancelled: bool = False


def parse_feed_message(payload: bytes) -> tuple[list[TripObs], int]:
    """Return trip-level observations and raw entity count."""
    feed = gtfs_realtime_pb2.FeedMessage()
    feed.ParseFromString(payload)
    out: list[TripObs] = []
    for ent in feed.entity:
        if ent.HasField("trip_update"):
            out.append(_from_trip_update(ent.trip_update))
        elif ent.HasField("vehicle"):
            out.append(_from_vehicle(ent.vehicle))
    return out, len(feed.entity)


def _from_trip_update(tu) -> TripObs:
    trip = tu.trip
    trip_id = trip.trip_id or None
    route_id = trip.route_id or None
    cancelled = trip.schedule_relationship == gtfs_realtime_pb2.TripDescriptor.CANCELED
    delays: list[int] = []
    stop_ids: list[str] = []
    skipped = False
    for stu in tu.stop_time_update:
        if stu.stop_id:
            stop_ids.append(stu.stop_id)
        if stu.schedule_relationship == gtfs_realtime_pb2.TripUpdate.StopTimeUpdate.SKIPPED:
            skipped = True
        for field in ("arrival", "departure"):
            ev = getattr(stu, field)
            if ev.HasField("delay"):
                delays.append(int(ev.delay))
    delay = delays[-1] if delays else None
    return TripObs(
        trip_id=trip_id,
        route_id=route_id,
        stop_ids=stop_ids,
        delay_seconds=delay,
        skipped=skipped,
        cancelled=cancelled,
    )


def _from_vehicle(vp) -> TripObs:
    trip = vp.trip
    return TripObs(
        trip_id=trip.trip_id or None,
        route_id=trip.route_id or None,
        stop_ids=[],
        delay_seconds=None,
        skipped=False,
        cancelled=trip.schedule_relationship == gtfs_realtime_pb2.TripDescriptor.CANCELED,
    )
