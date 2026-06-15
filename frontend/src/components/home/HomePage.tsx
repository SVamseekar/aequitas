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
      <h1 className="text-xl font-semibold text-foreground mb-1 font-mono tracking-tight">
        Bus Transport Intelligence for England
      </h1>
      <div className="text-sm mb-6 flex flex-wrap justify-between items-center gap-2 border-b border-border pb-4">
        <span className="text-muted-foreground">Evidence-graded analytics across 8 policy dimensions</span>
        {formattedDate && (
          <span className="text-[11px] font-mono text-muted-foreground bg-muted/40 px-2 py-0.5 rounded border border-border/40">
            Data as of: {formattedDate}
          </span>
        )}
      </div>
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        {data?.dimensions.map((d) => (
          <DimensionCard key={d.id} dim={d} />
        ))}
      </div>
    </div>
  )
}
