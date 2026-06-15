"""Tests for precompute_all_sections — verifies full 55-section x 30-combo coverage."""
import pytest

from aequitas.core.config import PipelineConfig
from aequitas.intelligence.section_registry import SECTION_REGISTRY
from aequitas.warehouse.precompute import precompute_all_sections


@pytest.fixture
def cfg() -> PipelineConfig:
    return PipelineConfig()


def test_precomputes_30_combos_times_55_sections(cfg):
    results = precompute_all_sections(cfg)
    assert len(results) == 30 * 55


def test_every_registered_section_appears_in_every_combo(cfg):
    results = precompute_all_sections(cfg)
    seen = {(r["region"], r["urban_rural"], r["section_id"]) for r in results}
    assert len(seen) == 30 * 55
    for section_id in SECTION_REGISTRY:
        matching = [r for r in results if r["section_id"] == section_id]
        assert len(matching) == 30, f"{section_id} missing combos"


def test_all_sections_produce_non_empty_stats_at_national_scope(cfg):
    results = precompute_all_sections(cfg)
    national_all = [
        r for r in results
        if r["region"] == "all" and r["urban_rural"] == "all"
    ]
    empty = [r["section_id"] for r in national_all if r["stats"] == {}]
    assert empty == [], f"unexpectedly empty at national scope: {empty}"


_POLICY_SCENARIO_NARRATIVE_SECTIONS = {
    "ps1_freq_restoration",
    "ps2_evening_extension",
    "ps3_drt_rural",
    "ps4_franchise",
    "ps5_scenario_comparison",
    "g5_scenario_model",
}


def test_policy_scenario_sections_render_non_empty_narratives(cfg):
    """A19 regression: ps1-ps5/g5 must always render a narrative.

    policy_scenarios.parquet is England-wide (not region/area-type scoped),
    so every one of the 30 region/urban_rural combos must produce a
    non-empty narrative for these sections — never silently suppressed.
    """
    results = precompute_all_sections(cfg)
    scenario_results = [r for r in results if r["section_id"] in _POLICY_SCENARIO_NARRATIVE_SECTIONS]
    assert len(scenario_results) == 30 * len(_POLICY_SCENARIO_NARRATIVE_SECTIONS)
    empty = [
        (r["section_id"], r["region"], r["urban_rural"])
        for r in scenario_results
        if not r["narrative"]
    ]
    assert empty == [], f"empty narrative for policy scenario sections: {empty}"


def test_f5_rural_penalty_renders_narrative_for_every_combo(cfg):
    """f5_rural_penalty must render a narrative for all 30 combos.

    Regions with zero LSOAs of one settlement type (e.g. London has 0
    Rural LSOAs) hit the insufficient_data sentinel from
    build_urban_rural_gap_stats, but urban_rural_gap.j2 still renders an
    explicit "insufficient data" narrative for that case (suppress >
    mislead, never silently empty).
    """
    results = precompute_all_sections(cfg)
    f5_results = [r for r in results if r["section_id"] == "f5_rural_penalty"]
    assert len(f5_results) == 30
    empty = [(r["region"], r["urban_rural"]) for r in f5_results if not r["narrative"]]
    assert empty == [], f"empty narrative for f5_rural_penalty: {empty}"


def test_gap_to_target_uses_fixed_national_median_across_regions(cfg):
    results = precompute_all_sections(cfg)
    a7_results = [
        r for r in results
        if r["section_id"] == "a7_investment_gap" and r["stats"] and not r["stats"].get("insufficient_data")
    ]
    targets = {
        r["region"]: r["stats"].get("target")
        for r in a7_results
        if r["urban_rural"] == "all"
    }
    # All regions must be judged against the SAME national yardstick (§2.5 fix)
    assert len(set(targets.values())) == 1
    assert all(r["stats"].get("target_description") == "national median" for r in a7_results)
