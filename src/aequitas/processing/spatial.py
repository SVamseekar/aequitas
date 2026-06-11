"""Spatial join: assign stops to LSOAs and regions.

Two-pass strategy matching Phase 0 audit methodology:
  Pass 1: Point-in-polygon (catches 99.99%)
  Pass 2: sjoin_nearest for coastal/pier orphans (max 2km)
"""

from pathlib import Path

import geopandas as gpd
import pandas as pd
from loguru import logger


def assign_stops_to_lsoa(
    stops_df: pd.DataFrame,
    lsoa_gdf: gpd.GeoDataFrame,
    max_nearest_distance_m: float = 2000.0,
) -> pd.DataFrame:
    """Assign each stop to an LSOA via two-pass spatial join.

    Pass 1: point-in-polygon (EPSG:27700) for >99.99% of stops.
    Pass 2: sjoin_nearest with max 2km for coastal/pier orphans.

    Returns stops_df with added 'lsoa_code' column.
    Ground truth match rate: 99.9993% (Phase 0 audit, joins.stop_to_lsoa_match_rate_pct).
    """
    # Convert stops to GeoDataFrame in BNG (EPSG:27700)
    stops_gdf = gpd.GeoDataFrame(
        stops_df.reset_index(drop=True),
        geometry=gpd.points_from_xy(stops_df["Longitude"], stops_df["Latitude"]),
        crs="EPSG:4326",
    ).to_crs("EPSG:27700")

    lsoa_27700 = lsoa_gdf.to_crs("EPSG:27700") if lsoa_gdf.crs.to_epsg() != 27700 else lsoa_gdf
    lsoa_27700 = lsoa_27700.reset_index(drop=True)

    # Pass 1: point-in-polygon
    logger.info("Pass 1: point-in-polygon spatial join")
    joined = gpd.sjoin(
        stops_gdf, lsoa_27700[["LSOA21CD", "geometry"]], how="left", predicate="within"
    )
    # A point on a shared boundary can match multiple polygons — keep the
    # first match per stop to preserve a 1:1 row alignment with stops_gdf.
    joined = joined[~joined.index.duplicated(keep="first")]
    matched_mask = joined["LSOA21CD"].notna()
    logger.info("Pass 1 matched: {}/{}", matched_mask.sum(), len(joined))

    # Pass 2: nearest for unmatched
    unmatched_idx = stops_gdf.index[~matched_mask.values]
    if len(unmatched_idx) > 0:
        logger.info("Pass 2: sjoin_nearest for {} unmatched stops", len(unmatched_idx))
        unmatched = stops_gdf.loc[unmatched_idx].copy()
        nearest = gpd.sjoin_nearest(
            unmatched,
            lsoa_27700[["LSOA21CD", "geometry"]],
            how="left",
            max_distance=max_nearest_distance_m,
        )
        # Ties at equal distance can yield multiple matches per point —
        # keep the first to preserve a 1:1 alignment with unmatched_idx.
        nearest = nearest[~nearest.index.duplicated(keep="first")]
        joined.loc[unmatched_idx, "LSOA21CD"] = nearest["LSOA21CD"].reindex(unmatched_idx).values

    result = stops_df.copy()
    result["lsoa_code"] = joined["LSOA21CD"].values
    final_rate = result["lsoa_code"].notna().mean()
    logger.info("Final match rate: {:.4%}", final_rate)
    return result
