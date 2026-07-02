# Frontend Tenant UI Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add the UI surfaces that make tenants and invites usable from the browser: a tenant switcher in the app header, an admin-only org-settings panel (invite members, list/remove members), and a public `/invite/:token` accept page. None of this UI existed before this migration — it's all new, built entirely on the routes Plans 02/03 already shipped and tested. Also closes a gap between the spec and Plan 04: `PolicyNotes.tsx` gets an edit UI for the new `PATCH /api/policy-notes/{id}` route, since no edit UI existed in the app before this migration and the spec calls for policy notes specifically (not saved-analyses/saved-regions) to support update.

**Architecture:** `TenantSwitcher.tsx` — a small dropdown added to `Header.tsx`, only rendered when `memberships.length > 1` (per spec). `OrgSettingsPage.tsx` — new admin-only page reachable from `UserMenu.tsx`, showing an invite form + member list with remove/role-change actions. `InviteAcceptPage.tsx` — new public route `/invite/:token`, handling the not-signed-in → sign-in → accept → redirect flow with the token preserved across the OAuth round-trip. `PolicyNotes.tsx` — the existing add-note form is extended to double as an edit form, reusing UI rather than adding a new component.

**Tech Stack:** No new dependencies — plain `fetch` calls against Plan 03's routes, same patterns established in Plan 05.

## Global Constraints

