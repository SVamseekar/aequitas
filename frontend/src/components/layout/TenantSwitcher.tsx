import { useAuth } from "@/contexts/AuthContext"
import { apiPost } from "@/api/client"
import { Building2, ChevronDown } from "lucide-react"
import { useState, useRef, useEffect } from "react"

/** Dropdown shown when the user belongs to more than one tenant. */
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

  const switchTenant = async (tenantId: string) => {
    await apiPost("/session/switch-tenant", { tenant_id: tenantId })
    await refresh()
    setOpen(false)
  }

  return (
    <div className="relative" ref={ref}>
      <button
        onClick={() => setOpen(!open)}
        className="flex items-center gap-1.5 px-2 py-1 rounded border border-border hover:bg-muted/40 text-[11px] font-mono text-muted-foreground max-w-[160px]"
        aria-label="Switch workspace"
      >
        <Building2 className="w-3 h-3 shrink-0" />
        <span className="truncate">{activeTenant?.name ?? "Workspace"}</span>
        <ChevronDown className="w-3 h-3 shrink-0" />
      </button>
      {open && (
        <div className="absolute right-0 top-full mt-1 w-56 py-1 rounded bg-card border border-border shadow-lg z-50">
          {memberships.map((m) => (
            <button
              key={m.tenant_id}
              onClick={() => void switchTenant(m.tenant_id)}
              className={`w-full text-left px-3 py-2 text-xs font-mono hover:bg-muted/50 ${
                m.tenant_id === activeTenant?.id
                  ? "text-indigo-400"
                  : "text-foreground"
              }`}
            >
              {m.tenant_name}
              <span className="text-muted-foreground ml-2">{m.role}</span>
            </button>
          ))}
        </div>
      )}
    </div>
  )
}
