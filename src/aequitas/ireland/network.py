"""TFI agency / route aggregates for HHI and network sections."""

from __future__ import annotations

from io import BytesIO
from pathlib import Path
from zipfile import ZipFile

import numpy as np
import pandas as pd
from loguru import logger


def load_tfi_network(gtfs_zip: Path) -> dict:
    """Agency shares (HHI 0–10,000), route counts, stops-per-route."""
    with ZipFile(gtfs_zip) as zf:
        names = {Path(n).name.lower(): n for n in zf.namelist()}
        agencies = pd.read_csv(BytesIO(zf.read(names["agency.txt"])))
        routes = pd.read_csv(BytesIO(zf.read(names["routes.txt"])), dtype=str)
        trips = pd.read_csv(BytesIO(zf.read(names["trips.txt"])), dtype=str)
        st_name = names.get("stop_times.txt")
        stop_times = None
        if st_name:
            # Only trip_id + stop_id for uniqueness — full file is large.
            stop_times = pd.read_csv(
                BytesIO(zf.read(st_name)),
                usecols=lambda c: c in ("trip_id", "stop_id"),
                dtype=str,
            )

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

    stops_per_route: list[int] = []
    if stop_times is not None and not stop_times.empty:
        tt = trips[["trip_id", "route_id"]].drop_duplicates()
        st = stop_times.merge(tt, on="trip_id", how="left")
        spr = st.groupby("route_id")["stop_id"].nunique()
        stops_per_route = spr.astype(int).tolist()

    logger.info("TFI network: {} agencies, HHI {:.0f}, {} routes", len(n_routes), hhi, int(total))
    return {
        "hhi": hhi,
        "n_agencies": int(len(n_routes)),
        "n_routes": int(total),
        "agencies": ranking,
        "stops_per_route": stops_per_route,
        "mean_stops_per_route": float(np.mean(stops_per_route)) if stops_per_route else None,
    }
