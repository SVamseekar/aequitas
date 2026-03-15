"""Route geometry processing — Haversine lengths, cross-LA analysis, stop sequences.

Ported from Phase 0 notebook 04a. Streams shapes.txt (3.2GB) in chunks to
avoid OOM. shape_dist_traveled is 100% null in BODS — compute via Haversine.

Cross-LA analysis: spatial join BODS stops → LSOA boundaries, extract LA name
from LSOA21NM (format: "<LA Name> NNN<letter>"), count unique LAs per route.
"""

import re
from pathlib import Path
from zipfile import ZipFile

import geopandas as gpd
import numpy as np
import pandas as pd
from loguru import logger

from aequitas.core.config import PipelineConfig
from aequitas.ingestion.bods import load_bods_routes, load_bods_trips


def _haversine_km(lat1: np.ndarray, lon1: np.ndarray, lat2: np.ndarray, lon2: np.ndarray) -> np.ndarray:
    """Vectorised Haversine distance in km."""
    R = 6371.0
    dlat = np.radians(lat2 - lat1)
    dlon = np.radians(lon2 - lon1)
    a = np.sin(dlat / 2) ** 2 + np.cos(np.radians(lat1)) * np.cos(np.radians(lat2)) * np.sin(dlon / 2) ** 2
    return 2 * R * np.arcsin(np.sqrt(a))


def _compute_shape_lengths(zip_path: Path, chunk_size: int = 500_000) -> pd.DataFrame:
    """Stream shapes.txt in chunks → per shape_id total length in km.

    BODS shape_dist_traveled is 100% null — compute via Haversine.
    """
    logger.info("Streaming shapes.txt to compute Haversine lengths")
    shape_lengths: dict[str, float] = {}

    with ZipFile(zip_path) as zf:
        with zf.open("shapes.txt") as f:
            reader = pd.read_csv(
                f,
                usecols=["shape_id", "shape_pt_lat", "shape_pt_lon", "shape_pt_sequence"],
                chunksize=chunk_size,
                dtype={"shape_id": str},
            )
            chunk_num = 0
            # Accumulate points per shape across chunks
            shape_points: dict[str, list[tuple[float, float]]] = {}
            for chunk in reader:
                chunk_num += 1
                if chunk_num % 10 == 0:
                    logger.info("  shapes.txt chunk {}, processed {} shapes so far", chunk_num, len(shape_points))
                chunk = chunk.sort_values(["shape_id", "shape_pt_sequence"])
                for shape_id, grp in chunk.groupby("shape_id"):
                    pts = list(zip(grp["shape_pt_lat"].values, grp["shape_pt_lon"].values))
                    if shape_id not in shape_points:
                        shape_points[shape_id] = pts
                    else:
                        shape_points[shape_id].extend(pts)

    logger.info("Computing Haversine lengths for {} shapes", len(shape_points))
    for shape_id, pts in shape_points.items():
        if len(pts) < 2:
            shape_lengths[shape_id] = 0.0
            continue
        lats = np.array([p[0] for p in pts])
        lons = np.array([p[1] for p in pts])
        dists = _haversine_km(lats[:-1], lons[:-1], lats[1:], lons[1:])
        shape_lengths[shape_id] = float(dists.sum())

    return pd.DataFrame({
        "shape_id": list(shape_lengths.keys()),
        "length_km": list(shape_lengths.values()),
    })