- Frontend test commands run from the `frontend/` directory.
- All work happens on `feature/enterprise-oauth-tenancy`.
- Tenant switcher only renders when `memberships.length > 1` — per spec, single-tenant users (the common case: personal workspace only) see nothing extra in the header.
- `/invite/:token` is a public route (added to `App.tsx` outside `ProtectedRoute`) — an unauthenticated visitor must be able to see the tenant name and be prompted to sign in, per the spec's Frontend section.
- The invite token must survive the OAuth redirect round-trip. This plan uses `sessionStorage` to stash the pending invite token before redirecting to Google, and reads it back after `/api/auth/me` resolves post-login — chosen over a query param through the OAuth flow because Google's redirect URI is fixed server-side (`/api/auth/callback/google`) and doesn't pass arbitrary frontend state through by default.
- This plan does not modify `PrivacyPage.tsx` (Plan 07's job) or delete any Supabase code (already gone as of Plan 05).

---

### Task 1: `TenantSwitcher.tsx`

**Files:**
- Create: `frontend/src/components/layout/TenantSwitcher.tsx`
- Modify: `frontend/src/components/layout/Header.tsx`
- Test: `frontend/src/components/layout/__tests__/TenantSwitcher.test.tsx`

**Interfaces:**
- Consumes: `useAuth()`'s `memberships`, `activeTenant`, `refresh` (Plan 05, Task 1); `POST /api/session/switch-tenant` (Plan 02)
- Produces: a `<TenantSwitcher />` component rendered in `Header.tsx`, visible only when `memberships.length > 1`

- [ ] **Step 1: Write the failing tests**

Create `frontend/src/components/layout/__tests__/TenantSwitcher.test.tsx`:

```tsx
import { render, screen, waitFor } from "@testing-library/react"
import { describe, it, expect, vi, beforeEach } from "vitest"

vi.mock("@/contexts/AuthContext", () => ({
  useAuth: vi.fn(),
}))

import { useAuth } from "@/contexts/AuthContext"
import { TenantSwitcher } from "../TenantSwitcher"

describe("TenantSwitcher", () => {
  beforeEach(() => {
    vi.restoreAllMocks()
  })

  it("renders nothing with only one membership", () => {
    vi.mocked(useAuth).mockReturnValue({
      user: { id: "u1", email: "a@example.com", display_name: "A" },
      activeTenant: { id: "t1", name: "Solo Workspace", slug: "solo" },
      role: "admin",
      memberships: [{ tenant_id: "t1", tenant_name: "Solo Workspace", tenant_slug: "solo", role: "admin" }],
      loading: false, signOut: vi.fn(), refresh: vi.fn(),
    })
    const { container } = render(<TenantSwitcher />)
    expect(container.firstChild).toBeNull()
  })

  it("renders a dropdown with multiple memberships", () => {
    vi.mocked(useAuth).mockReturnValue({
      user: { id: "u1", email: "a@example.com", display_name: "A" },
      activeTenant: { id: "t1", name: "Workspace One", slug: "one" },
      role: "admin",
      memberships: [
        { tenant_id: "t1", tenant_name: "Workspace One", tenant_slug: "one", role: "admin" },
        { tenant_id: "t2", tenant_name: "Workspace Two", tenant_slug: "two", role: "member" },
      ],
      loading: false, signOut: vi.fn(), refresh: vi.fn(),
    })
    render(<TenantSwitcher />)
    expect(screen.getByText("Workspace One")).toBeTruthy()
  })

  it("posts to switch-tenant and refreshes on selection", async () => {
    const refresh = vi.fn()
    vi.mocked(useAuth).mockReturnValue({
      user: { id: "u1", email: "a@example.com", display_name: "A" },
      activeTenant: { id: "t1", name: "Workspace One", slug: "one" },
      role: "admin",
      memberships: [
        { tenant_id: "t1", tenant_name: "Workspace One", tenant_slug: "one", role: "admin" },
        { tenant_id: "t2", tenant_name: "Workspace Two", tenant_slug: "two", role: "member" },
      ],
      loading: false, signOut: vi.fn(), refresh,
    })
    const fetchMock = vi.fn().mockResolvedValue({ ok: true, json: async () => ({ status: "ok" }) })
    vi.stubGlobal("fetch", fetchMock)

    render(<TenantSwitcher />)
    screen.getByRole("button").click()
    screen.getByText("Workspace Two").click()

    await waitFor(() => expect(fetchMock).toHaveBeenCalledWith(
      "/api/session/switch-tenant",
      expect.objectContaining({ method: "POST" }),
    ))
    await waitFor(() => expect(refresh).toHaveBeenCalled())
  })
})
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd frontend && npx vitest run src/components/layout/__tests__/TenantSwitcher.test.tsx`
Expected: FAIL — `TenantSwitcher.tsx` doesn't exist yet

- [ ] **Step 3: Write `TenantSwitcher.tsx`**

Create `frontend/src/components/layout/TenantSwitcher.tsx`:

```tsx
import { useState, useRef, useEffect } from "react"
import { useAuth } from "@/contexts/AuthContext"
import { ChevronDown, Building2 } from "lucide-react"

export function TenantSwitcher() {
  const { activeTenant, memberships, refresh } = useAuth()
  const [open, setOpen] = useState(false)
  const ref = useRef<HTMLDivElement>(null)

  useEffect(() => {
    const handleClick = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false)
    }
    document.addEventListener("mousedown", handleClick)
    return () => document.removeEventListener("mousedown", handleClick)
  }, [])

  if (memberships.length <= 1) return null

  const handleSwitch = async (tenantId: string) => {
    setOpen(false)
    await fetch("/api/session/switch-tenant", {
      method: "POST",
      credentials: "include",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ tenant_id: tenantId }),
    })
    await refresh()
  }

  return (
    <div className="relative" ref={ref}>
      <button
        onClick={() => setOpen(!open)}
        className="flex items-center gap-1.5 px-2 py-1 rounded text-xs font-mono text-muted-foreground hover:text-foreground transition-colors"
      >
        <Building2 className="w-3.5 h-3.5" />
        {activeTenant?.name ?? "Workspace"}
        <ChevronDown className="w-3 h-3" />
      </button>
      {open && (
        <div className="absolute left-0 top-full mt-2 w-56 py-1 rounded bg-card border border-border shadow-lg z-50">
          {memberships.map((m) => (
            <button
              key={m.tenant_id}
              onClick={() => void handleSwitch(m.tenant_id)}
              className="w-full text-left px-4 py-2 text-xs font-mono text-foreground hover:bg-muted/50 transition-colors"
            >
              {m.tenant_name}
              {m.tenant_id === activeTenant?.id && (
                <span className="text-indigo-400 ml-2">(active)</span>
              )}
            </button>
          ))}
        </div>
      )}
    </div>
  )
}
```

- [ ] **Step 4: Add `TenantSwitcher` to `Header.tsx`**

In `frontend/src/components/layout/Header.tsx`, add the import and render it before `UserMenu`:

```tsx
import { Link } from "react-router"
import { FilterDropdowns } from "./FilterDropdowns"
import { TenantSwitcher } from "./TenantSwitcher"
import { UserMenu } from "./UserMenu"
import { AequitasLogo } from "../shared/AequitasLogo"

export function Header() {
  return (
    <header className="border-b border-border bg-card/50">
      <div className="mx-auto max-w-7xl px-4 h-14 flex items-center justify-between">
        <Link
          to="/dashboard"
          className="flex items-center gap-2.5 text-sm font-mono font-bold tracking-widest uppercase text-foreground hover:text-indigo-400 transition-colors"
        >
          <AequitasLogo className="w-5 h-5 text-slate-300" />
          AEQUITAS <span className="text-muted-foreground font-normal">· Policy Intelligence</span>
        </Link>
        <div className="flex items-center gap-4">
          <TenantSwitcher />
          <FilterDropdowns />
          <UserMenu />
        </div>
      </div>
    </header>
  )
}
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `cd frontend && npx vitest run src/components/layout/__tests__/TenantSwitcher.test.tsx`
Expected: 3 passed

- [ ] **Step 6: Verify the frontend builds**

Run: `cd frontend && npm run build`
Expected: no errors

- [ ] **Step 7: Commit**

```bash
git add frontend/src/components/layout/TenantSwitcher.tsx frontend/src/components/layout/Header.tsx \
  frontend/src/components/layout/__tests__/TenantSwitcher.test.tsx
git commit -m "Add tenant switcher to app header, shown only with multiple memberships"
```

---

### Task 2: `OrgSettingsPage.tsx` — invite form + member list

**Files:**
- Create: `frontend/src/pages/OrgSettingsPage.tsx`
- Modify: `frontend/src/App.tsx`
- Modify: `frontend/src/components/layout/UserMenu.tsx`
- Test: `frontend/src/pages/__tests__/OrgSettingsPage.test.tsx`

**Interfaces:**
- Consumes: `useAuth()`'s `role`, `activeTenant` (Plan 05); `POST /api/tenants/{id}/invites`, `GET /api/tenants/{id}/members`, `DELETE /api/tenants/{id}/members/{user_id}`, `PATCH /api/tenants/{id}/members/{user_id}/role` (Plan 03)
- Produces: a new route `/org-settings`, admin-only in practice (non-admins see an explanatory message rather than the panel, matching how the backend already 403s them)

- [ ] **Step 1: Write the failing tests**

Create `frontend/src/pages/__tests__/OrgSettingsPage.test.tsx`:

```tsx
import { render, screen, waitFor } from "@testing-library/react"
import { describe, it, expect, vi, beforeEach } from "vitest"
import { MemoryRouter } from "react-router"

vi.mock("@/contexts/AuthContext", () => ({
  useAuth: vi.fn(),
}))

import { useAuth } from "@/contexts/AuthContext"
import OrgSettingsPage from "../OrgSettingsPage"

describe("OrgSettingsPage", () => {
  beforeEach(() => {
    vi.restoreAllMocks()
  })

  it("shows a non-admin message for member role", () => {
    vi.mocked(useAuth).mockReturnValue({
      user: { id: "u1", email: "a@example.com", display_name: "A" },
      activeTenant: { id: "t1", name: "Workspace", slug: "ws" },
      role: "member",
      memberships: [{ tenant_id: "t1", tenant_name: "Workspace", tenant_slug: "ws", role: "member" }],
      loading: false, signOut: vi.fn(), refresh: vi.fn(),
    })
    render(<MemoryRouter><OrgSettingsPage /></MemoryRouter>)
    expect(screen.getByText(/admin/i)).toBeTruthy()
  })

  it("loads and displays members for an admin", async () => {
    vi.mocked(useAuth).mockReturnValue({
      user: { id: "u1", email: "a@example.com", display_name: "A" },
      activeTenant: { id: "t1", name: "Workspace", slug: "ws" },
      role: "admin",
      memberships: [{ tenant_id: "t1", tenant_name: "Workspace", tenant_slug: "ws", role: "admin" }],
      loading: false, signOut: vi.fn(), refresh: vi.fn(),
    })
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: true,
        json: async () => [{ user_id: "u1", email: "a@example.com", display_name: "A", role: "admin" }],
      }),
    )

    render(<MemoryRouter><OrgSettingsPage /></MemoryRouter>)
    await waitFor(() => screen.getByText("a@example.com"))
  })

  it("submits an invite and displays the returned link", async () => {
    vi.mocked(useAuth).mockReturnValue({
      user: { id: "u1", email: "a@example.com", display_name: "A" },
      activeTenant: { id: "t1", name: "Workspace", slug: "ws" },
      role: "admin",
      memberships: [{ tenant_id: "t1", tenant_name: "Workspace", tenant_slug: "ws", role: "admin" }],
      loading: false, signOut: vi.fn(), refresh: vi.fn(),
    })
    const fetchMock = vi.fn()
      .mockResolvedValueOnce({ ok: true, json: async () => [] }) // initial member list
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({ token: "tok123", link: "https://example.com/invite/tok123" }),
      })
    vi.stubGlobal("fetch", fetchMock)

    render(<MemoryRouter><OrgSettingsPage /></MemoryRouter>)
    await waitFor(() => screen.getByPlaceholderText(/email/i))

    const emailInput = screen.getByPlaceholderText(/email/i) as HTMLInputElement
    emailInput.value = "newperson@example.com"
    emailInput.dispatchEvent(new Event("input", { bubbles: true }))

    screen.getByText(/send invite/i).click()

    await waitFor(() => screen.getByDisplayValue("https://example.com/invite/tok123"))
  })
})
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd frontend && npx vitest run src/pages/__tests__/OrgSettingsPage.test.tsx`
Expected: FAIL — `OrgSettingsPage.tsx` doesn't exist yet

- [ ] **Step 3: Write `OrgSettingsPage.tsx`**

Create `frontend/src/pages/OrgSettingsPage.tsx`:

```tsx
import { useState, useEffect, useCallback } from "react"
import { useNavigate } from "react-router"
import { useAuth } from "@/contexts/AuthContext"
import { ArrowLeft, Trash2 } from "lucide-react"

