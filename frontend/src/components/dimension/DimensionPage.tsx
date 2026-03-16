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

  const sections = data?.sections.filter((s) => !s.suppressed) ?? []

  if (sections.length === 0) {
    return (
      <p className="text-gray-500">
        No data available for {regionName} ({areaName}). Try selecting "All England" for national-level analysis.
      </p>
    )
  }

  return (
    <div>
      <h2 className="text-xl font-semibold text-gray-900 mb-1">{dim?.name}</h2>
      <p className="text-gray-500 text-sm mb-6">{dim?.description}</p>
      {sections.map((s) => (
        <SectionCard key={s.section_id} section={s} />
      ))}
    </div>
  )
}
