"""DuckDB query helpers — read-only access to pre-computed data."""
from __future__ import annotations

import json
import re
from typing import Any

import duckdb

# Dimension → section_ids that belong to it
# These match the section_ids produced by warehouse.precompute._SECTIONS
DIMENSION_PREFIXES: dict[str, list[str]] = {
    "equity": ["equity"],
    "accessibility": ["coverage_density", "gap_to_target"],
    "service_quality": ["coverage_density"],
    "route_network": ["coverage_density"],
    "correlations": ["correlation"],
    "economic": ["gap_to_target"],
    "bus_services_act": ["policy_scenario"],
    "scenarios": ["policy_scenario"],
}

# Headline section per dimension (section_id, stat_key)
HEADLINE_SECTIONS: dict[str, tuple[str, str]] = {
    "equity": ("equity", "gini"),
    "accessibility": ("coverage_density", "stops_per_1000"),
    "service_quality": ("coverage_density", "stops_per_1000"),
    "route_network": ("coverage_density", "stops_per_1000"),
    "correlations": ("correlation", "r2"),
    "economic": ("gap_to_target", "total_annual_cost_m"),
    "bus_services_act": ("policy_scenario", "readiness_score"),
    "scenarios": ("policy_scenario", "best_bcr"),
}


def query_sections(
    db: duckdb.DuckDBPyConnection,
    dimension: str,
    region: str = "all",
    urban_rural: str = "all",
) -> list[dict[str, Any]]:
    """Query section_results for a dimension's sections."""
    section_ids = DIMENSION_PREFIXES.get(dimension, [])
    if not section_ids:
        return []

    placeholders = ", ".join("?" for _ in section_ids)
    rows = db.execute(
        f"""
        SELECT section_id, stats, chart_data, narrative
        FROM section_results
        WHERE section_id IN ({placeholders})
          AND region = ?
          AND urban_rural = ?
        ORDER BY section_id
        """,
        [*section_ids, region, urban_rural],
    ).fetchall()

    results = []
    for section_id, stats, chart_data, narrative in rows:
        results.append({
            "section_id": section_id,
            "dimension": dimension,
            "stats": json.loads(stats) if isinstance(stats, str) else (stats or {}),
            "chart_data": json.loads(chart_data) if isinstance(chart_data, str) else (chart_data or {}),
            "narrative": narrative or "",
            "suppressed": not narrative or narrative.strip() == "",
        })
    return results


def query_overview(
    db: duckdb.DuckDBPyConnection,
    region: str = "all",
    urban_rural: str = "all",
) -> list[dict[str, Any]]:
    """Query headline stats for each dimension."""
    results = []
    for dim_id, (section_id, stat_key) in HEADLINE_SECTIONS.items():
        row = db.execute(
            """
            SELECT stats, narrative
            FROM section_results
            WHERE section_id = ? AND region = ? AND urban_rural = ?
            """,
            [section_id, region, urban_rural],
        ).fetchone()

        if row:
            stats = json.loads(row[0]) if isinstance(row[0], str) else (row[0] or {})
            raw = stats.get(stat_key, 0)
            # Extract a scalar — some stats are nested dicts (e.g. stops_per_1000)
            if isinstance(raw, dict):
                value = float(raw.get("national_avg", raw.get("value", 0)))
            elif isinstance(raw, (int, float)):
                value = float(raw)
            else:
                value = 0.0
        else:
            value = 0.0

        results.append({
            "id": dim_id,
            "value": value,
            "stat_key": stat_key,
        })
    return results


ALLOWED_TABLES = {
    "lsoa_service_quality",
    "lsoa_equity_metrics",
    "lsoa_accessibility",
    "lsoa_economic",
    "lsoa_policy",
    "route_details",
    "lta_readiness",
}


def query_lsoa(
    db: duckdb.DuckDBPyConnection,
    table: str,
    region: str | None = None,
    fields: list[str] | None = None,
    limit: int | None = None,
) -> tuple[list[dict], int]:
    """Query LSOA-level analytics table."""
    if table not in ALLOWED_TABLES:
        raise ValueError(f"Table '{table}' not in allowed list: {ALLOWED_TABLES}")

    # Count
    count_sql = f"SELECT COUNT(*) FROM {table}"
    params: list = []
    if region:
        count_sql += " WHERE region_code = ?"
        params.append(region)
    total = db.execute(count_sql, params).fetchone()[0]

    # Select — validate field names (alphanumeric + underscore only)
    if fields:
        for f in fields:
            if not re.match(r"^[a-zA-Z_][a-zA-Z0-9_]*$", f):
                raise ValueError(f"Invalid field name: '{f}'")
    cols = ", ".join(fields) if fields else "*"
    sql = f"SELECT {cols} FROM {table}"
    params = []
    if region:
        sql += " WHERE region_code = ?"
        params.append(region)
    if limit:
        sql += f" LIMIT {int(limit)}"

    rows = db.execute(sql, params).fetchdf().to_dict(orient="records")
    return rows, total


def query_provenance(
    db: duckdb.DuckDBPyConnection,
    metric_id: str,
) -> dict | None:
    """Query provenance for a metric."""
    row = db.execute(
        "SELECT metric_id, value, formula, inputs, source_files FROM provenance WHERE metric_id = ?",
        [metric_id],
    ).fetchone()
    if not row:
        return None
    return {
        "metric_id": row[0],
        "value": row[1],
        "formula": row[2],
        "inputs": json.loads(row[3]) if isinstance(row[3], str) else (row[3] or {}),
        "source_files": list(row[4]) if row[4] else [],
    }
