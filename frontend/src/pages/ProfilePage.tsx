import { useState, useEffect, useCallback } from "react"
import { useAuth } from "@/contexts/AuthContext"
import { useNavigate } from "react-router"
import { ArrowLeft, User, Copy, Check } from "lucide-react"
import { fetchJson, apiPatch, apiPost, apiDelete } from "@/api/client"

/** Labels match app DIMENSIONS in lib/constants.ts (policy interests). */
const DIMENSIONS = [
  "Equity & Deprivation",
  "Accessibility",
  "Service Quality",
  "Route Network",
  "Socio-Economic & ML",
  "Economic Appraisal",
  "Bus Services Act 2025",
  "Policy Scenarios",
]

interface MemberRow {
  user_id: string
  email: string
  display_name: string | null
  role: string
}

export default function ProfilePage() {
  const { user, activeTenant, role, memberships, signOut, refresh } = useAuth()
  const navigate = useNavigate()
  const [selectedDimensions, setSelectedDimensions] = useState<string[]>([])
  const [inviteEmail, setInviteEmail] = useState("")
  const [inviteLink, setInviteLink] = useState<string | null>(null)
  const [copied, setCopied] = useState(false)
  const [members, setMembers] = useState<MemberRow[]>([])
  const [inviteError, setInviteError] = useState<string | null>(null)

  const loadProfile = useCallback(async () => {
    try {
      const profile = await fetchJson<{ policy_interests: string[] }>("/profile")
      setSelectedDimensions(profile.policy_interests ?? [])
    } catch {
      // ignore
    }
  }, [])

  const loadMembers = useCallback(async () => {
    if (!activeTenant?.id || role !== "admin") return
    try {
      const data = await fetchJson<MemberRow[]>(`/tenants/${activeTenant.id}/members`)
      setMembers(data)
    } catch {
      setMembers([])
    }
  }, [activeTenant?.id, role])

  useEffect(() => {
    void loadProfile()
  }, [loadProfile])

  useEffect(() => {
    void loadMembers()
  }, [loadMembers])

  if (!user) return null

  const name = user.display_name ?? user.email?.split("@")[0]

  const toggleDimension = async (d: string) => {
    const next = selectedDimensions.includes(d)
      ? selectedDimensions.filter((x) => x !== d)
      : [...selectedDimensions, d]
    setSelectedDimensions(next)
    try {
      await apiPatch("/profile", { policy_interests: next })
    } catch {
      // revert on failure
      void loadProfile()
    }
  }

  const handleInvite = async () => {
    if (!activeTenant?.id || !inviteEmail.trim()) return
    setInviteError(null)
    try {
      const res = await apiPost<{ token: string; link: string }>(
        `/tenants/${activeTenant.id}/invites`,
        { email: inviteEmail.trim(), role: "member" },
      )
      setInviteLink(res.link)
      setInviteEmail("")
    } catch (e) {
      setInviteError(e instanceof Error ? e.message : "Invite failed")
    }
  }

  const handleCopy = async () => {
    if (!inviteLink) return
    await navigator.clipboard.writeText(inviteLink)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  const handleRemoveMember = async (userId: string) => {
    if (!activeTenant?.id) return
    await apiDelete(`/tenants/${activeTenant.id}/members/${userId}`)
    void loadMembers()
  }

  const handleSwitchTenant = async (tenantId: string) => {
    await apiPost("/session/switch-tenant", { tenant_id: tenantId })
    await refresh()
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
            {activeTenant?.name && (
              <p className="text-[11px] text-indigo-400 font-mono mt-1">
                {activeTenant.name}
                {role ? ` · ${role}` : ""}
              </p>
            )}
          </div>
        </div>

        {memberships.length > 1 && (
          <section className="mb-8">
            <h2 className="text-[11px] uppercase tracking-[0.15em] text-muted-foreground font-mono mb-4">
              Workspaces
            </h2>
            <div className="space-y-1">
              {memberships.map((m) => (
                <button
                  key={m.tenant_id}
                  onClick={() => void handleSwitchTenant(m.tenant_id)}
                  className={`w-full text-left px-3 py-2 rounded border text-xs font-mono transition-colors ${
                    m.tenant_id === activeTenant?.id
                      ? "border-indigo-500/40 bg-indigo-500/10 text-foreground"
                      : "border-border hover:bg-muted/40 text-muted-foreground"
                  }`}
                >
                  {m.tenant_name} · {m.role}
                </button>
              ))}
            </div>
          </section>
        )}

        <section className="mb-8">
          <h2 className="text-[11px] uppercase tracking-[0.15em] text-muted-foreground font-mono mb-4">
            Policy Interests
          </h2>
          <div className="flex flex-wrap gap-2">
            {DIMENSIONS.map((d) => (
              <button
                key={d}
                onClick={() => void toggleDimension(d)}
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

        {role === "admin" && activeTenant && (
          <section className="mb-8 border-t border-border pt-8">
            <h2 className="text-[11px] uppercase tracking-[0.15em] text-muted-foreground font-mono mb-4">
              Invite members
            </h2>
            <div className="flex gap-2 mb-3">
              <input
                type="email"
                value={inviteEmail}
                onChange={(e) => setInviteEmail(e.target.value)}
                placeholder="colleague@lta.gov.uk"
                className="flex-1 px-3 py-2 text-xs bg-muted/50 border border-border rounded font-mono text-foreground"
              />
              <button
                onClick={() => void handleInvite()}
                className="px-3 py-2 text-xs font-mono bg-indigo-600 text-white rounded hover:bg-indigo-500"
              >
                INVITE
              </button>
            </div>
            {inviteError && (
              <p className="text-xs text-red-400 mb-2 font-mono">{inviteError}</p>
            )}
            {inviteLink && (
              <div className="flex items-center gap-2 p-2 border border-border rounded bg-muted/30">
                <code className="text-[11px] font-mono flex-1 truncate">{inviteLink}</code>
                <button
                  onClick={() => void handleCopy()}
                  className="p-1.5 rounded hover:bg-muted text-muted-foreground"
                  aria-label="Copy invite link"
                >
                  {copied ? (
                    <Check className="w-3.5 h-3.5 text-green-400" />
                  ) : (
                    <Copy className="w-3.5 h-3.5" />
                  )}
                </button>
              </div>
            )}

            {members.length > 0 && (
              <div className="mt-6">
                <h3 className="text-[11px] uppercase tracking-[0.15em] text-muted-foreground font-mono mb-3">
                  Members
                </h3>
                <div className="space-y-1">
                  {members.map((m) => (
                    <div
                      key={m.user_id}
                      className="flex items-center justify-between px-3 py-2 border border-border rounded text-xs"
                    >
                      <div>
                        <span className="font-mono text-foreground">
                          {m.display_name ?? m.email}
                        </span>
                        <span className="text-muted-foreground font-mono ml-2">
                          {m.role}
                        </span>
                      </div>
                      {m.user_id !== user.id && (
                        <button
                          onClick={() => void handleRemoveMember(m.user_id)}
                          className="text-red-400 hover:text-red-300 font-mono text-[11px]"
                        >
                          REMOVE
                        </button>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            )}
          </section>
        )}

        <section className="border-t border-border pt-8">
          <h2 className="text-[11px] uppercase tracking-[0.15em] text-muted-foreground font-mono mb-4">
            Account
          </h2>
          <button
            onClick={async () => {
              await signOut()
              navigate("/auth")
            }}
            className="px-4 py-2 text-xs font-mono text-red-400 border border-red-400/30 rounded hover:bg-red-400/10 transition-colors"
          >
            SIGN OUT
          </button>
        </section>
      </div>
    </div>
  )
}
