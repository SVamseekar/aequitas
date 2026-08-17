"""NAP agency / route aggregates for HHI and network sections, by mode."""

from __future__ import annotations

from io import BytesIO
from pathlib import Path
from zipfile import ZipFile

import numpy as np
import pandas as pd
from loguru import logger

from aequitas.france.constants import ALL_PT_ROUTE_TYPES, BUS_ROUTE_TYPES


def load_nap_network(gtfs_dir: Path, *, mode: str = "bus") -> dict:
    allowed = BUS_ROUTE_TYPES if mode == "bus" else ALL_PT_ROUTE_TYPES
    n_routes: dict[str, int] = {}
    agency_name: dict[str, str] = {}
    n_feeds = 0
    for zp in sorted(gtfs_dir.glob("*.zip")):
        prefix = zp.stem
        try:
            with ZipFile(zp) as zf:
                names = {Path(n).name.lower(): n for n in zf.namelist()}
                if "routes.txt" not in names:
                    continue
                n_feeds += 1
                routes = pd.read_csv(BytesIO(zf.read(names["routes.txt"])), dtype=str)
                routes["route_type"] = pd.to_numeric(routes.get("route_type"), errors="coerce")
                routes = routes[routes["route_type"].isin(allowed)]
                if "agency.txt" in names:
                    agencies = pd.read_csv(BytesIO(zf.read(names["agency.txt"])), dtype=str)
                    ncol = "agency_name" if "agency_name" in agencies.columns else "agency_id"
                    if "agency_id" in agencies.columns:
                        for aid, nam in zip(agencies["agency_id"].astype(str), agencies[ncol].astype(str)):
                            agency_name[f"{prefix}:{aid}"] = nam
                if "agency_id" not in routes.columns:
                    routes["agency_id"] = "unknown"
                for aid, cnt in routes.groupby(routes["agency_id"].astype(str))["route_id"].nunique().items():
                    key = f"{prefix}:{aid}"
                    n_routes[key] = n_routes.get(key, 0) + int(cnt)
        except Exception as exc:  # noqa: BLE001
            logger.warning("network skip {}: {}", zp.name, exc)
    if not n_routes:
        return {
            "hhi": None,
            "n_agencies": 0,
            "n_routes": 0,
            "agencies": [],
            "stops_per_route": [],
            "mean_stops_per_route": None,
            "mode": mode,
            "n_feeds": n_feeds,
        }
    series = pd.Series(n_routes)
    total = float(series.sum()) or 1.0
    hhi = float(((series / total) ** 2).sum() * 10_000.0)
    ranking = [
        {
            "name": agency_name.get(str(aid), str(aid)),
            "agency_id": str(aid),
            "n_routes": int(n),
            "share": float(n / total),
        }
        for aid, n in series.sort_values(ascending=False).items()
    ]
    logger.info("NAP network ({}): {} agencies, HHI {:.0f}, {} routes, {} feeds", mode, len(series), hhi, int(total), n_feeds)
    return {
        "hhi": hhi,
        "n_agencies": int(len(series)),
        "n_routes": int(total),
        "agencies": ranking,
        "stops_per_route": [],
        "mean_stops_per_route": None,
        "mode": mode,
        "n_feeds": n_feeds,
    }
