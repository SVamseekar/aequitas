import { X, BookOpen } from "lucide-react"
import { useProvenance } from "@/api/hooks"

interface Props {
  metricId: string
  onClose: () => void
}

export function ProvenancePanel({ metricId, onClose }: Props) {
  const { data, isLoading, error } = useProvenance(metricId)

  return (
    <>
      {/* Backdrop */}
      <div className="fixed inset-0 bg-black/40 z-40" onClick={onClose} aria-hidden="true" />

      {/* Panel */}
      <div className="fixed top-0 right-0 h-full w-[360px] bg-background border-l border-border shadow-2xl z-50 flex flex-col">
        <div className="flex items-center justify-between px-4 py-3 border-b border-border">
          <div className="flex items-center gap-2">
            <BookOpen className="w-4 h-4 text-indigo-400" />
            <h3 className="text-xs font-mono font-bold uppercase tracking-widest text-foreground">Data Provenance</h3>
          </div>
          <button onClick={onClose} className="text-muted-foreground hover:text-foreground transition-colors" aria-label="Close provenance panel">
            <X className="w-4 h-4" />
          </button>
        </div>

        <div className="flex-1 overflow-y-auto p-4">
          <p className="text-[10px] font-mono text-indigo-400/70 uppercase tracking-wider mb-4">{metricId}</p>

          {isLoading && (
            <div className="space-y-2">
              {Array.from({ length: 4 }).map((_, i) => (
                <div key={i} className="h-6 bg-muted animate-pulse rounded" />
              ))}
            </div>
          )}

          {error && (
            <p className="text-xs text-muted-foreground">
              Provenance data not yet available for this metric. Check the Phase 0 EDA notebooks.
            </p>
          )}

          {data && (
            <div className="space-y-4">
              {data.description && (
                <section>
                  <p className="text-[10px] font-mono uppercase tracking-wider text-muted-foreground/60 mb-1">Description</p>
                  <p className="text-xs text-muted-foreground leading-relaxed">{data.description}</p>
                </section>
              )}

              {data.formula && (
                <section>
                  <p className="text-[10px] font-mono uppercase tracking-wider text-muted-foreground/60 mb-1">Formula</p>
                  <pre className="text-[10px] font-mono bg-muted rounded p-3 text-foreground overflow-x-auto whitespace-pre-wrap">
                    {data.formula}
                  </pre>
                </section>
              )}

              {data.notebook && (
                <section>
                  <p className="text-[10px] font-mono uppercase tracking-wider text-muted-foreground/60 mb-1">Notebook</p>
                  <p className="text-xs font-mono text-indigo-400">{data.notebook}</p>
                </section>
              )}

              {data.source_files && data.source_files.length > 0 && (
                <section>
                  <p className="text-[10px] font-mono uppercase tracking-wider text-muted-foreground/60 mb-1">Source files</p>
                  <ul className="space-y-1">
                    {data.source_files.map((f) => (
                      <li key={f} className="text-[10px] font-mono text-muted-foreground">{f}</li>
                    ))}
                  </ul>
                </section>
              )}

              {data.input_values && Object.keys(data.input_values).length > 0 && (
                <section>
                  <p className="text-[10px] font-mono uppercase tracking-wider text-muted-foreground/60 mb-1">Input values</p>
                  <div className="space-y-1">
                    {Object.entries(data.input_values).map(([k, v]) => (
                      <div key={k} className="flex justify-between text-[10px] font-mono">
                        <span className="text-muted-foreground">{k}</span>
                        <span className="text-foreground">{String(v)}</span>
                      </div>
                    ))}
                  </div>
                </section>
              )}
            </div>
          )}
        </div>
      </div>
    </>
  )
}