interface Member {
  user_id: string
  email: string
  display_name: string | null
  role: string
}

export default function OrgSettingsPage() {
  const { activeTenant, role, user } = useAuth()
  const navigate = useNavigate()
  const [members, setMembers] = useState<Member[]>([])
  const [inviteEmail, setInviteEmail] = useState("")
  const [inviteRole, setInviteRole] = useState("member")
  const [inviteLink, setInviteLink] = useState<string | null>(null)
  const [submitting, setSubmitting] = useState(false)

  const refreshMembers = useCallback(async () => {
    if (!activeTenant) return
    const res = await fetch(`/api/tenants/${activeTenant.id}/members`, { credentials: "include" })
    if (res.ok) setMembers(await res.json())
  }, [activeTenant])

  useEffect(() => {
    void refreshMembers()
  }, [refreshMembers])

  if (role !== "admin") {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center">
        <p className="text-sm text-muted-foreground font-mono">
          Only workspace admins can access organisation settings.
        </p>
      </div>
    )
  }

  const handleInvite = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!activeTenant) return
    setSubmitting(true)
    setInviteLink(null)
    try {
      const res = await fetch(`/api/tenants/${activeTenant.id}/invites`, {
        method: "POST",
        credentials: "include",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email: inviteEmail, role: inviteRole }),
      })
      if (res.ok) {
        const body = await res.json()
        setInviteLink(body.link)
        setInviteEmail("")
      }
    } finally {
      setSubmitting(false)
    }
  }

  const handleRemove = async (userId: string) => {
    if (!activeTenant) return
    await fetch(`/api/tenants/${activeTenant.id}/members/${userId}`, {
      method: "DELETE",
      credentials: "include",
    })
    void refreshMembers()
  }

  return (
    <div className="min-h-screen bg-background">
      <div className="max-w-2xl mx-auto px-6 py-10">
        <button
          onClick={() => navigate(-1)}
          className="flex items-center gap-2 text-xs text-muted-foreground hover:text-foreground mb-8 font-mono transition-colors"
        >
          <ArrowLeft className="w-3.5 h-3.5" />
          BACK
        </button>

        <h1 className="text-lg font-bold tracking-tight mb-1 text-foreground">
          {activeTenant?.name ?? "Organisation"} Settings
        </h1>
        <p className="text-xs text-muted-foreground mb-8">Manage members and invitations</p>

        <section className="mb-10">
          <h2 className="text-[11px] uppercase tracking-[0.15em] text-muted-foreground font-mono mb-4">
            Invite a member
          </h2>
          <form onSubmit={(e) => void handleInvite(e)} className="flex gap-2 mb-3">
            <input
              type="email"
              required
              placeholder="Email address"
              value={inviteEmail}
              onChange={(e) => setInviteEmail(e.target.value)}
              className="flex-1 px-3 py-2 rounded bg-muted/50 border border-border text-sm text-foreground placeholder:text-muted-foreground/40 focus:outline-none focus:border-indigo-500/50 font-mono"
            />
            <select
              value={inviteRole}
              onChange={(e) => setInviteRole(e.target.value)}
              className="px-3 py-2 rounded bg-muted/50 border border-border text-sm text-foreground font-mono"
            >
              <option value="member">Member</option>
              <option value="admin">Admin</option>
            </select>
            <button
              type="submit"
              disabled={submitting}
              className="px-4 py-2 rounded bg-indigo-600 text-white text-sm font-semibold hover:bg-indigo-500 transition-colors disabled:opacity-50"
            >
              Send invite
            </button>
          </form>
          {inviteLink && (
            <input
              readOnly
              value={inviteLink}
              onFocus={(e) => e.target.select()}
              className="w-full px-3 py-2 rounded bg-muted/30 border border-border text-xs text-muted-foreground font-mono"
            />
          )}
        </section>

        <section>
          <h2 className="text-[11px] uppercase tracking-[0.15em] text-muted-foreground font-mono mb-4">
            Members
          </h2>
          <div className="space-y-1">
            {members.map((m) => (
              <div
                key={m.user_id}
                className="flex items-center justify-between px-3 py-2 rounded border border-border"
              >
                <div>
                  <p className="text-sm text-foreground">{m.display_name ?? m.email}</p>
                  <p className="text-xs text-muted-foreground font-mono">{m.email} · {m.role}</p>
                </div>
                {m.user_id !== user?.id && (
                  <button
                    onClick={() => void handleRemove(m.user_id)}
                    className="p-1.5 rounded hover:bg-muted text-muted-foreground hover:text-red-400 transition-colors"
                    aria-label={`Remove ${m.email}`}
                  >
                    <Trash2 className="w-3.5 h-3.5" />
                  </button>
                )}
              </div>
            ))}
          </div>
        </section>
      </div>
    </div>
  )
}
```

- [ ] **Step 4: Register the `/org-settings` route in `App.tsx`**

In `frontend/src/App.tsx`, add the lazy import alongside the other page imports:

```tsx
const OrgSettingsPage = lazy(() => import("./pages/OrgSettingsPage"))
```

And add the protected route, alongside the existing `/profile`, `/saved`, `/notes`, `/regions` routes:

```tsx
              <Route path="/org-settings" element={<ProtectedRoute><OrgSettingsPage /></ProtectedRoute>} />
