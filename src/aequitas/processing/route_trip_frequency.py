"""Route trip frequency intermediate — per-route daily trip counts from BODS.

Computes `n_trips_per_day` per route_id by counting rows in BODS GTFS
trips.txt grouped by route_id (one row per scheduled trip on a representative
day), then joins route_short_name, agency_name, and primary_region from
route_geometries.parquet for display/filtering.

Output contract (consumed by b4_route_frequency):
    route_id, n_trips_per_day, route_short_name, agency_name, primary_region
"""

import pandas as pd
from loguru import logger

from aequitas.core.config import PipelineConfig
from aequitas.ingestion.bods import load_bods_routes, load_bods_trips

# GTFS route_type 3 = Bus. BODS includes other modes (rail, tube, DLR, coach,
# tram, ferry) under the same trips.txt — restricting to type 3 matches the
# ground-truth "13,099 unique BODS routes" (ground truth) and avoids non-bus
# services (e.g. London Underground, DLR) dominating the frequency ranking.
_BUS_ROUTE_TYPE = 3


def compute_route_trip_frequency(cfg: PipelineConfig) -> pd.DataFrame:
    """Build the route_id -> n_trips_per_day intermediate.

    Counts daily trips per bus route (GTFS route_type == 3) from BODS GTFS
    trips.txt and joins route_short_name, agency_name, and primary_region
    from route_geometries.parquet.

    Args:
        cfg: Pipeline config — provides raw_dir for the BODS zip and
            audit_dir for route_geometries.parquet.

    Returns:
        DataFrame with columns: route_id, n_trips_per_day, route_short_name,
        agency_name, primary_region.
    """
    zip_path = cfg.raw_dir / "bods" / "bods_gtfs_all.zip"
    trips = load_bods_trips(zip_path)
    routes = load_bods_routes(zip_path)

    bus_route_ids = set(routes.loc[routes["route_type"] == _BUS_ROUTE_TYPE, "route_id"])
    trips = trips[trips["route_id"].isin(bus_route_ids)]

    counts = (
        trips.groupby("route_id")
        .size()
        .reset_index(name="n_trips_per_day")
    )
    logger.info(
        "route_trip_frequency: {} routes, n_trips_per_day min={}, median={}, max={}",
        len(counts),
        counts["n_trips_per_day"].min(),
        counts["n_trips_per_day"].median(),
        counts["n_trips_per_day"].max(),
    )

    route_geometries = pd.read_parquet(cfg.audit_dir / "route_geometries.parquet")
    join_cols = ["route_id", "route_short_name", "agency_name", "primary_region"]
    available_cols = [c for c in join_cols if c in route_geometries.columns]
    result = counts.merge(route_geometries[available_cols], on="route_id", how="left")

    n_unmatched = result["primary_region"].isna().sum() if "primary_region" in result.columns else 0
    if n_unmatched:
        logger.warning(
            "route_trip_frequency: {} routes have no match in route_geometries", n_unmatched
        )

    return result
