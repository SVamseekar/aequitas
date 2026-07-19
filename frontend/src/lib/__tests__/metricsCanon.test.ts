import { describe, expect, it } from "vitest"
import {
  METRICS_CANON,
  authHeadlineStats,
  formatConcentrationIndex,
  formatGini,
  formatPalma,
  headlineInequalityStats,
  packEquityDisplayValue,
  scaleLine,
  scaleStats,
  tickerFallbackMetrics,
} from "../metricsCanon"

describe("METRICS_CANON", () => {
  it("locks section count at 55 (not legacy 51)", () => {
    expect(METRICS_CANON.sections).toBe(55)
  })

  it("locks Gini at 0.5741", () => {
    expect(METRICS_CANON.gini).toBe(0.5741)
    expect(formatGini()).toBe("0.5741")
  })

  it("locks scale and equity pack from ground truth", () => {
    expect(METRICS_CANON.trips).toBe(1_752_443)
    expect(METRICS_CANON.tripsDisplay).toBe("1.75M")
    expect(METRICS_CANON.routes).toBe(13_099)
    expect(METRICS_CANON.stops).toBe(274_719)
    expect(METRICS_CANON.lsoas).toBe(33_755)
    expect(METRICS_CANON.population).toBe(56_490_056)
    expect(METRICS_CANON.populationDisplay).toBe("56.5M")
    expect(METRICS_CANON.palma).toBe(5.702)
    expect(METRICS_CANON.concentrationIndex).toBe(0.1358)
    expect(METRICS_CANON.qualityChecks).toBe(103)
    expect(METRICS_CANON.qualityFails).toBe(0)
    expect(METRICS_CANON.eveningIsolatedPct).toBe(15.4)
    expect(METRICS_CANON.sundayDesertPct).toBe(20.0)
    expect(METRICS_CANON.rfR2).toBe(0.472)
    expect(METRICS_CANON.dimensions).toBe(8)
    expect(METRICS_CANON.filterCombos).toBe(30)
  })

  it("formats Palma and CI with GT packing", () => {
    expect(formatPalma()).toBe("5.702×")
    expect(formatConcentrationIndex()).toBe("+0.1358")
  })

  it("builds scale line and scale stats from canon", () => {
    const line = scaleLine()
    expect(line).toContain("1.75M")
    expect(line).toContain("13,099")
    expect(line).toContain("274,719")
    expect(line).toContain("33,755")
    expect(line).toContain("56.5M")

    const scale = scaleStats()
    expect(scale).toHaveLength(4)
    expect(scale.map((s) => s.label)).toEqual([
      "GTFS trips",
      "Bus stops",
      "Routes",
      "LSOAs",
    ])
  })

  it("headline and auth stats use Gini 0.5741", () => {
    const headlines = headlineInequalityStats()
    expect(headlines[0].value).toBe("0.5741")
    expect(headlines.some((h) => h.value.includes("5.702"))).toBe(true)

    const auth = authHeadlineStats()
    expect(auth[0].value).toBe("0.5741")
    expect(auth[1].value).toBe("5.702×")
  })

  it("packs truncated warehouse equity floats to GT display", () => {
    expect(packEquityDisplayValue("gini", 0.574)).toBe("0.5741")
    expect(packEquityDisplayValue("palma", 5.7)).toBe("5.702×")
    expect(packEquityDisplayValue("concentration_index", 0.1344)).toBe("+0.1358")
    // Far from GT → leave to caller
    expect(packEquityDisplayValue("gini", 0.4)).toBeNull()
    expect(packEquityDisplayValue("mean_sqi", 65.4)).toBeNull()
  })

  it("ticker fallback never uses truncated Gini", () => {
    const ticker = tickerFallbackMetrics()
    const gini = ticker.find((m) => m.key === "gini")
    expect(gini?.value).toBe("0.5741")
    expect(ticker.find((m) => m.key === "palma")?.value).toBe("5.702×")
  })
})
