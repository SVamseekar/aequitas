import { useFilters, useOps } from "@/api/hooks"
import { AREA_TYPES, COUNTRIES, regionsForCountry } from "@/lib/constants"
import { filterSentence } from "@/lib/scoreFormat"

function feedNoun(country: string): string {
  if (country === "ireland") {
    return "NTA GTFS-RT (Dublin Bus, Bus Éireann, Go-Ahead Ireland only — not the rest of the Republic)"
  }
  if (country === "netherlands") {
    return "OVapi GTFS-RT (mixed mode; briefing default stays bus). SES / buurten stay on the static pack"
  }
  if (country === "france") {
    return "NAP gtfs-rt union (incomplete; missing départements logged, not filled). F-EDI / IRIS / AOM stay on the static pack"
  }
  return "BODS GTFS-RT / SIRI-VM (OGL). Joined to existing stop → LSOA only — no Census re-download"
}

export default function OpsPage() {
  const { country, region, urbanRural, pack } = useFilters()
  const countryName = COUNTRIES.find((c) => c.code === country)?.name ?? country
  const regionName = regionsForCountry(country).find((r) => r.code === region)?.name ?? region
  const areaName = AREA_TYPES.find((a) => a.code === urbanRural)?.name ?? urbanRural
  const place = filterSentence(regionName, areaName)
  const ops = useOps(country, pack)

  const errStatus = (ops.error as { status?: number } | null)?.status
  const unknownPack =
    errStatus === 404 && Boolean(pack) && String(ops.error?.message ?? "").includes("Unknown pack")

  return (
    <div data-testid="ops-page" className="pb-10">
      <h1 className="text-2xl sm:text-3xl font-semibold tracking-tight mb-1">
        Ops — {place}
      </h1>
      <p className="text-sm text-muted-foreground mb-4 max-w-2xl">
        Where the published timetable is not what ran, if a free real-time feed exists. Not a second
        score. Not 15/30/45. {feedNoun(country)}.
      </p>

      {ops.isLoading ? (
        <div className="h-64 app-glass animate-pulse rounded-2xl" />
      ) : unknownPack ? (
        <p className="text-sm text-muted-foreground max-w-xl" data-testid="unknown-pack">
          Unknown pack {pack} for {countryName}. Ops is not time-travelled to a date we did not store.
        </p>
      ) : errStatus === 404 ? (
        <p className="text-sm text-muted-foreground max-w-xl" data-testid="ops-empty">
          No ops rollup for {countryName} yet. {feedNoun(country)}. We do not invent 0% on-time.
        </p>
      ) : ops.data?.empty ? (
        <p className="text-sm text-muted-foreground max-w-xl" data-testid="ops-empty">
          {ops.data.empty_reason}
        </p>
      ) : ops.data ? (
        <OpsExhibit data={ops.data} country={country} />
      ) : (
        <p className="text-sm text-muted-foreground">Ops snapshot could not be loaded.</p>
      )}
    </div>
  )
}

function OpsExhibit({
  data,
  country,
}: {
  data: NonNullable<ReturnType<typeof useOps>["data"]>
  country: string
}) {
  const rows = data.by_region ?? []
  const maxN = Math.max(1, ...rows.map((r) => r.n_updates))
  const pct = data.pct_late
  return (
    <div className="space-y-5">
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        <Stat label="Updates in window" value={data.n_updates.toLocaleString("en-GB")} />
        <Stat
          label={`Late > ${(data.late_threshold_seconds ?? 300) / 60} min`}
          value={pct == null ? "—" : `${pct.toFixed(1)}%`}
        />
        <Stat label="Skipped / cancelled" value={`${data.n_skipped} / ${data.n_cancelled}`} />
        <Stat
          label="Route coverage"
          value={data.coverage_pct == null ? "—" : `${data.coverage_pct.toFixed(1)}%`}
        />
      </div>

      {rows.length > 0 ? (
        <div data-testid="ops-strip">
          <h2 className="text-sm font-semibold mb-2">
            Late / skipped by {country === "england" ? "ITL1 region" : "region"} (this snapshot)
          </h2>
          <ul className="space-y-1.5">
            {rows.map((r) => (
              <li key={r.code} className="grid grid-cols-[minmax(7rem,11rem)_1fr_auto] gap-2 items-center">
                <span className="text-xs text-muted-foreground truncate">{r.name}</span>
                <div className="h-3 rounded-full bg-black/10 overflow-hidden flex">
                  <div
                    className="h-full bg-amber-700/80"
                    style={{ width: `${Math.max(2, (r.n_late / maxN) * 100)}%` }}
                    title={`${r.n_late} late`}
                  />
                  <div
                    className="h-full bg-stone-400/70"
                    style={{ width: `${Math.max(0, ((r.n_updates - r.n_late) / maxN) * 100)}%` }}
                  />
                </div>
                <span className="text-xs tabular-nums text-muted-foreground">
                  {r.n_late} late · {r.n_skipped} skipped · {r.n_updates}
                </span>
              </li>
            ))}
          </ul>
        </div>
      ) : (
        <p className="text-sm text-muted-foreground">
          No region join on this snapshot (stop_id did not match the static pack, or the feed had no
          stop ids).
        </p>
      )}

      {country === "england" && data.by_imd_decile?.some((d) => d.n_updates > 0) ? (
        <div>
          <h2 className="text-sm font-semibold mb-2">Updates that joined an IMD decile</h2>
          <div className="flex gap-1 items-end h-24">
            {data.by_imd_decile.map((d) => (
              <div key={d.imd_decile} className="flex-1 flex flex-col justify-end items-center gap-1">
                <div
                  className="w-full bg-amber-800/70 rounded-t"
                  style={{ height: `${Math.max(4, (d.n_updates / Math.max(1, ...data.by_imd_decile.map((x) => x.n_updates))) * 80)}px` }}
                />
                <span className="text-[10px] text-muted-foreground">{d.imd_decile}</span>
              </div>
            ))}
          </div>
          <p className="text-[11px] text-muted-foreground mt-1">Decile 1 = most deprived. England warehouse join only.</p>
        </div>
      ) : null}

      <p className="text-sm text-foreground max-w-2xl" data-testid="ops-coverage">
        {data.coverage_sentence}
      </p>
      <p className="text-xs text-muted-foreground" data-testid="ops-vintage">
        Rollup vintage {data.vintage}. {data.window_note} {data.late_threshold_note}
      </p>
    </div>
  )
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div className="app-glass rounded-2xl p-4">
      <p className="text-xs text-muted-foreground">{label}</p>
      <p className="text-xl font-semibold tabular-nums mt-1">{value}</p>
    </div>
  )
}
