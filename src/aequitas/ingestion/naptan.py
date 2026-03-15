"""NaPTAN bus stop ingestion.

Loads the NaPTAN Stops.csv and filters to England active bus stops.
Filter chain: StopType ∈ {BCT, BCS, BCE} → Status == 'active' → ATCO prefix 000-499.
"""

from pathlib import Path

import pandas as pd
from loguru import logger

_BUS_STOP_TYPES = frozenset({"BCT", "BCS", "BCE"})
_REQUIRED_COLS = ["ATCOCode", "CommonName", "Latitude", "Longitude", "StopType", "Status"]
_EXTRA_COLS = ["Easting", "Northing"]


def load_naptan(path: Path) -> pd.DataFrame:
    """Load and filter NaPTAN stops to England active bus stops.

    Returns a DataFrame with exactly the England active bus stops.
    Ground truth: 274,719 rows (Phase 0 audit).
    """
    logger.info("Loading NaPTAN from {}", path)
    df = pd.read_csv(path, usecols=_REQUIRED_COLS + _EXTRA_COLS, low_memory=False)
    logger.info("Raw NaPTAN rows: {}", len(df))

    # Filter: bus stop types only
    df = df[df["StopType"].isin(_BUS_STOP_TYPES)]
    logger.info("After StopType filter (BCT/BCS/BCE): {}", len(df))

    # Filter: active only
    df = df[df["Status"] == "active"]
    logger.info("After Status=active filter: {}", len(df))

    # Filter: England ATCO prefixes — first digit 0-4 (5+ is Scotland/Wales/NI)
    # Note: granular 3-digit prefix (000-499) is equivalent but first-digit is simpler
    df = df[df["ATCOCode"].str[0].isin({"0", "1", "2", "3", "4"})]
    logger.info("After England ATCO filter: {}", len(df))

    # Filter: stops with geocoordinates only (those without lat/lon cannot be spatially joined)
    df = df[df["Latitude"].notna() & df["Longitude"].notna()]
    logger.info("After coordinate filter: {}", len(df))

    # Deduplicate on ATCO code (should already be unique)
    n_before = len(df)
    df = df.drop_duplicates(subset="ATCOCode", keep="first")
    if len(df) < n_before:
        logger.warning("Dropped {} duplicate ATCOCodes", n_before - len(df))

    logger.info("Final NaPTAN England active bus stops: {}", len(df))
    return df.reset_index(drop=True)
