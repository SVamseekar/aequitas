"""OVapi agency / route aggregates for HHI and network sections, by mode."""

from __future__ import annotations

from io import BytesIO
from pathlib import Path
from zipfile import ZipFile

import numpy as np
import pandas as pd
from loguru import logger

from aequitas.netherlands.constants import ALL_PT_ROUTE_TYPES, BUS_ROUTE_TYPES


def load_ovapi_network(gtfs_zip: Path, *, mode: str = "bus", include_stops_per_route: bool = True) -> dict:
    allowed = BUS_ROUTE_TYPES if mode == "bus" else ALL_PT_ROUTE_TYPES
    with ZipFile(gtfs_zip) as zf:
        names = {Path(n).name.lower(): n for n in zf.namelist()}
        agencies = pd.read_csv(BytesIO(zf.read(names["agency.txt"])))
        routes = pd.read_csv(BytesIO(zf.read(names["routes.txt"])), dtype=str)
        trips = pd.read_csv(
            BytesIO(zf.read(names["trips.txt"])),
            dtype=str,
            usecols=lambda c: c in {"trip_id", "route_id"},
        )
    routes["route_type"] = pd.to_numeric(routes.get("route_type"), errors="coerce")
    routes = routes[routes["route_type"].isin(allowed)].copy()
    if "agency_id" not in routes.columns:
        routes["agency_id"] = "unknown"
    n_routes = routes.groupby("agency_id")["route_id"].nunique()
    total = float(n_routes.sum()) or 1.0
    shares = n_routes / total
    hhi = float((shares**2).sum() * 10_000.0)
    agency_name = {}
    if "agency_id" in agencies.columns:
        name_col = "agency_name" if "agency_name" in agencies.columns else "agency_id"
        agency_name = dict(zip(agencies["agency_id"].astype(str), agencies[name_col].astype(str)))
    ranking = [
        {
            "name": agency_name.get(str(aid), str(aid)),
            "agency_id": str(aid),
            "n_routes": int(n),
            "share": float(n_routes.loc[aid] / total),
        }
        for aid, n in n_routes.sort_values(ascending=False).items()
    ]
    keep_routes = set(routes["route_id"].astype(str))
    trips = trips[trips["route_id"].astype(str).isin(keep_routes)]
    stops_per_route: list[int] = []
    if not include_stops_per_route:
        logger.info("OVapi network ({}): {} agencies, HHI {:.0f}, {} routes (stops-per-route skipped)", mode, len(n_routes), hhi, int(total))
        return {
            "hhi": hhi,
            "n_agencies": int(len(n_routes)),
            "n_routes": int(total),
            "agencies": ranking,
            "stops_per_route": [],
            "mean_stops_per_route": None,
            "mode": mode,
        }
    with ZipFile(gtfs_zip) as zf:
        names = {Path(n).name.lower(): n for n in zf.namelist()}
        st_name = names.get("stop_times.txt")
        if st_name:
            acc: dict[str, set[str]] = {}
            with zf.open(st_name) as fh:
                for chunk in pd.read_csv(
                    fh, usecols=lambda c: c in ("trip_id", "stop_id"), dtype=str, chunksize=500_000
                ):
                    m = chunk.merge(trips, on="trip_id", how="inner")
                    for rid, g in m.groupby("route_id"):
                        acc.setdefault(str(rid), set()).update(g["stop_id"].astype(str))
            stops_per_route = [len(v) for v in acc.values()]
    logger.info("OVapi network ({}): {} agencies, HHI {:.0f}, {} routes", mode, len(n_routes), hhi, int(total))
    return {
        "hhi": hhi,
        "n_agencies": int(len(n_routes)),
        "n_routes": int(total),
        "agencies": ranking,
        "stops_per_route": stops_per_route,
        "mean_stops_per_route": float(np.mean(stops_per_route)) if stops_per_route else None,
        "mode": mode,
    }
