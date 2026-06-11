"""Tests for 19 new Jinja2 templates — verify they render without errors."""

import pytest
from aequitas.intelligence.engine import InsightEngine


@pytest.fixture
def engine():
    return InsightEngine()


TEMPLATE_TEST_CASES = [
    ("coverage_gap", {"pct_covered": 79.9, "n_zero_access": 6776, "pct_zero_access": 20.1, "pop_zero_access": 1_200_000, "worst_region": "South West"}),
    ("desert_spotlight", {"n_desert_lsoas": 4245, "pop_affected": 800_000, "largest_region": "South West", "largest_region_count": 612, "mean_imd_score": 25.3, "national_mean_imd": 21.7}),
    ("urban_rural_gap", {"urban_value": 4.2, "rural_value": 1.3, "unit": "stops/1k", "gap_pct": 223.1, "n_urban": 20000, "n_rural": 13000}),
    ("ml_prediction", {"r2": 0.472, "top_feature": "nocar_pct", "top_importance": 0.142, "n_features": 9}),
    ("service_hours", {"median_first_service": "06:32", "median_last_service": "18:45", "n_evening_isolated": 5189, "pct_evening_isolated": 15.4}),
    ("weekend_penalty", {"sunday_pct_drop": 80.0, "n_sunday_desert": 6745, "pct_sunday_desert": 20.0, "saturday_pct_drop": 35.0}),
    ("distribution", {"median": 18.7, "unit": "km", "metric_name": "route length", "p10": 8.4, "p90": 28.7, "skew_label": "right-skewed", "n_outliers": 23, "cv": 0.85}),
    ("market_concentration", {"hhi": 2800, "region_name": "North East", "top_operator": "Arriva", "top_operator_share": 45.2}),
    ("ml_clusters", {"n_clusters": 4, "entity_type": "LSOAs", "clusters": [{"id": 0, "n": 16944, "pct": 50.2, "description": "Affluent urban"}, {"id": 1, "n": 6023, "pct": 17.8, "description": "Deprived car-free"}]}),
    ("network_topology", {"n_cross_la": 5143, "pct_cross_la": 37.7, "densest_corridor": "Greater Manchester–Lancashire", "densest_count": 142, "mean_length": 23.0, "median_length": 18.7}),
    ("heatmap", {"x_dimension": "deprivation decile", "y_dimension": "area type", "metric_name": "SQI", "worst_cell": {"label": "Decile 1 × Rural", "value": 32.1}, "best_cell": {"label": "Decile 10 × Urban", "value": 78.4}}),
    ("equity_decile", {"most_deprived_value": 12.3, "least_deprived_value": 45.6, "unit": "trips/capita", "ratio": 3.7, "bottom_20_pct": 4.2}),
    ("anomaly_spotlight", {"n_anomalies": 1688, "pct_anomalies": 5.0, "n_positive": 312, "n_inefficiency": 245, "n_policy_failure": 189}),
    ("economic_value", {"annual_benefit": 45_000_000, "region_name": "North East", "n_trips": 125_000, "vot": 8.49}),
    ("bcr_analysis", {"bcr": 1.32, "area_name": "rural South West", "vfm_band": "Low", "investment_m": 12.5, "appraisal_years": 60}),
    ("carbon_reduction", {"co2_saving_tonnes": 952, "scope": "bottom IMD decile", "co2_value_k": 247, "carbon_price": 259.87, "modal_shift_trips": 34_600_000}),
    ("tier_distribution", {"n_total": 298, "n_tier1": 1, "n_tier2": 102, "n_tier3": 195, "top_lad": "North Yorkshire", "top_score": 87.3}),
    ("scenario_comparison", {"scenarios": [{"name": "Freq restoration", "population": 5_700_000, "cost_m": 45.0, "co2_t": 952}, {"name": "Evening extension", "population": 8_400_000, "cost_m": 32.0, "co2_t": 450}], "best_bcr_scenario": "Freq restoration"}),
]

# Map template name → section_id that uses it
_TEMPLATE_TO_SECTION = {
    "coverage_gap": "a3_walking_distance",
    "desert_spotlight": "a5_service_deserts",
    "urban_rural_gap": "a6_urban_rural_gap",
    "ml_prediction": "a8_coverage_prediction",
    "service_hours": "b2_operating_hours",
    "weekend_penalty": "b3_weekend_penalty",
    "distribution": "c1_route_length",
    "market_concentration": "c3_operator_hhi",
    "ml_clusters": "c6_route_archetypes",
    "network_topology": "c7_network_topology",
    "heatmap": "d7_deprivation_urban_rural",
    "equity_decile": "f2_disparity_ratio",
    "anomaly_spotlight": "g2_anomalies",
    "economic_value": "j1_economic_value",
    "bcr_analysis": "j2_bcr",
    "carbon_reduction": "j3_carbon",
    "tier_distribution": "bsa3_tier_distribution",
    "scenario_comparison": "ps5_scenario_comparison",
}


@pytest.mark.parametrize("template_name,stats", TEMPLATE_TEST_CASES, ids=[t[0] for t in TEMPLATE_TEST_CASES])
def test_template_renders(engine, template_name, stats):
    """Each new template renders without errors when given valid stats."""
    section_id = _TEMPLATE_TO_SECTION[template_name]
    result = engine.generate(section_id=section_id, region="all", urban_rural="all", stats=stats)
    assert not result["suppressed"], f"{template_name} was suppressed"
    assert len(result["narrative"]) > 0, f"{template_name} produced empty narrative"
    assert "None" not in result["narrative"], f"{template_name} has unresolved None"


# A17: insufficient_data sentinel cases — templates for sections affected by
# near-empty region/urban_rural filters (e.g. London/rural) must render a
# suppression narrative rather than being omitted from the page.
INSUFFICIENT_DATA_TEST_CASES = [
    ("coverage_gap", "a3_walking_distance", {"insufficient_data": True, "n_lsoas": 0}),
    ("desert_spotlight", "a5_service_deserts", {"insufficient_data": True, "n_lsoas": 0}),
    ("urban_rural_gap", "a6_urban_rural_gap", {"insufficient_data": True, "n_lsoas": 4969, "n_urban": 4969, "n_rural": 0}),
    ("gap_to_target", "a7_investment_gap", {"insufficient_data": True, "n_lsoas": 0}),
]


@pytest.mark.parametrize(
    "template_name,section_id,stats", INSUFFICIENT_DATA_TEST_CASES, ids=[t[0] for t in INSUFFICIENT_DATA_TEST_CASES]
)
def test_template_renders_insufficient_data_sentinel(engine, template_name, section_id, stats):
    """Insufficient-data sentinel renders a suppression narrative, not an empty section."""
    result = engine.generate(section_id=section_id, region="E12000007", urban_rural="rural", stats=stats)
    assert not result["suppressed"], f"{template_name} was suppressed for insufficient_data"
    assert "Insufficient data for this filter" in result["narrative"]
    assert "None" not in result["narrative"], f"{template_name} has unresolved None"
