"""Tests for section registry — single source of truth for all 50 sections."""

import pytest
from aequitas.intelligence.section_registry import SECTION_REGISTRY, SectionDef


def test_registry_has_50_sections():
    assert len(SECTION_REGISTRY) == 50


def test_all_section_ids_are_strings():
    for sid in SECTION_REGISTRY:
        assert isinstance(sid, str)
        assert len(sid) > 0


def test_all_entries_are_section_defs():
    for sid, entry in SECTION_REGISTRY.items():
        assert isinstance(entry, SectionDef), f"{sid} is not a SectionDef"


def test_all_templates_exist():
    """Every template referenced in the registry must be a known template."""
    from aequitas.intelligence.engine import _SECTION_TEMPLATES
    for sid, entry in SECTION_REGISTRY.items():
        assert entry.template in {v for v in _SECTION_TEMPLATES.values()}, \
            f"{sid} references unknown template {entry.template}"


def test_category_a_has_8():
    a_sections = [s for s in SECTION_REGISTRY if s.startswith("a")]
    assert len(a_sections) == 8


def test_category_d_has_8():
    d_sections = [s for s in SECTION_REGISTRY if s.startswith("d")]
    assert len(d_sections) == 8


def test_known_section_ids():
    """Spot-check key section IDs exist."""
    expected = ["a1_route_density", "b5_frequency_deprivation", "d1_coverage_deprivation",
                "f1_gini", "g2_anomalies", "j3_carbon", "bsa1_franchising_readiness", "ps5_scenario_comparison"]
    for sid in expected:
        assert sid in SECTION_REGISTRY, f"Missing section: {sid}"
