import { describe, it, expect, vi, beforeEach } from "vitest"
import { render, screen } from "@testing-library/react"
import { MemoryRouter, Route, Routes } from "react-router"

vi.mock("@/contexts/AuthContext", () => ({
  useAuth: vi.fn(),
}))

import { useAuth } from "@/contexts/AuthContext"
import { ProtectedRoute } from "../ProtectedRoute"

describe("ProtectedRoute", () => {
  beforeEach(() => {
    vi.mocked(useAuth).mockReset()
  })

  it("shows loading when auth is loading", () => {
    vi.mocked(useAuth).mockReturnValue({
      user: null,
      activeTenant: null,
      role: null,
      memberships: [],
      loading: true,
      signOut: vi.fn(),
      refresh: vi.fn(),
    })
    render(
      <MemoryRouter>
        <ProtectedRoute>
          <div>secret</div>
        </ProtectedRoute>
      </MemoryRouter>,
    )
    expect(screen.queryByText("secret")).toBeNull()
  })

  it("renders children when authenticated", () => {
    vi.mocked(useAuth).mockReturnValue({
      user: { id: "u1", email: "a@b.com", display_name: "A" },
      activeTenant: { id: "t1", name: "T", slug: "t" },
      role: "admin",
      memberships: [],
      loading: false,
      signOut: vi.fn(),
      refresh: vi.fn(),
    })
    render(
      <MemoryRouter>
        <ProtectedRoute>
          <div>secret</div>
        </ProtectedRoute>
      </MemoryRouter>,
    )
    expect(screen.getByText("secret")).toBeTruthy()
  })

  it("redirects to home when unauthenticated", () => {
    vi.mocked(useAuth).mockReturnValue({
      user: null,
      activeTenant: null,
      role: null,
      memberships: [],
      loading: false,
      signOut: vi.fn(),
      refresh: vi.fn(),
    })
    render(
      <MemoryRouter initialEntries={["/dashboard"]}>
        <Routes>
          <Route
            path="/dashboard"
            element={
              <ProtectedRoute>
                <div>secret</div>
              </ProtectedRoute>
            }
          />
          <Route path="/" element={<div>landing</div>} />
        </Routes>
      </MemoryRouter>,
    )
    expect(screen.getByText("landing")).toBeTruthy()
    expect(screen.queryByText("secret")).toBeNull()
  })
})
