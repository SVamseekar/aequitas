import { useState } from "react"
import { Info } from "lucide-react"
import type { SectionItem } from "@/api/types"
import { Markdown } from "@/components/shared/Markdown"
import { ChartRenderer } from "@/components/charts/ChartRenderer"
import { HIDDEN_STAT_KEYS, statLabel, sectionTitle } from "@/lib/constants"
import { packEquityDisplayValue } from "@/lib/metricsCanon"
import { extractHeadline } from "@/lib/narrative"
import { ProvenancePanel } from "./ProvenancePanel"
import { useFilters } from "@/api/hooks"
import { sectionPresentation } from '@/lib/sectionPresentation'
import { modelFeatureLabel } from '@/lib/modelLabels'
import { ChartInsights } from './ChartInsights'
import { chartMethod } from '@/lib/chartInsights'

function formatValue(key: string, v: unknown, country: string): string {
  if (v === null || v === undefined) return "—"
  if (typeof v === "number") {
    if (!Number.isFinite(v)) return '—'
    if (key === 'r2' || key === 'top_importance') return v.toFixed(4)
    if (key === 'p_value') return v < 0.0001 ? '< 0.0001' : v.toFixed(4)
    if (key === 'r' || key === 'concentration_index') return `${v > 0 ? '+' : ''}${v.toFixed(4)}`
    if (v === 0) return key.includes("pct") ? "0.0%" : "0.0"
    const packed = packEquityDisplayValue(key, v)
    if (packed !== null) return packed
    if (key === "hhi" || key.includes("hhi")) return `${v.toLocaleString("en-GB", { maximumFractionDigits: 1 })} / 10,000`
    if (key.includes("pct")) return `${v.toFixed(1)}%`
    if (key.includes("cost") || key.includes("benefit") || key.includes("value_k")) {
      if (country === "ireland") return `${v.toLocaleString(undefined, { maximumFractionDigits: 1 })} (people only)`
      return `£${v.toLocaleString(undefined, { maximumFractionDigits: 1 })}m`
    }
    if (key.includes("co2") || key.includes("saving")) return `${v.toLocaleString(undefined, { maximumFractionDigits: 0 })} t`
    if (Number.isInteger(v)) return v.toLocaleString()
    return parseFloat(v.toPrecision(4)).toString()
  }
  if (typeof v === "string") return key === 'top_feature' ? modelFeatureLabel(v) : v
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
  const labels: Record<string,string> = { r2: 'R²', n: 'Observations', n_features: 'Features', top_feature: 'Highest-importance feature', top_importance: 'Mean absolute SHAP value', total_annual_cost_m: 'Indicative annual cost', service_target: 'Service target', areas_below_target: 'Areas below target', association: 'Stored relationship' }
  if (labels[key]) return labels[key]
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
  featured?: boolean
}

