"""Load warehouse section stats and compute the in-country score."""

from __future__ import annotations

import json
from typing import Any

import duckdb

from aequitas.analytics.score import ScoreResult, compute_score, terms_from_section_stats
try:
    from aequitas.ireland.constants import COUNTY_NAME_BY_SLUG
except ImportError:
    COUNTY_NAME_BY_SLUG: dict[str, str] = {}
try:
    from aequitas.netherlands.constants import PROVINCE_NAME_BY_SLUG
except ImportError:
    PROVINCE_NAME_BY_SLUG: dict[str, str] = {}

_SECTIONS = (
    "a3_walking_distance",
    "b2_operating_hours",
    "b1_frequency",
    "d1_coverage_deprivation",
)


def _parse_stats(raw: Any) -> dict[str, Any]:
    if raw is None:
        return {}
    if isinstance(raw, str):
        return json.loads(raw)
    if isinstance(raw, dict):
        return raw
    return {}


def load_section_stats(
    db: duckdb.DuckDBPyConnection,
    region: str,
    urban_rural: str,
    mode: str | None = None,
) -> dict[str, dict[str, Any]]:
    cols = [r[1] for r in db.execute("PRAGMA table_info('section_results')").fetchall()]
    sql = """
        SELECT section_id, stats
        FROM section_results
        WHERE region = ? AND urban_rural = ?
          AND section_id IN ('a3_walking_distance', 'b2_operating_hours',
                             'b1_frequency', 'd1_coverage_deprivation')
    """
    params: list[Any] = [region, urban_rural]
    if "mode" in cols:
        sql += " AND mode = ?"
        params.append((mode or "bus").strip().lower() if (mode or "bus") in {"bus", "all"} else "bus")
    rows = db.execute(sql, params).fetchall()
    return {sid: _parse_stats(stats) for sid, stats in rows}


def score_for_filter(
    db: duckdb.DuckDBPyConnection,
    region: str = "all",
    urban_rural: str = "all",
    mode: str | None = None,
) -> ScoreResult:
    if region == "E12000007" and urban_rural == "rural":
        return compute_score({}, n_areas=0, region=region, urban_rural=urban_rural)
    by_id = load_section_stats(db, region, urban_rural, mode=mode)
    a3 = by_id.get("a3_walking_distance") or {}
    if a3.get("insufficient_data") and int(a3.get("n_lsoas") or a3.get("n_sas") or 0) == 0:
        return compute_score({}, n_areas=0, region=region, urban_rural=urban_rural)
    terms, n_areas = terms_from_section_stats(
        by_id.get("a3_walking_distance"),
        by_id.get("b2_operating_hours"),
        by_id.get("b1_frequency"),
        by_id.get("d1_coverage_deprivation"),
    )
    return compute_score(terms, n_areas=n_areas, region=region, urban_rural=urban_rural)


def _mode_clause(db: duckdb.DuckDBPyConnection, mode: str | None) -> tuple[str, list[Any]]:
    cols = [r[1] for r in db.execute("PRAGMA table_info('section_results')").fetchall()]
    if "mode" not in cols:
        return "", []
    m = (mode or "bus").strip().lower()
    if m not in {"bus", "all"}:
        m = "bus"
    return " AND mode = ?", [m]


def map_areas_for_filter(
    db: duckdb.DuckDBPyConnection,
    region: str = "all",
    urban_rural: str = "all",
    mode: str | None = None,
) -> dict[str, Any]:
    """Choropleth payload: prefer people in deserts (a5), else 400 m coverage (a3)."""
    if region == "E12000007" and urban_rural == "rural":
        return {
            "geography": "region",
            "metric_label": "People in deserts",
            "data": [],
            "empty": True,
            "empty_reason": "London has no rural LSOAs under the official classification.",
        }

    # Prefer regional a5 people counts for the national home map.
    extra_sql, extra_params = _mode_clause(db, mode)
    if region == "all":
        rows = db.execute(
            f"""
            SELECT region, stats
            FROM section_results
            WHERE urban_rural = ?
              AND region != 'all'
              AND section_id = 'a5_service_deserts'
              {extra_sql}
            """,
            [urban_rural, *extra_params],
        ).fetchall()
        data = []
        for rgn, stats in rows:
            s = _parse_stats(stats)
            if s.get("insufficient_data"):
                continue
            pop = s.get("pop_affected")
            if not isinstance(pop, (int, float)):
                continue
            data.append({"area_code": rgn, "area_name": _REGION_NAMES.get(rgn, rgn), "value": float(pop)})
        if data:
            return {
                "geography": "region",
                "metric_label": "People with no nearby stop",
                "data": data,
                "empty": False,
                "empty_reason": None,
            }
        # Fallback: 400 m coverage % by region
        rows = db.execute(
            f"""
            SELECT region, stats
            FROM section_results
            WHERE urban_rural = ?
              AND region != 'all'
              AND section_id = 'a3_walking_distance'
              {extra_sql}
            """,
            [urban_rural, *extra_params],
        ).fetchall()
        data = []
        for rgn, stats in rows:
            s = _parse_stats(stats)
            pct = s.get("pct_covered")
            if isinstance(pct, (int, float)):
                data.append(
                    {"area_code": rgn, "area_name": _REGION_NAMES.get(rgn, rgn), "value": float(pct)}
                )
        if data:
            return {
                "geography": "region",
                "metric_label": "People within 400 m of a stop (%)",
                "data": data,
                "empty": False,
                "empty_reason": None,
            }

    # Selected ITL1: use precomputed a5 choropleth LAD data if present.
    row = db.execute(
        f"""
        SELECT chart_data, stats
        FROM section_results
        WHERE region = ? AND urban_rural = ? AND section_id = 'a5_service_deserts'
        {extra_sql}
        """,
        [region, urban_rural, *extra_params],
    ).fetchone()
    if row:
        chart = _parse_stats(row[0])
        stats = _parse_stats(row[1])
        points = chart.get("data") if isinstance(chart.get("data"), list) else []
        if points:
            return {
                "geography": chart.get("geography") or "lad",
                "metric_label": "Sunday desert rate (%)",
                "data": points,
                "empty": False,
                "empty_reason": None,
                "title_count": stats.get("pop_affected"),
            }

    return {
        "geography": "region",
        "metric_label": "People in deserts",
        "data": [],
        "empty": True,
        "empty_reason": "No map layer for this filter in the warehouse pack.",
    }


_REGION_NAMES: dict[str, str] = {
    **COUNTY_NAME_BY_SLUG,
    **PROVINCE_NAME_BY_SLUG,
    "E12000001": "North East",
    "E12000002": "North West",
    "E12000003": "Yorkshire and The Humber",
    "E12000004": "East Midlands",
    "E12000005": "West Midlands",
    "E12000006": "East of England",
    "E12000007": "London",
    "E12000008": "South East",
    "E12000009": "South West",
}
