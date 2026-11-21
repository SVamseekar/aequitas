import { createContext, useContext } from "react"

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

export const AuthContext = createContext<AuthContextType>({
  user: null,
  activeTenant: null,
  role: null,
  memberships: [],
  loading: true,
  signOut: async () => {},
  refresh: async () => {},
})


export const useAuth = () => useContext(AuthContext)
