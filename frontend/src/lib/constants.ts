export interface DimensionDef {
  id: string
  name: string
  route: string
  prefixes: string[]
  headlineSection: string
  headlineStatKey: string
  description: string
}

export const COUNTRIES = [
  { code: "england", name: "England", packReady: true },
  { code: "ireland", name: "Ireland", packReady: true },
  { code: "netherlands", name: "Netherlands", packReady: true },
  { code: "france", name: "France", packReady: false },
] as const

export type CountryCode = (typeof COUNTRIES)[number]["code"]

export const DIMENSIONS: DimensionDef[] = [
  { id: "equity", name: "Equity & Deprivation", route: "/equity", prefixes: ["f"], headlineSection: "f2_disparity_ratio", headlineStatKey: "ratio", description: "Lorenz, IMD decile slope, rural penalty — in-country ranks only" },
  { id: "access", name: "Access", route: "/access", prefixes: ["a"], headlineSection: "a3_walking_distance", headlineStatKey: "pct_covered", description: "400m coverage, deserts, 15/30/45-min reach (Wave 2)" },
  { id: "service", name: "Service", route: "/service", prefixes: ["b"], headlineSection: "b1_frequency", headlineStatKey: "national_avg", description: "Frequency, evening isolation, Sunday deserts" },
  { id: "network", name: "Network", route: "/network", prefixes: ["c"], headlineSection: "c3_operator_hhi", headlineStatKey: "hhi", description: "Distributions, one HHI (0–10,000), archetypes" },
  { id: "correlations", name: "Correlations", route: "/correlations", prefixes: ["d", "g"], headlineSection: "d1_coverage_deprivation", headlineStatKey: "r", description: "One matrix plus one deep-dive scatter" },
  { id: "economy", name: "Economy", route: "/economy", prefixes: ["j"], headlineSection: "j3_carbon", headlineStatKey: "co2_saving_tonnes", description: "TAG/BCR/carbon — England scopes named honestly" },
  { id: "policy", name: "Policy", route: "/policy", prefixes: ["bsa"], headlineSection: "bsa1_franchising_readiness", headlineStatKey: "national_avg", description: "Bus Services Act 2025 (England). Other countries: not applicable." },
  { id: "scenarios", name: "Scenarios", route: "/scenarios", prefixes: ["ps"], headlineSection: "ps1_freq_restoration", headlineStatKey: "population_affected", description: "Listed interventions — who and £" },
]

export const IRELAND_DIMENSIONS: DimensionDef[] = [
  { id: "equity", name: "Equity & Deprivation", route: "/equity", prefixes: ["f"], headlineSection: "f2_disparity_ratio", headlineStatKey: "ratio", description: "Lorenz, Pobal HP 2022 decile slope, rural penalty — Republic ranks only" },
  { id: "access", name: "Access", route: "/access", prefixes: ["a"], headlineSection: "a3_walking_distance", headlineStatKey: "pct_covered", description: "400 m TFI coverage, deserts, service bands (15/30/45 when r5py ran)" },
  { id: "service", name: "Service", route: "/service", prefixes: ["b"], headlineSection: "b1_frequency", headlineStatKey: "national_avg", description: "TFI weekday quality, evening after 19:00, Sunday deserts" },
  { id: "network", name: "Network", route: "/network", prefixes: ["c"], headlineSection: "c3_operator_hhi", headlineStatKey: "hhi", description: "TFI agencies, one HHI (0–10,000), archetypes" },
  { id: "correlations", name: "Correlations", route: "/correlations", prefixes: ["d", "g"], headlineSection: "d1_coverage_deprivation", headlineStatKey: "r", description: "One HP matrix plus one scatter" },
  { id: "economy", name: "Economy", route: "/economy", prefixes: ["j"], headlineSection: "j3_carbon", headlineStatKey: "co2_saving_tonnes", description: "CAF/PAG / NTA PSO scope; illustrative EPA Ireland carbon" },
  { id: "policy", name: "National policy (NTA)", route: "/policy", prefixes: ["bsa"], headlineSection: "bsa1_franchising_readiness", headlineStatKey: "national_avg", description: "Connecting Ireland, BusConnects, Local Link, PSO" },
  { id: "scenarios", name: "Scenarios", route: "/scenarios", prefixes: ["ps"], headlineSection: "ps1_freq_restoration", headlineStatKey: "population_affected", description: "Irish interventions × HP decile. € only if cited." },
]

