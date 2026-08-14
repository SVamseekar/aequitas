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
  it("shows honest empty copy for France", () => {
    renderAt("/app/france")
    expect(screen.getByText(/France pack is not built yet/i)).toBeTruthy()
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
