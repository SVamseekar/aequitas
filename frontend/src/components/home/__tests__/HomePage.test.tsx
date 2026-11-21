import { describe, expect, it, vi } from "vitest"
import { render, screen } from "@testing-library/react"
import { MemoryRouter, Route, Routes } from "react-router"
import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { HomePage } from "../HomePage"

const mapState = { isLoading: false, data: undefined as unknown, error: null }
const overviewState = {
  data: undefined as unknown,
  isLoading: false,
  error: null,
}

vi.mock("@/api/hooks", async () => {
  const actual = await vi.importActual<typeof import("@/api/hooks")>("@/api/hooks")
  return {
    ...actual,
    useOverview: () => overviewState,
    useMapLayer: () => mapState,
  }
})

function renderAt(path: string) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={client}>
      <MemoryRouter initialEntries={[path]}>
        <Routes>
          <Route path="/app/:country" element={<HomePage />} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  )
}

describe("HomePage empty packs", () => {
  it("treats France as a live pack, not an empty-pack banner", () => {
    overviewState.isLoading = false
    overviewState.error = null
    overviewState.data = { score: 47.7, score_note: "ok", dimensions: [] }
    mapState.isLoading = false
    mapState.data = { empty: false, features: [] }
    mapState.error = null
    renderAt("/app/france")
    expect(screen.queryByText(/France pack is not built yet/i)).toBeNull()
    expect(screen.getByText(/Where the bus fails people/i)).toBeTruthy()
  })
})

describe("HomePage map race", () => {
  it("does not mount the map with empty data while the layer is loading", () => {
    overviewState.isLoading = false
    overviewState.error = null
    overviewState.data = {
      score: 80,
      score_note: "ok",
      dimensions: [],
    }
    mapState.isLoading = true
    mapState.data = undefined
    mapState.error = null
    renderAt("/app/england")
    expect(screen.getByTestId("home-loading")).toBeTruthy()
    expect(screen.queryByText(/Deserts/)).toBeNull()
  })
})

describe('Overview empty geography',()=>{
 it('keeps country, region, area and network context in the reference Explore navigation',()=>{
  overviewState.isLoading=false;overviewState.error=null;overviewState.data={score:55.5,dimensions:[]}
  mapState.isLoading=false;mapState.error=null;mapState.data={empty:true,data:[]}
  renderAt('/app/ireland?region=dublin&urban_rural=urban&pack=2026-08-13&view=map')
  const navigation=screen.getByRole('navigation',{name:'Explore briefing'})
  const access=navigation.querySelector('a[href*="/access"]')!
  const url=new URL(access.getAttribute('href')!,'http://localhost')
  expect(url.pathname).toBe('/app/ireland/access')
  expect(url.searchParams.get('region')).toBe('dublin')
  expect(url.searchParams.get('urban_rural')).toBe('urban')
  expect(url.searchParams.get('pack')).toBe('2026-08-13')
  expect(url.searchParams.has('view')).toBe(false)
 })
 it('offers an area reset while preserving the selected country, region and network',()=>{
  overviewState.isLoading=false;overviewState.error=null;overviewState.data={dimensions:[]}
  mapState.isLoading=false;mapState.error=null;mapState.data={empty:true,data:[]}
  renderAt('/app/england?region=E12000007&urban_rural=rural&pack=2026-08-01')
  expect(screen.getByRole('heading',{name:'No areas match this filter'})).toBeInTheDocument()
  const href=screen.getByRole('link',{name:'Reset area filter'}).getAttribute('href')!
  const url=new URL(href,'http://localhost')
  expect(url.pathname).toBe('/app/england')
  expect(url.searchParams.get('region')).toBe('E12000007')
  expect(url.searchParams.get('pack')).toBe('2026-08-01')
  expect(url.searchParams.get('urban_rural')).toBe('all')
 })
})