```

- [ ] **Step 5: Add an "Organisation Settings" entry to `UserMenu.tsx`**

In `frontend/src/components/layout/UserMenu.tsx`, add a new menu item (only when `role === "admin"` — but `UserMenu` doesn't currently read `role` from `useAuth()`, so add that destructure too):

```tsx
  const { user, signOut, role } = useAuth()
```

Then add a new menu button after the "SAVED" item and before the sign-out separator (adjust the `itemRefs` index numbering for the keyboard-nav logic accordingly — the existing items are indexed 0-4, so this new item becomes index 4 and "SIGN OUT" shifts to index 5):

```tsx
          {role === "admin" && (
            <button
              ref={setItemRef(4)}
              role="menuitem"
              tabIndex={-1}
              onClick={() => { navigate("/org-settings"); setOpen(false) }}
              className="w-full flex items-center gap-3 px-4 py-2.5 text-xs text-foreground hover:bg-muted/50 transition-colors font-mono"
            >
              <Building2 className="w-3.5 h-3.5 text-muted-foreground" />
              ORG SETTINGS
            </button>
          )}
```

Add `Building2` to the existing `lucide-react` import line, and renumber the "SIGN OUT" button's `setItemRef(4)` to `setItemRef(5)` to avoid a duplicate ref index.

- [ ] **Step 6: Run tests to verify they pass**

Run: `cd frontend && npx vitest run src/pages/__tests__/OrgSettingsPage.test.tsx`
Expected: 3 passed

- [ ] **Step 7: Verify the frontend builds**

Run: `cd frontend && npm run build`
Expected: no errors

- [ ] **Step 8: Manual verification in browser**

With backend (`DEV_AUTH_BYPASS=true`) and frontend dev servers running, navigate to `/org-settings` via the user menu, submit an invite, confirm the link appears, and confirm the dev-bypass admin appears in the member list.

- [ ] **Step 9: Commit**

```bash
git add frontend/src/pages/OrgSettingsPage.tsx frontend/src/App.tsx frontend/src/components/layout/UserMenu.tsx \
  frontend/src/pages/__tests__/OrgSettingsPage.test.tsx
