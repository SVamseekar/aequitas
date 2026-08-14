import { describe, expect, it, vi } from "vitest"
import { render, screen } from "@testing-library/react"
import { MemoryRouter, Route, Routes } from "react-router"
import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import TimePage from "../TimePage"
import { withSearch } from "@/lib/appRoutes"

const timeState = {
  isLoading: false,
  data: {
    one_date: true,
    empty: false,
    points: [{ pack_id: "2026-08-01", as_of: "2026-08-01", value: 80, n_areas: 33755 }],
    note: "Only one network date in this checkout.",
    area_noun: "LSOAs",
  } as Record<string, unknown> | undefined,
}

vi.mock("@/api/hooks", async () => {
  const actual = await vi.importActual<typeof import("@/api/hooks")>("@/api/hooks")
  return {
    ...actual,
    useTimeSeries: () => timeState,
  }
})

function renderAt(path: string) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={client}>
      <MemoryRouter initialEntries={[path]}>
        <Routes>
          <Route path="/app/:country/time" element={<TimePage />} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  )
}

describe("Time routes", () => {
  it("is its own page, not a dimension dump", () => {
    renderAt("/app/england/time?region=all&urban_rural=all")
    expect(screen.getByTestId("time-page")).toBeTruthy()
    expect(screen.getByRole("heading", { name: /Network dates/i })).toBeTruthy()
    expect(screen.getByTestId("one-date-note")).toBeTruthy()
  })

  it("Netherlands time is a date page", () => {
    renderAt("/app/netherlands/time")
    expect(screen.getByTestId("time-page")).toBeTruthy()
    expect(screen.getByText(/buurten/i)).toBeTruthy()
    expect(screen.queryByText(/BODS/)).toBeNull()
    expect(screen.queryByText(/IMD 2025/)).toBeNull()
    expect(screen.queryByText(/CSO/)).toBeNull()
  })

  it("London × rural is one sentence", () => {
    renderAt("/app/england/time?region=E12000007&urban_rural=rural")
    expect(screen.getByText(/no rural LSOAs/i)).toBeTruthy()
  })

  it("Ireland copy names Small Areas", () => {
    renderAt("/app/ireland/time")
    expect(screen.getByText(/Small Areas/i)).toBeTruthy()
    expect(screen.queryByText(/LSOAs/)).toBeNull()
    expect(screen.queryByText(/BODS/)).toBeNull()
  })

  it("withSearch keeps pack and country switch drops it in the helper contract", () => {
    expect(withSearch("/app/england/time", "region=all&urban_rural=all&pack=2026-08-01")).toEqual({
      pathname: "/app/england/time",
      search: "?region=all&urban_rural=all&pack=2026-08-01",
    })
  })
})