export const NETHERLANDS_DIMENSIONS: DimensionDef[] = [
  { id: "equity", name: "Equity & Deprivation", route: "/equity", prefixes: ["f"], headlineSection: "f2_disparity_ratio", headlineStatKey: "ratio", description: "Lorenz, SES-WOA decile slope, rural penalty — Dutch ranks only" },
  { id: "access", name: "Access", route: "/access", prefixes: ["a"], headlineSection: "a3_walking_distance", headlineStatKey: "pct_covered", description: "400 m OVapi coverage, deserts, service bands (15/30/45 when r5py ran)" },
  { id: "service", name: "Service", route: "/service", prefixes: ["b"], headlineSection: "b1_frequency", headlineStatKey: "national_avg", description: "OVapi weekday quality, evening after 19:00, Sunday deserts" },
  { id: "network", name: "Network", route: "/network", prefixes: ["c"], headlineSection: "c3_operator_hhi", headlineStatKey: "hhi", description: "OVapi agencies, one HHI (0–10,000), archetypes" },
  { id: "correlations", name: "Correlations", route: "/correlations", prefixes: ["d", "g"], headlineSection: "d1_coverage_deprivation", headlineStatKey: "r", description: "One SES-WOA matrix plus one scatter" },
  { id: "economy", name: "Economy", route: "/economy", prefixes: ["j"], headlineSection: "j3_carbon", headlineStatKey: "co2_saving_tonnes", description: "People-gap; no invented PBL euro" },
  { id: "policy", name: "Concession / OV-wet", route: "/policy", prefixes: ["bsa"], headlineSection: "bsa1_franchising_readiness", headlineStatKey: "national_avg", description: "Concession programmes, not a UK statute" },
  { id: "scenarios", name: "Scenarios", route: "/scenarios", prefixes: ["ps"], headlineSection: "ps1_freq_restoration", headlineStatKey: "population_affected", description: "OV / flex × people / SES. € only if cited." },
]

export function dimensionsForCountry(country: string): DimensionDef[] {
  if (country === "ireland") return IRELAND_DIMENSIONS
  if (country === "netherlands") return NETHERLANDS_DIMENSIONS
  return DIMENSIONS
}

/** Warehouse dimension ids still used by the API. */
export const DIMENSION_API_IDS: Record<string, string> = {
  equity: "equity",
  access: "accessibility",
  accessibility: "accessibility",
  service: "service_quality",
  "service-quality": "service_quality",
  network: "route_network",
  "route-network": "route_network",
  correlations: "correlations",
  economy: "economic",
  economic: "economic",
  policy: "bus_services_act",
  "bus-services-act": "bus_services_act",
  scenarios: "scenarios",
}

export const HIDDEN_STAT_KEYS = new Set([
  "higher_is_better",
  "ratio_undefined",
  "n_lsoas",
  "n_desert_lsoas",
  "palma_note",
  "reason",
  "same_as",
  "euro",
  "currency",
  "note",
  "omit_euro",
  "features",
  "clusters",
  "cells",
  "by_decile",
  "by_county",
  "ranking",
  "rows",
  "agencies",
  "scenario",
  "points_at",
  "labels",
  "rule",
  "method",
  "programme",
  "metric",
  "scale",
  "empty_reason",
  "x_label",
  "y_label",
  "is_lad_level_unfiltered",
  "insufficient_data",
  "entity_type",
  "unit",
  "omit",
  "catalogue",
  "title",
  "not_applicable",
  "index",
  "entity_type",
])

/** User-facing labels — never show warehouse column names. */
export const STAT_LABELS: Record<string, string> = {
  pct_covered: "People within 400m of a stop",
  n_zero_access: "LSOAs with no stop",
  pct_zero_access: "Share of LSOAs with no stop",
  pop_zero_access: "People with no nearby stop",
  n_sas: "Small Areas",
  n_desert_sas: "Small Areas beyond 400 m",
  pop_affected: "People affected",
  people_gap: "People below the national 400 m average",
  worst_region: "Worst-served region",
  gini: "Gini coefficient",
  palma: "Palma ratio",
  concentration_index: "Concentration index",
  hhi: "Operator HHI / 10,000",
  national_avg: "National average",
  top_agency_share_pct: "Top agency share",
  top_agency: "Top agency",
  n_agencies: "Agencies",
  n_routes: "Routes",
}

