import { X, BookOpen } from "lucide-react"
import { useEffect, useRef } from 'react'
import { useFilters, useProvenance } from "@/api/hooks"
import {GITHUB_URL} from '@/lib/site'
import {COUNTRIES,regionsForCountry} from '@/lib/constants'

interface Props {
  metricId: string
  onClose: () => void
}

export function ProvenancePanel({ metricId, onClose }: Props) {
  const { country, pack,region } = useFilters()
  const { data, isLoading, error, refetch } = useProvenance(metricId, country, pack)
  const inputs = data?.input_values ?? data?.inputs ?? {}
  const meaning = metricId === 'gini_national' ? 'Gini describes inequality in the distribution of scheduled trips per capita. Zero indicates equality; higher values indicate greater inequality. This is an in-country service measure.' : metricId === 'palma_ratio' ? 'Ratio of the service share received by the top 10% to that received by the bottom 40% of the population.' : metricId === 'concentration_index' ? 'Service distribution ordered by deprivation. Its sign depends on the stated in-country ordering.' : null
  const panel = useRef<HTMLDivElement>(null)
  useEffect(() => {
    const previous = document.activeElement
    const overflow = document.body.style.overflow
    document.body.style.overflow = 'hidden'
    panel.current?.querySelector<HTMLButtonElement>('button')?.focus()
    const keydown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') { event.preventDefault(); onClose(); return }
      if (event.key !== 'Tab') return
      const controls = panel.current?.querySelectorAll<HTMLElement>('button:not([disabled]),a[href],input:not([disabled]),select:not([disabled]),[tabindex="0"]')
      if (!controls?.length) return
      const first = controls[0], last = controls[controls.length - 1]
      if (event.shiftKey && document.activeElement === first) { event.preventDefault(); last.focus() }
      else if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first.focus() }
    }
    document.addEventListener('keydown', keydown)
    return () => {
      document.removeEventListener('keydown', keydown)
      document.body.style.overflow = overflow
      if (previous instanceof HTMLElement && previous.isConnected) previous.focus()
    }
  }, [onClose])

  return (
    <>
      {/* Backdrop */}
      <div className="fixed inset-0 bg-stone-900/10 z-40" onClick={onClose} aria-hidden="true" />

      {/* Panel */}
      <div ref={panel} role='dialog' aria-modal='true' aria-label='Data provenance' className="provenance-panel fixed top-0 right-0 h-full w-[min(100%,360px)] app-glass-strong border-l border-white/50 shadow-2xl z-50 flex flex-col">
        <div className="flex items-center justify-between px-4 py-3.5 border-b border-border/60">
          <div className="flex items-center gap-2">
            <BookOpen className="w-4 h-4 text-primary" />
            <h3 id='provenance-title' className="text-sm font-semibold text-foreground">Evidence & calculation</h3>
          </div>
          <button onClick={onClose} className="text-muted-foreground hover:text-foreground transition-colors" aria-label="Close provenance panel">
            <X className="w-4 h-4" />
          </button>
        </div>

        <div className="flex-1 overflow-y-auto p-4">
          <p className='text-xs text-muted-foreground mb-3'>{country.charAt(0).toUpperCase() + country.slice(1)} · {pack || 'current network'} · national metric provenance. Regional exhibits may use a different denominator.</p>
          <p className="text-[11px] font-mono text-primary/70 uppercase tracking-wide mb-4">{metricId}</p>

          {isLoading && (
            <div className="space-y-2" role='status' aria-label='Loading evidence provenance'>
              {Array.from({ length: 4 }).map((_, i) => (
                <div key={i} className="h-6 bg-muted animate-pulse rounded" />
              ))}
            </div>
          )}

          {error && (
            <div className="text-xs text-muted-foreground" role='alert'><p>
              Provenance is unavailable for this metric, country and network date. No other country's sources are substituted.
            </p><button type='button' className='app-panel-button mt-3' onClick={() => void refetch()}>Retry provenance</button></div>
          )}

          {data && (
            <div className="space-y-4">
              <section><h4 className='text-xs font-semibold'>{metricId==='gini_national'?'Gini of trips per capita':'Stored metric value'}</h4><p className='text-3xl text-primary mt-2'>{Number.isFinite(data.value) ? data.value.toLocaleString('en-GB', { minimumFractionDigits: 4, maximumFractionDigits: 4 }) : 'Unavailable'}</p>{meaning && <><h4 className='text-xs font-semibold mt-4'>What this measures</h4><p className='text-xs text-muted-foreground leading-relaxed mt-2'>{meaning}</p></>}</section>
              {data.description && (
                <section>
                  <p className="text-[11px] font-mono uppercase tracking-wide text-muted-foreground/60 mb-1">Description</p>
                  <p className="text-xs text-muted-foreground leading-relaxed">{data.description}</p>
                </section>
              )}

              {data.formula && (
                <section>
                  <p className="text-[11px] font-mono uppercase tracking-wide text-muted-foreground/60 mb-1">Formula</p>
                  <pre className="text-[11px] font-mono bg-muted rounded p-3 text-foreground overflow-x-auto whitespace-pre-wrap">
                    {data.formula}
                  </pre>
                </section>
              )}

              {data.notebook && (
                <section>
                  <p className="text-[11px] font-mono uppercase tracking-wide text-muted-foreground/60 mb-1">Notebook</p>
                  <p className="text-xs font-mono text-primary">{data.notebook}</p>
                </section>
              )}

              {data.source_files && data.source_files.length > 0 && (
                <section>
                  <p className="text-[11px] font-mono uppercase tracking-wide text-muted-foreground/60 mb-1">Source files</p>
                  <ul className="space-y-1">
                    {data.source_files.map((f) => (
                      <li key={f} className="text-[11px] font-mono text-muted-foreground">{f}</li>
                    ))}
                  </ul>
                </section>
              )}

              {Object.keys(inputs).length > 0 && (
                <section>
                  <p className="text-[11px] font-mono uppercase tracking-wide text-muted-foreground/60 mb-1">Input values</p>
                  <div className="space-y-1">
                    {Object.entries(inputs).map(([k, v]) => (
                      <div key={k} className="provenance-input text-[11px] font-mono">
                        <span className="text-muted-foreground">{k}</span>
                        <span className="text-foreground">{v !== null && typeof v === 'object' ? JSON.stringify(v) : String(v)}</span>
                      </div>
                    ))}
                  </div>
                </section>
              )}
              <section className='provenance-scope'><h4>Scope and processing</h4><dl><div><dt>Country</dt><dd>{COUNTRIES.find(row=>row.code===country)?.name??country}</dd></div><div><dt>Network</dt><dd>{pack||'Current registered network'}</dd></div><div><dt>Requested region</dt><dd>{regionsForCountry(country).find(row=>row.code===region)?.name??region}</dd></div><div><dt>Metric scope</dt><dd>Stored national provenance</dd></div></dl><p>A regional view does not refit or relabel this national provenance.</p></section>
              <section className='provenance-scope'><h4>Open source</h4><a className='app-text-link' href={GITHUB_URL} target='_blank' rel='noopener noreferrer'>Data sources and calculation code</a><h4 className='mt-4'>Limitations</h4><p>This metric describes the stored evidence. It does not establish causes.</p></section>
            </div>
          )}
        </div>
        <div className='p-4 border-t border-border'><button type='button' className='app-text-link' onClick={onClose}>Return to plot</button></div>
      </div>
    </>
  )
}
