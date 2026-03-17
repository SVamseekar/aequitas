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
})
