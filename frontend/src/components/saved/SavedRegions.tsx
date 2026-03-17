import { useState, useEffect } from "react"
import { useAuth } from "@/contexts/AuthContext"
import { listSavedRegions, deleteSavedRegion, type SavedRegionRow } from "@/lib/db"
import { Trash2, MapPin } from "lucide-react"

export function SavedRegions() {
  const { user } = useAuth()
  const [regions, setRegions] = useState<SavedRegionRow[]>([])
  const [loading, setLoading] = useState(true)

  const refresh = async () => {
    if (!user) return
    setLoading(true)
    const data = await listSavedRegions(user.id)
    setRegions(data)
    setLoading(false)
  }

  useEffect(() => { void refresh() }, [user])

  const handleDelete = async (id: string) => {
    await deleteSavedRegion(id)
    void refresh()
  }

  if (loading) {
    return <div className="flex justify-center py-16"><div className="w-2 h-2 rounded-full bg-indigo-500 animate-pulse" /></div>
  }

  if (regions.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-16 text-center">
        <MapPin className="w-8 h-8 text-muted-foreground/20 mb-3" />
        <p className="text-sm text-muted-foreground">No tracked regions yet.</p>
        <p className="text-xs text-muted-foreground/60 mt-1">Save regions from the filter panel to track them here.</p>
      </div>
    )
  }

  return (
    <div className="space-y-2">
      {regions.map((r) => (
        <div key={r.id} className="border border-border rounded bg-card p-4 flex items-start gap-3">
          <MapPin className="w-4 h-4 text-indigo-400 mt-0.5 shrink-0" />
          <div className="flex-1 min-w-0">
            <p className="text-sm font-medium text-foreground">{r.region_name}</p>
            <p className="text-[10px] font-mono text-muted-foreground/40 mt-0.5">{r.region_code}</p>
            {r.notes && <p className="text-xs text-muted-foreground mt-1">{r.notes}</p>}
          </div>
          <button
            onClick={() => void handleDelete(r.id)}
            className="p-1.5 rounded hover:bg-red-500/10 text-muted-foreground/40 hover:text-red-400 transition-colors shrink-0"
          >
            <Trash2 className="w-3.5 h-3.5" />
          </button>
        </div>
      ))}
    </div>
  )
}
