import { render, screen } from "@testing-library/react"
import { describe, it, expect, vi } from "vitest"
import { Suspense } from "react"

// Stub heavy chart libs that don't work in jsdom
vi.mock("@observablehq/plot", () => ({ plot: vi.fn(() => document.createElement("div")) }))
vi.mock("maplibre-gl", () => ({ Map: vi.fn(), Popup: vi.fn(() => ({ setLngLat: vi.fn().mockReturnThis(), setHTML: vi.fn().mockReturnThis(), addTo: vi.fn(), remove: vi.fn() })) }))
vi.mock("maplibre-gl/dist/maplibre-gl.css", () => ({}))

import { ChartRenderer } from "../ChartRenderer"

describe("ChartRenderer", () => {
  it("renders null for empty chartData", () => {
    const { container } = render(<ChartRenderer chartData={{}} />)
    expect(container.firstChild).toBeNull()
  })

  it("renders DataTable fallback for unknown chart type", async () => {
    render(
      <Suspense fallback={<div>loading</div>}>
        <ChartRenderer chartData={{ type: "unknown_type", data: [{ region: "South West", value: 42 }] }} />
      </Suspense>,
    )
    // DataTable renders a table element
    expect(screen.getByRole("table")).toBeTruthy()
  })

  it("wraps valid chart types in chart-animate-in div", () => {
    const { container } = render(
      <Suspense fallback={<div>loading</div>}>
        <ChartRenderer chartData={{ type: "horizontal_bar", data: [{ label: "A", value: 1 }] }} />
      </Suspense>,
    )
    expect(container.querySelector(".chart-animate-in")).toBeTruthy()
  })

  it("returns null for null chartData", () => {
    // @ts-expect-error — testing runtime null guard
    const { container } = render(<ChartRenderer chartData={null} />)
    expect(container.firstChild).toBeNull()
  })

  it("renders KpiTiles for kpi_tiles chart type", async () => {
    render(
      <Suspense fallback={<div>loading</div>}>
        <ChartRenderer
          chartData={{
            type: "kpi_tiles",
            title: "Frequency Restoration",
            tiles: [
              { label: "Population affected", value: 5_000_000, unit: "people" },
              { label: "Annual cost", value: 50, unit: "£m/yr" },
              { label: "CO₂ saved", value: 1200, unit: "t/yr" },
            ],
          }}
        />
      </Suspense>,
    )
    expect(await screen.findByText("Population affected")).toBeTruthy()
  })

  it("renders DataTable for table chart type", () => {
    render(
      <ChartRenderer
        chartData={{
          type: "table",
          title: "Scenario comparison",
          columns: ["Scenario", "Population affected"],
          data: [{ Scenario: "A", "Population affected": 5_000_000 }],
        }}
      />,
    )
    expect(screen.getByRole("table")).toBeTruthy()
    expect(screen.getByText("Scenario")).toBeTruthy()
  })
})
