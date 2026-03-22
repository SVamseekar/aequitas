import { useFilters, useOverview } from "@/api/hooks"
import { DimensionCard } from "./DimensionCard"

export function HomePage() {
  const { region, urbanRural } = useFilters()
  const { data, isLoading, error } = useOverview(region, urbanRural)

  if (isLoading) {
    return (
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        {Array.from({ length: 8 }).map((_, i) => (
          <div key={i} className="h-32 bg-muted animate-pulse rounded" />
        ))}
      </div>
    )
  }

  if (error) {
    return <p className="text-red-500 text-xs">Unable to load overview — try refreshing.</p>
  }

  return (
    <div>
      <h1 className="text-xl font-semibold text-foreground mb-1 font-mono tracking-tight">
        Bus Transport Intelligence for England
      </h1>
      <p className="text-muted-foreground text-sm mb-6">
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
