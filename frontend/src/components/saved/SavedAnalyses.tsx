import { useState, useEffect } from "react"
import { useAuth } from "@/contexts/AuthContext"
import { listSavedAnalyses, deleteSavedAnalysis, type SavedAnalysisRow } from "@/lib/db"
import { Trash2, ChevronDown, ChevronUp, Bookmark } from "lucide-react"

export function SavedAnalyses() {
  const { user } = useAuth()
  const [analyses, setAnalyses] = useState<SavedAnalysisRow[]>([])
  const [loading, setLoading] = useState(true)
  const [expanded, setExpanded] = useState<string | null>(null)

  const refresh = async () => {
    if (!user) return
    setLoading(true)
    const data = await listSavedAnalyses(user.id)
    setAnalyses(data)
    setLoading(false)
  }

  useEffect(() => { void refresh() }, [user])

  const handleDelete = async (id: string) => {
    await deleteSavedAnalysis(id)
    void refresh()
  }

  if (loading) {
    return <div className="flex justify-center py-16"><div className="w-2 h-2 rounded-full bg-indigo-500 animate-pulse" /></div>
  }

  if (analyses.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-16 text-center">
        <Bookmark className="w-8 h-8 text-muted-foreground/20 mb-3" />
        <p className="text-sm text-muted-foreground">No saved analyses yet.</p>
        <p className="text-xs text-muted-foreground/60 mt-1">Save narratives from the dashboard to find them here.</p>
      </div>
    )
  }

  return (
    <div className="space-y-2">
      {analyses.map((a) => (
        <div key={a.id} className="border border-border rounded bg-card">
          <div className="flex items-start gap-3 p-4">
            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium text-foreground truncate">{a.title}</p>
              <div className="flex items-center gap-3 mt-0.5">
                {a.dimension && (
                  <span className="text-[10px] font-mono text-indigo-400 uppercase">{a.dimension}</span>
                )}
                <span className="text-[10px] text-muted-foreground/40 font-mono">
                  {new Date(a.created_at).toLocaleDateString("en-GB")}
                </span>
              </div>
            </div>
            <div className="flex items-center gap-1 shrink-0">
              <button
                onClick={() => setExpanded(expanded === a.id ? null : a.id)}
                className="p-1.5 rounded hover:bg-muted text-muted-foreground transition-colors"
              >
                {expanded === a.id ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
              </button>
              <button
                onClick={() => void handleDelete(a.id)}
                className="p-1.5 rounded hover:bg-red-500/10 text-muted-foreground/40 hover:text-red-400 transition-colors"
              >
                <Trash2 className="w-3.5 h-3.5" />
              </button>
            </div>
          </div>
          {expanded === a.id && (
            <div className="px-4 pb-4 border-t border-border pt-3">
              <p className="text-xs text-muted-foreground leading-relaxed whitespace-pre-wrap">{a.content}</p>
            </div>
          )}
        </div>
      ))}
    </div>
  )
}
