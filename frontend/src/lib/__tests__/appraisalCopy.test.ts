import { describe, expect, it } from "vitest"
import {
  FRANCE_SECTION_TITLES,
  IRELAND_SECTION_TITLES,
  NETHERLANDS_SECTION_TITLES,
  dimensionsForCountry,
  sectionTitle,
} from "../constants"

const BANNED = /\bTAG\b|\bBSA\b|\bIMD\b|\bLSOA\b|3\.5%/

function economyPolicyText(country: "ireland" | "netherlands" | "france"): string {
  const dims = dimensionsForCountry(country).filter((d) => d.id === "economy" || d.id === "policy")
  const titles = ["j1_economic_value", "j2_bcr", "j3_carbon", "j4_investment_priority", "bsa1_franchising_readiness", "bsa3_tier_distribution"]
    .map((id) => sectionTitle(id, country) ?? "")
  return [...dims.map((d) => `${d.name} ${d.description}`), ...titles].join("\n")
}

describe("non-England economy and policy copy", () => {
  it("keeps TAG, BSA, IMD, LSOA, and 3.5% off Ireland, Netherlands, and France", () => {
    for (const country of ["ireland", "netherlands", "france"] as const) {
      expect(economyPolicyText(country)).not.toMatch(BANNED)
    }
  })

  it("names the national programme on the policy card", () => {
    expect(IRELAND_SECTION_TITLES.bsa1_franchising_readiness).toMatch(/Connecting Ireland/)
    expect(IRELAND_SECTION_TITLES.bsa1_franchising_readiness).toMatch(/BusConnects/)
    expect(IRELAND_SECTION_TITLES.bsa1_franchising_readiness).toMatch(/Local Link/)
    expect(IRELAND_SECTION_TITLES.bsa1_franchising_readiness).toMatch(/PSO/)
    expect(NETHERLANDS_SECTION_TITLES.bsa1_franchising_readiness).toMatch(/OV-wet/)
    expect(NETHERLANDS_SECTION_TITLES.bsa1_franchising_readiness).toMatch(/provincie concessies/)
    expect(FRANCE_SECTION_TITLES.bsa1_franchising_readiness).toMatch(/LOM/)
    expect(FRANCE_SECTION_TITLES.bsa1_franchising_readiness).toMatch(/AOM/)
    expect(FRANCE_SECTION_TITLES.bsa1_franchising_readiness).toMatch(/SPC/)
  })

  it("keeps England TAG and BSA on the England doors", () => {
    const england = dimensionsForCountry("england")
    expect(england.find((d) => d.id === "economy")?.description).toMatch(/TAG/)
    expect(england.find((d) => d.id === "policy")?.description).toMatch(/Bus Services Act 2025/)
  })
})
