export interface DimensionDef {
  id: string
  name: string
  route: string
  prefixes: string[]
  headlineSection: string
  headlineStatKey: string
  description: string
}

export const DIMENSIONS: DimensionDef[] = [
  { id: "equity", name: "Equity & Deprivation", route: "/equity", prefixes: ["f"], headlineSection: "f2_disparity_ratio", headlineStatKey: "ratio", description: "Gini/Lorenz/Palma, vulnerability index, triple deprivation" },
  { id: "accessibility", name: "Accessibility", route: "/accessibility", prefixes: ["a"], headlineSection: "a3_walking_distance", headlineStatKey: "pct_covered", description: "2SFCA, 400m coverage, service deserts, job/healthcare gaps" },
  { id: "service_quality", name: "Service Quality", route: "/service-quality", prefixes: ["b"], headlineSection: "b1_frequency", headlineStatKey: "national_avg", description: "Headway, evening isolation, Sunday deserts, peak ratios" },
  { id: "route_network", name: "Route Network", route: "/route-network", prefixes: ["c"], headlineSection: "c3_operator_hhi", headlineStatKey: "hhi", description: "Geometry, operator HHI, route clustering" },
  { id: "correlations", name: "Socio-Economic & ML", route: "/correlations", prefixes: ["d", "g"], headlineSection: "d1_coverage_deprivation", headlineStatKey: "r", description: "Deprivation correlations, SHAP, clustering, anomalies" },
  { id: "economic", name: "Economic Appraisal", route: "/economic", prefixes: ["j"], headlineSection: "j3_carbon", headlineStatKey: "co2_saving_tonnes", description: "BCR/Green Book, investment gap, GDP multipliers" },
  { id: "bus_services_act", name: "Bus Services Act 2025", route: "/bus-services-act", prefixes: ["bsa"], headlineSection: "bsa1_franchising_readiness", headlineStatKey: "national_avg", description: "LTA franchising readiness, operator concentration" },
  { id: "scenarios", name: "Policy Scenarios", route: "/scenarios", prefixes: ["ps"], headlineSection: "ps1_freq_restoration", headlineStatKey: "population_affected", description: "Frequency restoration, last bus extension, DRT" },
]

export const REGIONS = [
  { code: "all", name: "All England" },
  { code: "E12000001", name: "North East" },
  { code: "E12000002", name: "North West" },
  { code: "E12000003", name: "Yorkshire and The Humber" },
  { code: "E12000004", name: "East Midlands" },
  { code: "E12000005", name: "West Midlands" },
  { code: "E12000006", name: "East of England" },
  { code: "E12000007", name: "London" },
  { code: "E12000008", name: "South East" },
  { code: "E12000009", name: "South West" },
] as const

export const AREA_TYPES = [
  { code: "all", name: "All Areas" },
  { code: "urban", name: "Urban" },
  { code: "rural", name: "Rural" },
] as const

export const SECTION_TITLES: Record<string, string> = {
  a1_route_density: "Route density by region",
  a2_stop_density: "Stop density by region",
  a3_walking_distance: "Population within 400m of a stop",
  a4_coverage_equity: "Equity of coverage within regions",
  a5_service_deserts: "Service deserts",
  a6_urban_rural_gap: "Urban vs rural coverage gap",
  a7_investment_gap: "Investment to reach national average",
  a8_coverage_prediction: "Coverage prediction from demographics",
  b1_frequency: "Average frequency by region",
  b2_operating_hours: "Operating hours",
  b3_weekend_penalty: "Weekend service penalty",
  b4_route_frequency: "Most/least frequent routes",
  b5_frequency_deprivation: "Frequency vs deprivation",
  c1_route_length: "Route length distribution",
  c2_stops_per_route: "Stops per route",
  c3_operator_hhi: "Operator landscape (HHI)",
  c4_urban_rural_routes: "Urban vs rural routes",
  c5_length_vs_frequency: "Route length vs frequency",
  c6_route_archetypes: "Route archetypes",
  c7_network_topology: "Network topology",
  d1_coverage_deprivation: "Coverage vs deprivation",
  d2_coverage_unemployment: "Coverage vs unemployment",
  d3_coverage_car: "Coverage vs car ownership",
  d4_coverage_elderly: "Coverage vs elderly population",
  d5_coverage_income: "Coverage vs income",
  d6_transport_poverty: "Transport poverty clusters",
  d7_deprivation_urban_rural: "Deprivation x urban/rural",
  d8_feature_importance: "Feature importance",
  f1_gini: "Gini coefficient",
  f2_disparity_ratio: "Disparity by IMD decile",
  f3_ethnic_access: "Bus access by ethnicity",
  f5_rural_penalty: "Rural accessibility penalty",
  f6_equitable_regions: "Most equitable regions",
  g1_route_clusters: "Route clustering",
  g2_anomalies: "Anomaly detection",
  g3_coverage_model: "Coverage prediction",
  g4_shap: "Feature importance (SHAP)",
  g5_scenario_model: "Scenario modelling",
  j1_economic_value: "Economic value per region",
  j2_bcr: "BCR for coverage gaps",
  j3_carbon: "Carbon reduction from modal shift",
  j4_investment_priority: "Regional investment prioritisation",
  bsa1_franchising_readiness: "LTA franchising readiness",
  bsa2_operator_concentration: "Operator concentration",
  bsa3_tier_distribution: "Readiness tier distribution",
  ps1_freq_restoration: "Frequency restoration",
  ps2_evening_extension: "Evening extension",
  ps3_drt_rural: "DRT for rural areas",
  ps4_franchise: "Combined franchise",
  ps5_scenario_comparison: "Scenario comparison",
} as const