def compute_route_geometries(cfg: PipelineConfig) -> pd.DataFrame:
    """Compute route geometries: lengths, cross-LA flags, stop counts.

    Algorithm:
    1. Stream shapes.txt → Haversine length per shape_id
    2. trips.txt → map shape_id to route_id (canonical = max length variant)
    3. Spatial join: route stops → LA boundaries → n_las, cross_la flag
    4. routes.txt → merge metadata

    Returns DataFrame with columns matching Phase 0 route_geometries.parquet schema.
    """
    zip_path = cfg.raw_dir / "bods" / "bods_gtfs_all.zip"

    # Load routes + trips
    routes = load_bods_routes(zip_path)
    trips = load_bods_trips(zip_path)

    # Compute shape lengths
    shape_df = _compute_shape_lengths(zip_path, chunk_size=cfg.shapes_chunk_size)
    logger.info("Shape lengths computed: {} shapes", len(shape_df))

    # Link trips → shapes: for each route, find the shape with max length (canonical)
    trip_shapes = trips[trips["shape_id"].notna()][["route_id", "shape_id"]].drop_duplicates()
    trip_shapes = trip_shapes.merge(shape_df, on="shape_id", how="left")

    # For each route: take max-length shape as canonical
    route_shapes = (
        trip_shapes.groupby("route_id")
        .agg(
            length_km=("length_km", "max"),
            mean_length_km=("length_km", "mean"),
            min_length_km=("length_km", "min"),
            n_shapes=("shape_id", "nunique"),
        )
        .reset_index()
    )

    # Stop count per route from stop sequences
    logger.info("Computing stop counts per route from stop_times.txt")
    route_stops: dict[str, set[str]] = {}
    with ZipFile(zip_path) as zf:
        with zf.open("stop_times.txt") as f:
            reader = pd.read_csv(
                f,
                usecols=["trip_id", "stop_id"],
                chunksize=cfg.stop_times_chunk_size,
                dtype=str,
            )
            # trips → route_id mapping
            trip_to_route = trips.set_index("trip_id")["route_id"].to_dict()
            for chunk in reader:
                for trip_id, grp in chunk.groupby("trip_id"):
                    route_id = trip_to_route.get(trip_id)
                    if route_id is None:
                        continue
                    if route_id not in route_stops:
                        route_stops[route_id] = set()
                    route_stops[route_id].update(grp["stop_id"].values)

    stop_count_df = pd.DataFrame({
        "route_id": list(route_stops.keys()),
        "stop_count": [len(v) for v in route_stops.values()],
    })

    # Cross-LA analysis: spatial join BODS stops → LSOA boundaries → LA name
    # Methodology matches Phase 0 notebook 04a exactly.
    logger.info("Computing cross-LA analysis via spatial join of stops to LSOA boundaries")

    # Load BODS stops (England bbox filter)
    with ZipFile(zip_path) as zf:
        with zf.open("stops.txt") as f:
            bods_stops = pd.read_csv(f, usecols=["stop_id", "stop_lat", "stop_lon"])

    # England bbox filter
    bods_stops = bods_stops[
        bods_stops["stop_lat"].between(49.8, 55.9)
        & bods_stops["stop_lon"].between(-6.5, 1.9)
    ].copy()

    # Spatial join stops → LSOA boundaries
    lsoa_gdf = gpd.read_file(cfg.raw_dir / "boundaries" / "lsoa_2021_england_buc.geojson")[
        ["LSOA21CD", "LSOA21NM", "geometry"]
    ]
    # Extract LA name from LSOA21NM: strip trailing " NNN[A-Z]" pattern
    lsoa_gdf["la_name"] = lsoa_gdf["LSOA21NM"].str.replace(r"\s+\d+[A-Z]$", "", regex=True).str.strip()

    stops_gdf = gpd.GeoDataFrame(
        bods_stops[["stop_id", "stop_lat", "stop_lon"]],
        geometry=gpd.points_from_xy(bods_stops["stop_lon"], bods_stops["stop_lat"]),
        crs="EPSG:4326",
    ).to_crs("EPSG:27700")
    lsoa_27700 = lsoa_gdf.to_crs("EPSG:27700")

    stops_with_la = gpd.sjoin(
        stops_gdf, lsoa_27700[["la_name", "geometry"]], how="left", predicate="within"
    )[["stop_id", "la_name"]]

    # Build stop → LA lookup
    stop_to_la = stops_with_la.dropna(subset=["la_name"]).drop_duplicates()

    # Flatten route_stops to DataFrame for merge
    route_stop_rows = [
        {"route_id": r, "stop_id": s}
        for r, stops_set in route_stops.items()
        for s in stops_set
    ]
    route_stops_df = pd.DataFrame(route_stop_rows)
    route_stops_la = route_stops_df.merge(stop_to_la, on="stop_id", how="left")

    route_la_counts = (
        route_stops_la.dropna(subset=["la_name"])
        .groupby("route_id")["la_name"]
        .nunique()
        .reset_index()
        .rename(columns={"la_name": "n_las"})
    )

    la_df = route_la_counts.copy()
    la_df["cross_la"] = la_df["n_las"] > 1

    # Merge everything onto routes
    result = routes[["route_id", "route_short_name", "route_long_name", "agency_id"]].copy()
    result = result.merge(route_shapes, on="route_id", how="left")
    result = result.merge(stop_count_df, on="route_id", how="left")
    result = result.merge(la_df, on="route_id", how="left")
    result["has_geometry"] = result["length_km"].notna() & (result["length_km"] > 0)

    # Fill defaults for routes without geometry
    result["length_km"] = result["length_km"].fillna(0.0)
    result["n_shapes"] = result["n_shapes"].fillna(0).astype(int)
    result["n_las"] = result["n_las"].fillna(1).astype(int)
    result["cross_la"] = result["cross_la"].fillna(False)
    result["stop_count"] = result["stop_count"].fillna(0).astype(int)

    n_geom = result["has_geometry"].sum()
    n_cross = result["cross_la"].sum()
    mean_len = result[result["has_geometry"]]["length_km"].mean()
    logger.info(
        "Route geometries: {} routes, {} with geometry, {} cross-LA, mean length {:.1f} km",
        len(result), n_geom, n_cross, mean_len,
    )
    return result.reset_index(drop=True)
