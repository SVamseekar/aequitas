import { Download } from "lucide-react"
import { useParams } from "react-router"
import { useFilters, useSections } from "@/api/hooks"
import { DIMENSIONS, REGIONS, AREA_TYPES } from "@/lib/constants"
import { SectionCard } from "./SectionCard"
import { ScenarioBuilder } from "./ScenarioBuilder"

export function DimensionPage() {
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
    return <p className="text-red-500 text-xs">Unable to load data — try refreshing.</p>
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
  const exportUrl = `/api/export/${dimensionId}?region=${region}&urban_rural=${urbanRural}`

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
