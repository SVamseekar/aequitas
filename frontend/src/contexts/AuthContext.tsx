import {
  createContext,
  useContext,
  useEffect,
  useState,
  useCallback,
  type ReactNode,
} from "react"

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
    <AuthContext.Provider
      value={{ user, activeTenant, role, memberships, loading, signOut, refresh }}
    >
      {children}
    </AuthContext.Provider>
  )
}

export const useAuth = () => useContext(AuthContext)
