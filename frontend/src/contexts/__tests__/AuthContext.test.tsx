import { render, screen, waitFor } from "@testing-library/react"
import { describe, it, expect, vi, beforeEach } from "vitest"
import { AuthProvider, useAuth } from "../AuthContext"

function Consumer() {
  const { user, activeTenant, role, memberships, loading, signOut } = useAuth()
  if (loading) return <div>loading</div>
  if (!user) return <div>signed out</div>
  return (
    <div>
      <div>signed in as {user.email}</div>
      <div>tenant: {activeTenant?.name}</div>
      <div>role: {role}</div>
      <div>memberships: {memberships.length}</div>
      <button onClick={() => void signOut()}>sign out</button>
    </div>
  )
}

describe("AuthContext", () => {
  beforeEach(() => {
    vi.restoreAllMocks()
  })

  it("populates state from a successful /api/auth/me response", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: true,
        json: async () => ({
          user: { id: "u1", email: "alice@example.com", display_name: "Alice" },
          active_tenant: { id: "t1", name: "Alice's Workspace", slug: "alice-ws" },
          role: "admin",
          memberships: [
            {
              tenant_id: "t1",
              tenant_name: "Alice's Workspace",
              tenant_slug: "alice-ws",
              role: "admin",
            },
          ],
        }),
      }),
    )

    render(
      <AuthProvider>
        <Consumer />
      </AuthProvider>,
    )

    await waitFor(() => screen.getByText("signed in as alice@example.com"))
    expect(screen.getByText("tenant: Alice's Workspace")).toBeTruthy()
    expect(screen.getByText("role: admin")).toBeTruthy()
    expect(screen.getByText("memberships: 1")).toBeTruthy()
  })

  it("leaves user null on a 401 response", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ ok: false, status: 401 }))

    render(
      <AuthProvider>
        <Consumer />
      </AuthProvider>,
    )

    await waitFor(() => screen.getByText("signed out"))
  })

  it("signOut posts to /api/auth/logout and clears state", async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          user: { id: "u1", email: "alice@example.com", display_name: "Alice" },
          active_tenant: { id: "t1", name: "Workspace", slug: "ws" },
          role: "admin",
          memberships: [],
        }),
      })
      .mockResolvedValueOnce({ ok: true, json: async () => ({ status: "ok" }) })
    vi.stubGlobal("fetch", fetchMock)

    render(
      <AuthProvider>
        <Consumer />
      </AuthProvider>,
    )
    await waitFor(() => screen.getByText("signed in as alice@example.com"))

    screen.getByText("sign out").click()

    await waitFor(() => screen.getByText("signed out"))
    expect(fetchMock).toHaveBeenCalledWith(
      "/api/auth/logout",
      expect.objectContaining({ method: "POST" }),
    )
  })
})
