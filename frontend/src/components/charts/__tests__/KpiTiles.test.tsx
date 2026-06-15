import { render, screen } from "@testing-library/react"
import { describe, it, expect } from "vitest"

import KpiTiles from "../KpiTiles"

describe("KpiTiles", () => {
  it("renders a tile for each entry with label, value, and unit", () => {
    render(
      <KpiTiles
        chartData={{
          type: "kpi_tiles",
          title: "Frequency Restoration",
          tiles: [
            { label: "Population affected", value: 5_000_000, unit: "people" },
            { label: "Annual cost", value: 50, unit: "£m/yr" },
            { label: "CO₂ saved", value: 1200, unit: "t/yr" },
          ],
        }}
      />,
    )

    expect(screen.getByText("Population affected")).toBeTruthy()
    expect(screen.getByText("5,000,000")).toBeTruthy()
    expect(screen.getByText("people")).toBeTruthy()
    expect(screen.getByText("Annual cost")).toBeTruthy()
    expect(screen.getByText("50")).toBeTruthy()
    expect(screen.getByText("£m/yr")).toBeTruthy()
    expect(screen.getByText("CO₂ saved")).toBeTruthy()
    expect(screen.getByText("1,200")).toBeTruthy()
    expect(screen.getByText("t/yr")).toBeTruthy()
  })

  it("renders fallback message when tiles array is empty", () => {
    render(<KpiTiles chartData={{ type: "kpi_tiles", title: "Empty", tiles: [] }} />)
    expect(screen.getByText("No data available")).toBeTruthy()
  })

  it("renders a proportion bar when chartData.proportion is present", () => {
    const { container } = render(
      <KpiTiles
        chartData={{
          type: "kpi_tiles",
          title: "Frequency Restoration",
          tiles: [
            { label: "Population affected", value: 5_000_000, unit: "people" },
          ],
          proportion: {
            type: "grouped_bar",
            title: "Frequency Restoration — population affected vs England total",
            categories: ["England (56.5m)"],
            series: [
              { name: "Population affected", values: [5_000_000] },
              { name: "Remaining population", values: [51_490_056] },
            ],
          },
        }}
      />,
    )

    expect(screen.getAllByText("Population affected").length).toBeGreaterThan(0)
    expect(container.querySelector("svg")).toBeTruthy()
  })

  it("omits the proportion bar when chartData.proportion is absent", () => {
    const { container } = render(
      <KpiTiles
        chartData={{
          type: "kpi_tiles",
          title: "Frequency Restoration",
          tiles: [
            { label: "Population affected", value: 5_000_000, unit: "people" },
          ],
        }}
      />,
    )

    expect(container.querySelector("svg")).toBeNull()
  })
})
