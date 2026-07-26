import { useEffect, useState } from "react"
import { useNavigate, useParams } from "react-router"
import { useAuth } from "@/contexts/AuthContext"
import { fetchJson, apiPost } from "@/api/client"
import { Seo } from "@/components/shared/Seo"

export default function InviteAcceptPage() {
  const { token } = useParams<{ token: string }>()
  const { user, loading, refresh } = useAuth()
  const navigate = useNavigate()
  const [tenantName, setTenantName] = useState<string | null>(null)
  const [role, setRole] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [accepting, setAccepting] = useState(false)

  useEffect(() => {
    if (!token) return
    void (async () => {
      try {
        const data = await fetchJson<{ tenant_name: string; role: string }>(
          `/invites/${token}`,
        )
        setTenantName(data.tenant_name)
        setRole(data.role)
      } catch (e) {
        setError(e instanceof Error ? e.message : "Invite not found")
      }
    })()
  }, [token])

  const handleAccept = async () => {
    if (!token) return
    if (!user) {
      // Preserve invite token through OAuth via query param on return is not
      // automatic; send user to auth then they can re-open the invite link.
      navigate(`/auth?returnTo=/invite/${token}`)
      return
    }
    setAccepting(true)
    try {
      await apiPost(`/invites/${token}/accept`)
      await refresh()
      navigate("/dashboard")
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not accept invite")
      setAccepting(false)
    }
  }

  return (
    <>
      <Seo title="Accept invite — Aequitas" path={`/invite/${token ?? ""}`} noindex />
      <div className="min-h-screen app-atmosphere flex items-center justify-center p-6">
        <div className="w-full max-w-md app-glass-strong rounded-2xl border border-white/60 p-8">
          {loading ? (
            <div className="flex justify-center py-8">
              <div className="w-2 h-2 rounded-full bg-primary animate-pulse" />
            </div>
          ) : error ? (
            <div>
              <h1 className="text-lg font-bold mb-2">Invite unavailable</h1>
              <p className="text-sm text-muted-foreground">{error}</p>
            </div>
          ) : (
            <div>
              <h1 className="text-lg font-bold mb-2">Join workspace</h1>
              <p className="text-sm text-muted-foreground mb-6">
                You&apos;ve been invited to join{" "}
                <span className="text-foreground font-medium">
                  {tenantName ?? "a workspace"}
                </span>
                {role ? ` as ${role}` : ""}.
              </p>
              <button
                onClick={() => void handleAccept()}
                disabled={accepting}
                className="w-full px-4 py-3 text-sm font-medium bg-primary text-white rounded hover:bg-primary/90 disabled:opacity-50"
              >
                {user
                  ? accepting
                    ? "Accepting…"
                    : "Accept invite"
                  : "Sign in to accept"}
              </button>
            </div>
          )}
        </div>
      </div>
    </>
  )
}
