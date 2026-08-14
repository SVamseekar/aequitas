import { describe, expect, it } from "vitest"
import { filterImpossibleSections, isLondonRural, selectUniqueSections } from "../uniqueExhibits"
import type { SectionItem } from "@/api/types"

function sec(id: string): SectionItem {
  return {
    section_id: id,
    dimension: "correlations",
    stats: { r: 0.2 },
    chart_data: {},
    narrative: "n",
    suppressed: false,
  }
}

describe("selectUniqueSections", () => {
  it("keeps one matrix and one scatter for correlations", () => {
    const out = selectUniqueSections("correlations", [
      sec("d1_coverage_deprivation"),
      sec("d2_coverage_unemployment"),
      sec("d3_coverage_car"),
      sec("g4_shap"),
    ])
    const ids = out.map((s) => s.section_id)
    expect(ids).toContain("d1_coverage_deprivation")
    expect(ids).toContain("d2_coverage_unemployment")
    expect(ids).not.toContain("d3_coverage_car")
    expect(ids).toContain("g4_shap")
  })

  it("drops only rural DRT on an urban filter", () => {
    const kept = filterImpossibleSections(
      [sec("ps1_freq_restoration"), sec("ps3_drt_rural"), sec("ps5_scenario_comparison")],
      "urban",
    )
    expect(kept.map((s) => s.section_id)).toEqual(["ps1_freq_restoration", "ps5_scenario_comparison"])
  })

  it("flags London rural", () => {
    expect(isLondonRural("E12000007", "rural")).toBe(true)
    expect(isLondonRural("E12000007", "urban")).toBe(false)
  })

  it("Ireland correlations keep HP matrix plus d1 scatter", () => {
    const omit = {
      ...sec("d2_coverage_unemployment"),
      stats: { omit: true },
    }
    const out = selectUniqueSections(
      "correlations",
      [
        sec("d7_deprivation_urban_rural"),
        sec("d1_coverage_deprivation"),
        omit,
        { ...sec("d3_coverage_car"), stats: { omit: true } },
        sec("g4_shap"),
        sec("d8_feature_importance"),
      ],
      "ireland",
    )
    const ids = out.map((s) => s.section_id)
    expect(ids).toContain("d7_deprivation_urban_rural")
    expect(ids).toContain("d1_coverage_deprivation")
    expect(ids).toContain("d8_feature_importance")
    expect(ids.filter((id) => id === "d2_coverage_unemployment")).toHaveLength(1)
    expect(ids).not.toContain("d3_coverage_car")
    expect(ids).not.toContain("g4_shap")
  })

  it("puts OVapi HHI first on Netherlands Network", () => {
    const out = selectUniqueSections(
      "route_network",
      [sec("c1_route_length"), sec("c3_operator_hhi"), sec("c2_stops_per_route")],
      "netherlands",
    )
    expect(out.map((s) => s.section_id)[0]).toBe("c3_operator_hhi")
  })

  it("keeps a single HHI exhibit on the network page", () => {
    const out = selectUniqueSections("route_network", [
      sec("c3_operator_hhi"),
      sec("c1_route_length"),
      sec("c4_urban_rural_routes"),
    ])
    expect(out.map((s) => s.section_id)).toEqual(["c3_operator_hhi", "c1_route_length"])
  })
})
