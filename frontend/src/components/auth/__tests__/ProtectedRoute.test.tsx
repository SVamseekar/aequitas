import { render, screen } from "@testing-library/react"
import { describe, it, expect, vi } from "vitest"
import { MemoryRouter } from "react-router"

vi.mock("@/contexts/AuthContext", () => ({
  useAuth: vi.fn(),
}))

import { useAuth } from "@/contexts/AuthContext"
import { ProtectedRoute } from "../ProtectedRoute"

describe("ProtectedRoute", () => {
  it("shows loading spinner while auth is resolving", () => {
    vi.mocked(useAuth).mockReturnValue({ user: null, session: null, loading: true, signOut: vi.fn() })
    const { container } = render(
      <MemoryRouter>
        <ProtectedRoute><div>Protected</div></ProtectedRoute>
      </MemoryRouter>,
    )
    expect(container.querySelector(".animate-pulse")).toBeTruthy()
  })

  it("renders children when user is authenticated", () => {
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    vi.mocked(useAuth).mockReturnValue({ user: { id: "u1" } as any, session: null, loading: false, signOut: vi.fn() })
    render(
      <MemoryRouter>
        <ProtectedRoute><div>Protected Content</div></ProtectedRoute>
      </MemoryRouter>,
    )
    expect(screen.getByText("Protected Content")).toBeTruthy()
  })

  it("redirects to /auth when unauthenticated", () => {
    vi.mocked(useAuth).mockReturnValue({ user: null, session: null, loading: false, signOut: vi.fn() })
    const { container } = render(
      <MemoryRouter initialEntries={["/"]}>
        <ProtectedRoute><div>Protected</div></ProtectedRoute>
      </MemoryRouter>,
    )
    // Navigate replaces content — protected content should not be visible
    expect(container.querySelector("div:not(:empty)")).toBeNull()
  })
})