git commit -m "Add OrgSettingsPage with invite form and member list"
```

---

### Task 3: `InviteAcceptPage.tsx` — public `/invite/:token` route

**Files:**
- Create: `frontend/src/pages/InviteAcceptPage.tsx`
- Modify: `frontend/src/App.tsx`
- Test: `frontend/src/pages/__tests__/InviteAcceptPage.test.tsx`

**Interfaces:**
- Consumes: `useAuth()`'s `user` (Plan 05); `GET /api/invites/{token}`, `POST /api/invites/{token}/accept` (Plan 03)
- Produces: public route `/invite/:token` — shows tenant name + role, prompts Google sign-in if not authenticated (preserving the token across the redirect via `sessionStorage`), then posts accept and redirects into `/dashboard`

- [ ] **Step 1: Write the failing tests**

Create `frontend/src/pages/__tests__/InviteAcceptPage.test.tsx`:

```tsx
import { render, screen, waitFor } from "@testing-library/react"
import { describe, it, expect, vi, beforeEach } from "vitest"
import { MemoryRouter, Route, Routes } from "react-router"

vi.mock("@/contexts/AuthContext", () => ({
  useAuth: vi.fn(),
}))

import { useAuth } from "@/contexts/AuthContext"
import InviteAcceptPage from "../InviteAcceptPage"

function renderAtToken(token: string) {
  return render(
    <MemoryRouter initialEntries={[`/invite/${token}`]}>
      <Routes>
        <Route path="/invite/:token" element={<InviteAcceptPage />} />
      </Routes>
    </MemoryRouter>,
  )
}

describe("InviteAcceptPage", () => {
  beforeEach(() => {
    vi.restoreAllMocks()
    sessionStorage.clear()
  })

  it("shows the tenant name and prompts sign-in when not authenticated", async () => {
    vi.mocked(useAuth).mockReturnValue({
      user: null, activeTenant: null, role: null, memberships: [],
      loading: false, signOut: vi.fn(), refresh: vi.fn(),
    })
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({ ok: true, json: async () => ({ tenant_name: "Acme LTA", role: "member" }) }),
    )

    renderAtToken("tok123")

    await waitFor(() => screen.getByText(/Acme LTA/))
    expect(screen.getByText(/sign in/i)).toBeTruthy()
  })

  it("stashes the token in sessionStorage before redirecting to Google sign-in", async () => {
    vi.mocked(useAuth).mockReturnValue({
      user: null, activeTenant: null, role: null, memberships: [],
      loading: false, signOut: vi.fn(), refresh: vi.fn(),
    })
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({ ok: true, json: async () => ({ tenant_name: "Acme LTA", role: "member" }) }),
    )

    renderAtToken("tok123")
    await waitFor(() => screen.getByText(/sign in/i))

    screen.getByText(/sign in/i).click()
    expect(sessionStorage.getItem("pending_invite_token")).toBe("tok123")
  })

  it("posts accept and shows success when already authenticated", async () => {
    vi.mocked(useAuth).mockReturnValue({
      user: { id: "u1", email: "a@example.com", display_name: "A" },
      activeTenant: { id: "t1", name: "Existing", slug: "existing" },
      role: "admin", memberships: [],
      loading: false, signOut: vi.fn(), refresh: vi.fn(),
    })
    const fetchMock = vi.fn()
      .mockResolvedValueOnce({ ok: true, json: async () => ({ tenant_name: "Acme LTA", role: "member" }) })
      .mockResolvedValueOnce({ ok: true, json: async () => ({ status: "ok", tenant_id: "t2" }) })
    vi.stubGlobal("fetch", fetchMock)

    renderAtToken("tok123")

    await waitFor(() => expect(fetchMock).toHaveBeenCalledWith(
      "/api/invites/tok123/accept",
      expect.objectContaining({ method: "POST" }),
    ))
  })

  it("shows an error for an invalid or expired token", async () => {
    vi.mocked(useAuth).mockReturnValue({
      user: null, activeTenant: null, role: null, memberships: [],
      loading: false, signOut: vi.fn(), refresh: vi.fn(),
    })
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ ok: false, status: 404 }))

    renderAtToken("bad-token")

    await waitFor(() => screen.getByText(/invalid|expired|not found/i))
  })
})
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd frontend && npx vitest run src/pages/__tests__/InviteAcceptPage.test.tsx`
Expected: FAIL — `InviteAcceptPage.tsx` doesn't exist yet

- [ ] **Step 3: Write `InviteAcceptPage.tsx`**

Create `frontend/src/pages/InviteAcceptPage.tsx`:

```tsx
import { useState, useEffect } from "react"
import { useParams, useNavigate } from "react-router"
import { useAuth } from "@/contexts/AuthContext"

interface InvitePreview {
  tenant_name: string
  role: string
}

const PENDING_INVITE_KEY = "pending_invite_token"

