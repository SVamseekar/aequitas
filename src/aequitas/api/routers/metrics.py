"""Metrics router — GET /api/metrics/ticker."""
from __future__ import annotations

import json

import duckdb
from fastapi import APIRouter, Depends
from loguru import logger

from aequitas.api.deps import get_db

router = APIRouter(tags=["metrics"])

# Locked Phase 0 ground truth packing (do not change without re-running audit).
# Equity keys always use this pack — section_results currently truncates Palma/CI.
_FALLBACK: list[dict] = [
    {"key": "gini", "label": "Gini Coefficient", "value": "0.5741", "sub": "bus service inequality"},
    {"key": "palma", "label": "Palma Ratio", "value": "5.702×", "sub": "top 10% vs bottom 40%"},
    {"key": "concentration_index", "label": "Concentration Index", "value": "+0.1358", "sub": "pro-rich bias"},
    {"key": "evening_isolated", "label": "Evening Isolated", "value": "15.4%", "sub": "5,189 LSOAs"},
    {"key": "sunday_deserts", "label": "Sunday Deserts", "value": "20.0%", "sub": "6,745 LSOAs"},
    {"key": "mean_sqi", "label": "Mean SQI", "value": "65.4", "sub": "out of 100"},
]

# Equity metrics locked to ground-truth packing (gini 4 dp, palma 3 dp, CI 4 dp).
_EQUITY_LOCKED_KEYS = frozenset({"gini", "palma", "concentration_index"})


@router.get("/metrics/ticker")
def get_ticker_metrics(
    db: duckdb.DuckDBPyConnection | None = Depends(get_db),
) -> list[dict]:
    """Return headline stats for the metrics ticker.

    Equity metrics (Gini / Palma / CI) use Phase 0 locked ground truth packing.
    Operating-hours and SQI metrics prefer live ``section_results`` when present.
    """
    if db is None:
        return list(_FALLBACK)

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
        return list(_FALLBACK)

    if not rows:
        logger.info("No ticker rows in warehouse — returning fallback")
        return list(_FALLBACK)

    stats_by_section: dict[str, dict] = {}
    for section_id, stats in rows:
        stats_by_section[section_id] = json.loads(stats) if isinstance(stats, str) else stats

    # Prefer provenance table for equity if present (matches GT packing).
    provenance_equity = _read_equity_from_provenance(db)

    return _build_live_ticker(stats_by_section, provenance_equity)


def _read_equity_from_provenance(db: duckdb.DuckDBPyConnection) -> dict[str, float]:
    """Load locked equity values from provenance when available."""
    out: dict[str, float] = {}
    try:
        rows = db.execute(
            """
            SELECT metric_id, value FROM provenance
            WHERE metric_id IN ('gini_national', 'palma_ratio', 'concentration_index')
            """
        ).fetchall()
    except duckdb.CatalogException:
        return out
    for metric_id, value in rows:
        if metric_id == "gini_national" and value is not None:
            out["gini"] = float(value)
        elif metric_id == "palma_ratio" and value is not None:
            out["palma"] = float(value)
        elif metric_id == "concentration_index" and value is not None:
            out["concentration_index"] = float(value)
    return out


def _build_live_ticker(
    stats_by_section: dict[str, dict],
    provenance_equity: dict[str, float] | None = None,
) -> list[dict]:
    """Map live warehouse stats onto ticker shape; equity prefers GT packing."""
    fallback_by_key = {m["key"]: m for m in _FALLBACK}
    provenance_equity = provenance_equity or {}
    metrics: list[dict] = []

    # --- Equity: provenance → FALLBACK (never use truncated section_results) ---
    if "gini" in provenance_equity:
        g = provenance_equity["gini"]
        metrics.append(
            {
                "key": "gini",
                "label": "Gini Coefficient",
                "value": f"{g:.4f}",
                "sub": "bus service inequality",
            }
        )
    else:
        metrics.append(fallback_by_key["gini"])

    if "palma" in provenance_equity:
        p = provenance_equity["palma"]
        metrics.append(
            {
                "key": "palma",
                "label": "Palma Ratio",
                "value": f"{p:.3f}×",
                "sub": "top 10% vs bottom 40%",
            }
        )
    else:
        metrics.append(fallback_by_key["palma"])

    if "concentration_index" in provenance_equity:
        ci = provenance_equity["concentration_index"]
        sign = "+" if ci >= 0 else ""
        sub = "pro-rich bias" if ci >= 0 else "pro-poor bias"
        metrics.append(
            {
                "key": "concentration_index",
                "label": "Concentration Index",
                "value": f"{sign}{ci:.4f}",
                "sub": sub,
            }
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
            {
                "key": "mean_sqi",
                "label": "Mean SQI",
                "value": f"{freq_stats['national_avg']:.1f}",
                "sub": "out of 100",
            }
        )
    else:
        metrics.append(fallback_by_key["mean_sqi"])

    # Ensure key order matches FALLBACK for clients that index positionally.
    assert [m["key"] for m in metrics] == [m["key"] for m in _FALLBACK]
    assert _EQUITY_LOCKED_KEYS  # referenced for documentation / lint
    return metrics
