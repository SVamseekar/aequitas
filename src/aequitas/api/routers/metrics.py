"""Metrics router — GET /api/metrics/ticker."""
from __future__ import annotations

import duckdb
from fastapi import APIRouter, Depends
from loguru import logger

from aequitas.api.deps import get_db

router = APIRouter(tags=["metrics"])

# Locked ground truth values (Phase 0 audit — do not change without re-running audit)
_FALLBACK: list[dict] = [
    {"key": "gini", "label": "Gini Coefficient", "value": "0.5741", "sub": "bus service inequality"},
    {"key": "palma", "label": "Palma Ratio", "value": "5.702×", "sub": "top 10% vs bottom 40%"},
    {"key": "concentration_index", "label": "Concentration Index", "value": "+0.1358", "sub": "pro-rich bias"},
    {"key": "evening_isolated", "label": "Evening Isolated", "value": "15.4%", "sub": "5,189 LSOAs"},
    {"key": "sunday_deserts", "label": "Sunday Deserts", "value": "20.0%", "sub": "6,745 LSOAs"},
    {"key": "mean_sqi", "label": "Mean SQI", "value": "65.4", "sub": "out of 100"},
]


@router.get("/metrics/ticker")
def get_ticker_metrics(
    db: duckdb.DuckDBPyConnection | None = Depends(get_db),
) -> list[dict]:
    """Return headline stats for the metrics ticker.

    Attempts to pull live values from the warehouse; falls back to Phase 0
    locked ground truth if the warehouse is not yet populated.
    """
    if db is None:
        return _FALLBACK

    try:
        rows = db.execute(
            """
            SELECT section_id, stats
            FROM section_results
            WHERE region = 'all' AND urban_rural = 'all'
              AND section_id IN (
                'equity_gini', 'equity_palma', 'equity_concentration',
                'sq_evening_isolated', 'sq_sunday_deserts', 'sq_mean_sqi'
              )
            """
        ).fetchall()
    except duckdb.CatalogException:
        logger.warning("section_results table not found — returning fallback ticker")
        return _FALLBACK

    if not rows:
        logger.info("No ticker rows in warehouse — returning fallback")
        return _FALLBACK

    # TODO: map warehouse rows to ticker format once warehouse is populated
    logger.debug("Ticker query returned rows but live mapping not yet implemented")
    return _FALLBACK