export default function InviteAcceptPage() {
  const { token } = useParams<{ token: string }>()
  const { user, refresh } = useAuth()
  const navigate = useNavigate()
  const [preview, setPreview] = useState<InvitePreview | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [accepting, setAccepting] = useState(false)

  useEffect(() => {
    if (!token) return
    fetch(`/api/invites/${token}`, { credentials: "include" })
      .then((res) => {
        if (!res.ok) {
          setError(res.status === 410 ? "This invite has expired or was already accepted." : "Invite not found.")
          return null
        }
        return res.json()
      })
      .then((body) => {
        if (body) setPreview(body)
      })
      .catch(() => setError("Invite not found."))
  }, [token])

  useEffect(() => {
    if (!user || !token || !preview) return
    setAccepting(true)
    fetch(`/api/invites/${token}/accept`, { method: "POST", credentials: "include" })
      .then(async (res) => {
        if (!res.ok) {
          setError("Could not accept this invite.")
          return
        }
        sessionStorage.removeItem(PENDING_INVITE_KEY)
        await refresh()
        navigate("/dashboard")
      })
      .finally(() => setAccepting(false))
  }, [user, token, preview, refresh, navigate])

  const handleSignIn = () => {
    if (token) sessionStorage.setItem(PENDING_INVITE_KEY, token)
    window.location.href = "/api/auth/login/google"
  }

  if (error) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center px-6">
        <p className="text-sm text-red-400 font-mono">{error}</p>
      </div>
    )
  }

  if (!preview) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center">
        <div className="w-2 h-2 rounded-full bg-indigo-500 animate-pulse" />
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-background flex items-center justify-center px-6">
      <div className="max-w-sm w-full text-center">
        <h1 className="text-lg font-bold text-foreground mb-2">
          Join {preview.tenant_name}
        </h1>
        <p className="text-xs text-muted-foreground mb-8 font-mono">
          You've been invited as {preview.role}
        </p>
        {user ? (
          <p className="text-xs text-muted-foreground font-mono">
            {accepting ? "Accepting invite…" : "Signed in — finishing up…"}
          </p>
        ) : (
          <button
            onClick={handleSignIn}
            className="w-full px-4 py-3 rounded bg-indigo-600 text-white font-semibold text-sm hover:bg-indigo-500 transition-colors"
          >
            Sign in with Google to accept
          </button>
        )}
      </div>
    </div>
  )
}
```

- [ ] **Step 4: Register the public `/invite/:token` route in `App.tsx`**

In `frontend/src/App.tsx`, add the lazy import:

```tsx
const InviteAcceptPage = lazy(() => import("./pages/InviteAcceptPage"))
```

And add the route outside `ProtectedRoute` (it's public, per the spec), alongside the other public routes like `/auth`:

```tsx
              <Route path="/invite/:token" element={<InviteAcceptPage />} />
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `cd frontend && npx vitest run src/pages/__tests__/InviteAcceptPage.test.tsx`
Expected: 4 passed

- [ ] **Step 6: Verify the frontend builds**

Run: `cd frontend && npm run build`
Expected: no errors

- [ ] **Step 7: Manual verification in browser**

With both servers running: from `OrgSettingsPage`, send an invite to a test email, copy the link, open it in an incognito window (so no existing session), confirm it shows the tenant name and a sign-in prompt, complete Google sign-in, and confirm it redirects to `/dashboard` with the new tenant now in `memberships` (visible via the tenant switcher if this makes membership count > 1).

- [ ] **Step 8: Run the full frontend suite**

Run: `cd frontend && npx vitest run`
Expected: all tests pass (pre-existing + all tests added across Plans 05-06)

- [ ] **Step 9: Commit**

```bash
git add frontend/src/pages/InviteAcceptPage.tsx frontend/src/App.tsx \
  frontend/src/pages/__tests__/InviteAcceptPage.test.tsx
git commit -m "Add public invite-accept page with sign-in-preserving redirect flow"
```

---

### Task 4: `PolicyNotes.tsx` — edit UI for the new `PATCH /api/policy-notes/{id}` route

**Files:**
- Modify: `frontend/src/components/saved/PolicyNotes.tsx`
- Test: `frontend/src/components/saved/__tests__/PolicyNotes.test.tsx` (new — no test file exists for this component today)

**Interfaces:**
- Consumes: `PATCH /api/policy-notes/{note_id}` (Plan 04, Task 5 — added specifically because the spec calls for policy notes to support update, unlike `saved_analyses`/`saved_regions`); Plan 05's fetch-based rewrite of this component's `listPolicyNotes`/`createPolicyNote`/`deletePolicyNote` calls (mechanical `db.ts` → `fetch` swap, per Plan 05 Task 6 Step 1)
- Produces: an "Edit" button per note that opens the existing add-note form pre-filled with that note's current `stance`/`thesis`/`critique`, submitting via `PATCH` instead of `POST` — closing the gap between the spec's backend requirement and the frontend, since no edit UI exists in the app today

