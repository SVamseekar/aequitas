"""Tests for new evidence gate rules — InsightEngine expansion."""

import pytest
from aequitas.intelligence.rules import (
    MinLsoaRule,
    DesertRule,
    UrbanRuralRule,
    MLPredictionRule,
    DistributionRule,
    MarketConcentrationRule,
    ClusterRule,
    NetworkRule,
    HeatmapRule,
    DecileRule,
    DemographicRule,
    AccessibilityRule,
    AnomalyRule,
    CarbonRule,
    TierRule,
    ScenarioComparisonRule,
)


# --- MinLsoaRule ---
def test_min_lsoa_fires_large():
    assert MinLsoaRule().should_fire(n_lsoas=500)

def test_min_lsoa_suppresses_small():
    assert not MinLsoaRule().should_fire(n_lsoas=50)

def test_min_lsoa_boundary():
    assert MinLsoaRule().should_fire(n_lsoas=100)
    assert not MinLsoaRule().should_fire(n_lsoas=99)


# --- DesertRule ---
def test_desert_fires():
    assert DesertRule().should_fire(n_desert_lsoas=1)

def test_desert_suppresses_zero():
    assert not DesertRule().should_fire(n_desert_lsoas=0)


# --- UrbanRuralRule ---
def test_urban_rural_fires():
    assert UrbanRuralRule().should_fire(n_urban=100, n_rural=50)

def test_urban_rural_suppresses_low_urban():
    assert not UrbanRuralRule().should_fire(n_urban=10, n_rural=50)

def test_urban_rural_suppresses_low_rural():
    assert not UrbanRuralRule().should_fire(n_urban=100, n_rural=5)


# --- MLPredictionRule ---
def test_ml_prediction_fires():
    assert MLPredictionRule().should_fire(r2=0.472, n_features=9)

def test_ml_prediction_suppresses_negative_r2():
    assert not MLPredictionRule().should_fire(r2=-0.1, n_features=9)

def test_ml_prediction_suppresses_few_features():
    assert not MLPredictionRule().should_fire(r2=0.5, n_features=2)


# --- DistributionRule ---
def test_distribution_fires():
    assert DistributionRule().should_fire(n=100)

def test_distribution_suppresses():
    assert not DistributionRule().should_fire(n=10)


# --- MarketConcentrationRule ---
def test_market_fires():
    assert MarketConcentrationRule().should_fire(n_operators=5)

def test_market_suppresses_monopoly():
    assert not MarketConcentrationRule().should_fire(n_operators=1)


# --- ClusterRule ---
def test_cluster_fires():
    assert ClusterRule().should_fire(n_clusters=4)

def test_cluster_suppresses():
    assert not ClusterRule().should_fire(n_clusters=1)


# --- NetworkRule ---
def test_network_fires():
    assert NetworkRule().should_fire(n_routes=100)

def test_network_suppresses():
    assert not NetworkRule().should_fire(n_routes=5)


# --- HeatmapRule ---
def test_heatmap_fires():
    assert HeatmapRule().should_fire(min_cell_n=50)

def test_heatmap_suppresses():
    assert not HeatmapRule().should_fire(min_cell_n=5)


# --- DecileRule ---
def test_decile_fires():
    assert DecileRule().should_fire(decile_counts=[200] * 10)

def test_decile_suppresses_one_small():
    counts = [200] * 9 + [50]
    assert not DecileRule().should_fire(decile_counts=counts)


# --- DemographicRule ---
def test_demographic_fires():
    assert DemographicRule().should_fire(group_counts=[100, 200, 150])

def test_demographic_suppresses():
    assert not DemographicRule().should_fire(group_counts=[100, 10, 150])


# --- AccessibilityRule ---
def test_accessibility_fires():
    assert AccessibilityRule().should_fire(n_pois=100)

def test_accessibility_suppresses():
    assert not AccessibilityRule().should_fire(n_pois=5)


# --- AnomalyRule ---
def test_anomaly_fires():
    assert AnomalyRule().should_fire(n_anomalies=100)

def test_anomaly_suppresses():
    assert not AnomalyRule().should_fire(n_anomalies=5)


# --- CarbonRule ---
def test_carbon_fires():
    assert CarbonRule().should_fire(co2_saving=100.0)

def test_carbon_suppresses():
    assert not CarbonRule().should_fire(co2_saving=0.0)

def test_carbon_suppresses_negative():
    assert not CarbonRule().should_fire(co2_saving=-5.0)


# --- TierRule ---
def test_tier_fires():
    assert TierRule().should_fire(n_lads=50)

def test_tier_suppresses():
    assert not TierRule().should_fire(n_lads=5)


# --- ScenarioComparisonRule ---
def test_scenario_fires():
    assert ScenarioComparisonRule().should_fire(n_scenarios=4)

def test_scenario_suppresses():
    assert not ScenarioComparisonRule().should_fire(n_scenarios=1)
