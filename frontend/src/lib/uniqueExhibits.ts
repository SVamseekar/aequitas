import type { SectionItem } from "@/api/types"

const CORRELATION_MATRIX_ID = "d1_coverage_deprivation"
const CORRELATION_SCATTER_IDS = new Set([
  "d2_coverage_unemployment",
  "d3_coverage_car",
  "d4_coverage_elderly",
  "d5_coverage_income",
  "d9a_health_access",
  "d9b_employment_access",
  "d9c_crime_access",
  "d9d_environment_access",
  "d9e_barriers_access",
])

const EQUITY_KEEP = new Set(["f1_gini", "f2_disparity_ratio", "f3_ethnic_access", "f5_rural_penalty"])
const ACCESS_KEEP = new Set(["a3_walking_distance", "a5_service_deserts", "a6_urban_rural_gap"])
const NETWORK_KEEP = new Set(["c1_route_length", "c2_stops_per_route", "c3_operator_hhi", "c6_route_archetypes"])
const ECONOMY_KEEP = new Set(["j1_economic_value", "j2_bcr", "j3_carbon"])

const IRELAND_ACCESS_KEEP = new Set([
  "a1_route_density",
  "a2_stop_density",
  "a3_walking_distance",
  "a4_coverage_equity",
  "a5_service_deserts",
  "a6_urban_rural_gap",
  "a7_investment_gap",
  "a8_coverage_prediction",
])
const IRELAND_EQUITY_KEEP = new Set(["f1_gini", "f2_disparity_ratio", "f3_ethnic_access", "f5_rural_penalty", "f6_equitable_regions"])
const IRELAND_NETWORK_KEEP = new Set([
  "c1_route_length",
  "c2_stops_per_route",
  "c3_operator_hhi",
  "c4_urban_rural_routes",
  "c5_length_vs_frequency",
  "c6_route_archetypes",
  "c7_network_topology",
])
const IRELAND_ECONOMY_KEEP = new Set(["j1_economic_value", "j2_bcr", "j3_carbon", "j4_investment_priority"])

/** Keep unique exhibits per question — warehouse still holds every metric. */
export function selectUniqueSections(
  dimensionId: string,
  sections: SectionItem[],
  country = "england",
): SectionItem[] {
  const ireland = country === "ireland" || country === "netherlands"
  if (dimensionId === "correlations") {
    if (ireland) {
      const matrix = sections.filter((s) => s.section_id === "d7_deprivation_urban_rural")
      const scatter = sections.filter((s) => s.section_id === CORRELATION_MATRIX_ID)
      const extra = sections.filter((s) => s.section_id === "d8_feature_importance")
      const omits = sections.filter((s) => s.stats?.omit).slice(0, 1)
      return [...matrix, ...scatter, ...extra, ...omits]
    }
    const matrix = sections.filter((s) => s.section_id === CORRELATION_MATRIX_ID)
    const scatter = sections.find(
      (s) => CORRELATION_SCATTER_IDS.has(s.section_id) && !s.stats?.omit,
    )
    const extra = sections.filter(
      (s) => s.section_id.startsWith("g") || s.section_id === "d6_transport_poverty" || s.section_id === "d8_feature_importance",
    )
    return [...matrix, ...(scatter ? [scatter] : []), ...extra]
  }
  if (dimensionId === "equity") {
    return sections.filter((s) => (ireland ? IRELAND_EQUITY_KEEP : EQUITY_KEEP).has(s.section_id))
  }
  if (dimensionId === "accessibility") {
    return sections.filter((s) => (ireland ? IRELAND_ACCESS_KEEP : ACCESS_KEEP).has(s.section_id))
  }
  if (dimensionId === "route_network") {
    const keep = ireland ? IRELAND_NETWORK_KEEP : NETWORK_KEEP
    const filtered = sections.filter((s) => keep.has(s.section_id))
    if (country === "netherlands") {
      const order = [
        "c3_operator_hhi",
        "c1_route_length",
        "c2_stops_per_route",
        "c4_urban_rural_routes",
        "c5_length_vs_frequency",
        "c6_route_archetypes",
        "c7_network_topology",
      ]
      const byId = new Map(filtered.map((s) => [s.section_id, s]))
      return order.map((id) => byId.get(id)).filter((s): s is SectionItem => Boolean(s))
    }
    return filtered
  }
  if (country === "netherlands" && dimensionId === "scenarios") {
    const order = [
      "ps5_scenario_comparison",
      "ps1_freq_restoration",
      "ps2_evening_extension",
      "ps3_drt_rural",
      "ps4_franchise",
    ]
    const byId = new Map(sections.map((s) => [s.section_id, s]))
    return order.map((id) => byId.get(id)).filter((s): s is SectionItem => Boolean(s))
  }
  if (dimensionId === "economic") {
    return sections.filter((s) => (ireland ? IRELAND_ECONOMY_KEEP : ECONOMY_KEEP).has(s.section_id))
  }
  if (ireland && dimensionId === "bus_services_act") {
    return sections.filter((s) => s.section_id !== "bsa2_operator_concentration")
  }
  return sections
}

export function isUrbanDrtEmpty(sectionId: string, urbanRural: string): boolean {
  return sectionId === "ps3_drt_rural" && urbanRural === "urban"
}

export function isLondonRural(region: string, urbanRural: string): boolean {
  return region === "E12000007" && urbanRural === "rural"
}

/** Drop only the DRT card on an urban filter — keep the rest of Scenarios. */
export function filterImpossibleSections(
  sections: SectionItem[],
  urbanRural: string,
): SectionItem[] {
  return sections.filter((s) => !isUrbanDrtEmpty(s.section_id, urbanRural))
}
