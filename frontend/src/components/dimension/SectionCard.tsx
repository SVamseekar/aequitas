import { useState } from "react"
import type { SectionItem } from "@/api/types"
import { Markdown } from "@/components/shared/Markdown"
import { ChartRenderer } from "@/components/charts/ChartRenderer"
import { SECTION_TITLES } from "@/lib/constants"

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
    // Format nested objects with simple key: value pairs
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
  const title = SECTION_TITLES[section.section_id]
    ?? (section.chart_data?.title as string | undefined)
    ?? section.section_id.replace(/_/g, " ")

  const hasChart = section.chart_data && Object.keys(section.chart_data).length > 0
  const hasNarrative = !!section.narrative?.trim()

  // Flatten stats: extract scalar values, unwrap single nested objects like 'scenario'
  const flatStats: [string, unknown][] = []
  for (const [k, v] of Object.entries(section.stats ?? {})) {
    if (Array.isArray(v) || k === "unit" || k === "entity_type") continue
    if (typeof v === "object" && v !== null) {
      const obj = v as Record<string, unknown>
      if ("best" in obj) continue // handled by rankingStats
      // Unwrap nested scenario/cluster objects into their fields
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

  // Extract best/worst/national_avg if present (common pattern)
  const rankingStats = Object.entries(section.stats ?? {}).filter(
    ([, v]) => typeof v === "object" && v !== null && "best" in (v as Record<string, unknown>)
  )

  const hasRanking = rankingStats.length > 0
  const nationalAvg = section.stats?.national_avg as number | undefined
  const unit = section.stats?.unit as string | undefined

  return (
    <article className="bg-white rounded-lg border border-gray-200 overflow-hidden mb-4">
      {/* Header */}
      <div className="px-6 pt-5 pb-3">
        <h3 className="text-base font-semibold text-gray-900">{title}</h3>
      </div>

      {/* Chart — full width, no padding */}
      {hasChart && (
        <div className="px-4 pb-3">
          <ChartRenderer chartData={section.chart_data} />
        </div>
      )}

      {/* Ranking summary (best/worst pattern) */}
      {hasRanking && (
        <div className="px-6 pb-3">
          {rankingStats.map(([, val]) => {
            const obj = val as { best: { name: string; value: number }; worst: { name: string; value: number } }
            return (
              <div key="ranking" className="flex gap-4 text-sm">
                <span className="text-green-700">Best: <strong>{obj.best.name}</strong> ({obj.best.value})</span>
                <span className="text-red-700">Worst: <strong>{obj.worst.name}</strong> ({obj.worst.value})</span>
                {nationalAvg !== undefined && (
                  <span className="text-gray-500">Avg: {nationalAvg}{unit ? ` ${unit}` : ""}</span>
                )}
              </div>
            )
          })}
        </div>
      )}

      {/* Metric cards */}
      {displayStats.length > 0 && !hasRanking && (
        <div className="px-6 pb-4">
          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-3">
            {displayStats.map(([key, val]) => (
              <div key={key} className="bg-gray-50 rounded-lg p-3">
                <p className="text-xs text-gray-500 uppercase tracking-wider leading-tight">
                  {formatKey(key)}
                </p>
                <p className="text-base font-semibold text-gray-900 mt-1">
                  {formatValue(key, val)}
                </p>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Narrative toggle */}
      {hasNarrative && (
        <div className="px-6 pb-5 border-t border-gray-100 pt-3">
          <button
            type="button"
            className="text-indigo-600 text-sm font-medium hover:text-indigo-800"
            onClick={() => setNarrativeOpen(!narrativeOpen)}
          >
            {narrativeOpen ? "Hide analysis" : "Read analysis"}
          </button>
          {narrativeOpen && (
            <div className="mt-3 prose prose-sm max-w-none">
              <Markdown content={section.narrative} />
            </div>
          )}
        </div>
      )}
    </article>
  )
}
