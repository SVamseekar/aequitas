"""Section registry — maps every section_id to its template, chart type, and evidence gate.

Single source of truth for all 50 analytical sections. Used by precompute.py
to iterate over sections and by the frontend to know what chart to render.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class SectionDef:
    """Definition of one analytical section."""

    template: str
    """Jinja2 template filename (e.g. 'ranking.j2')."""

    chart_type: str
    """Chart data type (e.g. 'horizontal_bar', 'scatter_regression')."""

    category: str
    """Category label (e.g. 'A', 'B', 'BSA')."""

    title: str
    """Human-readable question title."""


SECTION_REGISTRY: dict[str, SectionDef] = {
    # Category A: Coverage & Accessibility
    "a1_route_density": SectionDef("ranking.j2", "horizontal_bar", "A", "Route density by region"),
    "a2_stop_density": SectionDef("ranking.j2", "horizontal_bar", "A", "Stop density by region"),
    "a3_walking_distance": SectionDef("coverage_gap.j2", "stacked_bar", "A", "Population within 400m of a stop"),
    "a4_coverage_equity": SectionDef("equity.j2", "lorenz_curve", "A", "Equity of coverage within regions"),
    "a5_service_deserts": SectionDef("desert_spotlight.j2", "choropleth", "A", "Service deserts"),
    "a6_urban_rural_gap": SectionDef("urban_rural_gap.j2", "grouped_bar", "A", "Urban vs rural coverage gap"),
    "a7_investment_gap": SectionDef("gap_to_target.j2", "horizontal_bar", "A", "Investment to reach national average"),
    "a8_coverage_prediction": SectionDef("ml_prediction.j2", "shap_bar", "A", "Coverage prediction from demographics"),
    # Category B: Service Quality
    "b1_frequency": SectionDef("ranking.j2", "horizontal_bar", "B", "Average frequency by region"),
    "b2_operating_hours": SectionDef("service_hours.j2", "grouped_bar", "B", "Operating hours"),
    "b3_weekend_penalty": SectionDef("weekend_penalty.j2", "grouped_bar", "B", "Weekend service penalty"),
    "b4_route_frequency": SectionDef("route_frequency_ranking.j2", "horizontal_bar", "B", "Most/least frequent routes"),
    "b5_frequency_deprivation": SectionDef("correlation.j2", "scatter_regression", "B", "Frequency vs deprivation"),
    # Category C: Route Characteristics
    "c1_route_length": SectionDef("distribution.j2", "box_violin", "C", "Route length distribution"),
    "c2_stops_per_route": SectionDef("distribution.j2", "box_violin", "C", "Stops per route"),
    "c3_operator_hhi": SectionDef("market_concentration.j2", "horizontal_bar", "C", "Operator landscape (HHI)"),
    "c4_urban_rural_routes": SectionDef("urban_rural_gap.j2", "stacked_bar", "C", "Urban vs rural routes"),
    "c5_length_vs_frequency": SectionDef("correlation.j2", "scatter_regression", "C", "Route length vs frequency"),
    "c6_route_archetypes": SectionDef("ml_clusters.j2", "scatter_clusters", "C", "Route archetypes"),
    "c7_network_topology": SectionDef("network_topology.j2", "horizontal_bar", "C", "Network topology"),
    # Category D: Socio-Economic Correlations
    "d1_coverage_deprivation": SectionDef("correlation.j2", "scatter_regression", "D", "Coverage vs deprivation"),
    "d2_coverage_unemployment": SectionDef("correlation.j2", "scatter_regression", "D", "Coverage vs unemployment"),
    "d3_coverage_car": SectionDef("correlation.j2", "scatter_regression", "D", "Coverage vs car ownership"),
    "d4_coverage_elderly": SectionDef("correlation.j2", "scatter_regression", "D", "Coverage vs elderly population"),
    "d5_coverage_income": SectionDef("correlation.j2", "scatter_regression", "D", "Coverage vs income"),
    "d6_transport_poverty": SectionDef("ml_clusters.j2", "scatter_clusters", "D", "Transport poverty clusters"),
    "d7_deprivation_urban_rural": SectionDef("heatmap.j2", "heatmap", "D", "Deprivation x urban/rural"),
    "d8_feature_importance": SectionDef("ml_prediction.j2", "shap_bar", "D", "Feature importance"),
    # Category F: Equity & Social Inclusion
    "f1_gini": SectionDef("equity.j2", "lorenz_curve", "F", "Gini coefficient"),
    "f2_disparity_ratio": SectionDef("equity_decile.j2", "horizontal_bar", "F", "Disparity by IMD decile"),
    "f3_ethnic_access": SectionDef("correlation.j2", "scatter_regression", "F", "Bus access by ethnicity"),
    "f5_rural_penalty": SectionDef("urban_rural_gap.j2", "grouped_bar", "F", "Rural accessibility penalty"),
    "f6_equitable_regions": SectionDef("ranking.j2", "horizontal_bar", "F", "Most equitable regions"),
    # Category G: ML Insights
    "g1_route_clusters": SectionDef("ml_clusters.j2", "scatter_clusters", "G", "Route clustering"),
    "g2_anomalies": SectionDef("anomaly_spotlight.j2", "scatter_regression", "G", "Anomaly detection"),
    "g3_coverage_model": SectionDef("ml_prediction.j2", "scatter_regression", "G", "Coverage prediction"),
    "g4_shap": SectionDef("ml_prediction.j2", "shap_bar", "G", "Feature importance (SHAP)"),
    "g5_scenario_model": SectionDef("policy_scenario.j2", "kpi_tiles", "G", "Scenario modelling"),
    # Category J: Economic Impact & BCR
    "j1_economic_value": SectionDef("economic_value.j2", "horizontal_bar", "J", "Economic value per region"),
    "j2_bcr": SectionDef("bcr_analysis.j2", "horizontal_bar", "J", "BCR for coverage gaps"),
    "j3_carbon": SectionDef("carbon_reduction.j2", "horizontal_bar", "J", "Carbon reduction from modal shift"),
    "j4_investment_priority": SectionDef("ranking.j2", "horizontal_bar", "J", "Regional investment prioritisation"),
    # Category BSA: Bus Services Act 2025
    "bsa1_franchising_readiness": SectionDef("ranking.j2", "horizontal_bar", "BSA", "LTA franchising readiness"),
    "bsa2_operator_concentration": SectionDef("market_concentration.j2", "horizontal_bar", "BSA", "Operator concentration"),
    "bsa3_tier_distribution": SectionDef("tier_distribution.j2", "stacked_bar", "BSA", "Readiness tier distribution"),
    # Category PS: Policy Scenario Modelling
    "ps1_freq_restoration": SectionDef("policy_scenario.j2", "kpi_tiles", "PS", "Frequency restoration"),
    "ps2_evening_extension": SectionDef("policy_scenario.j2", "kpi_tiles", "PS", "Evening extension"),
    "ps3_drt_rural": SectionDef("policy_scenario.j2", "kpi_tiles", "PS", "DRT for rural areas"),
    "ps4_franchise": SectionDef("policy_scenario.j2", "kpi_tiles", "PS", "Combined franchise"),
    "ps5_scenario_comparison": SectionDef("scenario_comparison.j2", "table", "PS", "Scenario comparison"),
}
