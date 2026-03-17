import { useParams } from "react-router"
import { useFilters, useSections } from "@/api/hooks"
import { DIMENSIONS, REGIONS, AREA_TYPES } from "@/lib/constants"
import { SectionCard } from "./SectionCard"

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
          <div key={i} className="h-48 bg-gray-200 animate-pulse rounded-lg" />
        ))}
      </div>
    )
  }

  if (error) {
    return <p className="text-red-600">Unable to load data — try refreshing.</p>
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
        <p className="text-gray-500 text-lg">
          No data available for <strong>{regionName}</strong> ({areaName}).
        </p>
        <p className="text-gray-400 text-sm mt-2">
          Try selecting "All England" and "All Areas" for national-level analysis.
        </p>
      </div>
    )
  }

  const withCharts = sections.filter((s) => Object.keys(s.chart_data ?? {}).length > 0).length
  const withNarrative = sections.filter((s) => (s.narrative?.trim().length ?? 0) > 0).length

  return (
    <div>
      <div className="mb-6">
        <h2 className="text-xl font-semibold text-gray-900">{dim?.name}</h2>
        <p className="text-gray-500 text-sm mt-1">{dim?.description}</p>
        <p className="text-gray-400 text-xs mt-2">
          {sections.length} sections | {withCharts} charts | {withNarrative} narratives |
          {" "}{regionName} | {areaName}
        </p>
      </div>
      {sections.map((s) => (
        <SectionCard key={s.section_id} section={s} />
      ))}
    </div>
  )
}
