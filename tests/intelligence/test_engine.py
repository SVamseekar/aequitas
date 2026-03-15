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
