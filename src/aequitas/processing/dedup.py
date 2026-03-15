"""Cross-region deduplication for stops and routes.

Stops: deduplicate by stop_id (ATCO code) — keep first occurrence.
Routes: deduplicate by route_id — aggregate regions into list, take max trips_per_day.
"""

import pandas as pd
from loguru import logger


def deduplicate_stops(df: pd.DataFrame, id_col: str = "stop_id") -> pd.DataFrame:
    """Deduplicate stops by stop_id, keeping first occurrence.

    Args:
        df: DataFrame with stop records (may have cross-region duplicates).
        id_col: Column containing the stop identifier (default: 'stop_id').

    Returns:
        DataFrame with duplicates removed, original index reset.
    """
    n_before = len(df)
    result = df.drop_duplicates(subset=id_col, keep="first")
    n_dropped = n_before - len(result)
    if n_dropped > 0:
        logger.info("deduplicate_stops: dropped {} duplicates ({} → {})", n_dropped, n_before, len(result))
    return result.reset_index(drop=True)


def deduplicate_routes(df: pd.DataFrame) -> pd.DataFrame:
    """Deduplicate routes by route_id, merging cross-region occurrences.

    For each unique route_id:
    - regions_served: sorted list of all unique region_codes
    - trips_per_day: max across all occurrences
    - line_name: first occurrence

    Args:
        df: DataFrame with route records, must have columns:
            route_id, line_name, region_code, trips_per_day.

    Returns:
        One row per unique route_id with aggregated fields.
    """
    n_before = len(df)
    grouped = df.groupby("route_id", sort=False)
    result = grouped.agg(
        line_name=("line_name", "first"),
        trips_per_day=("trips_per_day", "max"),
        regions_served=("region_code", lambda x: sorted(set(x))),
    ).reset_index()
    logger.info(
        "deduplicate_routes: {} records → {} unique routes", n_before, len(result)
    )
    return result
