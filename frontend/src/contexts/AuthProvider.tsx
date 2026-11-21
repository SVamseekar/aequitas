import { useEffect, useState, useCallback, type ReactNode } from "react"
import { AuthContext, type AuthUser, type ActiveTenant, type Membership } from "./AuthContext"

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
    <AuthContext.Provider
      value={{ user, activeTenant, role, memberships, loading, signOut, refresh }}
    >
      {children}
    </AuthContext.Provider>
  )
}
