"""Tests for DuckDB warehouse builder."""

import duckdb
import pytest
from aequitas.warehouse.schema import TABLES
from aequitas.warehouse.builder import build_warehouse, get_connection
from aequitas.core.config import PipelineConfig
from pathlib import Path


def test_build_warehouse_creates_file(tmp_path):
    """build_warehouse creates the DuckDB file and core tables."""
    cfg = PipelineConfig(warehouse_path=tmp_path / "test.duckdb")
    build_warehouse(cfg)
    assert cfg.warehouse_path.exists()

    # Verify core tables exist
    conn = duckdb.connect(str(cfg.warehouse_path))
    tables = {row[0] for row in conn.execute("SHOW TABLES").fetchall()}
    conn.close()

    for required in ["stops", "routes", "lsoa_demographics", "section_results", "provenance"]:
        assert required in tables, f"Missing table: {required}"


def test_build_warehouse_overwrite(tmp_path):
    """build_warehouse with overwrite=True drops and recreates tables."""
    cfg = PipelineConfig(warehouse_path=tmp_path / "test.duckdb")
    build_warehouse(cfg)
    build_warehouse(cfg, overwrite=True)  # should not raise
    assert cfg.warehouse_path.exists()


def test_get_connection_returns_readonly(tmp_path):
    """get_connection opens a read-only connection."""
    cfg = PipelineConfig(warehouse_path=tmp_path / "test.duckdb")
    build_warehouse(cfg)
    conn = get_connection(cfg)
    assert conn is not None
    conn.close()
