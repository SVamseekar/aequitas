"""Metrics router — GET /api/metrics/ticker."""
from __future__ import annotations

import json

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
              AND section_id IN ('f1_gini', 'b2_operating_hours', 'b3_weekend_penalty', 'b1_frequency')
            """
        ).fetchall()
    except duckdb.CatalogException:
        logger.warning("section_results table not found — returning fallback ticker")
        return _FALLBACK

    if not rows:
        logger.info("No ticker rows in warehouse — returning fallback")
        return _FALLBACK

    stats_by_section: dict[str, dict] = {}
    for section_id, stats in rows:
        stats_by_section[section_id] = json.loads(stats) if isinstance(stats, str) else stats

    return _build_live_ticker(stats_by_section)


def _build_live_ticker(stats_by_section: dict[str, dict]) -> list[dict]:
    """Map live `section_results` stats onto the ticker shape, falling back per-metric.

    Args:
        stats_by_section: section_id -> stats dict for region='all', urban_rural='all'.

    Returns:
        Ticker metrics list with live values where available, otherwise the
        Phase 0 locked fallback value for that metric.
    """
    fallback_by_key = {m["key"]: m for m in _FALLBACK}
    metrics: list[dict] = []

    gini_stats = stats_by_section.get("f1_gini")
    if gini_stats and "gini" in gini_stats:
        metrics.append(
            {"key": "gini", "label": "Gini Coefficient", "value": f"{gini_stats['gini']:.4f}", "sub": "bus service inequality"}
        )
    else:
        metrics.append(fallback_by_key["gini"])

    if gini_stats and "palma" in gini_stats:
        metrics.append(
            {"key": "palma", "label": "Palma Ratio", "value": f"{gini_stats['palma']:.3f}×", "sub": "top 10% vs bottom 40%"}
        )
    else:
        metrics.append(fallback_by_key["palma"])

    if gini_stats and "concentration_index" in gini_stats:
        ci = gini_stats["concentration_index"]
        sign = "+" if ci >= 0 else ""
        sub = "pro-rich bias" if ci >= 0 else "pro-poor bias"
        metrics.append(
            {"key": "concentration_index", "label": "Concentration Index", "value": f"{sign}{ci:.4f}", "sub": sub}
        )
    else:
        metrics.append(fallback_by_key["concentration_index"])

    hours_stats = stats_by_section.get("b2_operating_hours")
    if hours_stats and "n_evening_isolated" in hours_stats and "pct_evening_isolated" in hours_stats:
        metrics.append(
            {
                "key": "evening_isolated",
                "label": "Evening Isolated",
                "value": f"{hours_stats['pct_evening_isolated']:.1f}%",
                "sub": f"{hours_stats['n_evening_isolated']:,} LSOAs",
            }
        )
    else:
        metrics.append(fallback_by_key["evening_isolated"])

    weekend_stats = stats_by_section.get("b3_weekend_penalty")
    if weekend_stats and "n_sunday_desert" in weekend_stats and "pct_sunday_desert" in weekend_stats:
        metrics.append(
            {
                "key": "sunday_deserts",
                "label": "Sunday Deserts",
                "value": f"{weekend_stats['pct_sunday_desert']:.1f}%",
                "sub": f"{weekend_stats['n_sunday_desert']:,} LSOAs",
            }
        )
    else:
        metrics.append(fallback_by_key["sunday_deserts"])

    freq_stats = stats_by_section.get("b1_frequency")
    if freq_stats and "national_avg" in freq_stats:
        metrics.append(
            {"key": "mean_sqi", "label": "Mean SQI", "value": f"{freq_stats['national_avg']:.1f}", "sub": "out of 100"}
        )
    else:
        metrics.append(fallback_by_key["mean_sqi"])

    return metrics
