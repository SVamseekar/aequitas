import { describe, expect, it, vi } from "vitest"
import { render, screen } from "@testing-library/react"
import { MemoryRouter, Route, Routes } from "react-router"
import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import ReachPage from "../ReachPage"
import { withSearch } from "@/lib/appRoutes"

const bandsState = {
  isLoading: false,
  data: { empty: true, empty_reason: "fixture" } as Record<string, unknown> | undefined,
}

vi.mock("@/api/hooks", async () => {
  const actual = await vi.importActual<typeof import("@/api/hooks")>("@/api/hooks")
  return {
    ...actual,
    useReachBands: () => bandsState,
    useReach: () => ({ isLoading: false, data: { available: false, geographies: [], note: "not precomputed" } }),
    useScore: () => ({ data: { score: 54, n_areas: 10 } }),
  }
})

function renderAt(path: string) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={client}>
      <MemoryRouter initialEntries={[path]}>
        <Routes>
          <Route path="/app/:country/reach" element={<ReachPage />} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  )
}

describe("Reach routes", () => {
  it("is its own page, not a dimension dump", () => {
    renderAt("/app/england/reach?region=E12000005&urban_rural=rural")
    expect(screen.getByTestId("reach-page")).toBeTruthy()
    expect(screen.getByText(/Not official PTAL/i)).toBeTruthy()
  })

  it("Netherlands reach is a bands page", () => {
    renderAt("/app/netherlands/reach")
    expect(screen.queryByText(/Netherlands pack is not built yet/i)).toBeNull()
  })

  it("London × rural is one sentence", () => {
    renderAt("/app/england/reach?region=E12000007&urban_rural=rural")
    expect(screen.getByText(/no rural LSOAs/i)).toBeTruthy()
  })

  it("withSearch keeps filters on the reach path", () => {
    expect(withSearch("/app/england/reach", "region=E12000005&urban_rural=rural")).toEqual({
      pathname: "/app/england/reach",
      search: "?region=E12000005&urban_rural=rural",
    })
  })

  it("does not mount the choropleth with empty data while bands are loading", () => {
    bandsState.isLoading = true
    bandsState.data = undefined
    renderAt("/app/england/reach")
    expect(screen.queryByRole("img", { name: /bands/i })).toBeNull()
    expect(screen.queryByText(/boundaries could not be loaded/i)).toBeNull()
    bandsState.isLoading = false
    bandsState.data = { empty: true, empty_reason: "fixture" }
  })

  it("says so when the map payload has no rows", () => {
    bandsState.isLoading = false
    bandsState.data = {
      empty: false,
      label: "Aequitas service band (no travel-time model)",
      narrative: "In England, 1 LSOA is assigned a band.",
      formula: "service band",
      map: { geography: "region", metric_label: "band", data: [] },
      people_by_band_decile: [],
      band_totals: [],
    }
    renderAt("/app/england/reach")
    expect(screen.getByText(/could not be loaded|No map areas/i)).toBeTruthy()
    bandsState.data = { empty: true, empty_reason: "fixture" }
  })
})
