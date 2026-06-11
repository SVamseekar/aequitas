"""Route urban/rural classification — per-route area-type via stop-LSOA join.

Classifies each BODS route as "urban", "rural", or "mixed" based on the
urban/rural split (ONS RUC 2021, via lsoa_service_quality.urban_rural) of the
LSOAs its stops fall in. Reuses `route_stop_sequences.parquet` (all 13,640
routes, not gated on the 53% with shape geometry) and the existing, tested
`assign_stops_to_lsoa` two-pass spatial join.

Output contract (consumed by c4_urban_rural_routes and, later, b4_route_frequency):
    route_id, urban_rural_classification (urban/rural/mixed), primary_region
"""

import pandas as pd
from loguru import logger

from aequitas.core.config import PipelineConfig
from aequitas.ingestion.boundaries import load_lsoa_boundaries
from aequitas.processing.spatial import assign_stops_to_lsoa

_URBAN_RURAL_THRESHOLD = 0.8

# England bounding box (matches route_geometry.py's BODS-stops filter) —
# excludes Scotland/Wales/NI stops that LSOA boundaries (England-only) and
# the 2km nearest-fallback can never match.
_ENGLAND_LAT_RANGE = (49.8, 55.9)
_ENGLAND_LON_RANGE = (-6.5, 1.9)


def _classify_route(group: pd.Series) -> str:
    """Classify a route's urban/rural mix from per-stop urban_rural labels.

    Args:
        group: Series of "Urban"/"Rural" values, one per stop on the route.

    Returns:
        "urban" if >80% of stops are Urban, "rural" if >80% are Rural,
        else "mixed".
    """
    urban_share = (group == "Urban").mean()
    rural_share = (group == "Rural").mean()
    if urban_share > _URBAN_RURAL_THRESHOLD:
        return "urban"
    if rural_share > _URBAN_RURAL_THRESHOLD:
        return "rural"
    return "mixed"


def _assign_unique_stops_to_lsoa(stops: pd.DataFrame, cfg: PipelineConfig) -> pd.DataFrame:
    """Spatial-join unique stops to LSOAs, then to urban/rural labels.

    Args:
        stops: DataFrame with unique stop_id, stop_lat, stop_lon.
        cfg: Pipeline config (provides raw_dir for boundaries).

    Returns:
        stops with added lsoa_code and urban_rural columns.
    """
    lsoa_gdf = load_lsoa_boundaries(cfg.raw_dir / "boundaries")
    stops_renamed = stops.rename(columns={"stop_lon": "Longitude", "stop_lat": "Latitude"})
    joined = assign_stops_to_lsoa(stops_renamed, lsoa_gdf, max_nearest_distance_m=2000.0)

    sqi = pd.read_parquet(cfg.audit_dir / "lsoa_service_quality.parquet")
    urban_rural_lookup = sqi[["LSOA21CD", "urban_rural"]].drop_duplicates()
    joined = joined.merge(
        urban_rural_lookup, left_on="lsoa_code", right_on="LSOA21CD", how="left"
    )
    return joined[["stop_id", "urban_rural"]]


def compute_route_urban_rural(cfg: PipelineConfig) -> pd.DataFrame:
    """Build the route_id -> urban/rural/mixed classification intermediate.

    Joins unique stops (deduped from route_stop_sequences) to LSOAs via the
    existing two-pass spatial join, attaches urban/rural labels from
    lsoa_service_quality, classifies each route by its stop mix, and merges
    primary_region from route_geometries.

    Args:
        cfg: Pipeline config — provides audit_dir for source parquets and
            raw_dir for LSOA boundaries.

    Returns:
        DataFrame with columns: route_id, urban_rural_classification,
        primary_region.
    """
    sequences = pd.read_parquet(cfg.audit_dir / "route_stop_sequences.parquet")
    logger.info(
        "route_stop_sequences: {} rows, {} unique routes, {} unique stops",
        len(sequences), sequences["route_id"].nunique(),
        sequences[["stop_id", "stop_lat", "stop_lon"]].drop_duplicates().shape[0],
    )

    unique_stops = sequences[["stop_id", "stop_lat", "stop_lon"]].drop_duplicates(subset=["stop_id"])
    in_england = unique_stops["stop_lat"].between(*_ENGLAND_LAT_RANGE) & unique_stops["stop_lon"].between(
        *_ENGLAND_LON_RANGE
    )
    n_outside = (~in_england).sum()
    if n_outside:
        logger.info("Excluding {} stops outside England bbox from spatial join", n_outside)
    stop_labels = _assign_unique_stops_to_lsoa(unique_stops[in_england], cfg)

    route_stops = sequences[["route_id", "stop_id"]].drop_duplicates().merge(
        stop_labels, on="stop_id", how="left"
    )

    classifications = (
        route_stops.groupby("route_id")["urban_rural"]
        .apply(_classify_route)
        .reset_index()
        .rename(columns={"urban_rural": "urban_rural_classification"})
    )

    route_geometries = pd.read_parquet(cfg.audit_dir / "route_geometries.parquet")
    result = classifications.merge(
        route_geometries[["route_id", "primary_region"]], on="route_id", how="left"
    )

    logger.info(
        "route_urban_rural: {} routes classified — {}",
        len(result),
        result["urban_rural_classification"].value_counts().to_dict(),
    )
    return result
