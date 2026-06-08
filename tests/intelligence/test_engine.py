"""Tests for InsightEngine orchestrator."""

import pytest
from aequitas.intelligence.engine import InsightEngine


def test_engine_produces_narrative():
    engine = InsightEngine()
    result = engine.generate(
        section_id="coverage_density",
        region="all",
        urban_rural="all",
        stats={"stops_per_1000": {"best": {"name": "East of England", "value": 2.54}}},
    )
    assert "narrative" in result
    assert len(result["narrative"]) > 0
    assert result["suppressed"] is False


def test_engine_suppresses_when_no_evidence():
    engine = InsightEngine()
    result = engine.generate(
        section_id="coverage_density",
        region="all",
        urban_rural="urban",
        stats={},
    )
    # Subset scope with no ranking data → suppressed
    assert result is not None
    assert result["suppressed"] is True


def test_engine_suppresses_unknown_section():
    engine = InsightEngine()
    result = engine.generate(
        section_id="nonexistent_section",
        region="all",
        urban_rural="all",
        stats={"foo": "bar"},
    )
    assert result["suppressed"] is True


def test_engine_equity_narrative():
    engine = InsightEngine()
    result = engine.generate(
        section_id="equity",
        region="all",
        urban_rural="all",
        stats={
            "gini": 0.5741,
            "palma": 5.702,
            "concentration_index": 0.1358,
        },
    )
    assert "0.5741" in result["narrative"] or "5.702" in result["narrative"]


def test_engine_returns_scope():
    engine = InsightEngine()
    result = engine.generate(section_id="ranking", region="all", urban_rural="all", stats={"x": 1})
    assert result["scope"] == "all_regions"


def test_engine_single_region_scope():
    engine = InsightEngine()
    result = engine.generate(
        section_id="single_region",
        region="E12000003",
        urban_rural="all",
        stats={
            "region_name": "Yorkshire and The Humber",
            "value": 1.85,
            "unit": "stops/1k",
            "vs_national_pct": -12.3,
            "national_avg": 2.11,
        },
    )
    assert result["scope"] == "single_region"
    assert "Yorkshire" in result["narrative"]


def test_single_region_shape_renders_single_region_template():
    """When stats look like single_region shape, engine must use single_region.j2,
    not ranking.j2 — even though a1_route_density maps to ranking.j2 in the registry."""
    from aequitas.intelligence.engine import InsightEngine

    engine = InsightEngine()
    stats = {
        "region_name": "North East",
        "value": 1.23,
        "national_avg": 1.50,
        "vs_national_pct": -18.0,
        "unit": "trips/capita",
    }
    result = engine.generate(
        section_id="a1_route_density", region="E12000001", urban_rural="all", stats=stats
    )
    assert not result["suppressed"]
    assert "North East" in result["narrative"]
    assert "1.23" in result["narrative"]
    # ranking.j2's distinctive heading must NOT appear — confirms single_region.j2 was used
    assert "Regional Spread" not in result["narrative"]


def test_ranking_shape_still_renders_ranking_template():
    """Stats with best/worst must still render via ranking.j2 (regression guard)."""
    from aequitas.intelligence.engine import InsightEngine

    engine = InsightEngine()
    stats = {
        "best": {"name": "London", "value": 3.0, "pct_above": 50.0},
        "worst": {"name": "North East", "value": 1.0, "pct_below": 50.0},
        "national_avg": 2.0,
        "unit": "trips/capita",
    }
    result = engine.generate(
        section_id="a1_route_density", region="all", urban_rural="all", stats=stats
    )
    assert not result["suppressed"]
    assert "Regional Spread" in result["narrative"]
