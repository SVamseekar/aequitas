import { describe, expect, it } from "vitest"
import { filterSentence, formatInCountryScore } from "../scoreFormat"
import { compareMetricLabel } from "../compareLabels"

describe("formatInCountryScore", () => {
  it("keeps one decimal when bus vs all would otherwise collide", () => {
    expect(formatInCountryScore(70.6)).toBe("70.6")
    expect(formatInCountryScore(72.0)).toBe("72.0")
    expect(formatInCountryScore(80)).toBe("80.0")
  })
  it("renders empty as em dash", () => {
    expect(formatInCountryScore(null)).toBe("—")
    expect(formatInCountryScore(Number.NaN)).toBe("—")
  })
})

describe("filterSentence", () => {
  it("names region and rural", () => {
    expect(filterSentence("West Midlands", "Rural")).toBe("West Midlands, rural")
    expect(filterSentence("All Ireland", "All Areas")).toBe("Ireland")
    expect(filterSentence("Cork", "Urban")).toBe("Cork, urban")
  })
})

describe("compareMetricLabel", () => {
  it("uses English not snake_case", () => {
    expect(compareMetricLabel("pct_within_400m")).toBe("People within 400 m of a stop")
    expect(compareMetricLabel("in_country_score")).toBe("In-country score")
  })
})
