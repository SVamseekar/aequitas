"""Metrics router — GET /api/metrics/ticker."""
from __future__ import annotations

import json

import duckdb
from fastapi import APIRouter, Depends
from loguru import logger

from aequitas.api.deps import country_warehouse

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
    region: str = "all",
    urban_rural: str = "all",
    country: str = "england",
    mode: str = "bus",
    db: duckdb.DuckDBPyConnection | None = Depends(country_warehouse),
) -> list[dict]:
    """Return headline stats for the metrics ticker for the active filters."""
    if db is None:
        if country in {"ireland", "netherlands", "france"}:
            return [
                {
                    "key": "pack",
                    "label": {
                        "ireland": "Ireland pack",
                        "netherlands": "Netherlands pack",
                        "france": "France pack",
                    }[country],
                    "value": "—",
                    "sub": "warehouse not built",
                }
            ]
        return list(_FALLBACK)

    try:
        cols = [r[1] for r in db.execute("PRAGMA table_info('section_results')").fetchall()]
        sql = """
            SELECT section_id, stats
            FROM section_results
            WHERE region = ? AND urban_rural = ?
              AND section_id IN ('f1_gini', 'b2_operating_hours', 'b3_weekend_penalty', 'b1_frequency')
        """
        params: list = [region, urban_rural]
        if "mode" in cols:
            m = (mode or "bus").strip().lower()
            if m not in {"bus", "all"}:
                m = "bus"
            sql += " AND mode = ?"
            params.append(m)
        rows = db.execute(sql, params).fetchall()
    except duckdb.CatalogException:
        logger.warning("section_results table not found — returning fallback ticker")
        if country in {"ireland", "netherlands", "france"}:
            return [
                {
                    "key": "pack",
                    "label": country.title(),
                    "value": "—",
                    "sub": "warehouse table missing",
                }
            ]
        return list(_FALLBACK)

    if not rows:
        logger.info("No ticker rows in warehouse — returning fallback")
        if country in {"ireland", "netherlands", "france"}:
            return [
                {
                    "key": "pack",
                    "label": {
                        "netherlands": "Netherlands",
                        "france": "France",
                    }.get(country, "Ireland"),
                    "value": "—",
                    "sub": "no ticker rows for this filter",
                }
            ]
        return list(_FALLBACK)

    stats_by_section: dict[str, dict] = {}
    for section_id, stats in rows:
        stats_by_section[section_id] = json.loads(stats) if isinstance(stats, str) else stats

    # Prefer filter-specific equity stats; national provenance only as fallback.
    f1 = stats_by_section.get("f1_gini") or {}
    filter_equity: dict[str, float] = {}
    if isinstance(f1.get("gini"), (int, float)):
        filter_equity["gini"] = float(f1["gini"])
    if isinstance(f1.get("palma"), (int, float)):
        filter_equity["palma"] = float(f1["palma"])
    if isinstance(f1.get("concentration_index"), (int, float)):
        filter_equity["concentration_index"] = float(f1["concentration_index"])

    provenance_equity = _read_equity_from_provenance(db)
    if region == "all" and urban_rural == "all":
        merged = {**provenance_equity, **filter_equity} if filter_equity else provenance_equity
    else:
        merged = filter_equity
    allow_fallback = country == "england" and region == "all" and urban_rural == "all"
    entity = (
        "Small Areas"
        if country == "ireland"
        else "buurten"
        if country == "netherlands"
        else "IRIS"
        if country == "france"
        else "LSOAs"
    )
    metrics = _build_live_ticker(
        stats_by_section,
        merged,
        allow_equity_fallback=allow_fallback,
        entity=entity,
    )
    try:
        from aequitas.api.services.score import score_for_filter

        scored = score_for_filter(
            db, region, urban_rural, mode=mode if country in {"netherlands", "france"} else None
        )
        if scored.score is None:
            score_chip = {
                "key": "in_country_score",
                "label": "In-country score",
                "value": "—",
                "sub": scored.note or "no score for this filter",
            }
        else:
            score_chip = {
                "key": "in_country_score",
                "label": "In-country score",
                "value": (
                    f"{scored.score:.1f}"
                    if abs(scored.score - round(scored.score)) > 0.05
                    else f"{scored.score:.0f}"
                ),
                "sub": scored.note or "0–100, this filter",
            }
        dated = _network_date_chip(country)
        return [score_chip, *([dated] if dated else []), *metrics]
    except Exception:
        dated = _network_date_chip(country)
        return [*([dated] if dated else []), *metrics]


def _network_date_chip(country: str) -> dict | None:
    """Live pack shows the harvest / as_of date. Unknown pack= never reaches here."""
    try:
        from aequitas.warehouse.packs import current_pack

        rec = current_pack(country) or {}
        as_of = rec.get("as_of") or rec.get("pack_id")
        if not as_of:
            return None
        label = {
            "england": "BODS pack",
            "ireland": "TFI pack",
            "netherlands": "OVapi pack",
            "france": "NAP harvest",
        }.get(country, "Network")
        return {
            "key": "network_date",
            "label": label,
            "value": str(as_of),
            "sub": "network date",
        }
    except Exception:
        return None


