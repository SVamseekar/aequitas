"""Tests for DuckDB warehouse schema."""

import duckdb
import pytest
from aequitas.warehouse.schema import TABLES, CORE_TABLES, ANALYTICS_PARQUET_SOURCES


def test_schema_has_required_tables():
    required = {
        "stops", "routes", "lsoa_demographics", "section_results", "provenance",
        # Analytics tables (LSOA-level data for maps + drill-downs)
        "lsoa_service_quality", "lsoa_equity_metrics", "lsoa_accessibility",
        "lsoa_economic", "lsoa_policy", "route_details", "lta_readiness",
    }
    assert required.issubset(set(TABLES.keys()))


def test_core_tables_are_valid_ddl():
    """All core table DDL can be executed against an in-memory DuckDB."""
    conn = duckdb.connect(":memory:")
    for table_name, ddl in CORE_TABLES.items():
        conn.execute(ddl)
    tables = {row[0] for row in conn.execute("SHOW TABLES").fetchall()}
    assert "stops" in tables
    assert "section_results" in tables
    assert "provenance" in tables
    conn.close()


def test_analytics_parquet_sources_have_expected_keys():
    """All original sources are present; new expanded sources are also allowed."""
    required = {
        "lsoa_service_quality",
        "lsoa_equity_metrics",
        "lsoa_accessibility",
        "lsoa_economic",
        "lsoa_policy",
        "route_details",
        "lta_readiness",
    }
    assert required.issubset(set(ANALYTICS_PARQUET_SOURCES.keys()))
    # New expanded sources must also be present
    new_sources = {
        "stop_headways", "coverage_prediction", "shap_importance",
        "route_clusters", "lsoa_clusters", "anomalies",
        "modal_shift_scenarios", "policy_scenarios",
    }
    assert new_sources.issubset(set(ANALYTICS_PARQUET_SOURCES.keys()))
