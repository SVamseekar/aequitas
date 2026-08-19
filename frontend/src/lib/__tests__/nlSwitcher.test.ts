import { describe, expect, it } from "vitest"
import { withSearch } from "../appRoutes"
import { NETHERLANDS_DIMENSIONS, NETHERLANDS_REGIONS, dimensionsForCountry, regionsForCountry } from "../constants"

describe("Netherlands switcher", () => {
  it("lists 12 provincies and local dimension titles", () => {
    expect(regionsForCountry("netherlands")).toEqual(NETHERLANDS_REGIONS)
    expect(NETHERLANDS_REGIONS.some((r) => r.code === "noord-holland")).toBe(true)
    expect(NETHERLANDS_REGIONS.some((r) => (r.code as string) === "E12000007")).toBe(false)
    const dims = dimensionsForCountry("netherlands")
    expect(dims).toBe(NETHERLANDS_DIMENSIONS)
    expect(dims.find((d) => d.id === "policy")?.name).toMatch(/OV-wet|Concession/)
    expect(dims.find((d) => d.id === "policy")?.name).not.toMatch(/Bus Services Act|NTA/)
  })

  it("drops E12 and Irish counties and keeps mode", () => {
    const { search } = withSearch("/app/netherlands", "?region=E12000007&mode=all&dublin=1")
    const p = new URLSearchParams(search)
    expect(p.get("region")).toBe("all")
    expect(p.get("mode")).toBe("all")
    const ie = withSearch("/app/netherlands", "?region=dublin")
    expect(new URLSearchParams(ie.search).get("region")).toBe("all")
  })
})
