"""TFI agency / route aggregates for HHI and network sections."""

from __future__ import annotations

from io import BytesIO
from pathlib import Path
from zipfile import ZipFile

import numpy as np
import pandas as pd
from loguru import logger

from aequitas.analytics.route_distributions import scan_zip_route_stats


def load_tfi_network(gtfs_zip: Path) -> dict:
    """Agency shares (HHI 0–10,000), route counts, stops-per-route."""
    with ZipFile(gtfs_zip) as zf:
        names = {Path(n).name.lower(): n for n in zf.namelist()}
        agencies = pd.read_csv(BytesIO(zf.read(names["agency.txt"])))
        routes = pd.read_csv(BytesIO(zf.read(names["routes.txt"])), dtype=str)
        route_ids = set(routes["route_id"].astype(str))
        stops_per_route, lengths = scan_zip_route_stats(zf, names, route_ids, id_prefix="")

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

    logger.info("TFI network: {} agencies, HHI {:.0f}, {} routes", len(n_routes), hhi, int(total))
    return {
        "hhi": hhi,
        "n_agencies": int(len(n_routes)),
        "n_routes": int(total),
        "agencies": ranking,
        "stops_per_route": stops_per_route,
        "mean_stops_per_route": float(np.mean(stops_per_route)) if stops_per_route else None,
        "route_length_km": lengths,
    }
