"""Route-length and stops-per-route histograms from one country's GTFS.

Length uses ``shape_dist_traveled`` when ``shapes.txt`` is present. A missing
shapes file is an omit sentence. Stop counts still ship from ``stop_times``.
"""

from __future__ import annotations

from io import BytesIO
from zipfile import ZipFile

import pandas as pd

LENGTH_OMIT = (
    "Route shapes are not in this GTFS pack, so the route-length distribution is omitted."
)
STOPS_OMIT = "Stops-per-route list not persisted."

_STOP_EDGES = (5, 10, 20, 40, 80, 10_000)
_STOP_LABELS = ("1–4", "5–9", "10–19", "20–39", "40–79", "80+")
_LENGTH_EDGES = (5, 10, 20, 40, 80, 10_000)
_LENGTH_LABELS = ("0–5 km", "5–10 km", "10–20 km", "20–40 km", "40–80 km", "80+ km")


def histogram_chart(
    values: list[float] | None,
    *,
    title: str,
    unit: str,
    kind: str,
    empty_reason: str,
) -> dict:
    """Bin *values*. Empty input is a histogram with a sentence, never zero-filled bins."""
    if not values:
        return {
            "type": "histogram",
            "title": title,
            "unit": unit,
            "data": [],
            "bins": [],
            "n": 0,
            "empty_reason": empty_reason,
        }
    edges = _LENGTH_EDGES if kind == "length" else _STOP_EDGES
    labels = _LENGTH_LABELS if kind == "length" else _STOP_LABELS
    counts = [0] * len(labels)
    for raw in values:
        v = float(raw)
        for i, hi in enumerate(edges):
            if v < hi or (i == len(edges) - 1):
                counts[i] += 1
                break
    data = [{"label": lab, "value": n} for lab, n in zip(labels, counts) if n > 0]
    return {
        "type": "histogram",
        "title": title,
        "unit": unit,
        "data": data,
        "bins": data,
        "n": len(values),
    }


def network_charts(
    extras: dict,
    *,
    place: str,
    length_title: str,
    stops_title: str,
) -> tuple[dict, dict]:
    lengths = extras.get("route_length_km")
    stops = extras.get("stops_per_route") or []
    c1 = histogram_chart(
        list(lengths) if lengths else None,
        title=length_title.format(place=place),
        unit="km",
        kind="length",
        empty_reason=LENGTH_OMIT,
    )
    c2 = histogram_chart(
        [float(v) for v in stops] if stops else None,
        title=stops_title.format(place=place),
        unit="stops",
        kind="stops",
        empty_reason=STOPS_OMIT,
    )
    return c1, c2


def scan_zip_route_stats(
    zf: ZipFile,
    names: dict[str, str],
    route_ids: set[str],
    *,
    id_prefix: str,
) -> tuple[list[int], list[float] | None]:
    """Unique stops per prefixed route id, plus km lengths when shapes exist.

    ``id_prefix`` is the feed dataset id (France NAP zip stem). It keeps
    colliding ``route_id`` values from different feeds apart.
    """
    if "trips.txt" not in names or "stop_times.txt" not in names or not route_ids:
        return [], None
    trips = pd.read_csv(
        BytesIO(zf.read(names["trips.txt"])),
        dtype=str,
        usecols=lambda c: c in {"trip_id", "route_id", "shape_id"},
    )
    trips = trips[trips["route_id"].astype(str).isin(route_ids)].copy()
    if trips.empty:
        shapes_present = "shapes.txt" in names
        return [], ([] if shapes_present else None)
    prefix = f"{id_prefix}:" if id_prefix else ""
    trips["route_key"] = prefix + trips["route_id"].astype(str)
    trip_route = trips[["trip_id", "route_key"]].drop_duplicates()
    acc: dict[str, set[str]] = {}
    with zf.open(names["stop_times.txt"]) as fh:
        for chunk in pd.read_csv(
            fh,
            usecols=lambda c: c in ("trip_id", "stop_id"),
            dtype=str,
            chunksize=400_000,
        ):
            merged = chunk.merge(trip_route, on="trip_id", how="inner")
            if merged.empty:
                continue
            for rid, grp in merged.groupby("route_key"):
                acc.setdefault(str(rid), set()).update(grp["stop_id"].astype(str))
    stops = [len(v) for v in acc.values()]
    if "shapes.txt" not in names or "shape_id" not in trips.columns:
        return stops, None
    lengths = _lengths_km(zf, names["shapes.txt"], trips)
    return stops, lengths


def _lengths_km(zf: ZipFile, shape_name: str, trips: pd.DataFrame) -> list[float] | None:
    with zf.open(shape_name) as fh:
        header = pd.read_csv(fh, nrows=0)
    if "shape_dist_traveled" not in header.columns or "shape_id" not in header.columns:
        return None
    dist: dict[str, float] = {}
    with zf.open(shape_name) as fh:
        for chunk in pd.read_csv(
            fh,
            usecols=["shape_id", "shape_dist_traveled"],
            dtype={"shape_id": str},
            chunksize=400_000,
        ):
            chunk["shape_dist_traveled"] = pd.to_numeric(chunk["shape_dist_traveled"], errors="coerce")
            peaked = chunk.groupby("shape_id")["shape_dist_traveled"].max()
            for sid, val in peaked.items():
                if pd.isna(val):
                    continue
                prev = dist.get(str(sid))
                dist[str(sid)] = float(val) if prev is None else max(prev, float(val))
    if not dist:
        return None
    work = trips.dropna(subset=["shape_id"]).copy()
    work["km"] = work["shape_id"].astype(str).map(dist)
    # GTFS shape_dist_traveled is metres.
    per_route = work.groupby("route_key")["km"].max() / 1000.0
    values = [float(v) for v in per_route.dropna().tolist() if float(v) > 0]
    return values or None
