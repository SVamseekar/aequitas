"""LSOA router — allowed tables, aliases, never 500 on missing catalog names."""
from __future__ import annotations

import duckdb
import pytest

from aequitas.api.services.warehouse import (
    ALLOWED_TABLES,
    TABLE_ALIASES,
    resolve_lsoa_table,
)


# Tables that must be safe to expose (exist in the live warehouse build).
_EXPECTED_LIVE_TABLES = {
    "lsoa_demographics",
    "anomalies",
    "coverage_prediction",
    "lsoa_clusters",
    "routes",
    "stops",
}


def test_resolve_lsoa_table_rejects_unknown():
    with pytest.raises(ValueError, match="not in allowed list"):
        resolve_lsoa_table("evil_table")


def test_resolve_lsoa_table_accepts_canonical():
    assert resolve_lsoa_table("lsoa_demographics") == "lsoa_demographics"


def test_resolve_lsoa_table_aliases():
    assert resolve_lsoa_table("lsoa_policy") == "policy_scenarios"
    assert "lsoa_policy" in TABLE_ALIASES


def test_allowed_tables_do_not_include_phantom_names():
    """Old allowlist names that never existed in DuckDB must not be in ALLOWED_TABLES."""
    phantoms = {
        "lsoa_service_quality",
        "lsoa_equity_metrics",
        "lsoa_accessibility",
        "lsoa_economic",
        "lsoa_policy",
        "route_details",
        "lta_readiness",
    }
    assert phantoms.isdisjoint(ALLOWED_TABLES)
    assert _EXPECTED_LIVE_TABLES.issubset(ALLOWED_TABLES)


def test_lsoa_invalid_table(api_client):
    resp = api_client.get("/api/lsoa/evil_table")
    assert resp.status_code == 400


def test_lsoa_allowed_table_returns_200(api_client, tmp_path, monkeypatch):
    """Each allowed table that exists in the test DB returns 200 with total >= 0."""
    db_path = tmp_path / "lsoa.duckdb"
    conn = duckdb.connect(str(db_path))
    conn.execute(
        """
        CREATE TABLE lsoa_demographics (
            lsoa_cd VARCHAR, region VARCHAR, urban_rural VARCHAR
        )
        """
    )
    conn.execute(
        "INSERT INTO lsoa_demographics VALUES ('E01000001', 'E12000007', 'Urban')"
    )
    conn.execute(
        """
        CREATE TABLE anomalies (
            lsoa_cd VARCHAR, service_quality_index DOUBLE
        )
        """
    )
    conn.execute("INSERT INTO anomalies VALUES ('E01000001', 65.4)")
    conn.execute(
        """
        CREATE TABLE coverage_prediction (
            lsoa_cd VARCHAR, residual DOUBLE
        )
        """
    )
    conn.execute("INSERT INTO coverage_prediction VALUES ('E01000001', 0.1)")
    conn.execute(
        """
        CREATE TABLE lsoa_clusters (
            lsoa_cd VARCHAR, hdbscan_label INTEGER
        )
        """
    )
    conn.execute("INSERT INTO lsoa_clusters VALUES ('E01000001', 1)")
    conn.execute(
        """
        CREATE TABLE routes (
            route_id VARCHAR
        )
        """
    )
    # empty routes — still 200, total 0
    conn.execute(
        """
        CREATE TABLE stops (
            stop_id VARCHAR, region_code VARCHAR
        )
        """
    )
    conn.execute("INSERT INTO stops VALUES ('S1', 'E12000007')")
    conn.execute(
        """
        CREATE TABLE section_results (
            region VARCHAR, urban_rural VARCHAR, section_id VARCHAR,
            stats JSON, chart_data JSON, narrative VARCHAR,
            PRIMARY KEY (region, urban_rural, section_id)
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE provenance (
            metric_id VARCHAR PRIMARY KEY,
            value DOUBLE, formula VARCHAR, inputs JSON, source_files VARCHAR[]
        )
        """
    )
    conn.close()

    monkeypatch.setenv("AEQUITAS_DB_PATH", str(db_path))
    monkeypatch.setenv("DEV_AUTH_BYPASS", "true")

    # Recreate app so it picks up the new DB path
    from aequitas.api.app import create_app
    from fastapi.testclient import TestClient

    app = create_app()
    with TestClient(app) as client:
        for table in sorted(_EXPECTED_LIVE_TABLES):
            resp = client.get(f"/api/lsoa/{table}", params={"limit": 5})
            assert resp.status_code == 200, f"{table}: {resp.status_code} {resp.text}"
            body = resp.json()
            assert "rows" in body
            assert body["total"] >= 0

        # Alias should resolve without 500
        resp = client.get("/api/lsoa/lsoa_policy", params={"limit": 1})
        # policy_scenarios not in this minimal DB → empty 200, not 500
        assert resp.status_code in (200, 400)

        # Missing table that is allowed but not in DB must not 500
        resp = client.get("/api/lsoa/route_clusters", params={"limit": 1})
        assert resp.status_code == 200
        assert resp.json()["total"] == 0
        assert resp.json()["rows"] == []


def test_query_lsoa_missing_table_returns_empty():
    """Catalog miss → empty result, never CatalogException bubble."""
    from aequitas.api.services.warehouse import query_lsoa

    db = duckdb.connect(":memory:")
    # allowed name but table does not exist
    rows, total = query_lsoa(db, "lsoa_demographics", limit=5)
    assert rows == []
    assert total == 0
    db.close()
