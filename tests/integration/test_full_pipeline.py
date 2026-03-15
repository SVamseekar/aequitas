"""End-to-end pipeline integration test.

Runs the warehouse build and validation stages against Phase 0 audit Parquets
and validates against the Phase 0 ground truth. These tests are @pytest.mark.slow
because they load large Parquet files and build a DuckDB warehouse.

Run with: pytest tests/integration/ -v -m slow
"""

import duckdb
import pytest
from pathlib import Path

from aequitas.core.config import PipelineConfig
from aequitas.core.constants import POPULATION_ENGLAND, LSOA_COUNT_ENGLAND

pytestmark = pytest.mark.slow


@pytest.fixture(scope="module")
def pipeline_output(tmp_path_factory):
    """Build warehouse into isolated temp directory using Phase 0 audit Parquets."""
    from aequitas.pipeline._stages import run_warehouse, run_validation

    out_dir = tmp_path_factory.mktemp("pipeline")
    cfg = PipelineConfig(
        processed_dir=out_dir / "processed",
        warehouse_path=out_dir / "aequitas.duckdb",
    )
    cfg.processed_dir.mkdir(parents=True, exist_ok=True)
    run_warehouse(cfg)
    return cfg


def test_duckdb_exists(pipeline_output):
    assert pipeline_output.warehouse_path.exists()


def test_duckdb_has_core_tables(pipeline_output):
    con = duckdb.connect(str(pipeline_output.warehouse_path), read_only=True)
    tables = {r[0] for r in con.execute("SHOW TABLES").fetchall()}
    required = {"stops", "routes", "lsoa_demographics", "section_results", "provenance"}
    assert required.issubset(tables), f"Missing tables: {required - tables}"
    con.close()


def test_validation_gates_pass():
    """Ground truth validation against Phase 0 audit Parquets."""
    from aequitas.validation.ground_truth import validate_against_ground_truth

    cfg = PipelineConfig()
    report = validate_against_ground_truth(cfg)
    failed = [c for c in report["checks"] if c["status"] == "FAIL"]
    assert len(failed) == 0, f"Ground truth failures: {[c['name'] for c in failed]}"


def test_precompute_produces_results():
    """Precompute section results from Phase 0 audit data."""
    from aequitas.warehouse.precompute import precompute_all_sections

    cfg = PipelineConfig()
    results = precompute_all_sections(cfg)
    assert len(results) > 0

    for r in results[:5]:
        assert "region" in r
        assert "urban_rural" in r
        assert "section_id" in r
        assert "narrative" in r
