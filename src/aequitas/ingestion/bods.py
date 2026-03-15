"""BODS GTFS ingestion — routes, trips, stops, calendar from zip.

Reads from the bulk GTFS archive. stop_times.txt (5.8GB) and shapes.txt (3.2GB)
are NOT loaded here — they're streamed in processing stages that need them.
"""

from pathlib import Path
from zipfile import ZipFile

import pandas as pd
from loguru import logger


def _read_from_zip(zip_path: Path, filename: str, **kwargs: object) -> pd.DataFrame:
    """Read a CSV file from inside a zip archive."""
    with ZipFile(zip_path) as zf:
        with zf.open(filename) as f:
            return pd.read_csv(f, **kwargs)


def load_bods_routes(zip_path: Path) -> pd.DataFrame:
    """Load routes.txt from BODS GTFS zip.

    Returns all routes as-is. Deduplication happens in processing stage.
    Ground truth: 13,099 unique route_ids.
    """
    logger.info("Loading BODS routes from {}", zip_path)
    df = _read_from_zip(zip_path, "routes.txt")
    logger.info("BODS routes loaded: {}", len(df))
    return df


def load_bods_trips(zip_path: Path) -> pd.DataFrame:
    """Load trips.txt from BODS GTFS zip.

    Ground truth: 1,752,443 trips.
    """
    logger.info("Loading BODS trips from {}", zip_path)
    df = _read_from_zip(zip_path, "trips.txt", low_memory=False)
    logger.info("BODS trips loaded: {}", len(df))
    return df


def load_bods_stops(zip_path: Path) -> pd.DataFrame:
    """Load stops.txt from BODS GTFS zip.

    Ground truth: 310,598 unique stop_ids.
    """
    logger.info("Loading BODS stops from {}", zip_path)
    df = _read_from_zip(zip_path, "stops.txt")
    logger.info("BODS stops loaded: {} rows, {} unique stop_ids", len(df), df["stop_id"].nunique())
    return df


def load_bods_calendar(zip_path: Path) -> pd.DataFrame:
    """Load calendar.txt from BODS GTFS zip."""
    logger.info("Loading BODS calendar from {}", zip_path)
    df = _read_from_zip(zip_path, "calendar.txt")
    logger.info("BODS calendar loaded: {} services", len(df))
    return df
