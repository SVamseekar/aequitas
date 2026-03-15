"""POI (Points of Interest) ingestion — loads Phase 0 geocoded Parquet files.

Design decision: POI data loads from Phase 0 geocoded Parquets in data/audit/.
Geocoding was validated in notebooks 03b-03e with confirmed counts.
Re-implementing geocoding adds complexity with no improvement to ground truth.
"""

from pathlib import Path

import pandas as pd
from loguru import logger


def load_hospitals(parquet_path: Path) -> pd.DataFrame:
    """Load geocoded NHS hospitals from Phase 0 audit Parquet.

    Filters to rows with valid lat/lon coordinates.
    Ground truth: 3,714 geocoded hospitals (Phase 0 notebook 03b).
    """
    logger.info("Loading hospitals from {}", parquet_path)
    df = pd.read_parquet(parquet_path)
    df = df[df["lat"].notna() & df["lon"].notna()].copy()
    logger.info("Hospitals loaded: {} geocoded", len(df))
    return df.reset_index(drop=True)


def load_gp_surgeries(parquet_path: Path) -> pd.DataFrame:
    """Load geocoded NHS GP surgeries from Phase 0 audit Parquet.

    Filters to rows with valid lat/lon coordinates.
    Ground truth: 12,059 geocoded GP practices (Phase 0 notebook 03c).
    """
    logger.info("Loading GP surgeries from {}", parquet_path)
    df = pd.read_parquet(parquet_path)
    df = df[df["lat"].notna()].copy()
    logger.info("GP surgeries loaded: {} geocoded", len(df))
    return df.reset_index(drop=True)


def load_schools(parquet_path: Path) -> pd.DataFrame:
    """Load geocoded schools from Phase 0 audit Parquet.

    Ground truth (secondary): 3,336 schools (Phase 0 notebook 03d).
    Use schools_secondary_geocoded.parquet for accessibility analysis.
    """
    logger.info("Loading schools from {}", parquet_path)
    df = pd.read_parquet(parquet_path)
    logger.info("Schools loaded: {} records", len(df))
    return df.reset_index(drop=True)


def load_employment_proxy(parquet_path: Path) -> pd.DataFrame:
    """Load LSOA employment proxy from Phase 0 audit Parquet.

    Employment proxy derived from BRES MSOA 2023 data, distributed to LSOAs
    by population weight. Ground truth: 32,919 LSOAs with proxy (97.5% coverage).
    """
    logger.info("Loading employment proxy from {}", parquet_path)
    df = pd.read_parquet(parquet_path)
    logger.info("Employment proxy loaded: {} LSOAs", len(df))
    return df.reset_index(drop=True)
