"""Tests for query_overview — verifies HEADLINE_SECTIONS resolves to non-zero values (§5)."""
import duckdb
import pytest

from aequitas.api.services.warehouse import HEADLINE_SECTIONS, query_overview
from aequitas.intelligence.section_registry import SECTION_REGISTRY


def test_headline_section_ids_exist_in_registry():
    for dim_id, (section_id, _stat_key) in HEADLINE_SECTIONS.items():
        assert section_id in SECTION_REGISTRY, f"{dim_id} references unknown section_id {section_id!r}"


def test_overview_returns_non_zero_values_for_national_scope(tmp_path):
    db_path = tmp_path / "warehouse.duckdb"
    db = duckdb.connect(str(db_path))
    db.execute("""
        CREATE TABLE section_results (
            region VARCHAR, urban_rural VARCHAR, section_id VARCHAR,
            stats JSON, narrative VARCHAR
        )
    """)

    fixture_stats = {
        "f1_gini": {"gini": 0.5741},
        "a3_walking_distance": {"pct_covered": 92.4},
        "b1_frequency": {"national_avg": 12.3},
        "c3_operator_hhi": {"hhi": 1850.0},
        "d1_coverage_deprivation": {"r": -0.0644},
        "j3_carbon": {"co2_saving_tonnes": 5278.5},
        "bsa1_franchising_readiness": {"national_avg": 41.2},
        "ps1_freq_restoration": {"scenario": {"population_affected": 5689818}},
    }
    for section_id, stats in fixture_stats.items():
        db.execute(
            "INSERT INTO section_results VALUES (?, ?, ?, ?, ?)",
            ["all", "all", section_id, stats, "narrative text"],
        )

    overview = query_overview(db, region="all", urban_rural="all")

    assert len(overview) == len(HEADLINE_SECTIONS)
    by_id = {row["id"]: row for row in overview}
    assert set(by_id) == set(HEADLINE_SECTIONS)

    nonzero_count = sum(1 for row in overview if row.get("value") not in (0, 0.0, None))
    assert nonzero_count == len(HEADLINE_SECTIONS), (
        f"expected all {len(HEADLINE_SECTIONS)} headline dimensions non-zero, got {nonzero_count}: {overview}"
    )
