"""Turn trip observations into a rollup the API can serve (no live math in handlers)."""

from __future__ import annotations

from collections import Counter, defaultdict
from typing import Any, Iterable

from aequitas.ops.proto import LATE_THRESHOLD_SECONDS, TripObs
from aequitas.ops.store import utcnow


def build_rollup(
    *,
    country: str,
    observations: list[TripObs],
    n_entities: int,
    feeds: list[dict[str, Any]],
    n_static_routes: int | None,
    coverage_sentence: str,
    empty: bool = False,
    empty_reason: str | None = None,
    by_region: list[dict[str, Any]] | None = None,
    by_imd_decile: list[dict[str, Any]] | None = None,
    extra: dict[str, Any] | None = None,
    window_note: str = "Single collector snapshot, not live-to-the-second polling.",
) -> dict[str, Any]:
    now = utcnow()
    with_delay = [o for o in observations if o.delay_seconds is not None]
    n_late = sum(1 for o in with_delay if o.delay_seconds > LATE_THRESHOLD_SECONDS)
    n_early = sum(1 for o in with_delay if o.delay_seconds < -LATE_THRESHOLD_SECONDS)
    n_on_time = len(with_delay) - n_late - n_early
    n_skipped = sum(1 for o in observations if o.skipped)
    n_cancelled = sum(1 for o in observations if o.cancelled)
    route_ids = {o.route_id for o in observations if o.route_id}
    n_routes = len(route_ids)
    coverage_pct = None
    if n_static_routes and n_static_routes > 0:
        coverage_pct = round(100.0 * n_routes / n_static_routes, 2)
    pct_late = round(100.0 * n_late / len(with_delay), 2) if with_delay else None
    pct_early = round(100.0 * n_early / len(with_delay), 2) if with_delay else None
    body: dict[str, Any] = {
        "country": country,
        "empty": empty,
        "empty_reason": empty_reason,
        "window_start": now,
        "window_end": now,
        "window_note": window_note,
        "late_threshold_seconds": LATE_THRESHOLD_SECONDS,
        "late_threshold_note": "Late = delay > 300 seconds (5 minutes) vs scheduled, from GTFS-RT stop_time_update delay.",
        "n_entities": n_entities,
        "n_updates": len(observations),
        "n_with_delay": len(with_delay),
        "n_late": n_late,
        "n_early": n_early,
        "n_on_time": n_on_time,
        "pct_late": pct_late,
        "pct_early": pct_early,
        "n_skipped": n_skipped,
        "n_cancelled": n_cancelled,
        "n_static_routes": n_static_routes,
        "n_routes_with_update": n_routes,
        "coverage_pct": coverage_pct,
        "coverage_sentence": coverage_sentence,
        "vintage": now,
        "feeds": feeds,
        "by_region": by_region or [],
        "by_imd_decile": by_imd_decile or [],
    }
    if extra:
        body.update(extra)
    return body


def region_strip(rows: Iterable[tuple[str, str, TripObs]]) -> list[dict[str, Any]]:
    """rows: (region_code, region_name, obs) for observations that joined a region."""
    buckets: dict[str, list[TripObs]] = defaultdict(list)
    names: dict[str, str] = {}
    for code, name, obs in rows:
        buckets[code].append(obs)
        names[code] = name
    out: list[dict[str, Any]] = []
    for code, obs_list in sorted(buckets.items(), key=lambda kv: kv[0]):
        delayed = [o for o in obs_list if o.delay_seconds is not None]
        n_late = sum(1 for o in delayed if o.delay_seconds > LATE_THRESHOLD_SECONDS)
        out.append(
            {
                "code": code,
                "name": names[code],
                "n_updates": len(obs_list),
                "n_with_delay": len(delayed),
                "n_late": n_late,
                "n_skipped": sum(1 for o in obs_list if o.skipped),
                "pct_late": round(100.0 * n_late / len(delayed), 2) if delayed else None,
            }
        )
    return out


def imd_strip(rows: Iterable[tuple[int, TripObs]]) -> list[dict[str, Any]]:
    buckets: dict[int, list[TripObs]] = defaultdict(list)
    for decile, obs in rows:
        if 1 <= decile <= 10:
            buckets[decile].append(obs)
    out: list[dict[str, Any]] = []
    for decile in range(1, 11):
        obs_list = buckets.get(decile, [])
        delayed = [o for o in obs_list if o.delay_seconds is not None]
        n_late = sum(1 for o in delayed if o.delay_seconds > LATE_THRESHOLD_SECONDS)
        out.append(
            {
                "imd_decile": decile,
                "n_updates": len(obs_list),
                "n_with_delay": len(delayed),
                "n_late": n_late,
                "pct_late": round(100.0 * n_late / len(delayed), 2) if delayed else None,
            }
        )
    return out


def count_route_ids(observations: list[TripObs]) -> Counter:
    return Counter(o.route_id for o in observations if o.route_id)
