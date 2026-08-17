import { describe, expect, it } from "vitest"
import { tickerForUnknownPack } from "../tickerCountry"

describe("tickerForUnknownPack", () => {
  it("Ireland unknown pack never names England", () => {
    const blob = JSON.stringify(tickerForUnknownPack("ireland"))
    expect(blob).toMatch(/Ireland/)
    expect(blob).toMatch(/unknown network date/)
    expect(blob).not.toMatch(/England is live/)
    expect(blob).not.toMatch(/LSOA/)
  })

  it("England unknown pack does not use Ireland nouns", () => {
    const blob = JSON.stringify(tickerForUnknownPack("england"))
    expect(blob).toMatch(/England/)
    expect(blob).toMatch(/unknown network date/)
    expect(blob).not.toMatch(/Ireland/)
    expect(blob).not.toMatch(/Small Area/)
  })

  it("France unknown pack never names England or LSOA", () => {
    const blob = JSON.stringify(tickerForUnknownPack("france"))
    expect(blob).toMatch(/France/)
    expect(blob).toMatch(/unknown network date/)
    expect(blob).not.toMatch(/England is live/)
    expect(blob).not.toMatch(/LSOA/)
  })

  it("Netherlands unknown pack never names England", () => {
    const blob = JSON.stringify(tickerForUnknownPack("netherlands"))
    expect(blob).toMatch(/Netherlands/)
    expect(blob).toMatch(/unknown network date/)
    expect(blob).not.toMatch(/England is live/)
  })
})
