import { useState, useEffect, useCallback } from "react"
import { useAuth } from "@/contexts/AuthContext"
import { listPolicyNotes, createPolicyNote, deletePolicyNote, type PolicyNoteRow } from "@/lib/db"
import { Plus, Trash2, FileText } from "lucide-react"

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
  const [form, setForm] = useState<{ dimension: string; region: string; stance: "priority" | "monitor" | "adequate"; thesis: string }>(
    { dimension: "equity", region: "all", stance: "monitor", thesis: "" }
  )

  const refresh = useCallback(async () => {
    if (!user) return
    setLoading(true)
    const data = await listPolicyNotes(user.id)
    setNotes(data)
    setLoading(false)
  }, [user])

  useEffect(() => { void refresh() }, [refresh])

  const handleCreate = async () => {
    if (!user || !form.thesis.trim()) return
    await createPolicyNote(user.id, form)
    setForm({ dimension: "equity", region: "all", stance: "monitor", thesis: "" })
    setAdding(false)
    void refresh()
  }

  const handleDelete = async (id: string) => {
    await deletePolicyNote(id)
    void refresh()
  }

  if (loading) {
    return <div className="flex justify-center py-16"><div className="w-2 h-2 rounded-full bg-indigo-500 animate-pulse" /></div>
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-4">
        <span className="text-[10px] uppercase tracking-[0.15em] text-muted-foreground font-mono">
          {notes.length} notes
        </span>
        <button
          onClick={() => setAdding(!adding)}
          className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-mono bg-indigo-600 text-white rounded hover:bg-indigo-500 transition-colors"
        >
          <Plus className="w-3.5 h-3.5" />
          NEW NOTE
        </button>
      </div>

      {adding && (
        <div className="border border-indigo-500/30 rounded bg-card p-4 mb-4 space-y-3">
          <div className="grid grid-cols-2 gap-3">
            <select
              value={form.dimension}
              onChange={(e) => setForm((f) => ({ ...f, dimension: e.target.value }))}
              className="px-3 py-2 text-xs bg-muted/50 border border-border rounded font-mono text-foreground"
            >
              {DIMENSIONS.map((d) => <option key={d} value={d}>{d}</option>)}
            </select>
            <select
              value={form.stance}
              onChange={(e) => setForm((f) => ({ ...f, stance: e.target.value as "priority" | "monitor" | "adequate" }))}
              className="px-3 py-2 text-xs bg-muted/50 border border-border rounded font-mono text-foreground"
            >
              <option value="priority">Priority</option>
              <option value="monitor">Monitor</option>
              <option value="adequate">Adequate</option>
            </select>
          </div>
          <textarea
            value={form.thesis}
            onChange={(e) => setForm((f) => ({ ...f, thesis: e.target.value }))}
            placeholder="Policy thesis or observation..."
            rows={3}
            className="w-full px-3 py-2 text-xs bg-muted/50 border border-border rounded font-mono text-foreground placeholder:text-muted-foreground/40 resize-none focus:outline-none focus:border-indigo-500/50"
          />
          <div className="flex gap-2">
            <button
              onClick={() => void handleCreate()}
              className="px-3 py-1.5 text-xs font-mono bg-indigo-600 text-white rounded hover:bg-indigo-500 transition-colors"
            >
              SAVE
            </button>
            <button
              onClick={() => setAdding(false)}
              className="px-3 py-1.5 text-xs font-mono text-muted-foreground hover:text-foreground transition-colors"
            >
              CANCEL
            </button>
          </div>
        </div>
      )}

      {notes.length === 0 && !adding ? (
        <div className="flex flex-col items-center justify-center py-16 text-center">
          <FileText className="w-8 h-8 text-muted-foreground/20 mb-3" />
          <p className="text-sm text-muted-foreground">No policy notes yet.</p>
          <p className="text-xs text-muted-foreground/60 mt-1">Record your analysis stance per dimension.</p>
        </div>
      ) : (
        <div className="space-y-2">
          {notes.map((n) => (
            <div key={n.id} className="border border-border rounded bg-card p-4">
              <div className="flex items-start gap-3">
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-2">
                    <span className="text-[10px] font-mono text-indigo-400 uppercase">{n.dimension}</span>
                    <span className={`text-[10px] font-mono px-1.5 py-0.5 rounded border ${STANCE_LABELS[n.stance]?.colour ?? ""}`}>
                      {STANCE_LABELS[n.stance]?.label ?? n.stance}
                    </span>
                  </div>
                  <p className="text-xs text-foreground leading-relaxed">{n.thesis}</p>
                  <p className="text-[10px] text-muted-foreground/40 font-mono mt-2">
                    {new Date(n.created_at).toLocaleDateString("en-GB")}
                  </p>
                </div>
                <button
                  onClick={() => void handleDelete(n.id)}
                  className="p-1.5 rounded hover:bg-red-500/10 text-muted-foreground/40 hover:text-red-400 transition-colors shrink-0"
                >
                  <Trash2 className="w-3.5 h-3.5" />
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
