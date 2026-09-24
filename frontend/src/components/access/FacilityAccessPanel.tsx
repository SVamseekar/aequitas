import { useDestinations, useFilters } from "@/api/hooks"
import { filterSentence } from "@/lib/scoreFormat"
import { AREA_TYPES, regionsForCountry } from "@/lib/constants"

const DEST = [
  { id: "jobs", label: "Jobs" },
  { id: "gp", label: "GP" },
  { id: "school", label: "School" },
] as const

function pct(value: number | null | undefined): string {
  if (value == null || Number.isNaN(value)) return "—"
  return `${(value * 100).toFixed(1)}%`
}

export function FacilityAccessPanel() {
  const { country, region, urbanRural } = useFilters()
  const { data, isLoading, isError } = useDestinations(country)
  const regionName = regionsForCountry(country).find((r) => r.code === region)?.name ?? region
  const areaName = AREA_TYPES.find((a) => a.code === urbanRural)?.name ?? urbanRural
  const place = filterSentence(regionName, areaName)
  const facility = data?.facility_400m ?? {}
  const distances = data?.official_distances
  const hasFacility = DEST.some((d) => facility[d.id]?.available)
  const hasDistances = Boolean(distances?.available)

  return (
    <section className="app-glass-strong rounded-2xl border border-white/60 p-5 mb-6">
      <h2 className="text-lg font-semibold text-foreground">400 m to official jobs, GPs, and schools</h2>
      <p className="text-sm text-muted-foreground mt-1">
        For {place}, people whose small-area centroid is within 400 m of an official destination
        file for this country. Not the stop-coverage bar above, and not 15/30/45 travel time.
      </p>

      {isLoading ? (
        <div className="h-24 app-glass animate-pulse rounded-xl mt-4" role="status" aria-label="Loading official destinations" />
      ) : isError ? (
        <p className="text-sm text-destructive mt-4" role="alert">
          Official destination inventory failed to load. No substitute counts are shown.
        </p>
      ) : hasFacility ? (
        <div className="grid gap-3 sm:grid-cols-3 mt-4">
          {DEST.map((d) => {
            const row = facility[d.id]
            return (
              <div key={d.id} className="rounded-xl border border-border/70 p-3">
                <p className="text-xs text-muted-foreground">{d.label}</p>
                <p className="text-2xl font-bold tabular-nums mt-1">{pct(row?.people_share)}</p>
                <p className="text-xs text-muted-foreground mt-1">
                  {row?.available
                    ? `${row.n_within_400m.toLocaleString()} of ${row.n_areas.toLocaleString()} areas`
                    : "No official file"}
                </p>
                {row?.note ? <p className="text-xs text-muted-foreground mt-2">{row.note}</p> : null}
              </div>
            )
          })}
        </div>
      ) : (
        <p className="text-sm text-muted-foreground mt-4 max-w-2xl">
          {data?.note
            ?? "No official destination extract on disk for this country. We do not copy another country's points."}
        </p>
      )}

      {hasDistances ? (
        <p className="text-sm text-muted-foreground mt-4">
          Official CBS distance table present ({distances?.rows.toLocaleString()} buurten). This is
          nabijheid in kilometres, not OSM and not an England file.
        </p>
      ) : null}
    </section>
  )
}
