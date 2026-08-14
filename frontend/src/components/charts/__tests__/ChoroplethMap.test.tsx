import { render, screen, waitFor } from "@testing-library/react"
import { describe, expect, it, vi, afterEach } from "vitest"
import ChoroplethMap from "../ChoroplethMap"

vi.mock("maplibre-gl", () => ({
  default: {
    Map: vi.fn(() => ({
      on: vi.fn(),
      fitBounds: vi.fn(),
      remove: vi.fn(),
      getCanvas: () => ({ style: {} }),
    })),
    Popup: vi.fn(() => ({
      setLngLat: vi.fn().mockReturnThis(),
      setDOMContent: vi.fn().mockReturnThis(),
      addTo: vi.fn(),
      remove: vi.fn(),
    })),
  },
}))
vi.mock("maplibre-gl/dist/maplibre-gl.css", () => ({}))

afterEach(() => {
  vi.unstubAllGlobals()
})

describe("ChoroplethMap empty / unmatched", () => {
  it("does not paint a hollow box when data is empty — shows the load-failure sentence", async () => {
    render(
      <ChoroplethMap
        chartData={{
          type: "choropleth",
          geography: "region",
          metric_label: "band",
          data: [],
          title: "Bands — England",
        }}
      />,
    )
    expect(await screen.findByText(/Map boundaries could not be loaded/i)).toBeTruthy()
  })

  it("sets mapUnavailable when GeoJSON matches zero features", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: true,
        json: async () => ({
          features: [
            { properties: { RGN22CD: "E12000001", RGN22NM: "North East" }, geometry: { type: "Polygon", coordinates: [] } },
          ],
        }),
      }),
    )
    render(
      <ChoroplethMap
        chartData={{
          type: "choropleth",
          geography: "region",
          metric_label: "band",
          data: [{ area_code: "Unknown", area_name: "Unknown", value: 6 }],
          title: "Bands",
        }}
      />,
    )
    await waitFor(() => {
      expect(screen.getByText(/Map boundaries could not be loaded/i)).toBeTruthy()
    })
  })

  it("matches Fryslân GeoJSON name friesland, not the Frisian label", async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({
        features: [
          {
            properties: { name: "friesland", statnaam: "Fryslân", statcode: "PV21" },
            geometry: {
              type: "Polygon",
              coordinates: [[[5.2, 53.0], [6.2, 53.0], [6.2, 53.4], [5.2, 53.4], [5.2, 53.0]]],
            },
          },
        ],
      }),
    })
    vi.stubGlobal("fetch", fetchMock)
    render(
      <ChoroplethMap
        chartData={{
          type: "choropleth",
          geography: "netherlands_provincie",
          metric_label: "People",
          data: [{ area_code: "friesland", area_name: "Fryslân", value: 64.5 }],
          title: "Fryslân",
        }}
      />,
    )
    await waitFor(() => {
      expect(screen.getByTestId("choropleth-svg-fallback").querySelector("path")).toBeTruthy()
    })
    expect(screen.queryByText(/Map boundaries could not be loaded/i)).toBeNull()
    const url = String(fetchMock.mock.calls[0]?.[0] ?? "")
    expect(url).toContain("netherlands_provincies.geojson")
  })

  it("loads Ireland county GeoJSON when area codes are county slugs", async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({
        features: [
          {
            properties: { COUNTY_SLUG: "dublin", COUNTY: "Dublin" },
            geometry: { type: "Polygon", coordinates: [[[-6.3, 53.3], [-6.2, 53.3], [-6.2, 53.4], [-6.3, 53.4], [-6.3, 53.3]]] },
          },
        ],
      }),
    })
    vi.stubGlobal("fetch", fetchMock)
    render(
      <ChoroplethMap
        chartData={{
          type: "choropleth",
          metric_label: "People",
          data: [{ area_code: "dublin", area_name: "Dublin", value: 100 }],
          title: "Deserts — Ireland",
        }}
      />,
    )
    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalled()
    })
    const url = String(fetchMock.mock.calls[0]?.[0] ?? "")
    expect(url).toContain("ireland_counties.geojson")
  })

  it("paints an SVG fallback for England ITL1 without waiting for MapLibre", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: true,
        json: async () => ({
          features: [
            {
              properties: { RGN22CD: "E12000007", RGN22NM: "London" },
              geometry: {
                type: "Polygon",
                coordinates: [[[-0.5, 51.3], [0.2, 51.3], [0.2, 51.7], [-0.5, 51.7], [-0.5, 51.3]]],
              },
            },
          ],
        }),
      }),
    )
    render(
      <ChoroplethMap
        chartData={{
          type: "choropleth",
          geography: "region",
          metric_label: "People",
          data: [{ area_code: "E12000007", area_name: "London", value: 100 }],
          title: "Deserts — England",
        }}
      />,
    )
    await waitFor(() => {
      expect(screen.getByTestId("choropleth-svg-fallback")).toBeTruthy()
    })
    expect(screen.getByTestId("choropleth-svg-fallback").querySelector("path")).toBeTruthy()
  })
})