export function SectionCard({ section, featured = false }: Props) {
  const [provenanceMetric, setProvenanceMetric] = useState<string | null>(null)
  const provenanceId =
    PROVENANCE_KEYS[section.section_id] ??
    (typeof section.stats?.gini === "number" ? "gini_national" : null)

  const { country } = useFilters()
  const presentation = sectionPresentation(section, country)

  const rawTitle = section.chart_data?.title
  const title = presentation.title ?? sectionTitle(section.section_id, country)
    ?? (typeof rawTitle === "string" ? rawTitle : undefined)
    ?? (typeof section.stats?.title === "string" ? section.stats.title : undefined)
    ?? section.section_id.replace(/_/g, " ")

  const omitted = Boolean(section.stats?.omit)
  let chartData = omitted ? undefined : presentation.chartData
  if(featured&&chartData?.type==='scatter_regression')chartData={...chartData,show_summary:false}
  const pctCovered = section.stats?.pct_covered
  if (
    country !== "ireland" &&
    section.section_id === "a3_walking_distance" &&
    typeof pctCovered === "number" &&
    (!chartData?.type || !chartData?.data)
  ) {
    chartData = {
      type: "horizontal_bar",
      x_label: country === 'england' ? '% of LSOAs' : '% of population',
      data: [
        { label: country === 'england' ? 'Non-zero access score' : 'Within 400m of a stop', value: Number(pctCovered.toFixed(1)) },
        { label: country === 'england' ? 'Zero access score' : 'Beyond 400m', value: Number((100 - pctCovered).toFixed(1)) },
      ],
    }
  }

  const hasChart = Boolean(
    chartData &&
      (chartData.type || (Array.isArray(chartData.data) && chartData.data.length > 0)),
  )
  const narrative = chartMethod(section,country)
  const hasNarrative = !!narrative?.trim()
  const headline = hasNarrative ? extractHeadline(narrative) : null

  // Flatten stats
  const flatStats: [string, unknown][] = []
  for (const [k, v] of Object.entries(section.stats ?? {})) {
    if (k === 'n_observations' && section.stats.n === v) continue
    if (Array.isArray(v) || (HIDDEN_STAT_KEYS.has(k) && !(featured && k === 'n_lsoas'))) continue
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
  const settlementSummary = country === 'england' && (section.section_id === 'f5_rural_penalty' || section.section_id === 'a6_urban_rural_gap')
  const displayStats: [string, unknown][] = country === 'england' && section.chart_data.type === 'scatter_regression' ? [
    ['r', section.stats.r], ['n', section.stats.n], ['p_value', section.stats.p_value], ['association', `${section.stats.direction ?? 'Unavailable'} (${section.stats.strength ?? 'strength unavailable'})`],
  ] : country === 'england' && section.section_id === 'a7_investment_gap' ? [
    ['areas_below_target', `${formatValue('pct_below', section.stats.pct_below, country)} · ${formatValue('n_below', section.stats.n_below, country)} areas`],
    ['service_target', `${formatValue('target', section.stats.target, country)} trips per capita (${section.stats.target_description ?? 'benchmark unavailable'})`],
    ['mean_gap', section.stats.mean_gap], ['total_annual_cost_m', section.stats.total_annual_cost_m],
  ] : settlementSummary ? [
    ['urban_value', section.stats.urban_value], ['rural_value', section.stats.rural_value], ['gap_pct', section.stats.gap_pct],
    ['observations', `Urban: ${typeof section.stats.n_urban === 'number' ? section.stats.n_urban.toLocaleString('en-GB') : '—'}\nRural: ${typeof section.stats.n_rural === 'number' ? section.stats.n_rural.toLocaleString('en-GB') : '—'}`],
  ] : flatStats

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
      <article data-section={section.section_id} className={`app-glass-strong rounded-2xl overflow-hidden mb-4 animate-fade-in${featured ? ' evidence-featured' : ''}`}>
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
        {headline && !(featured&&chartData?.type==='scatter_regression') && (
          <div className="px-5 pb-3">
            <p className="text-sm text-foreground border-l-2 border-primary pl-3 leading-relaxed">
              {featured && section.section_id === 'f1_gini' ? 'Lorenz curve: population ordered by trips per capita, lowest first.' : headline}
            </p>
          </div>
        )}

        {/* Chart */}
        {hasChart && (
          <div className="px-4 pb-3 evidence-chart">
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
        {(displayStats.length > 0 || featured) && (
          <div className="px-5 pb-4 evidence-statistics">
            <ChartInsights section={section} country={country} />
            {!hasRanking&&<div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-2">
              {displayStats.map(([key, val]) => (
                <div key={key} data-stat={key} className="app-glass rounded-xl p-3">
                  <p className="text-[11px] text-muted-foreground uppercase tracking-wide leading-tight">
                    {settlementSummary && key === 'urban_value' ? section.section_id === 'f5_rural_penalty' ? 'Urban SQI' : 'Urban trips per capita' : settlementSummary && key === 'rural_value' ? section.section_id === 'f5_rural_penalty' ? 'Rural SQI' : 'Rural trips per capita' : settlementSummary && key === 'gap_pct' ? 'Relative gap' : key === 'pct_covered' && country === 'england' ? 'LSOAs with non-zero access score' : key === 'n_lsoas' ? `Observations (${country === 'ireland' ? 'Small Areas' : country === 'netherlands' ? 'buurten' : country === 'france' ? 'IRIS' : 'LSOAs'})` : formatKey(key, country)}
                  </p>
                  <p className="text-sm font-semibold text-foreground mt-1 tabular-nums">
                    {formatValue(key, val, country)}
                  </p>
                </div>
              ))}
            </div>}
          </div>
        )}

        {hasNarrative && (
          <div className="px-5 pb-4 border-t border-border/60 pt-3">
            {featured && section.section_id === 'f1_gini' && <p className='text-xs text-muted-foreground mb-3'>Gini, Palma and the deprivation concentration index describe distinct distributions. Income Gini is a separate measure and is not a direct benchmark for service inequality.</p>}
            <p className="text-[11px] font-semibold uppercase tracking-wide text-muted-foreground mb-2">
              What this shows
            </p>
            <div className="text-sm">
              <Markdown content={narrative} />
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
