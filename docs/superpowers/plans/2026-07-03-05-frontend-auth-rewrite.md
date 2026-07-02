# Frontend Auth Rewrite Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the Supabase-backed `AuthContext`/`AuthPage` with a cookie-session-backed equivalent, delete `integrations/supabase/client.ts` and `lib/db.ts` entirely, and repoint every consumer (`ChatSidebar.tsx`, `useChat.ts`, `DimensionPage.tsx`, `UserMenu.tsx`, `ProfilePage.tsx`) at the FastAPI routes Plan 04 built. After this plan, the frontend has zero Supabase imports anywhere and a full end-to-end Google sign-in works in the browser — but there's still no tenant-switcher UI or invite-management UI (Plan 06), and `@supabase/supabase-js` is still listed in `package.json` (removed in Plan 07's cleanup, alongside the deleted `supabase` Python package).

**Architecture:** `AuthContext.tsx` becomes a thin wrapper around `fetch('/api/auth/me')` — no Supabase SDK, no `onAuthStateChange` listener (cookie-session state doesn't push events to the client the way Supabase's client-side SDK did; state is simply refetched after login/logout). `AuthPage.tsx` collapses to a single "Continue with Google" full-page redirect, deleting the email/password form entirely (this app never had real password-based users per the spec's Context section). `lib/db.ts`'s thirteen exported functions are replaced by direct `fetch` calls through `api/client.ts`, colocated in the three page components that were the only consumers per Plan 04's new REST endpoints, since `db.ts` itself is deleted rather than reimplemented as a wrapper.

**Tech Stack:** No new frontend dependencies. `@supabase/supabase-js` remains in `package.json` until Plan 07 (this plan stops importing it everywhere, but doesn't touch the dependency list itself — that's a Plan 07 cleanup task, not an auth-rewrite task).

## Global Constraints

- Frontend test commands run from the `frontend/` directory (`npx vitest run`).
- All work happens on `feature/enterprise-oauth-tenancy`.
- `signOut` must be preserved in `AuthContext`'s exported shape — not dropped, not renamed to `logout` — because `UserMenu.tsx` and `ProfilePage.tsx` both destructure it directly from `useAuth()` today.
- `AuthContext`'s new state shape: `{user, activeTenant, role, memberships, loading, signOut}` (camelCase in JS state; the API returns snake_case `active_tenant`, mapped at the fetch boundary).
- `user` in the new shape needs `id`, `email`, and something usable for avatar/display-name — `UserMenu.tsx` and `ProfilePage.tsx` currently read `user.user_metadata.{avatar_url,full_name,picture,name}` and `user.email` (Supabase's `User` type shape). Since Google OAuth data isn't persisted as an avatar URL in the new schema (only `email`/`display_name` per Plan 01's `users` table), those two components' avatar-lookup logic is simplified in this plan to drop the (now nonexistent) avatar image entirely and fall back to the existing initials/icon placeholder — this is a deliberate, small scope reduction, not an oversight, since no route in Plan 01-04 stores or returns a Google avatar URL.
- `api/client.ts`'s `fetchJson` adds `credentials: 'include'` so the session cookie rides on every request — this replaces its current `supabase.auth.getSession()` bearer-token logic entirely.
- This plan does not touch `PrivacyPage.tsx`'s copy (Plan 07 does that, alongside deleting the Supabase RLS/migration files it currently describes).

---

### Task 1: Rewrite `AuthContext.tsx`

**Files:**
- Modify: `frontend/src/contexts/AuthContext.tsx`
- Test: `frontend/src/contexts/__tests__/AuthContext.test.tsx`

**Interfaces:**
- Consumes: `GET /api/auth/me` (Plan 02), `POST /api/auth/logout` (Plan 02)
- Produces: `useAuth()` returning `{user: {id, email, display_name} | null, activeTenant: {id, name, slug} | null, role: string | null, memberships: Array<{tenant_id, tenant_name, tenant_slug, role}>, loading: boolean, signOut: () => Promise<void>}` — consumed by every one of the 12 `useAuth()` call sites listed in the spec, and by Task 3's tenant switcher (Plan 06) which reads `memberships`

- [ ] **Step 1: Write the failing tests**

Create `frontend/src/contexts/__tests__/AuthContext.test.tsx`:

```tsx
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
          memberships: [{ tenant_id: "t1", tenant_name: "Alice's Workspace", tenant_slug: "alice-ws", role: "admin" }],
        }),
      }),
    )

    render(<AuthProvider><Consumer /></AuthProvider>)

    await waitFor(() => screen.getByText("signed in as alice@example.com"))
    expect(screen.getByText("tenant: Alice's Workspace")).toBeTruthy()
    expect(screen.getByText("role: admin")).toBeTruthy()
    expect(screen.getByText("memberships: 1")).toBeTruthy()
  })

  it("leaves user null on a 401 response", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ ok: false, status: 401 }))

    render(<AuthProvider><Consumer /></AuthProvider>)

    await waitFor(() => screen.getByText("signed out"))
  })

  it("signOut posts to /api/auth/logout and clears state", async () => {
    const fetchMock = vi.fn()
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

    render(<AuthProvider><Consumer /></AuthProvider>)
    await waitFor(() => screen.getByText("signed in as alice@example.com"))

    screen.getByText("sign out").click()

    await waitFor(() => screen.getByText("signed out"))
    expect(fetchMock).toHaveBeenCalledWith("/api/auth/logout", expect.objectContaining({ method: "POST" }))
  })
})
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd frontend && npx vitest run src/contexts/__tests__/AuthContext.test.tsx`
Expected: FAIL — current `AuthContext` reads Supabase state, not `fetch('/api/auth/me')`

- [ ] **Step 3: Rewrite `AuthContext.tsx`**

Replace the entire content of `frontend/src/contexts/AuthContext.tsx`:

```tsx
import { createContext, useContext, useEffect, useState, useCallback, type ReactNode } from "react"

export interface AuthUser {
  id: string
  email: string
  display_name: string | null
}

export interface ActiveTenant {
  id: string
  name: string | null
  slug: string | null
}

export interface Membership {
  tenant_id: string
  tenant_name: string
  tenant_slug: string
  role: string
}

interface AuthContextType {
  user: AuthUser | null
  activeTenant: ActiveTenant | null
  role: string | null
  memberships: Membership[]
  loading: boolean
  signOut: () => Promise<void>
  refresh: () => Promise<void>
}

const AuthContext = createContext<AuthContextType>({
  user: null,
  activeTenant: null,
  role: null,
  memberships: [],
  loading: true,
  signOut: async () => {},
  refresh: async () => {},
})

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<AuthUser | null>(null)
  const [activeTenant, setActiveTenant] = useState<ActiveTenant | null>(null)
  const [role, setRole] = useState<string | null>(null)
  const [memberships, setMemberships] = useState<Membership[]>([])
  const [loading, setLoading] = useState(true)

  const refresh = useCallback(async () => {
    setLoading(true)
    try {
      const res = await fetch("/api/auth/me", { credentials: "include" })
      if (!res.ok) {
        setUser(null)
        setActiveTenant(null)
        setRole(null)
        setMemberships([])
        return
      }
      const body = await res.json()
      setUser(body.user)
      setActiveTenant(body.active_tenant)
      setRole(body.role)
      setMemberships(body.memberships ?? [])
    } catch {
      setUser(null)
      setActiveTenant(null)
      setRole(null)
      setMemberships([])
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    void refresh()
  }, [refresh])

  const signOut = useCallback(async () => {
    await fetch("/api/auth/logout", { method: "POST", credentials: "include" })
    setUser(null)
    setActiveTenant(null)
    setRole(null)
    setMemberships([])
  }, [])

  return (
    <AuthContext.Provider value={{ user, activeTenant, role, memberships, loading, signOut, refresh }}>
      {children}
    </AuthContext.Provider>
  )
}

export const useAuth = () => useContext(AuthContext)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd frontend && npx vitest run src/contexts/__tests__/AuthContext.test.tsx`
Expected: 3 passed

- [ ] **Step 5: Commit**

```bash
git add frontend/src/contexts/AuthContext.tsx frontend/src/contexts/__tests__/AuthContext.test.tsx
git commit -m "Rewrite AuthContext against /api/auth/me, dropping Supabase client"
```

---

### Task 2: Rewrite `AuthPage.tsx` — Google-only sign-in

**Files:**
- Modify: `frontend/src/pages/AuthPage.tsx`

**Interfaces:**
- Consumes: `useAuth()` (Task 1); redirects the browser to `GET /api/auth/login/google` (Plan 02)
- Produces: an `AuthPage` with no email/password form, single "Continue with Google" button that does a full-page redirect

- [ ] **Step 1: Replace `AuthPage.tsx`'s content**

Replace the entire content of `frontend/src/pages/AuthPage.tsx`:

```tsx
import { Navigate, useNavigate } from "react-router"
import { useAuth } from "@/contexts/AuthContext"
import { Toaster, toast } from "sonner"
import { AequitasLogo } from "@/components/shared/AequitasLogo"
import { Seo } from "@/components/shared/Seo"

const HEADLINE_STATS = [
  { label: "GINI COEFF", value: "0.5741", note: "bus service" },
  { label: "PALMA RATIO", value: "5.702×", note: "top 10% vs bottom 40%" },
  { label: "EVENING ISO", value: "15.4%", note: "of LSOAs" },
]

export default function AuthPage() {
  const { user, loading } = useAuth()
  const navigate = useNavigate()

  if (loading) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center">
        <div className="w-2 h-2 rounded-full bg-indigo-500 animate-pulse" />
      </div>
    )
  }

  if (user) return <Navigate to="/dashboard" replace />

  const handleGoogle = async () => {
    try {
      const res = await fetch("/api/auth/login/google", { redirect: "manual" })
      if (res.type === "opaqueredirect" || res.status === 0 || (res.status >= 300 && res.status < 400)) {
        window.location.href = "/api/auth/login/google"
        return
      }
      toast.error("Google sign-in is not configured")
    } catch {
      toast.error("Google sign-in is not configured")
    }
  }

  return (
    <>
      <Seo
        title="Sign In — Aequitas"
        description="Sign in to Aequitas to access policy intelligence analytics for transport equity."
        path="/auth"
        noindex
      />
      <Toaster position="top-right" />
      <div className="min-h-screen bg-background flex">
        {/* Left — branding panel */}
        <div className="hidden lg:flex lg:w-[55%] flex-col justify-between relative overflow-hidden">
          <div className="absolute inset-0 opacity-40 bg-[linear-gradient(to_right,#80808012_1px,transparent_1px),linear-gradient(to_bottom,#80808012_1px,transparent_1px)] bg-[size:24px_24px]" />

          <div className="relative z-10 p-10">
            <button
              onClick={() => navigate("/")}
              className="flex items-center gap-2.5 text-sm font-mono font-bold tracking-widest text-foreground uppercase hover:text-indigo-400 transition-colors"
            >
              <AequitasLogo className="w-5 h-5 text-slate-300" />
              AEQUITAS
            </button>
          </div>

          <div className="relative z-10 p-10 pb-16">
            <div className="h-px bg-indigo-500/40 mb-8 max-w-sm" />
            <h1 className="text-4xl xl:text-5xl font-bold leading-[1.05] tracking-tight mb-5">
              Policy Intelligence
              <br />
              <span className="text-indigo-400">with Evidence.</span>
            </h1>
            <p className="text-sm text-muted-foreground max-w-sm leading-relaxed">
              Evidence-graded analytics for UK bus transport policy. 8 dimensions.
              33,755 LSOAs. Gemini-powered natural language Q&A.
            </p>

            <div className="mt-10 grid grid-cols-3 gap-px max-w-sm">
              {HEADLINE_STATS.map((m) => (
                <div key={m.label} className="bg-card/60 p-3 border border-border">
                  <p className="text-[11px] font-mono uppercase tracking-widest text-muted-foreground/60">
                    {m.label}
                  </p>
                  <p className="text-sm font-mono font-semibold text-indigo-400 mt-1">
                    {m.value}
                  </p>
                  <p className="text-[11px] font-mono text-muted-foreground/40">
                    {m.note}
                  </p>
                </div>
              ))}
            </div>
          </div>

          <div className="relative z-10 p-10 pt-0">
            <p className="text-[11px] text-amber-400 font-mono font-semibold tracking-wide">
              POLICY ANALYSIS TOOL — NOT OFFICIAL DfT GUIDANCE
            </p>
          </div>
        </div>

        {/* Right — sign-in */}
        <div className="flex-1 flex items-center justify-center p-6 sm:p-12 border-l border-border">
          <div className="w-full max-w-sm">
            <div className="lg:hidden mb-10 flex items-center gap-2">
              <AequitasLogo className="w-5 h-5 text-slate-300" />
              <span className="text-sm font-mono font-bold tracking-widest uppercase">AEQUITAS</span>
            </div>

            <h2 className="text-lg font-bold tracking-tight mb-1 text-foreground">
              Welcome
            </h2>
            <p className="text-xs text-muted-foreground mb-8">
              Sign in with Google to access the policy intelligence terminal
            </p>

            <button
              onClick={() => void handleGoogle()}
              className="w-full flex items-center justify-center gap-3 px-4 py-3 rounded border border-border bg-card hover:bg-muted/60 transition-colors text-sm font-medium"
            >
              <svg className="w-4 h-4" viewBox="0 0 24 24">
                <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92a5.06 5.06 0 0 1-2.2 3.32v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.1z"/>
                <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/>
                <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"/>
                <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"/>
              </svg>
              Continue with Google
            </button>
          </div>
        </div>
      </div>
    </>
  )
}
```

Note: `handleGoogle`'s `fetch(..., {redirect: 'manual'})` pre-check follows WorkforceGuard's pattern of surfacing config errors before navigating away from the SPA — a browser `fetch` with `redirect: 'manual'` against a redirecting endpoint returns an opaque response (`type: 'opaqueredirect'`) rather than following it, which lets this code detect "the backend responded with a redirect" (success — proceed with `window.location.href`) versus "the backend errored" (show a toast instead of silently navigating to a broken page).

- [ ] **Step 2: Verify the frontend builds**

Run: `cd frontend && npm run build`
Expected: build completes with no TypeScript errors

- [ ] **Step 3: Commit**

```bash
git add frontend/src/pages/AuthPage.tsx
git commit -m "Rewrite AuthPage as Google-only sign-in, dropping email/password form"
```

---

### Task 3: `api/client.ts` — cookie credentials instead of bearer token

**Files:**
- Modify: `frontend/src/api/client.ts`

**Interfaces:**
- Consumes: nothing (no more Supabase import)
- Produces: `fetchJson<T>(path, params?) -> Promise<T>` with `credentials: 'include'` on every request; a 401 response triggers a state-clearing side effect

- [ ] **Step 1: Rewrite `client.ts`**

Replace the entire content of `frontend/src/api/client.ts`:

```ts
const BASE = "/api"

export async function fetchJson<T>(path: string, params?: Record<string, string>): Promise<T> {
  const url = new URL(`${BASE}${path}`, window.location.origin)
  if (params) {
    Object.entries(params).forEach(([k, v]) => url.searchParams.set(k, v))
  }

  const res = await fetch(url.toString(), { credentials: "include" })
  if (!res.ok) throw new Error(`API ${res.status}: ${await res.text()}`)
  return res.json() as Promise<T>
}
```

Note: no explicit 401-interceptor side effect is added here beyond the thrown error — per the spec's Frontend section, "a 401 interceptor clears auth state (matches WorkforceGuard's pattern)." Since `fetchJson` is a plain function (not a class with access to `AuthContext`), the simplest compliant approach is: callers that need to react to a 401 (e.g. redirecting to `/auth`) catch the thrown error and call `useAuth()`'s exposed `refresh()` (added in Task 1's `AuthContext`, which re-fetches `/api/auth/me` and will naturally clear state on a 401). This plan does not add a global interceptor since `fetchJson` has no React context access; components needing this behavior call `refresh()` from `useAuth()` in their own catch blocks. Confirm no existing caller special-cased a bearer-token-401 scenario before treating this as complete — grep with the command in Step 2.

- [ ] **Step 2: Confirm no remaining reference to the old Authorization-header logic**

Run: `grep -rn "Authorization" frontend/src/api/`
Expected: no output

- [ ] **Step 3: Verify the frontend builds**

Run: `cd frontend && npm run build`
Expected: build completes with no errors

- [ ] **Step 4: Commit**

```bash
git add frontend/src/api/client.ts
git commit -m "Switch api/client.ts to cookie credentials, drop Supabase bearer-token logic"
```

---

### Task 4: Update `useChat.ts` and `DimensionPage.tsx` — drop manual token attachment

**Files:**
- Modify: `frontend/src/hooks/useChat.ts`
- Modify: `frontend/src/components/dimension/DimensionPage.tsx`

**Interfaces:**
- Consumes: nothing new — both files' own `fetch` calls gain `credentials: 'include'` in place of the manual `Authorization` header they built from `supabase.auth.getSession()`
- Produces: no Supabase import remains in either file

- [ ] **Step 1: Update `useChat.ts`**

`frontend/src/hooks/useChat.ts` currently imports `supabase` and calls `supabase.auth.getSession()` to attach a bearer token (confirmed at lines 1 and 11 of the existing file). Replace:

```ts
import { supabase } from "@/integrations/supabase/client"

const BASE = "/api"

export async function fetchJson<T>(path: string, params?: Record<string, string>): Promise<T> {
  const url = new URL(`${BASE}${path}`, window.location.origin)
  if (params) {
    Object.entries(params).forEach(([k, v]) => url.searchParams.set(k, v))
  }
  
  const { data: { session } } = await supabase.auth.getSession()
  const headers: Record<string, string> = {}
  if (session?.access_token) {
    headers["Authorization"] = `Bearer ${session.access_token}`
  }

  const res = await fetch(url.toString(), { headers })
  if (!res.ok) throw new Error(`API ${res.status}: ${await res.text()}`)
  return res.json() as Promise<T>
}
```

with:

```ts
const BASE = "/api"

export async function fetchJson<T>(path: string, params?: Record<string, string>): Promise<T> {
  const url = new URL(`${BASE}${path}`, window.location.origin)
  if (params) {
    Object.entries(params).forEach(([k, v]) => url.searchParams.set(k, v))
  }

  const res = await fetch(url.toString(), { credentials: "include" })
  if (!res.ok) throw new Error(`API ${res.status}: ${await res.text()}`)
  return res.json() as Promise<T>
}
```

Note: this file duplicates `api/client.ts`'s `fetchJson` under a different name/location — that duplication predates this migration (both existed with near-identical Supabase logic) and is out of scope to consolidate here; this plan only removes the Supabase dependency from each, not the duplication itself.

Read the rest of `useChat.ts` first — this replacement only covers the fragment shown above (which per the earlier grep is lines 1-20 of the file, matching its known content). If the actual file has additional logic beyond line 20 using `session` or `supabase` elsewhere, grep for it before finalizing:

Run: `grep -n "supabase\|session" frontend/src/hooks/useChat.ts`
Expected after the edit above: no output

- [ ] **Step 2: Update `DimensionPage.tsx`**

`frontend/src/components/dimension/DimensionPage.tsx` imports `supabase` at line 5 and calls `supabase.auth.getSession()` at line 100 (confirmed) for its PDF export fetch. Find that fetch call:

Run: `grep -n "supabase\|getSession\|/api/export" frontend/src/components/dimension/DimensionPage.tsx`

Then remove the `import { supabase } from "@/integrations/supabase/client"` line, and replace the pattern:

```tsx
const { data: { session } } = await supabase.auth.getSession()
// ... uses session?.access_token to build an Authorization header for the export fetch
```

with a direct `fetch(..., { credentials: 'include' })` call that drops the `Authorization` header entirely — the exact surrounding code (how the export URL and filename are built) must be read from the live file before editing, since it wasn't fully captured in the grep above. Read the full function containing this fetch call, then apply the same `credentials: 'include'` substitution pattern used in Task 3.

- [ ] **Step 3: Confirm no remaining Supabase imports in either file**

Run: `grep -ln "supabase" frontend/src/hooks/useChat.ts frontend/src/components/dimension/DimensionPage.tsx`
Expected: no output

- [ ] **Step 4: Verify the frontend builds and typechecks**

Run: `cd frontend && npm run build && npx tsc --noEmit -p tsconfig.json`
Expected: both succeed with no errors

- [ ] **Step 5: Commit**

```bash
git add frontend/src/hooks/useChat.ts frontend/src/components/dimension/DimensionPage.tsx
git commit -m "Drop manual Supabase token attachment from useChat and DimensionPage export"
```

---

### Task 5: Update `UserMenu.tsx` and `ProfilePage.tsx` — new user shape, wire policy_interests

**Files:**
- Modify: `frontend/src/components/layout/UserMenu.tsx`
- Modify: `frontend/src/pages/ProfilePage.tsx`

**Interfaces:**
- Consumes: `useAuth()`'s new `user: AuthUser` shape (Task 1) — `{id, email, display_name}`, no `user_metadata`; `GET /api/profile` / `PATCH /api/profile` (Plan 04, Task 6)
- Produces: both components render correctly with the new user shape; `ProfilePage.tsx`'s Policy Interests picker persists via the new `/api/profile` routes instead of local-only `useState`

- [ ] **Step 1: Update `UserMenu.tsx`**

In `frontend/src/components/layout/UserMenu.tsx`, replace the avatar/name derivation (currently lines 79-81, reading Supabase's `user_metadata`):

```tsx
  const rawAvatar = user.user_metadata?.["avatar_url"] ?? user.user_metadata?.["picture"]
  const avatar = typeof rawAvatar === "string" ? rawAvatar : undefined
  const rawName = user.user_metadata?.["full_name"] ?? user.user_metadata?.["name"] ?? user.email?.split("@")[0]
  const name = typeof rawName === "string" ? rawName : undefined
```

with:

```tsx
  const name = user.display_name ?? user.email.split("@")[0]
```

Then find the JSX block rendering the avatar image (the `{avatar && !imgError ? (...) : (...)}` conditional around line 99-111) and replace it with just the fallback branch, since no avatar URL exists in the new schema:

```tsx
        <div className="w-6 h-6 rounded bg-muted flex items-center justify-center border border-border">
          <User className="w-3 h-3 text-muted-foreground" />
        </div>
```

Remove the now-unused `imgError`/`setImgError` state (`const [imgError, setImgError] = useState(false)`) since nothing references it anymore.

- [ ] **Step 2: Update `ProfilePage.tsx`**

Replace the entire content of `frontend/src/pages/ProfilePage.tsx`:

```tsx
import { useState, useEffect } from "react"
import { useAuth } from "@/contexts/AuthContext"
import { useNavigate } from "react-router"
import { ArrowLeft, User } from "lucide-react"

const DIMENSIONS = [
  "Equity & Deprivation",
  "Accessibility",
  "Service Quality",
  "Route Network",
  "Modal Shift & Carbon",
  "Economic Appraisal",
  "Bus Services Act 2025",
  "Policy Scenarios",
]

export default function ProfilePage() {
  const { user, signOut } = useAuth()
  const navigate = useNavigate()
  const [selectedDimensions, setSelectedDimensions] = useState<string[]>([])
  const [loaded, setLoaded] = useState(false)

  useEffect(() => {
    if (!user) return
    fetch("/api/profile", { credentials: "include" })
      .then((res) => (res.ok ? res.json() : { policy_interests: [] }))
      .then((body) => {
        setSelectedDimensions(body.policy_interests ?? [])
        setLoaded(true)
      })
      .catch(() => setLoaded(true))
  }, [user])

  if (!user) return null

  const name = user.display_name ?? user.email.split("@")[0]

  const toggleDimension = (d: string) => {
    const next = selectedDimensions.includes(d)
      ? selectedDimensions.filter((x) => x !== d)
      : [...selectedDimensions, d]
    setSelectedDimensions(next)
    void fetch("/api/profile", {
      method: "PATCH",
      credentials: "include",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ policy_interests: next }),
    })
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

        <div className="flex items-center gap-4 mb-10">
          <div className="w-12 h-12 rounded bg-muted flex items-center justify-center border border-border">
            <User className="w-5 h-5 text-muted-foreground" />
          </div>
          <div>
            <p className="text-sm font-semibold text-foreground">{name}</p>
            <p className="text-xs text-muted-foreground font-mono">{user.email}</p>
          </div>
        </div>

        <section className="mb-8">
          <h2 className="text-[11px] uppercase tracking-[0.15em] text-muted-foreground font-mono mb-4">
            Policy Interests
          </h2>
          <div className="flex flex-wrap gap-2">
            {DIMENSIONS.map((d) => (
              <button
                key={d}
                disabled={!loaded}
                onClick={() => toggleDimension(d)}
                className={`px-3 py-1.5 rounded text-xs font-mono transition-colors border ${
                  selectedDimensions.includes(d)
                    ? "bg-indigo-600 text-white border-indigo-600"
                    : "bg-muted/30 text-muted-foreground border-border hover:border-indigo-500/40"
                }`}
              >
                {d}
              </button>
            ))}
          </div>
        </section>

        <section className="border-t border-border pt-8">
          <h2 className="text-[11px] uppercase tracking-[0.15em] text-muted-foreground font-mono mb-4">
            Account
          </h2>
          <button
            onClick={async () => { await signOut(); navigate("/auth") }}
            className="px-4 py-2 text-xs font-mono text-red-400 border border-red-400/30 rounded hover:bg-red-400/10 transition-colors"
          >
            SIGN OUT
          </button>
        </section>
      </div>
    </div>
  )
}
```

- [ ] **Step 3: Verify the frontend builds and typechecks**

Run: `cd frontend && npm run build && npx tsc --noEmit -p tsconfig.json`
Expected: both succeed with no errors

- [ ] **Step 4: Manual verification in browser (dev server)**

Run: `cd frontend && npm run dev` (with the backend running separately with `DEV_AUTH_BYPASS=true`)

Navigate to `/profile`, confirm the page loads, toggle a Policy Interests chip, refresh the page, and confirm the toggled selection persisted (proves the `GET`/`PATCH /api/profile` round-trip works, not just that the UI renders).

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/layout/UserMenu.tsx frontend/src/pages/ProfilePage.tsx
git commit -m "Update UserMenu and ProfilePage for new user shape, wire Policy Interests to /api/profile"
```

---

### Task 6: Rewrite `ChatSidebar.tsx` and delete `lib/db.ts` / `integrations/supabase/client.ts`

**Files:**
- Modify: `frontend/src/components/chat/ChatSidebar.tsx`
- Delete: `frontend/src/lib/db.ts`
- Delete: `frontend/src/integrations/supabase/client.ts` (and the now-empty `frontend/src/integrations/supabase/` directory, if nothing else lives there)
- Test: check for any other importer of `lib/db.ts` before deleting

**Interfaces:**
- Consumes: `GET/POST/DELETE /api/conversations`, `GET/POST /api/conversations/{id}/messages` (Plan 04, Task 2)
- Produces: `ChatSidebar.tsx` fully functional with zero Supabase imports; `lib/db.ts` and the Supabase client module no longer exist anywhere in the tree

- [ ] **Step 1: Find every remaining importer of `lib/db.ts`**

Run: `grep -rln "from [\"']@/lib/db[\"']\|from [\"']\.\./\.\./lib/db[\"']\|from [\"']\./db[\"']" frontend/src/ --include="*.tsx" --include="*.ts"`

Expected output should include `ChatSidebar.tsx` and likely `SavedAnalyses.tsx`, `PolicyNotes.tsx`, `SavedRegions.tsx` (the three pages driving `/saved`, `/notes`, `/regions` per the spec's routing table) — **these three pages are out of scope for this plan's task list but must not be left broken.** If they import from `lib/db.ts`, they need the same fetch-based rewrite pattern as `ChatSidebar.tsx` below before `lib/db.ts` can actually be deleted. Read each file this grep returns, and for any beyond `ChatSidebar.tsx`, apply the equivalent of Step 2 below (swap `db.ts` function calls for direct `fetch` calls against `/api/saved-analyses`, `/api/policy-notes`, `/api/saved-regions` respectively, using the exact JSON field names Plan 04's routers return — `title`/`content`/`section_id`/`dimension`/`tags` for saved-analyses; `dimension`/`region`/`stance`/`thesis`/`critique` for policy-notes; `region_code`/`region_name`/`notes` for saved-regions). This is a mechanical, per-file repeat of Step 2's pattern — apply it to each file the grep surfaces, then re-run the grep to confirm zero remaining importers before Step 4's deletion.

- [ ] **Step 2: Rewrite `ChatSidebar.tsx`**

In `frontend/src/components/chat/ChatSidebar.tsx`, replace:

```tsx
import { listConversations, deleteConversation, type ConversationRow } from "@/lib/db"
```

with a local type definition and inline fetch calls (no more `lib/db.ts` import):

```tsx
interface ConversationRow {
  id: string
  user_id: string
  title: string
  created_at: string
  updated_at: string
}

async function listConversations(): Promise<ConversationRow[]> {
  const res = await fetch("/api/conversations", { credentials: "include" })
  if (!res.ok) return []
  return res.json()
}

async function deleteConversation(id: string): Promise<void> {
  await fetch(`/api/conversations/${id}`, { method: "DELETE", credentials: "include" })
}
```

Then update the two call sites that previously passed `user.id`:

```tsx
  const refresh = useCallback(async () => {
    if (!user) return
    setLoading(true)
    try {
      const data = await listConversations(user.id)
      setConversations(data)
    } catch {
      // silently ignore — list will be stale
    } finally {
      setLoading(false)
    }
  }, [user])
```

becomes:

```tsx
  const refresh = useCallback(async () => {
    if (!user) return
    setLoading(true)
    try {
      const data = await listConversations()
      setConversations(data)
    } catch {
      // silently ignore — list will be stale
    } finally {
      setLoading(false)
    }
  }, [user])
```

(`listConversations()` no longer takes a `userId` argument, since the backend derives tenant scope from the session cookie, not a client-supplied id — remove the argument at the call site.)

- [ ] **Step 3: Delete `lib/db.ts` and the Supabase client module**

```bash
git rm frontend/src/lib/db.ts frontend/src/integrations/supabase/client.ts
```

Then check whether `frontend/src/integrations/supabase/` is now empty:

Run: `ls frontend/src/integrations/supabase/ 2>/dev/null`

If empty (or the directory no longer exists after `git rm`), no further action needed — `git rm` on the last file in a directory removes the directory implicitly when committed. If other files remain in that directory, leave them — this plan only deletes the Supabase client, not the whole `integrations/` tree.

- [ ] **Step 4: Verify the frontend builds and typechecks with zero remaining Supabase references**

Run: `grep -rln "supabase" frontend/src/ --include="*.ts" --include="*.tsx" -i`
Expected: no output (this confirms Task 4's `useChat.ts`/`DimensionPage.tsx` changes and this task's `ChatSidebar.tsx`/`db.ts` changes together eliminated every Supabase reference in the source tree — `@supabase/supabase-js` itself still sits in `package.json` until Plan 07, but nothing imports it)

Run: `cd frontend && npm run build && npx tsc --noEmit -p tsconfig.json`
Expected: both succeed with no errors

- [ ] **Step 5: Manual verification in browser**

With the backend running (`DEV_AUTH_BYPASS=true`) and frontend dev server running, navigate to `/dashboard`, open the chat sidebar, create a new conversation, send a message, confirm it persists across a page refresh, then delete the conversation and confirm it disappears from the list.

- [ ] **Step 6: Commit**

```bash
git add frontend/src/components/chat/ChatSidebar.tsx
git add -u frontend/src/lib/db.ts frontend/src/integrations/supabase/client.ts
git commit -m "Rewrite ChatSidebar against /api/conversations, delete lib/db.ts and Supabase client"
```

---

### Task 7: Update `ProtectedRoute.test.tsx` mock shape

**Files:**
- Modify: `frontend/src/components/auth/__tests__/ProtectedRoute.test.tsx`

**Interfaces:**
- Consumes: nothing new — `ProtectedRoute.tsx` itself only reads `user`/`loading` from `useAuth()` and needs no logic change (confirmed unaffected in the spec's "Confirmed unaffected" section)
- Produces: the existing 3 tests pass against the new `useAuth()` mock shape

- [ ] **Step 1: Update the three `vi.mocked(useAuth).mockReturnValue(...)` calls**

In `frontend/src/components/auth/__tests__/ProtectedRoute.test.tsx`, each of the three test cases currently mocks the old shape `{ user, session, loading, signOut }`. Update all three to the new shape:

```tsx
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
    vi.mocked(useAuth).mockReturnValue({
      user: null, activeTenant: null, role: null, memberships: [],
      loading: true, signOut: vi.fn(), refresh: vi.fn(),
    })
    const { container } = render(
      <MemoryRouter>
        <ProtectedRoute><div>Protected</div></ProtectedRoute>
      </MemoryRouter>,
    )
    expect(container.querySelector(".animate-pulse")).toBeTruthy()
  })

  it("renders children when user is authenticated", () => {
    vi.mocked(useAuth).mockReturnValue({
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      user: { id: "u1", email: "a@example.com", display_name: "A" } as any,
      activeTenant: null, role: "admin", memberships: [],
      loading: false, signOut: vi.fn(), refresh: vi.fn(),
    })
    render(
      <MemoryRouter>
        <ProtectedRoute><div>Protected Content</div></ProtectedRoute>
      </MemoryRouter>,
    )
    expect(screen.getByText("Protected Content")).toBeTruthy()
  })

  it("redirects to /auth when unauthenticated", () => {
    vi.mocked(useAuth).mockReturnValue({
      user: null, activeTenant: null, role: null, memberships: [],
      loading: false, signOut: vi.fn(), refresh: vi.fn(),
    })
    const { container } = render(
      <MemoryRouter initialEntries={["/"]}>
        <ProtectedRoute><div>Protected</div></ProtectedRoute>
      </MemoryRouter>,
    )
    expect(container.querySelector("div:not(:empty)")).toBeNull()
  })
})
```

- [ ] **Step 2: Run the test to verify it passes**

Run: `cd frontend && npx vitest run src/components/auth/__tests__/ProtectedRoute.test.tsx`
Expected: 3 passed

- [ ] **Step 3: Run the full frontend suite**

Run: `cd frontend && npx vitest run`
Expected: all tests pass (16 pre-existing + this plan's new `AuthContext.test.tsx` tests, with `ProtectedRoute.test.tsx` updated in place)

- [ ] **Step 4: Commit**

```bash
git add frontend/src/components/auth/__tests__/ProtectedRoute.test.tsx
git commit -m "Update ProtectedRoute test mocks to new AuthContext shape"
```

---

## Handoff

At the end of this plan: the frontend has zero Supabase imports anywhere in `frontend/src/`. `AuthContext`, `AuthPage`, `ChatSidebar`, `useChat`, `DimensionPage`'s export flow, `UserMenu`, and `ProfilePage` all talk to the FastAPI backend via cookie-session `fetch` calls. `@supabase/supabase-js` is still in `frontend/package.json` (unused but not yet removed) and `lib/db.ts`/`integrations/supabase/client.ts` are deleted from the tree. A full Google OAuth round-trip can be manually verified end-to-end on localhost.

Plan `06-frontend-tenant-ui.md` begins here: it adds the tenant switcher, invite-management panel, member list, and the public `/invite/:token` accept page — all new UI surfaces, none of which existed before this migration.
