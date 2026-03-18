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
          <div key={i} className="h-48 bg-muted animate-pulse rounded" />
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

  if (sections.length === 0) {
    return (
      <div className="text-center py-12">
        <p className="text-muted-foreground text-sm">
          No data available for <strong>{regionName}</strong> ({areaName}).
        </p>
        <p className="text-muted-foreground/60 text-xs mt-2">
          Try selecting "All England" and "All Areas" for national-level analysis.
        </p>
      </div>
    )
  }

  const withCharts = sections.filter((s) => Object.keys(s.chart_data ?? {}).length > 0).length
  const withNarrative = sections.filter((s) => (s.narrative?.trim().length ?? 0) > 0).length
  const exportParams = new URLSearchParams({ region, urban_rural: urbanRural })
  const exportUrl = `/api/export/${encodeURIComponent(dimensionId)}?${exportParams}`

  return (
    <div>
      <div className="mb-6 flex items-start justify-between gap-4">
        <div>
          <h2 className="text-base font-semibold text-foreground font-mono tracking-tight">{dim?.name}</h2>
          <p className="text-muted-foreground text-xs mt-1">{dim?.description}</p>
          <p className="text-muted-foreground/50 text-[10px] font-mono mt-2 uppercase tracking-wider">
            {sections.length} sections · {withCharts} charts · {withNarrative} narratives ·{" "}
            {regionName} · {areaName}
          </p>
        </div>
        <a
          href={exportUrl}
          download
          className="flex items-center gap-2 px-3 py-1.5 text-xs border border-border rounded hover:bg-muted hover:border-indigo-500/40 transition-colors shrink-0 font-mono text-muted-foreground hover:text-foreground"
        >
          <Download className="w-3.5 h-3.5" />
          Export PDF
        </a>
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
