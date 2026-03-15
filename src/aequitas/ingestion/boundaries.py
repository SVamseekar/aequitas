"""Boundary ingestion — LSOA and region GeoJSON.

Loads pre-downloaded boundary files with dynamic column detection
to handle ONS vintage variations (RGN21/RGN22).
"""

from pathlib import Path

import geopandas as gpd
from loguru import logger


def load_lsoa_boundaries(boundaries_dir: Path) -> gpd.GeoDataFrame:
    """Load LSOA 2021 boundaries for England.

    Returns GeoDataFrame with columns: LSOA21CD, LSOA21NM, geometry.
    Ground truth: 33,755 LSOAs (Phase 0 audit).
    """
    path = boundaries_dir / "lsoa_2021_england_buc.geojson"
    logger.info("Loading LSOA boundaries from {}", path)
    gdf = gpd.read_file(path)
    logger.info("LSOA boundaries loaded: {} features", len(gdf))
    return gdf


def load_region_boundaries(boundaries_dir: Path) -> gpd.GeoDataFrame:
    """Load region boundaries for England (9 regions).

    Handles both RGN21CD and RGN22CD column naming (ONS vintage variation).
    Returns GeoDataFrame with standardised columns: region_code, region_name, geometry.
    """
    path = boundaries_dir / "regions_2021_england_buc.geojson"
    logger.info("Loading region boundaries from {}", path)
    gdf = gpd.read_file(path)

    # Detect code/name column names dynamically
    code_col = next(
        (c for c in gdf.columns if c.startswith("RGN") and c.endswith("CD")), None
    )
    name_col = next(
        (c for c in gdf.columns if c.startswith("RGN") and c.endswith("NM")), None
    )
    if code_col is None or name_col is None:
        raise ValueError(f"Cannot find RGN code/name columns. Got: {list(gdf.columns)}")

    gdf = gdf.rename(columns={code_col: "region_code", name_col: "region_name"})
    logger.info("Region boundaries loaded: {} regions (code col: {})", len(gdf), code_col)
    return gdf[["region_code", "region_name", "geometry"]]
