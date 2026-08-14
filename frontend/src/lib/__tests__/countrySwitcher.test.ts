import { describe, expect, it } from "vitest"
import { COUNTRIES, IRELAND_REGIONS, regionsForCountry } from "../constants"
import { appPath, withSearch } from "../appRoutes"

describe("country switcher", () => {
  it("marks Ireland pack ready and NL/FR empty", () => {
    expect(COUNTRIES.find((c) => c.code === "ireland")?.packReady).toBe(true)
    expect(COUNTRIES.find((c) => c.code === "netherlands")?.packReady).toBe(true)
    expect(COUNTRIES.find((c) => c.code === "france")?.packReady).toBe(false)
  })

  it("Ireland region list is counties, All Ireland, no E12", () => {
    const regions = regionsForCountry("ireland")
    expect(regions[0]).toEqual({ code: "all", name: "All Ireland" })
    expect(regions.some((r) => r.code === "cork")).toBe(true)
    expect(regions.some((r) => String(r.code).startsWith("E12"))).toBe(false)
    expect(IRELAND_REGIONS.length).toBe(27)
  })

  it("switching country conceptually drops pack (withSearch does not invent a pack)", () => {
    const kept = withSearch("/app/ireland/time", "region=all&urban_rural=all")
    expect(kept.search).not.toContain("pack=")
  })

  it("withSearch keeps filters and country path stays ireland", () => {
    expect(withSearch(appPath("ireland", "reach"), "region=cork&urban_rural=rural")).toEqual({
      pathname: "/app/ireland/reach",
      search: "?region=cork&urban_rural=rural",
    })
    expect(appPath("ireland", "access")).not.toContain("E12")
  })

  it("warehouse economic slug is not a product path", () => {
    expect(appPath("ireland", "economy")).toBe("/app/ireland/economy")
    expect(appPath("ireland", "economic")).not.toBe("/app/ireland/economy")
  })
})
