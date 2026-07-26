import { useFilters, useOverview } from "@/api/hooks"
import { DimensionCard } from "./DimensionCard"

export function HomePage() {
  const { region, urbanRural } = useFilters()
  const { data, isLoading, error } = useOverview(region, urbanRural)

  if (isLoading) {
    return (
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 sm:gap-4">
        {Array.from({ length: 8 }).map((_, i) => (
          <div key={i} className="h-32 app-glass animate-pulse rounded-2xl" />
        ))}
      </div>
    )
  }

  if (error) {
    return (
      <p className="text-destructive text-sm">Unable to load overview — try refreshing.</p>
    )
  }

  const formattedDate = data?.built_at
    ? new Date(data.built_at).toLocaleString("en-GB", {
        day: "numeric",
        month: "short",
        year: "numeric",
        hour: "2-digit",
        minute: "2-digit",
        timeZoneName: "short",
      })
    : null

  return (
    <div>
      <h1 className="text-2xl sm:text-3xl font-semibold text-foreground tracking-tight mb-1">
        Bus transport intelligence for England
      </h1>
      <div className="text-sm mb-6 flex flex-wrap justify-between items-center gap-2 border-b border-border/70 pb-4">
        <span className="text-muted-foreground">
          Evidence-graded analytics across 8 policy dimensions
        </span>
        {formattedDate && (
          <span className="app-glass text-xs text-muted-foreground px-2.5 py-1 rounded-full">
            Data as of: {formattedDate}
          </span>
        )}
      </div>
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 sm:gap-4">
        {data?.dimensions.map((d) => (
          <DimensionCard key={d.id} dim={d} />
        ))}
      </div>
    </div>
  )
}
