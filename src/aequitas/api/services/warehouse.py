"""DuckDB query helpers — read-only access to pre-computed data."""
from __future__ import annotations

import json
import re
from typing import Any

import duckdb
from loguru import logger

# Dimension → section_id prefixes. The 50 section IDs follow a naming convention:
# a1_*, a2_*, ..., b1_*, ..., bsa1_*, ps1_*, etc.
# Each dimension maps to one or more prefix groups.
DIMENSION_PREFIXES: dict[str, list[str]] = {
    "equity": ["f"],
    "accessibility": ["a"],
    "service_quality": ["b"],
    "route_network": ["c"],
    "correlations": ["d", "g"],
    "economic": ["j"],
    "bus_services_act": ["bsa"],
    "scenarios": ["ps"],
}

# Headline section per dimension (section_id, stat_key)
# Keys must match actual stats produced by precompute.py
HEADLINE_SECTIONS: dict[str, tuple[str, str]] = {
    "equity": ("f1_gini", "gini"),
    "accessibility": ("a3_walking_distance", "pct_covered"),
    "service_quality": ("b1_frequency", "national_avg"),
    "route_network": ("c3_operator_hhi", "hhi"),
    "correlations": ("d1_coverage_deprivation", "r"),
    "economic": ("j3_carbon", "co2_saving_tonnes"),
    "bus_services_act": ("bsa1_franchising_readiness", "national_avg"),
    "scenarios": ("ps1_freq_restoration", "scenario.population_affected"),
}


def _build_prefix_pattern(prefixes: list[str]) -> str:
    """Build a SQL WHERE clause for prefix-based section_id matching.

    Single-letter prefixes (e.g. "b") use regexp to match "b<digit>..."
    to avoid collisions like "b%" matching "bsa1_*". Multi-letter prefixes
    (e.g. "bsa", "ps") use plain LIKE.

    Safety: prefixes are sourced exclusively from the DIMENSION_PREFIXES constant
    above — they are never derived from user input, so SQL injection is not possible.
    """
    conditions = []
    for p in prefixes:
        if len(p) == 1:
            conditions.append(f"regexp_matches(section_id, '^{p}[0-9]')")
        else:
            conditions.append(f"section_id LIKE '{p}%'")
    return " OR ".join(conditions)


def query_sections(
    db: duckdb.DuckDBPyConnection,
    dimension: str,
    region: str = "all",
    urban_rural: str = "all",
) -> list[dict[str, Any]]:
    """Query section_results for a dimension's sections."""
    prefixes = DIMENSION_PREFIXES.get(dimension, [])
    if not prefixes:
        logger.debug(f"No prefixes for dimension={dimension}")
        return []

    where_prefix = _build_prefix_pattern(prefixes)
    logger.debug(f"Querying sections: dimension={dimension}, region={region}, urban_rural={urban_rural}")
    rows = db.execute(
        f"""
        SELECT section_id, stats, chart_data, narrative
        FROM section_results
        WHERE ({where_prefix})
          AND region = ?
          AND urban_rural = ?
        ORDER BY section_id
        """,
        [region, urban_rural],
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
            # Support dot-path keys like "scenario.population_affected"
            raw: Any = stats
            for part in stat_key.split("."):
                if isinstance(raw, dict):
                    raw = raw.get(part, 0)
                else:
                    raw = 0
                    break
            # Extract a scalar — some stats are nested dicts
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
        logger.warning(f"Rejected LSOA query for disallowed table: {table}")
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
        sql += " LIMIT ?"
        params.append(int(limit))

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
