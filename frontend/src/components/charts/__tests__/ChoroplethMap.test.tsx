import { fireEvent, render, screen, waitFor } from "@testing-library/react"
import { describe, expect, it, vi, afterEach } from "vitest"
import ChoroplethMap from "../ChoroplethMap"
import { StrictMode } from 'react'
import maplibregl from 'maplibre-gl'

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
  it('keeps Irish projected-metre coverage in SVG and reports the actual ready state',async()=>{
    const create=vi.mocked(maplibregl.Map);create.mockClear()
    const status=vi.fn()
    vi.stubGlobal('fetch',vi.fn().mockResolvedValue({ok:true,json:async()=>({features:[{properties:{COUNTY_SLUG:'dublin',COUNTY:'Dublin'},geometry:{type:'Polygon',coordinates:[[[700000,720000],[710000,720000],[710000,730000],[700000,730000],[700000,720000]]]}}]})}))
    render(<ChoroplethMap onStatus={status} chartData={{geography:'ireland_county',color_mode:'coverage',data:[{area_code:'dublin',area_name:'Dublin',value:55}]}} />)
    const fallback=await screen.findByTestId('choropleth-svg-fallback')
    expect(fallback.querySelector('path')).toBeTruthy()
    expect(create).not.toHaveBeenCalled()
    expect(status).toHaveBeenCalledWith('ready')
  })
  it('keeps a matched missing observation unavailable rather than painting an observed zero', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: true, json: async () => ({ features: [{ properties: { RGN22CD: 'E12000005', RGN22NM: 'West Midlands' }, geometry: { type: 'Polygon', coordinates: [[[-2,52],[-1,52],[-1,53],[-2,52]]] } }] }) }))
    render(<ChoroplethMap chartData={{ geography: 'region', color_mode: 'reach_rate', data: [{ area_code: 'E12000005', area_name: 'West Midlands', value: null }] }} />)
    const map = await screen.findByTestId('choropleth-svg-fallback')
    expect(map.querySelector('path')).toHaveAttribute('fill', '#d9d7d2')
    expect(map.querySelector('title')?.textContent).toContain('Unavailable')
  })
  it('opens the real area from the SVG map with mouse and keyboard', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: true, json: async () => ({ features: [{ properties: { RGN22CD: 'E12000002', RGN22NM: 'North West' }, geometry: { type: 'Polygon', coordinates: [[[-3, 53], [-2, 53], [-2, 54], [-3, 54], [-3, 53]]] } }] }) }))
    const onAreaClick = vi.fn()
    render(<ChoroplethMap onAreaClick={onAreaClick} chartData={{ geography: 'region', color_mode: 'coverage', metric_label: 'Coverage (%)', data: [{ area_code: 'E12000002', area_name: 'North West', value: 83.1 }] }} />)
    const region = await screen.findByRole('button', { name: /North West: 83.1%/ })
    fireEvent.click(region)
    fireEvent.keyDown(region, { key: 'Enter' })
    expect(onAreaClick.mock.calls).toEqual([['E12000002'], ['E12000002']])
  })
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
  it('uses a fixed percentage scale for Reach rates and keeps zero as observed', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: true, json: async () => ({ features: [{ properties: { RGN22CD: 'E12000005', RGN22NM: 'West Midlands' }, geometry: { type: 'Polygon', coordinates: [[[-2,52],[-1,52],[-1,53],[-2,52]]] } }] }) }))
    render(<ChoroplethMap chartData={{ geography: 'region', color_mode: 'reach_rate', data: [{ area_code: 'E12000005', area_name: 'West Midlands', value: 0 }] }} />)
    await waitFor(() => expect(screen.getByTestId('choropleth-svg-fallback')).toBeTruthy())
    const map = screen.getByTestId('choropleth-svg-fallback')
    expect(map.querySelector('path')).toHaveAttribute('fill', '#4f8050')
    expect(map.querySelector('title')?.textContent).toContain('0%')
  })
  it('does not mount a map from a discarded StrictMode boundary request', async () => {
    const create = vi.mocked(maplibregl.Map)
    create.mockClear()
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: true, json: async () => ({ features: [{ properties: { RGN22CD: 'E12000005', RGN22NM: 'West Midlands' }, geometry: { type: 'Polygon', coordinates: [[[-2,52],[-1,52],[-1,53],[-2,52]]] } }] }) }))
    render(<StrictMode><ChoroplethMap chartData={{ geography: 'region', color_mode: 'coverage', data: [{ area_code: 'E12000005', area_name: 'West Midlands', value: 80 }] }} /></StrictMode>)
    await waitFor(() => expect(create).toHaveBeenCalled())
    expect(create).toHaveBeenCalledTimes(1)
  })
})
