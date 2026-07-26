import { Component, type ReactNode } from "react"
import { Download, AlertTriangle } from "lucide-react"
import { useParams } from "react-router"
import { useFilters, useSections } from "@/api/hooks"

import { DIMENSIONS, REGIONS, AREA_TYPES } from "@/lib/constants"
import { SectionCard } from "./SectionCard"
import { ScenarioBuilder } from "./ScenarioBuilder"

// Error boundary to catch rendering crashes in child components
interface ErrorBoundaryState {
  hasError: boolean
  error: Error | null
}

class DimensionErrorBoundary extends Component<{ children: ReactNode }, ErrorBoundaryState> {
  state: ErrorBoundaryState = { hasError: false, error: null }

  static getDerivedStateFromError(error: Error) {
    return { hasError: true, error }
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="flex flex-col items-center justify-center py-16 text-center">
          <AlertTriangle className="w-8 h-8 text-red-400/60 mb-3" />
          <p className="text-sm text-foreground font-medium">Something went wrong rendering this page.</p>
          <p className="text-xs text-muted-foreground mt-1">{this.state.error?.message}</p>
          <button
            onClick={() => this.setState({ hasError: false, error: null })}
            className="mt-4 px-4 py-1.5 text-xs font-mono border border-border rounded hover:bg-muted transition-colors"
          >
            Try again
          </button>
        </div>
      )
    }
    return this.props.children
  }
}

function DimensionPageContent() {
  const { dimensionSlug } = useParams<{ dimensionSlug: string }>()
  const dim = DIMENSIONS.find((d) => d.route === `/${dimensionSlug}`)
  const dimensionId = dim?.id ?? dimensionSlug ?? ""

  const { region, urbanRural } = useFilters()
  const { data, isLoading, error } = useSections(dimensionId, region, urbanRural)
  const regionName = REGIONS.find((r) => r.code === region)?.name ?? region
  const areaName = AREA_TYPES.find((a) => a.code === urbanRural)?.name ?? urbanRural

  if (isLoading) {
    return (
      <div className="space-y-4">
        {Array.from({ length: 4 }).map((_, i) => (
          <div key={i} className="h-48 app-glass animate-pulse rounded-2xl" />
        ))}
      </div>
    )
  }

  if (error) {
    return (
      <div className="flex flex-col items-center justify-center py-16 text-center">
        <AlertTriangle className="w-8 h-8 text-red-400/60 mb-3" />
        <p className="text-sm text-foreground">Unable to load data.</p>
        <p className="text-xs text-muted-foreground mt-1">Check your connection and try refreshing the page.</p>
      </div>
    )
  }

  // Show all sections that have any content (stats, chart, or narrative)
  const sections = data?.sections.filter(
    (s) =>
      Object.keys(s.stats ?? {}).length > 0 ||
      Object.keys(s.chart_data ?? {}).length > 0 ||
      (s.narrative?.trim().length ?? 0) > 0
  ) ?? []

  // London is classified almost entirely urban under RUC — rural combos thin out.
  const isLondonRural = region === "E12000007" && urbanRural === "rural"
  const impossibleGeographyCopy = isLondonRural
    ? "No LSOAs match this filter (e.g. London has no rural LSOAs under the RUC classification). Choose Urban or All Areas."
    : null

  if (sections.length === 0) {
    return (
      <div className="text-center py-12 max-w-md mx-auto">
        <p className="text-muted-foreground text-sm">
          {impossibleGeographyCopy ?? (
            <>
              No LSOAs match this filter for <strong>{regionName}</strong> ({areaName}).
            </>
          )}
        </p>
        <p className="text-muted-foreground/60 text-xs mt-2">
          {isLondonRural
            ? "This is expected geography, not a data outage."
            : 'Try selecting "All England" and "All Areas" for national-level analysis.'}
        </p>
      </div>
    )
  }

  const withCharts = sections.filter((s) => Object.keys(s.chart_data ?? {}).length > 0).length
  const withNarrative = sections.filter((s) => (s.narrative?.trim().length ?? 0) > 0).length
  const exportParams = new URLSearchParams({ region, urban_rural: urbanRural })
  const exportUrl = `/api/export/${encodeURIComponent(dimensionId)}?${exportParams}`

  const handleExportPdf = async () => {
    const resp = await fetch(exportUrl, { credentials: "include" })
    if (!resp.ok) throw new Error(`Export failed (${resp.status})`)
    const blob = await resp.blob()
    const url = URL.createObjectURL(blob)
    const anchor = document.createElement("a")
    anchor.href = url
    anchor.download = `aequitas_${dimensionId}_${region}_${urbanRural}.pdf`
    anchor.click()
    URL.revokeObjectURL(url)
  }

  return (
    <div>
      {impossibleGeographyCopy && (
        <div
          role="status"
          className="mb-4 rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-950"
        >
          <p className="font-medium text-amber-900">Limited geography for this filter</p>
          <p className="mt-1 text-amber-900/80">{impossibleGeographyCopy}</p>
          <p className="mt-1 text-amber-900/70 text-xs">
            Some sections below may be empty or national-only for this combo — switch to Urban or All Areas for full London coverage.
          </p>
        </div>
      )}
      <div className="mb-6 flex items-start justify-between gap-4">
        <div>
          <h2 className="text-xl font-semibold text-foreground tracking-tight">{dim?.name}</h2>
          <p className="text-muted-foreground text-sm mt-1">{dim?.description}</p>
          <p className="text-muted-foreground text-xs mt-2">
            {sections.length} sections · {withCharts} charts · {withNarrative} narratives ·{" "}
            {regionName} · {areaName}
          </p>
        </div>
        <button
          type="button"
          onClick={() => void handleExportPdf()}
          className="app-glass flex items-center gap-2 px-3.5 py-2 text-xs font-semibold rounded-full hover:border-primary/35 transition-colors shrink-0 text-muted-foreground hover:text-foreground"
        >
          <Download className="w-3.5 h-3.5" />
          Export PDF
        </button>
      </div>

      {/* Scenario builder — only on scenarios dimension */}
      {dimensionId === "scenarios" && <ScenarioBuilder />}

      {sections.map((s) => (
        <SectionCard key={s.section_id} section={s} />
      ))}
    </div>
  )
}

export function DimensionPage() {
  return (
    <DimensionErrorBoundary>
      <DimensionPageContent />
    </DimensionErrorBoundary>
  )
}