export const IRELAND_STAT_LABELS: Record<string, string> = {
  ...STAT_LABELS,
  n_zero_access: "Small Areas with no stop",
  pct_zero_access: "Share of Small Areas with no stop",
  n_sas: "Small Areas",
}

export const NETHERLANDS_STAT_LABELS: Record<string, string> = {
  ...STAT_LABELS,
  n_zero_access: "Buurten with no stop",
  pct_zero_access: "Share of buurten with no stop",
  n_sas: "Buurten",
  n_lsoas: "Buurten",
}

export function statLabel(key: string, country?: string): string {
  const table =
    country === "ireland"
      ? IRELAND_STAT_LABELS
      : country === "netherlands"
        ? NETHERLANDS_STAT_LABELS
        : STAT_LABELS
  if (table[key]) return table[key]
  return key
    .replace(/_/g, " ")
    .replace(/\bn_/g, "")
    .replace(/\bpct_/g, "")
    .replace(/\b\w/g, (c) => c.toUpperCase())
}

export const IRELAND_REGIONS = [
  { code: "all", name: "All Ireland" },
  { code: "carlow", name: "Carlow" },
  { code: "cavan", name: "Cavan" },
  { code: "clare", name: "Clare" },
  { code: "cork", name: "Cork" },
  { code: "donegal", name: "Donegal" },
  { code: "dublin", name: "Dublin" },
  { code: "galway", name: "Galway" },
  { code: "kerry", name: "Kerry" },
  { code: "kildare", name: "Kildare" },
  { code: "kilkenny", name: "Kilkenny" },
  { code: "laois", name: "Laois" },
  { code: "leitrim", name: "Leitrim" },
  { code: "limerick", name: "Limerick" },
  { code: "longford", name: "Longford" },
  { code: "louth", name: "Louth" },
  { code: "mayo", name: "Mayo" },
  { code: "meath", name: "Meath" },
  { code: "monaghan", name: "Monaghan" },
  { code: "offaly", name: "Offaly" },
  { code: "roscommon", name: "Roscommon" },
  { code: "sligo", name: "Sligo" },
  { code: "tipperary", name: "Tipperary" },
  { code: "waterford", name: "Waterford" },
  { code: "westmeath", name: "Westmeath" },
  { code: "wexford", name: "Wexford" },
  { code: "wicklow", name: "Wicklow" },
] as const

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

export const NETHERLANDS_REGIONS = [
  { code: "all", name: "All Netherlands" },
  { code: "drenthe", name: "Drenthe" },
  { code: "flevoland", name: "Flevoland" },
  { code: "friesland", name: "Fryslân" },
  { code: "gelderland", name: "Gelderland" },
  { code: "groningen", name: "Groningen" },
  { code: "limburg", name: "Limburg" },
  { code: "noord-brabant", name: "Noord-Brabant" },
  { code: "noord-holland", name: "Noord-Holland" },
  { code: "overijssel", name: "Overijssel" },
  { code: "utrecht", name: "Utrecht" },
  { code: "zeeland", name: "Zeeland" },
  { code: "zuid-holland", name: "Zuid-Holland" },
] as const

export function regionsForCountry(country: string): readonly { code: string; name: string }[] {
  if (country === "ireland") return IRELAND_REGIONS
  if (country === "england") return REGIONS
  if (country === "netherlands") return NETHERLANDS_REGIONS
  const label = country.charAt(0).toUpperCase() + country.slice(1)
  return [{ code: "all", name: `All ${label}` }]
}

