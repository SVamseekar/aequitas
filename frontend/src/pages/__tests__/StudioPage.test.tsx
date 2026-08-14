import { describe, expect, it, vi } from "vitest"
import { render, screen } from "@testing-library/react"
import { MemoryRouter, Route, Routes } from "react-router"
import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import StudioPage from "../StudioPage"
import { withSearch } from "@/lib/appRoutes"

vi.mock("@/components/studio/StudioEditorMap", () => ({
  default: () => <div data-testid="studio-editor-map">editor</div>,
}))
vi.mock("@/components/studio/StudioResultMap", () => ({
  default: () => <div data-testid="studio-result-map">result</div>,
}))

function renderAt(path: string) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={client}>
      <MemoryRouter initialEntries={[path]}>
        <Routes>
          <Route path="/app/:country/studio" element={<StudioPage />} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  )
}

describe("Studio routes", () => {
  it("keeps studio as its own page, not a dimension slug", () => {
    renderAt("/app/england/studio?region=E12000005&urban_rural=rural")
    expect(screen.getByText(/Studio/)).toBeTruthy()
    expect(screen.getByTestId("studio-patch-list")).toBeTruthy()
  })

  it("Netherlands studio is not an empty-pack sentence", () => {
    renderAt("/app/netherlands/studio")
    expect(screen.queryByText(/Netherlands pack is not built yet/i)).toBeNull()
  })

  it("London × rural is one sentence", () => {
    renderAt("/app/england/studio?region=E12000007&urban_rural=rural")
    expect(screen.getByText(/no rural LSOAs/i)).toBeTruthy()
  })

  it("withSearch keeps filters on the studio path", () => {
    expect(withSearch("/app/england/studio", "region=E12000005&urban_rural=rural")).toEqual({
      pathname: "/app/england/studio",
      search: "?region=E12000005&urban_rural=rural",
    })
  })
})