**Context**: `PolicyNotes.tsx` today (before Plan 05's rewrite) only supports create and delete — there's a `NEW NOTE` button and a `Trash2` delete icon per note, but nothing lets a user revise a note's stance or thesis after saving it. The spec's Backend section explicitly calls for `policy_notes.py — list/create/update/delete` (contrasted with `saved_analyses`/`saved_regions`, which are list/create/delete only) because a policy note is meant to be a living document — a stance that gets revised as new evidence comes in, not a one-shot save. This task builds the missing UI, reusing the existing inline form rather than introducing a new component.

- [ ] **Step 1: Write the failing test**

Create `frontend/src/components/saved/__tests__/PolicyNotes.test.tsx`:

```tsx
import { describe, it, expect, vi, beforeEach } from "vitest"
import { render, screen, fireEvent, waitFor } from "@testing-library/react"

vi.mock("@/contexts/AuthContext", () => ({
  useAuth: vi.fn(),
}))

import { useAuth } from "@/contexts/AuthContext"
import { PolicyNotes } from "../PolicyNotes"

const mockUser = { id: "user-1", email: "test@example.com", display_name: "Test User" }

function renderWithAuth() {
  vi.mocked(useAuth).mockReturnValue({
    user: mockUser,
    activeTenant: { id: "tenant-1", name: "Test", slug: "test" },
    role: "admin",
    memberships: [],
    loading: false,
    signOut: vi.fn(),
    refresh: vi.fn(),
  })
  return render(<PolicyNotes />)
}

describe("PolicyNotes edit flow", () => {
  beforeEach(() => {
    vi.stubGlobal(
      "fetch",
      vi.fn((url: string, options?: RequestInit) => {
        if (url === "/api/policy-notes" && (!options || options.method === undefined)) {
          return Promise.resolve({
            ok: true,
            json: () =>
              Promise.resolve([
                {
                  id: "note-1", user_id: "user-1", dimension: "equity", region: "all",
                  stance: "monitor", thesis: "Initial thesis", critique: null,
                  created_at: "2026-01-01T00:00:00Z", updated_at: "2026-01-01T00:00:00Z",
                },
              ]),
          })
        }
        if (url === "/api/policy-notes/note-1" && options?.method === "PATCH") {
          return Promise.resolve({
            ok: true,
            json: () =>
              Promise.resolve({
                id: "note-1", user_id: "user-1", dimension: "equity", region: "all",
                stance: "priority", thesis: "Revised thesis", critique: "New evidence",
                created_at: "2026-01-01T00:00:00Z", updated_at: "2026-01-02T00:00:00Z",
              }),
          })
        }
        return Promise.resolve({ ok: true, json: () => Promise.resolve([]) })
      }),
    )
  })

  it("opens an edit form pre-filled with the note's current values and submits via PATCH", async () => {
    renderWithAuth()

    await waitFor(() => screen.getByText("Initial thesis"))

    fireEvent.click(screen.getByLabelText("Edit note"))

    const thesisInput = screen.getByDisplayValue("Initial thesis") as HTMLTextAreaElement
    fireEvent.change(thesisInput, { target: { value: "Revised thesis" } })

    fireEvent.click(screen.getByText("SAVE"))

    await waitFor(() => {
      expect(fetch).toHaveBeenCalledWith(
        "/api/policy-notes/note-1",
        expect.objectContaining({ method: "PATCH", credentials: "include" }),
      )
    })
  })
})
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd frontend && npx vitest run src/components/saved/__tests__/PolicyNotes.test.tsx`
Expected: FAIL — no `"Edit note"` labelled element exists yet in the current component

- [ ] **Step 3: Add the edit UI to `PolicyNotes.tsx`**

This builds on top of Plan 05's fetch-based rewrite of this component (which replaced the `@/lib/db` imports with `fetch` calls following the pattern shown in Plan 05 Task 6). Add an `updatePolicyNote` fetch helper, an editing-state field, a `Pencil` edit icon per note, and reuse the existing form for both create and edit:

```tsx
import { useState, useEffect, useCallback } from "react"
import { useAuth } from "@/contexts/AuthContext"
import { Plus, Trash2, FileText, Pencil } from "lucide-react"

interface PolicyNoteRow {
  id: string
  user_id: string
  dimension: string
  region: string
  stance: "priority" | "monitor" | "adequate"
  thesis: string
  critique: string | null
  created_at: string
  updated_at: string
}

async function listPolicyNotes(): Promise<PolicyNoteRow[]> {
  const res = await fetch("/api/policy-notes", { credentials: "include" })
  if (!res.ok) return []
  return res.json()
}

async function createPolicyNote(body: { dimension: string; region: string; stance: string; thesis: string }): Promise<void> {
  await fetch("/api/policy-notes", {
    method: "POST",
    credentials: "include",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  })
}

async function updatePolicyNote(
  id: string,
  body: { stance: string; thesis: string; critique: string | null },
): Promise<void> {
  await fetch(`/api/policy-notes/${id}`, {
    method: "PATCH",
    credentials: "include",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  })
}

async function deletePolicyNote(id: string): Promise<void> {
  await fetch(`/api/policy-notes/${id}`, { method: "DELETE", credentials: "include" })
}
```

(Note: `listPolicyNotes`/`createPolicyNote`/`deletePolicyNote` above are shown for completeness matching Plan 05's mechanical rewrite — if Plan 05 already added equivalent functions to this file, don't duplicate them; only add `updatePolicyNote`, which is new.)

Then update the component body — add editing state and the edit/save handlers:

```tsx
const DIMENSIONS = [
  "equity", "accessibility", "service_quality", "route_network",
  "modal_shift", "economic", "bus_services_act", "scenarios",
]

const STANCE_LABELS: Record<string, { label: string; colour: string }> = {
  priority: { label: "Priority", colour: "text-red-400 bg-red-400/10 border-red-400/20" },
  monitor: { label: "Monitor", colour: "text-yellow-400 bg-yellow-400/10 border-yellow-400/20" },
  adequate: { label: "Adequate", colour: "text-green-400 bg-green-400/10 border-green-400/20" },
}

export function PolicyNotes() {
  const { user } = useAuth()
  const [notes, setNotes] = useState<PolicyNoteRow[]>([])
  const [loading, setLoading] = useState(true)
  const [adding, setAdding] = useState(false)
  const [editingId, setEditingId] = useState<string | null>(null)
  const [form, setForm] = useState<{ dimension: string; region: string; stance: "priority" | "monitor" | "adequate"; thesis: string; critique: string }>(
    { dimension: "equity", region: "all", stance: "monitor", thesis: "", critique: "" }
  )

  const refresh = useCallback(async () => {
    if (!user) return
    setLoading(true)
    const data = await listPolicyNotes()
    setNotes(data)
    setLoading(false)
  }, [user])

  useEffect(() => { void refresh() }, [refresh])

  const resetForm = () => {
    setForm({ dimension: "equity", region: "all", stance: "monitor", thesis: "", critique: "" })
    setAdding(false)
    setEditingId(null)
  }

  const handleCreate = async () => {
    if (!user || !form.thesis.trim()) return
    await createPolicyNote({ dimension: form.dimension, region: form.region, stance: form.stance, thesis: form.thesis })
    resetForm()
    void refresh()
  }

  const startEdit = (note: PolicyNoteRow) => {
    setForm({
      dimension: note.dimension, region: note.region, stance: note.stance,
      thesis: note.thesis, critique: note.critique ?? "",
    })
    setEditingId(note.id)
    setAdding(false)
  }

  const handleSaveEdit = async () => {
    if (!editingId || !form.thesis.trim()) return
    await updatePolicyNote(editingId, {
      stance: form.stance, thesis: form.thesis, critique: form.critique.trim() || null,
    })
    resetForm()
    void refresh()
  }

  const handleDelete = async (id: string) => {
    await deletePolicyNote(id)
    void refresh()
  }
```

In the JSX, change the note-list `Trash2` button block to add an edit button before it:

```tsx
                <button
                  aria-label="Edit note"
                  onClick={() => startEdit(n)}
                  className="p-1.5 rounded hover:bg-indigo-500/10 text-muted-foreground/40 hover:text-indigo-400 transition-colors shrink-0"
                >
                  <Pencil className="w-3.5 h-3.5" />
                </button>
                <button
                  onClick={() => void handleDelete(n.id)}
                  className="p-1.5 rounded hover:bg-red-500/10 text-muted-foreground/40 hover:text-red-400 transition-colors shrink-0"
                >
                  <Trash2 className="w-3.5 h-3.5" />
                </button>
```

And change the form's visibility condition from `{adding && (...)}` to `{(adding || editingId) && (...)}`, add a `critique` textarea below the existing `thesis` textarea, and change the form's SAVE button to call `handleSaveEdit` when `editingId` is set:

```tsx
      {(adding || editingId) && (
        <div className="border border-indigo-500/30 rounded bg-card p-4 mb-4 space-y-3">
          {/* ... existing dimension/stance selects and thesis textarea unchanged ... */}
          <textarea
            value={form.critique}
            onChange={(e) => setForm((f) => ({ ...f, critique: e.target.value }))}
            placeholder="Critique or revision note (optional)..."
            rows={2}
            className="w-full px-3 py-2 text-xs bg-muted/50 border border-border rounded font-mono text-foreground placeholder:text-muted-foreground/40 resize-none focus:outline-none focus:border-indigo-500/50"
          />
          <div className="flex gap-2">
            <button
              onClick={() => void (editingId ? handleSaveEdit() : handleCreate())}
              className="px-3 py-1.5 text-xs font-mono bg-indigo-600 text-white rounded hover:bg-indigo-500 transition-colors"
            >
              SAVE
            </button>
            <button
              onClick={resetForm}
              className="px-3 py-1.5 text-xs font-mono text-muted-foreground hover:text-foreground transition-colors"
            >
              CANCEL
            </button>
          </div>
        </div>
      )}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd frontend && npx vitest run src/components/saved/__tests__/PolicyNotes.test.tsx`
Expected: 1 passed

- [ ] **Step 5: Manual verification in browser**

Navigate to `/notes`, create a note, click its edit icon, change the thesis and stance, save, and confirm the note's display updates immediately and persists across a page refresh.

- [ ] **Step 6: Commit**

```bash
git add frontend/src/components/saved/PolicyNotes.tsx frontend/src/components/saved/__tests__/PolicyNotes.test.tsx
git commit -m "Add edit UI to PolicyNotes, wiring the PATCH /api/policy-notes/{id} route"
```

---

## Handoff

At the end of this plan: the full tenant lifecycle works end-to-end from the browser — an admin invites someone by email, the invite email (or copied link) leads to `/invite/:token`, the invitee signs in with Google if needed and lands in the shared tenant, the tenant switcher appears once they belong to more than one workspace, and `OrgSettingsPage` lets admins manage members and roles. `PolicyNotes.tsx` also gained an edit UI, closing the gap between the spec's backend `update` requirement (Plan 04) and the frontend.

Plan `07-cleanup-cutover.md` begins here — the final plan: delete `src/aequitas/api/auth.py`, the `supabase` Python dependency, `@supabase/supabase-js`, all Supabase RLS/migration files, fix `PrivacyPage.tsx`'s now-false claims about Supabase, and run the full verification pass (backend + frontend suites, manual OAuth round-trip) before merging `feature/enterprise-oauth-tenancy` back to `main`.
