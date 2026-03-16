import { useFilters, useOverview } from "@/api/hooks"
import { DimensionCard } from "./DimensionCard"

export function HomePage() {
  const { region, urbanRural } = useFilters()
  const { data, isLoading, error } = useOverview(region, urbanRural)

  if (isLoading) {
    return (
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        {Array.from({ length: 8 }).map((_, i) => (
          <div key={i} className="h-32 bg-gray-200 animate-pulse rounded-lg" />
        ))}
      </div>
    )
  }

  if (error) {
    return <p className="text-red-600">Unable to load overview — try refreshing.</p>
  }

  return (
    <div>
      <h1 className="text-2xl font-semibold text-gray-900 mb-1">
        Bus Transport Intelligence for England
      </h1>
      <p className="text-gray-500 mb-6">
        Evidence-graded analytics across 8 policy dimensions
      </p>
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        {data?.dimensions.map((d) => (
          <DimensionCard key={d.id} dim={d} />
        ))}
      </div>
    </div>
  )
}