def _filter_sqi(
    freq_stats: dict,
    *,
    allow_equity_fallback: bool,
    stats_by_section: dict[str, dict],
) -> float | None:
    """SQI for the ticker. Filtered views never reuse England's national_avg."""
    if freq_stats.get("insufficient_data"):
        return None
    if allow_equity_fallback:
        avg = freq_stats.get("national_avg")
        if isinstance(avg, (int, float)):
            return float(avg)
        val = freq_stats.get("value")
        return float(val) if isinstance(val, (int, float)) else None
    # Empty cuts (London × rural) sometimes leak a regional `value` / national_avg.
    has_areas = bool(stats_by_section.get("f1_gini")) or (
        "n_evening_isolated" in (stats_by_section.get("b2_operating_hours") or {})
    )
    if not has_areas:
        return None
    val = freq_stats.get("value")
    return float(val) if isinstance(val, (int, float)) else None


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
    allow_equity_fallback: bool = True,
    entity: str = "LSOAs",
) -> list[dict]:
    """Map live warehouse stats onto ticker shape; Gini always 4 decimal places."""
    fallback_by_key = {m["key"]: m for m in _FALLBACK}
    provenance_equity = provenance_equity or {}
    metrics: list[dict] = []

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
    elif allow_equity_fallback:
        metrics.append(fallback_by_key["gini"])
    else:
        metrics.append({"key": "gini", "label": "Gini Coefficient", "value": "—", "sub": f"no {entity} for this filter"})

    if "palma" in provenance_equity:
        p = provenance_equity["palma"]
        palma_sub = (
            "bottom 40% have no weekday NAP trips"
            if p == 0.0 and entity == "IRIS"
            else "bottom 40% have no weekday trips"
            if p == 0.0 and entity == "Small Areas"
            else "top 10% vs bottom 40%"
        )
        metrics.append(
            {
                "key": "palma",
                "label": "Palma Ratio",
                "value": f"{p:.3f}×",
                "sub": palma_sub,
            }
        )
    elif allow_equity_fallback:
        metrics.append(fallback_by_key["palma"])
    else:
        metrics.append({"key": "palma", "label": "Palma Ratio", "value": "—", "sub": f"no {entity} for this filter"})

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
    elif allow_equity_fallback:
        metrics.append(fallback_by_key["concentration_index"])
    else:
        metrics.append(
            {
                "key": "concentration_index",
                "label": "Concentration Index",
                "value": "—",
                "sub": f"no {entity} for this filter",
            }
        )

    hours_stats = stats_by_section.get("b2_operating_hours")
    if hours_stats and "n_evening_isolated" in hours_stats and "pct_evening_isolated" in hours_stats:
        metrics.append(
            {
                "key": "evening_isolated",
                "label": "Evening Isolated",
                "value": f"{hours_stats['pct_evening_isolated']:.1f}%",
                "sub": f"{hours_stats['n_evening_isolated']:,} {entity}",
            }
        )
    elif allow_equity_fallback:
        metrics.append(fallback_by_key["evening_isolated"])
    else:
        metrics.append(
            {
                "key": "evening_isolated",
                "label": "Evening Isolated",
                "value": "—",
                "sub": "no figure for this filter",
            }
        )

    weekend_stats = stats_by_section.get("b3_weekend_penalty")
    if weekend_stats and "n_sunday_desert" in weekend_stats and "pct_sunday_desert" in weekend_stats:
        metrics.append(
            {
                "key": "sunday_deserts",
                "label": "Sunday Deserts",
                "value": f"{weekend_stats['pct_sunday_desert']:.1f}%",
                "sub": f"{weekend_stats['n_sunday_desert']:,} {entity}",
            }
        )
    elif allow_equity_fallback:
        metrics.append(fallback_by_key["sunday_deserts"])
    else:
        metrics.append(
            {
                "key": "sunday_deserts",
                "label": "Sunday Deserts",
                "value": "—",
                "sub": "no figure for this filter",
            }
        )

    freq_stats = stats_by_section.get("b1_frequency") or {}
    sqi = _filter_sqi(freq_stats, allow_equity_fallback=allow_equity_fallback, stats_by_section=stats_by_section)
    if sqi is not None:
        metrics.append(
            {
                "key": "mean_sqi",
                "label": "Mean SQI",
                "value": f"{sqi:.1f}",
                "sub": "out of 100",
            }
        )
    elif allow_equity_fallback:
        metrics.append(fallback_by_key["mean_sqi"])
    else:
        metrics.append(
            {
                "key": "mean_sqi",
                "label": "Mean SQI",
                "value": "—",
                "sub": "no figure for this filter",
            }
        )

    # Base keys stay in FALLBACK order; optional score chip is prepended by the router.
    assert [m["key"] for m in metrics] == [m["key"] for m in _FALLBACK]
    assert _EQUITY_LOCKED_KEYS  # referenced for documentation / lint
    return metrics
