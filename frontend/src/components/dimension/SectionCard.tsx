import { useState } from "react"
import { Info } from "lucide-react"
import type { SectionItem } from "@/api/types"
import { Markdown } from "@/components/shared/Markdown"
import { ChartRenderer } from "@/components/charts/ChartRenderer"
import { SECTION_TITLES } from "@/lib/constants"
import { ProvenancePanel } from "./ProvenancePanel"

function formatValue(key: string, v: unknown): string {
  if (v === null || v === undefined) return "—"
  if (typeof v === "number") {
    if (key.includes("pct")) return `${v.toFixed(1)}%`
    if (key.includes("cost") || key.includes("benefit") || key.includes("value_k"))
      return `£${v.toLocaleString(undefined, { maximumFractionDigits: 1 })}m`
    if (key.includes("co2") || key.includes("saving")) return `${v.toLocaleString(undefined, { maximumFractionDigits: 0 })} t`
    if (Number.isInteger(v)) return v.toLocaleString()
    return parseFloat(v.toPrecision(4)).toString()
  }
  if (typeof v === "string") return v
  if (typeof v === "object" && !Array.isArray(v)) {
    const obj = v as Record<string, unknown>
    if ("best" in obj && "worst" in obj) {
      const best = obj.best as Record<string, unknown>
      const worst = obj.worst as Record<string, unknown>
      return `Best: ${best.name} (${best.value}) | Worst: ${worst.name} (${worst.value})`
    }
    if ("label" in obj && "value" in obj) return `${obj.label}: ${obj.value}`
    if ("name" in obj && "value" in obj) return `${obj.name}: ${obj.value}`
    if ("national_avg" in obj) return String(obj.national_avg)
    const entries = Object.entries(obj).filter(([, val]) => typeof val !== "object")
    if (entries.length > 0) return entries.map(([k, val]) => `${k}: ${val}`).join(", ")
    return JSON.stringify(v)
  }
  return String(v)
}

function formatKey(key: string): string {
  return key
    .replace(/_/g, " ")
    .replace(/\b(pct|n|hhi|r2|vot|co2|bcr|drt|lta)\b/gi, (m) => m.toUpperCase())
}

interface Props {
  section: SectionItem
}

export function SectionCard({ section }: Props) {
  const [narrativeOpen, setNarrativeOpen] = useState(false)
  const [provenanceMetric, setProvenanceMetric] = useState<string | null>(null)

  const rawTitle = section.chart_data?.title
  const title = SECTION_TITLES[section.section_id]
    ?? (typeof rawTitle === "string" ? rawTitle : undefined)
    ?? section.section_id.replace(/_/g, " ")

  const hasChart = section.chart_data && Object.keys(section.chart_data).length > 0
  const hasNarrative = !!section.narrative?.trim()

  // Flatten stats
  const flatStats: [string, unknown][] = []
  for (const [k, v] of Object.entries(section.stats ?? {})) {
    if (Array.isArray(v) || k === "unit" || k === "entity_type") continue
    if (typeof v === "object" && v !== null) {
      const obj = v as Record<string, unknown>
      if ("best" in obj) continue
      for (const [innerK, innerV] of Object.entries(obj)) {
        if (typeof innerV !== "object" || innerV === null) {
          flatStats.push([innerK, innerV])
        }
      }
    } else {
      flatStats.push([k, v])
    }
  }
  const displayStats = flatStats

  const rankingStats = Object.entries(section.stats ?? {}).filter(
    ([, v]) => typeof v === "object" && v !== null && "best" in (v as Record<string, unknown>)
  )

  const hasRanking = rankingStats.length > 0
  const rawAvg = section.stats?.national_avg
  const nationalAvg = typeof rawAvg === "number" ? rawAvg : undefined
  const rawUnit = section.stats?.unit
  const unit = typeof rawUnit === "string" ? rawUnit : undefined

  return (
    <>
      <article className="bg-card border border-border rounded overflow-hidden mb-4 animate-fade-in">
        {/* Header */}
        <div className="px-5 pt-4 pb-3 flex items-center justify-between">
          <h3 className="text-xs font-semibold font-mono uppercase tracking-wider text-foreground">{title}</h3>
          <button
            type="button"
            onClick={() => setProvenanceMetric(section.section_id)}
            className="text-muted-foreground/40 hover:text-indigo-400 transition-colors ml-2"
            title="Show data source"
            aria-label="Show data provenance"
          >
            <Info className="w-3.5 h-3.5" />
          </button>
        </div>

        {/* Chart */}
        {hasChart && (
          <div className="px-4 pb-3">
            <ChartRenderer chartData={section.chart_data} />
          </div>
        )}

        {/* Ranking summary */}
        {hasRanking && (
          <div className="px-5 pb-3">
            {rankingStats.map(([statKey, val]) => {
              const obj = val as { best: { name: string; value: number }; worst: { name: string; value: number } }
              return (
                <div key={statKey} className="flex gap-4 text-xs">
                  <span className="text-green-400">Best: <strong>{obj.best.name}</strong> ({obj.best.value})</span>
                  <span className="text-red-400">Worst: <strong>{obj.worst.name}</strong> ({obj.worst.value})</span>
                  {nationalAvg !== undefined && (
                    <span className="text-muted-foreground">Avg: {nationalAvg}{unit ? ` ${unit}` : ""}</span>
                  )}
                </div>
              )
            })}
          </div>
        )}

        {/* Metric cards */}
        {displayStats.length > 0 && !hasRanking && (
          <div className="px-5 pb-4">
            <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-2">
              {displayStats.map(([key, val]) => (
                <div key={key} className="bg-background rounded border border-border p-3">
                  <p className="text-[9px] font-mono text-muted-foreground/60 uppercase tracking-wider leading-tight">
                    {formatKey(key)}
                  </p>
                  <p className="text-sm font-semibold text-foreground mt-1 font-mono">
                    {formatValue(key, val)}
                  </p>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Narrative toggle */}
        {hasNarrative && (
          <div className="px-5 pb-4 border-t border-border pt-3">
            <button
              type="button"
              className="text-[10px] font-mono text-indigo-400 hover:text-indigo-300 uppercase tracking-wider transition-colors"
              onClick={() => setNarrativeOpen(!narrativeOpen)}
            >
              {narrativeOpen ? "Hide analysis" : "Read analysis"}
            </button>
            {narrativeOpen && (
              <div className="mt-3 prose prose-sm prose-invert max-w-none text-xs text-muted-foreground">
                <Markdown content={section.narrative} />
              </div>
            )}
          </div>
        )}
      </article>

      {provenanceMetric && (
        <ProvenancePanel
          metricId={provenanceMetric}
          onClose={() => setProvenanceMetric(null)}
        />
      )}
    </>
  )
}
