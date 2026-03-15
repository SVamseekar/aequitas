"""Tests for InsightEngine context resolver."""

import pytest
from aequitas.intelligence.context import resolve_context, AnalysisScope


def test_all_regions_all_areas():
    ctx = resolve_context(region="all", urban_rural="all")
    assert ctx.scope == AnalysisScope.ALL_REGIONS
    assert ctx.n_groups == 9
    assert ctx.show_rankings is True
    assert ctx.compare_to_national is False


def test_single_region():
    ctx = resolve_context(region="E12000003", urban_rural="all")
    assert ctx.scope == AnalysisScope.SINGLE_REGION
    assert ctx.n_groups == 1
    assert ctx.show_rankings is False
    assert ctx.compare_to_national is True


def test_subset():
    ctx = resolve_context(region="all", urban_rural="urban")
    assert ctx.scope == AnalysisScope.SUBSET
    assert ctx.n_groups == 1
    assert ctx.show_rankings is False


def test_subset_single_region_urban():
    ctx = resolve_context(region="E12000001", urban_rural="urban")
    assert ctx.scope == AnalysisScope.SUBSET
    assert ctx.n_groups == 1


def test_invalid_region_raises():
    with pytest.raises(ValueError, match="Invalid region code"):
        resolve_context(region="BADCODE", urban_rural="all")


def test_invalid_urban_rural_raises():
    with pytest.raises(ValueError, match="Invalid urban_rural"):
        resolve_context(region="all", urban_rural="suburban")
