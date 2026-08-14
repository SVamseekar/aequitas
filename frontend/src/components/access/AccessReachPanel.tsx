import { Link, useSearchParams } from "react-router"
import { useFilters, useReach } from "@/api/hooks"
import { AREA_TYPES, regionsForCountry } from "@/lib/constants"
import { appPath, withSearch } from "@/lib/appRoutes"
import { filterSentence } from "@/lib/scoreFormat"

const DEST = [
  { id: "jobs", label: "Jobs" },
  { id: "gp", label: "GP" },
  { id: "school", label: "School" },
] as const

const CUTOFFS = [15, 30, 45] as const

export function AccessReachPanel() {
  const { country, region, urbanRural } = useFilters()
  const [params, setParams] = useSearchParams()
  const cutoffRaw = Number(params.get("cutoff") ?? "45")
  const cutoff = CUTOFFS.includes(cutoffRaw as 15 | 30 | 45) ? cutoffRaw : 45
  const dest = DEST.some((d) => d.id === params.get("dest")) ? (params.get("dest") as string) : "jobs"
  const { data, isLoading } = useReach(region, urbanRural, dest, cutoff, country)
  const regionName = regionsForCountry(country).find((r) => r.code === region)?.name ?? region
  const areaName = AREA_TYPES.find((a) => a.code === urbanRural)?.name ?? urbanRural
  const place = filterSentence(regionName, areaName)

  const setControl = (key: string, value: string) => {
    const next = new URLSearchParams(params)
    next.set(key, value)
    setParams(next)
  }

  return (
    <section className="app-glass-strong rounded-2xl border border-white/60 p-5 mb-6">
      <h2 className="text-lg font-semibold text-foreground">Jobs, GP, and school in 15 / 30 / 45 minutes</h2>
      <p className="text-sm text-muted-foreground mt-1">
        For {place}, destinations reachable by walk + bus (r5py / R5). Counts, not Hansen. Not the 400 m
        walking bar above.{" "}
        <Link className="underline" to={withSearch(appPath(country, "reach"), params.toString())}>
          Open Reach for bands and the research pack
        </Link>
        .
      </p>

      <div className="flex flex-wrap gap-2 mt-4">
        {CUTOFFS.map((c) => (
          <button
            key={c}
            type="button"
            onClick={() => setControl("cutoff", String(c))}
            className={`px-3 py-1.5 text-xs rounded-full border ${
              cutoff === c ? "border-primary bg-primary/10 text-foreground" : "border-border text-muted-foreground"
            }`}
          >
            {c} min
          </button>
        ))}
        {DEST.map((d) => (
          <button
            key={d.id}
            type="button"
            onClick={() => setControl("dest", d.id)}
            className={`px-3 py-1.5 text-xs rounded-full border ${
              dest === d.id ? "border-primary bg-primary/10 text-foreground" : "border-border text-muted-foreground"
            }`}
          >
            {d.label}
          </button>
        ))}
      </div>

      {isLoading ? (
        <div className="h-24 app-glass animate-pulse rounded-xl mt-4" />
      ) : !data?.available ? (
        <p className="text-sm text-muted-foreground mt-4 max-w-2xl">
          {data?.note
            ?? `${cutoff}-minute ${dest} not precomputed for ${place} in this pack.`}
        </p>
      ) : (
        <div className="mt-4">
          <p className="text-3xl font-bold tabular-nums">
            {data.median !== null ? Math.round(data.median).toLocaleString("en-GB") : "—"}
          </p>
          <p className="text-sm text-muted-foreground">
            Median {dest} reachable in {cutoff} minutes across {data.n_areas.toLocaleString("en-GB")}{" "}
            {country === "ireland" ? "Small Areas" : "LSOAs"}
            in {place}.
          </p>
          <div className="mt-4 space-y-1">
            {data.histogram.map((bin) => {
              const max = Math.max(...data.histogram.map((b) => b.n), 1)
              return (
                <div key={bin.bin} className="flex items-center gap-2 text-xs">
                  <span className="w-28 shrink-0 text-muted-foreground">{bin.bin}</span>
                  <div className="flex-1 h-3 bg-muted rounded">
                    <div
                      className="h-3 rounded bg-primary/70"
                      style={{ width: `${(100 * bin.n) / max}%` }}
                    />
                  </div>
                  <span className="tabular-nums w-10 text-right">{bin.n}</span>
                </div>
              )
            })}
          </div>
        </div>
      )}
    </section>
  )
}
