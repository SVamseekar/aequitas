"""Tests for precompute_all_sections — verifies full 51-section x 30-combo coverage."""
import pytest

from aequitas.core.config import PipelineConfig
from aequitas.intelligence.section_registry import SECTION_REGISTRY
from aequitas.warehouse.precompute import _STUB_SECTIONS, precompute_all_sections


@pytest.fixture
def cfg() -> PipelineConfig:
    return PipelineConfig()


def test_precomputes_30_combos_times_51_sections(cfg):
    results = precompute_all_sections(cfg)
    assert len(results) == 30 * 51


def test_every_registered_section_appears_in_every_combo(cfg):
    results = precompute_all_sections(cfg)
    seen = {(r["region"], r["urban_rural"], r["section_id"]) for r in results}
    assert len(seen) == 30 * 51
    for section_id in SECTION_REGISTRY:
        matching = [r for r in results if r["section_id"] == section_id]
        assert len(matching) == 30, f"{section_id} missing combos"


def test_stub_sections_produce_empty_stats_everywhere(cfg):
    results = precompute_all_sections(cfg)
    for section_id in _STUB_SECTIONS:
        matching = [r for r in results if r["section_id"] == section_id]
        assert len(matching) == 30
        assert all(r["stats"] == {} for r in matching)


def test_non_stub_sections_produce_non_empty_stats_at_national_scope(cfg):
    results = precompute_all_sections(cfg)
    national_all = [
        r for r in results
        if r["region"] == "all" and r["urban_rural"] == "all" and r["section_id"] not in _STUB_SECTIONS
    ]
    empty = [r["section_id"] for r in national_all if r["stats"] == {}]
    assert empty == [], f"unexpectedly empty at national scope: {empty}"


def test_gap_to_target_uses_fixed_national_median_across_regions(cfg):
    results = precompute_all_sections(cfg)
    targets = {
        r["region"]: r["stats"].get("target")
        for r in results
        if r["section_id"] == "a7_investment_gap" and r["urban_rural"] == "all" and r["stats"]
    }
    # All regions must be judged against the SAME national yardstick (§2.5 fix)
    assert len(set(targets.values())) == 1
    assert all(r["stats"].get("target_description") == "national median" for r in results if r["section_id"] == "a7_investment_gap" and r["stats"])
