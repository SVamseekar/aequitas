import { useState } from "react"
import { Info } from "lucide-react"
import type { SectionItem } from "@/api/types"
import { Markdown } from "@/components/shared/Markdown"
import { ChartRenderer } from "@/components/charts/ChartRenderer"
import { HIDDEN_STAT_KEYS, statLabel, sectionTitle } from "@/lib/constants"
import { packEquityDisplayValue } from "@/lib/metricsCanon"
import { extractHeadline } from "@/lib/narrative"
import { ProvenancePanel } from "./ProvenancePanel"
import { useFilters, useScenarioCalculation } from "@/api/hooks"

function formatValue(key: string, v: unknown, country: string): string {
  if (v === null || v === undefined) return "—"
  if (typeof v === "number") {
    if (v === 0) return key.includes("pct") ? "0.0%" : "0.0"
    const packed = packEquityDisplayValue(key, v)
    if (packed !== null) return packed
    if (key === "hhi" || key.includes("hhi")) return `${Math.round(v).toLocaleString("en-GB")} / 10,000`
    if (key.includes("pct")) return `${v.toFixed(1)}%`
    if (key.includes("cost") || key.includes("benefit") || key.includes("value_k")) {
      if (country === "ireland") return `${v.toLocaleString(undefined, { maximumFractionDigits: 1 })} (people only)`
      return `£${v.toLocaleString(undefined, { maximumFractionDigits: 1 })}m`
    }
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

function formatKey(key: string, country: string): string {
  return statLabel(key, country)
}

/** Section / stat keys that resolve on GET /api/provenance/{id}. */
const PROVENANCE_KEYS: Record<string, string> = {
  f1_gini: "gini_national",
  gini: "gini_national",
  palma: "palma_ratio",
  concentration_index: "concentration_index",
}

interface Props {
  section: SectionItem
}

export function SectionCard({ section }: Props) {
  const [provenanceMetric, setProvenanceMetric] = useState<string | null>(null)
  const provenanceId =
    PROVENANCE_KEYS[section.section_id] ??
    (typeof section.stats?.gini === "number" ? "gini_national" : null)

  const { country, region, urbanRural } = useFilters()
  const { populationAffected, co2Saving, total_cost } = useScenarioCalculation(region, urbanRural)

  const rawTitle = section.chart_data?.title
  const title = sectionTitle(section.section_id, country)
    ?? (typeof rawTitle === "string" ? rawTitle : undefined)
    ?? (typeof section.stats?.title === "string" ? section.stats.title : undefined)
    ?? section.section_id.replace(/_/g, " ")

  const omitted = Boolean(section.stats?.omit)
  let chartData = omitted ? undefined : section.chart_data
  const pctCovered = section.stats?.pct_covered
  if (
    country !== "ireland" &&
    section.section_id === "a3_walking_distance" &&
    typeof pctCovered === "number" &&
    (!chartData?.type || !chartData?.data)
  ) {
    chartData = {
      type: "horizontal_bar",
      x_label: "% of population",
      data: [
        { label: "Within 400m of a stop", value: Number(pctCovered.toFixed(1)) },
        { label: "Beyond 400m", value: Number((100 - pctCovered).toFixed(1)) },
      ],
    }
  }
  if (country !== "ireland" && section.section_id === "ps5_scenario_comparison" && chartData) {
    const originalData = Array.isArray(chartData.data) ? chartData.data : []
    const costPerBeneficiary = populationAffected > 0 ? (total_cost * 1_000_000) / populationAffected : 0
    const customRow = {
      "Scenario": "My Custom Scenario (Sandbox)",
      "Population affected": populationAffected,
      "Cost £m/yr": Number(total_cost.toFixed(1)),
      "CO2 t/yr": Number((co2Saving * 1000).toFixed(0)),
      "Cost/beneficiary (£)": Number(costPerBeneficiary.toFixed(2))
    }
    chartData = {
      ...chartData,
      data: [customRow, ...originalData]
    }
  }

  const hasChart = Boolean(
    chartData &&
      (chartData.type || (Array.isArray(chartData.data) && chartData.data.length > 0)),
  )
  const hasNarrative = !!section.narrative?.trim()
  const headline = hasNarrative ? extractHeadline(section.narrative) : null

  // Flatten stats
  const flatStats: [string, unknown][] = []
  for (const [k, v] of Object.entries(section.stats ?? {})) {
    if (Array.isArray(v) || HIDDEN_STAT_KEYS.has(k)) continue
    if (k === "bcr" && (v === null || v === undefined) && section.stats?.omit_euro) continue
    if (typeof v === "object" && v !== null) {
      const obj = v as Record<string, unknown>
      if ("best" in obj) continue
      if (("label" in obj && "value" in obj) || ("name" in obj && "value" in obj)) {
        flatStats.push([k, v])
        continue
      }
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
      <article className="app-glass-strong rounded-2xl overflow-hidden mb-4 animate-fade-in">
        {/* Header */}
        <div className="px-5 pt-4 pb-3 flex items-center justify-between">
          <h3 className="text-sm font-semibold tracking-tight text-foreground">{title}</h3>
          {provenanceId && (
            <button
              type="button"
              onClick={() => setProvenanceMetric(provenanceId)}
              className="text-muted-foreground hover:text-primary transition-colors ml-2"
              title="Show data source"
              aria-label="Show data provenance"
            >
              <Info className="w-3.5 h-3.5" />
            </button>
          )}
        </div>

        {/* Headline finding */}
        {headline && (
          <div className="px-5 pb-3">
            <p className="text-sm text-foreground border-l-2 border-primary pl-3 leading-relaxed">
              {headline}
            </p>
          </div>
        )}

        {/* Chart */}
        {hasChart && (
          <div className="px-4 pb-3">
            <ChartRenderer chartData={chartData ?? {}} />
          </div>
        )}

        {/* Ranking summary */}
        {hasRanking && (
          <div className="px-5 pb-3">
            {rankingStats.map(([statKey, val]) => {
              const obj = val as { best: { name: string; value: number }; worst: { name: string; value: number } }
              return (
                <div key={statKey} className="flex flex-wrap gap-4 text-xs">
                  <span className="text-emerald-700">Best: <strong>{obj.best.name}</strong> ({obj.best.value})</span>
                  <span className="text-red-700">Worst: <strong>{obj.worst.name}</strong> ({obj.worst.value})</span>
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
                <div key={key} className="app-glass rounded-xl p-3">
                  <p className="text-[11px] text-muted-foreground uppercase tracking-wide leading-tight">
                    {formatKey(key, country)}
                  </p>
                  <p className="text-sm font-semibold text-foreground mt-1 tabular-nums">
                    {formatValue(key, val, country)}
                  </p>
                </div>
              ))}
            </div>
          </div>
        )}

        {hasNarrative && (
          <div className="px-5 pb-4 border-t border-border/60 pt-3">
            <p className="text-[11px] font-semibold uppercase tracking-wide text-muted-foreground mb-2">
              For this filter
            </p>
            <div className="text-sm">
              <Markdown content={section.narrative} />
            </div>
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
