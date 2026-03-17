import { useState } from "react"
import type { SectionItem } from "@/api/types"
import { Markdown } from "@/components/shared/Markdown"
import { ChartRenderer } from "@/components/charts/ChartRenderer"

const SECTION_TITLES: Record<string, string> = {
  coverage_density: "Coverage Density",
  equity: "Equity & Distribution",
  correlation: "Socio-Economic Correlations",
  gap_to_target: "Gap to Target",
  policy_scenario: "Policy Scenarios",
}

function formatValue(key: string, v: unknown): string {
  if (v === null || v === undefined) return "—"
  if (typeof v === "number") {
    if (key.includes("pct")) return `${v}%`
    if (Number.isInteger(v)) return v.toLocaleString()
    // Show at most 4 significant digits
    return parseFloat(v.toPrecision(4)).toString()
  }
  if (typeof v === "string") return v
  if (typeof v === "object" && !Array.isArray(v)) {
    const obj = v as Record<string, unknown>
    if ("best" in obj && "worst" in obj) {
      const best = obj.best as Record<string, unknown>
      const worst = obj.worst as Record<string, unknown>
      return `${best.name}: ${best.value} / ${worst.name}: ${worst.value}`
    }
    if ("national_avg" in obj) return String(obj.national_avg)
    return JSON.stringify(v)
  }
  return String(v)
}

interface Props {
  section: SectionItem
}

export function SectionCard({ section }: Props) {
  const [open, setOpen] = useState(false)
  const title =
    (section.chart_data?.title as string | undefined) ??
    SECTION_TITLES[section.section_id] ??
    section.section_id.replace(/_/g, " ")

  const hasChart = section.chart_data && Object.keys(section.chart_data).length > 0
  const hasStats = section.stats && Object.keys(section.stats).length > 0
  const hasNarrative = !!section.narrative?.trim()

  // Filter out large arrays (like lorenz_x/lorenz_y) from stat display
  const displayStats = hasStats
    ? Object.entries(section.stats).filter(
        ([, v]) => !Array.isArray(v)
      )
    : []

  return (
    <article className="bg-white rounded-lg border border-gray-200 p-6 mb-4">
      <h3 className="text-lg font-semibold text-gray-900 mb-3 capitalize">{title}</h3>

      {hasChart && (
        <div className="mb-3">
          <ChartRenderer chartData={section.chart_data} />
        </div>
      )}

      {displayStats.length > 0 && (
        <div className="grid grid-cols-2 sm:grid-cols-3 gap-3 mb-4">
          {displayStats.map(([key, val]) => (
            <div key={key} className="bg-gray-50 rounded-lg p-3">
              <p className="text-xs text-gray-500 uppercase tracking-wider">
                {key.replace(/_/g, " ")}
              </p>
              <p className="text-lg font-semibold text-gray-900 mt-1">
                {formatValue(key, val)}
              </p>
            </div>
          ))}
        </div>
      )}

      {hasNarrative && (
        <>
          <button
            type="button"
            className="text-indigo-600 text-sm font-medium hover:text-indigo-800"
            onClick={() => setOpen(!open)}
          >
            {open ? "Hide details" : "Read analysis"}
          </button>
          {open && (
            <div className="mt-3 prose prose-sm max-w-none">
              <Markdown content={section.narrative} />
            </div>
          )}
        </>
      )}
    </article>
  )
}
