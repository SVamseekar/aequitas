"""Tests for evidence-gated insight rules."""

import pytest
from aequitas.intelligence.context import resolve_context
from aequitas.intelligence.rules import (
    CorrelationRule,
    GapToInvestmentRule,
    GiniEquityRule,
    RankingRule,
    SingleRegionRule,
)


def test_ranking_rule_fires_for_all_regions():
    ctx = resolve_context(region="all", urban_rural="all")
    rule = RankingRule()
    assert rule.should_fire(ctx, n_groups=9)


def test_ranking_rule_suppresses_for_subset():
    ctx = resolve_context(region="all", urban_rural="urban")
    rule = RankingRule()
    assert not rule.should_fire(ctx, n_groups=1)


def test_ranking_rule_suppresses_too_few_groups():
    ctx = resolve_context(region="all", urban_rural="all")
    rule = RankingRule()
    assert not rule.should_fire(ctx, n_groups=2)


def test_single_region_rule_fires():
    ctx = resolve_context(region="E12000003", urban_rural="all")
    rule = SingleRegionRule()
    assert rule.should_fire(ctx)


def test_single_region_rule_suppresses_all_regions():
    ctx = resolve_context(region="all", urban_rural="all")
    rule = SingleRegionRule()
    assert not rule.should_fire(ctx)


def test_correlation_rule_suppresses_low_n():
    rule = CorrelationRule()
    assert not rule.should_fire(n=10, p_value=0.01)


def test_correlation_rule_suppresses_insignificant():
    rule = CorrelationRule()
    assert not rule.should_fire(n=100, p_value=0.10)


def test_correlation_rule_fires_when_valid():
    rule = CorrelationRule()
    assert rule.should_fire(n=100, p_value=0.01)


def test_gini_rule_fires_large_n():
    rule = GiniEquityRule()
    assert rule.should_fire(n_lsoas=33755)


def test_gini_rule_suppresses_small_n():
    rule = GiniEquityRule()
    assert not rule.should_fire(n_lsoas=50)


def test_gap_rule_fires_when_below_target():
    rule = GapToInvestmentRule()
    assert rule.should_fire(n_below_target=100)


def test_gap_rule_suppresses_when_none_below():
    rule = GapToInvestmentRule()
    assert not rule.should_fire(n_below_target=0)
