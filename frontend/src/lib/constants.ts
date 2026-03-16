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
  { id: "equity", name: "Equity & Deprivation", route: "/equity", prefixes: ["f"], headlineSection: "f1_gini", headlineStatKey: "gini", description: "Gini/Lorenz/Palma, vulnerability index, triple deprivation" },
  { id: "accessibility", name: "Accessibility", route: "/accessibility", prefixes: ["a"], headlineSection: "a5_service_deserts", headlineStatKey: "desert_count", description: "2SFCA, 400m coverage, service deserts, job/healthcare gaps" },
  { id: "service_quality", name: "Service Quality", route: "/service-quality", prefixes: ["b"], headlineSection: "b1_frequency", headlineStatKey: "mean_headway", description: "Headway, evening isolation, Sunday deserts, peak ratios" },
  { id: "route_network", name: "Route Network", route: "/route-network", prefixes: ["c"], headlineSection: "c3_operator_hhi", headlineStatKey: "national_hhi", description: "Geometry, operator HHI, route clustering" },
  { id: "correlations", name: "Socio-Economic & ML", route: "/correlations", prefixes: ["d", "g"], headlineSection: "d8_feature_importance", headlineStatKey: "top_feature_importance", description: "Deprivation correlations, SHAP, clustering, anomalies" },
  { id: "economic", name: "Economic Appraisal", route: "/economic", prefixes: ["j"], headlineSection: "j2_bcr", headlineStatKey: "national_bcr", description: "BCR/Green Book, investment gap, GDP multipliers" },
  { id: "bus_services_act", name: "Bus Services Act 2025", route: "/bus-services-act", prefixes: ["bsa"], headlineSection: "bsa1_franchising_readiness", headlineStatKey: "mean_readiness", description: "LTA franchising readiness, operator concentration" },
  { id: "scenarios", name: "Policy Scenarios", route: "/scenarios", prefixes: ["ps"], headlineSection: "ps5_scenario_comparison", headlineStatKey: "best_scenario_bcr", description: "Frequency restoration, last bus extension, DRT" },
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
