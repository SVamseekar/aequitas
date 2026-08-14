import { Component, type ReactNode } from "react"
import { Download, AlertTriangle } from "lucide-react"
import { useParams } from "react-router"
import { useFilters, useSections } from "@/api/hooks"

import { DIMENSION_API_IDS, AREA_TYPES, regionsForCountry, dimensionsForCountry } from "@/lib/constants"
import { COUNTRIES } from "@/lib/constants"
import { filterImpossibleSections, isLondonRural, selectUniqueSections } from "@/lib/uniqueExhibits"
import { filterSentence } from "@/lib/scoreFormat"
import { SectionCard } from "./SectionCard"
import { ScenarioBuilder } from "./ScenarioBuilder"
import { AccessReachPanel } from "@/components/access/AccessReachPanel"

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
  const { country, region, urbanRural, pack, mode } = useFilters()
  const dim = dimensionsForCountry(country).find((d) => d.route === `/${dimensionSlug}` || d.id === dimensionSlug)
  const apiDimensionId = DIMENSION_API_IDS[dimensionSlug ?? ""] ?? dim?.id ?? dimensionSlug ?? ""
  const countryName = COUNTRIES.find((c) => c.code === country)?.name ?? country
  const { data, isLoading, error } = useSections(apiDimensionId, region, urbanRural, country, pack, mode)
  const regionName = regionsForCountry(country).find((r) => r.code === region)?.name ?? region
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

  const unique = filterImpossibleSections(
    selectUniqueSections(apiDimensionId, sections, country),
    urbanRural,
  )
  const londonRural = isLondonRural(region, urbanRural)
  const showUrbanDrtNote = apiDimensionId === "scenarios" && urbanRural === "urban"
  const packReady = COUNTRIES.find((c) => c.code === country)?.packReady ?? false
  const packMissing = !packReady
  const impossibleGeographyCopy = londonRural
    ? `London has no rural LSOAs under the official urban/rural classification — this ${countryName} filter is empty.`
    : packMissing
      ? `${countryName} pack is not built yet. England and Ireland are live; the method is the same.`
      : null

  if (unique.length === 0 || londonRural || packMissing) {
    return (
      <div>
        <h1 className="text-xl font-semibold text-foreground tracking-tight mb-3">
          {dim?.name ?? "Dimension"}
        </h1>
        <p className="text-muted-foreground text-sm py-8 max-w-xl">
          {impossibleGeographyCopy ??
            `No areas match ${regionName} (${areaName}) for this ${countryName} filter.`}
        </p>
      </div>
    )
  }

  const withCharts = unique.filter((s) => Object.keys(s.chart_data ?? {}).length > 0).length
  const withNarrative = unique.filter((s) => (s.narrative?.trim().length ?? 0) > 0).length
  const exportParams = new URLSearchParams({ region, urban_rural: urbanRural })
  const exportUrl = `/api/export/${encodeURIComponent(apiDimensionId)}?${exportParams}`

  const handleExportPdf = async () => {
    const resp = await fetch(exportUrl, { credentials: "include" })
    if (!resp.ok) throw new Error(`Export failed (${resp.status})`)
    const blob = await resp.blob()
    const url = URL.createObjectURL(blob)
    const anchor = document.createElement("a")
    anchor.href = url
    anchor.download = `aequitas_${apiDimensionId}_${region}_${urbanRural}.pdf`
    anchor.click()
    URL.revokeObjectURL(url)
  }

  return (
    <div>
      {showUrbanDrtNote && (
        <p role="status" className="mb-4 text-sm text-muted-foreground">
          Demand-responsive rural scenarios do not apply to an urban-only filter — that card is hidden.
        </p>
      )}
      <div className="mb-6 flex items-start justify-between gap-4">
        <div>
          <h1 className="text-xl font-semibold text-foreground tracking-tight">
            {dim?.name} — {filterSentence(regionName, areaName)}
          </h1>
          <p className="text-muted-foreground text-sm mt-1">{dim?.description}</p>
          <p className="text-muted-foreground text-xs mt-2">
            {countryName} · {regionName} · {areaName}
            {withCharts > 0 ? ` · ${withCharts} exhibits` : ""}
            {withNarrative > 0 ? ` · ${withNarrative} briefings` : ""}
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
      {apiDimensionId === "scenarios" && country === "england" && <ScenarioBuilder />}

      {unique.map((s) => (
        <SectionCard key={s.section_id} section={s} />
      ))}

      {apiDimensionId === "accessibility" && <AccessReachPanel />}
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