export const IRELAND_SECTION_TITLES: Record<string, string> = {
  a1_route_density: "Route density by county",
  a2_stop_density: "Stop density by county",
  a3_walking_distance: "Population within 400m of a TFI stop",
  a4_coverage_equity: "Equity of coverage within counties",
  a5_service_deserts: "Service deserts (people beyond 400 m)",
  a6_urban_rural_gap: "Urban vs rural coverage gap",
  a7_investment_gap: "People-gap to national 400 m average",
  a8_coverage_prediction: "Coverage ~ HP and density",
  b1_frequency: "Average weekday service quality by county",
  b2_operating_hours: "Evening service (after 19:00)",
  b3_weekend_penalty: "Sunday TFI penalty",
  b4_route_frequency: "Most/least frequent TFI agencies",
  b5_frequency_deprivation: "Frequency vs Pobal HP 2022",
  c3_operator_hhi: "TFI operator HHI (0–10,000)",
  d1_coverage_deprivation: "Coverage vs Pobal HP 2022",
  f1_gini: "Gini of TFI weekday trips per capita",
  f2_disparity_ratio: "Disparity by Pobal HP decile",
  f6_equitable_regions: "Most equitable counties",
  j1_economic_value: "Priority population by county (CAF/PAG scope)",
  j2_bcr: "CAF/PAG BCR",
  j3_carbon: "Illustrative carbon (EPA Ireland / SEAI)",
  j4_investment_priority: "County × HP coverage gap",
  bsa1_franchising_readiness: "NTA programme coverage by county",
  bsa2_operator_concentration: "TFI operator concentration",
  bsa3_tier_distribution: "Local Link / BusConnects / Connecting Ireland tiers",
  ps1_freq_restoration: "Restore TFI / Local Link weekday frequency",
  ps2_evening_extension: "Evening Local Link / urban TFI",
  ps3_drt_rural: "Connecting Ireland / rural RTP",
  ps4_franchise: "Combined Connecting Ireland + BusConnects package",
  ps5_scenario_comparison: "Irish intervention comparison",
}

export const NETHERLANDS_SECTION_TITLES: Record<string, string> = {
  a1_route_density: "Route density by provincie",
  a2_stop_density: "Stop density by provincie",
  a3_walking_distance: "Population within 400 m of an OVapi stop",
  a4_coverage_equity: "Equity of coverage within provincies",
  a5_service_deserts: "Service deserts (people beyond 400 m)",
  a6_urban_rural_gap: "Urban vs rural coverage (stedelijkheid)",
  a7_investment_gap: "People-gap to national 400 m average",
  a8_coverage_prediction: "Coverage ~ SES-WOA and density",
  b1_frequency: "Average weekday service quality by provincie",
  b2_operating_hours: "Evening service (after 19:00)",
  b3_weekend_penalty: "Sunday OVapi penalty",
  b4_route_frequency: "Most/least frequent OVapi agencies",
  b5_frequency_deprivation: "Frequency vs SES-WOA",
  c3_operator_hhi: "OVapi operator HHI (0–10,000)",
  d1_coverage_deprivation: "Coverage vs SES-WOA",
  d7_deprivation_urban_rural: "SES-WOA × stedelijkheid",
  f1_gini: "Gini of OVapi weekday trips per capita",
  f2_disparity_ratio: "Disparity by SES-WOA decile",
  f6_equitable_regions: "Most equitable provincies",
  j1_economic_value: "Priority population by provincie (people-gap)",
  j2_bcr: "People-only gap (no invented PBL euro)",
  j3_carbon: "Illustrative people-gap (no invented PBL euro)",
  j4_investment_priority: "Provincie × SES-WOA coverage gap",
  bsa1_franchising_readiness: "Concession / OV-wet coverage by provincie",
  bsa2_operator_concentration: "OVapi operator concentration",
  bsa3_tier_distribution: "Concession programme tiers",
  ps1_freq_restoration: "Restore OV weekday frequency",
  ps2_evening_extension: "Evening OV",
  ps3_drt_rural: "Rural OV / flex",
  ps4_franchise: "Combined concession package",
  ps5_scenario_comparison: "Dutch intervention comparison",
}

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
  d9a_health_access: "Coverage vs health deprivation",
  d9b_employment_access: "Coverage vs employment deprivation",
  d9c_crime_access: "Service quality vs crime",
  d9d_environment_access: "Service quality vs living environment",
  d9e_barriers_access: "Coverage vs housing/services barriers",
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

export function sectionTitle(sectionId: string, country: string): string | undefined {
  if (country === "ireland" && IRELAND_SECTION_TITLES[sectionId]) return IRELAND_SECTION_TITLES[sectionId]
  if (country === "netherlands" && NETHERLANDS_SECTION_TITLES[sectionId]) {
    return NETHERLANDS_SECTION_TITLES[sectionId]
  }
  return SECTION_TITLES[sectionId]
}
