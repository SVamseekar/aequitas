import { lazy, Suspense, useState } from "react"
import { Link, useSearchParams } from "react-router"
import { useFilters, useReach, useReachBands, useScore } from "@/api/hooks"
import { AccessReachPanel } from "@/components/access/AccessReachPanel"
import { AREA_TYPES, COUNTRIES, regionsForCountry } from "@/lib/constants"
import { appPath, withSearch } from "@/lib/appRoutes"
import { filterSentence, formatInCountryScore } from "@/lib/scoreFormat"
import { isLondonRural } from "@/lib/uniqueExhibits"

const ChoroplethMap = lazy(() => import("@/components/charts/ChoroplethMap"))

const BAND_SWATCH: Record<number, { color: string; meaning: string }> = {
  1: { color: "#4a1c0c", meaning: "1 — no nearby stop or no weekday service" },
  2: { color: "#8b3a1a", meaning: "2 — stop nearby, evening and Sunday isolated" },
  3: { color: "#c45c26", meaning: "3 — thin weekday service" },
  4: { color: "#e8b86d", meaning: "4 — moderate weekday service" },
  5: { color: "#c5d4a8", meaning: "5 — good weekday service" },
  6: { color: "#6b8f71", meaning: "6 — high weekday quality" },
}

function BandDecileHeatmap({
  rows,
  indexLabel,
  areaNoun,
}: {
  rows: { band: number; imd_decile: number; people: number; n_areas: number }[]
  indexLabel: string
  areaNoun: string
}) {
  const [open, setOpen] = useState(false)
  const max = Math.max(1, ...rows.map((r) => r.people))
  const cell = (band: number, dec: number) =>
    rows.find((r) => r.band === band && r.imd_decile === dec)
  const worstPeople = rows.filter((r) => r.band <= 2 && r.imd_decile <= 3).reduce((s, r) => s + r.people, 0)
  return (
    <div>
      <p className="text-sm mt-2 max-w-2xl" data-testid="band-decile-claim">
        {worstPeople > 0
          ? `${worstPeople.toLocaleString("en-GB")} people sit in bands 1–2 and deprivation deciles 1–3 (most deprived, thinnest service).`
          : "No people sit in both the worst two bands and the most deprived three deciles for this filter."}
      </p>
      <div className="overflow-x-auto mt-3" data-testid="band-decile-heatmap">
        <table className="text-[11px] border-collapse">
          <thead>
            <tr>
              <th className="text-left pr-2 py-1 text-muted-foreground font-medium">
                Band \\ {indexLabel}
              </th>
              {Array.from({ length: 10 }, (_, i) => (
                <th key={i} className="w-8 text-center text-muted-foreground font-medium">{i + 1}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {[1, 2, 3, 4, 5, 6].map((b) => (
              <tr key={b}>
                <td className="pr-2 py-0.5 font-medium">{b}</td>
                {Array.from({ length: 10 }, (_, i) => {
                  const hit = cell(b, i + 1)
                  const p = hit?.people ?? 0
                  const t = p / max
                  return (
                    <td
                      key={i}
                      title={hit ? `${p.toLocaleString("en-GB")} people · ${hit.n_areas} ${areaNoun}` : "0"}
                      className="w-8 h-7 text-center tabular-nums"
                      style={{
                        background: p ? `rgba(74, 28, 12, ${0.12 + t * 0.75})` : "transparent",
                        color: t > 0.55 ? "#f7f1e8" : "inherit",
                      }}
                    >
                      {p ? (p >= 1000 ? `${Math.round(p / 1000)}k` : p) : ""}
                    </td>
                  )
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <button
        type="button"
        className="text-xs underline mt-2"
        onClick={() => setOpen((v) => !v)}
        data-testid="band-decile-toggle"
      >
        {open ? "Hide all cells" : "All cells"}
      </button>
      {open ? (
        <table className="mt-2 text-sm w-full max-w-xl" data-testid="band-decile-table">
          <thead>
            <tr className="text-left text-muted-foreground">
              <th className="py-1">Band</th>
              <th>{indexLabel} decile</th>
              <th>People</th>
              <th>{areaNoun}</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((r) => (
              <tr key={`${r.band}-${r.imd_decile}`}>
                <td className="py-1">{r.band}</td>
                <td>{r.imd_decile}</td>
                <td className="tabular-nums">{r.people.toLocaleString("en-GB")}</td>
                <td>{r.n_areas}</td>
              </tr>
            ))}
          </tbody>
        </table>
      ) : null}
    </div>
  )
}

export default function ReachPage() {
  const { country, region, urbanRural } = useFilters()
  const [params] = useSearchParams()
  const countryName = COUNTRIES.find((c) => c.code === country)?.name ?? country
  const regionName = regionsForCountry(country).find((r) => r.code === region)?.name ?? region
  const areaName = AREA_TYPES.find((a) => a.code === urbanRural)?.name ?? urbanRural
  const place = filterSentence(regionName, areaName)
  const ireland = country === "ireland"
  const netherlands = country === "netherlands"
  const areaNoun =
    ireland ? "Small Areas" : netherlands ? "buurten" : country === "france" ? "IRIS" : "LSOAs"
  const indexLabel =
    ireland ? "HP" : netherlands ? "SES-WOA" : country === "france" ? "F-EDI" : "IMD"
  const londonRural = isLondonRural(region, urbanRural)
  const dest = params.get("dest") ?? "jobs"
  const cutoff = Number(params.get("cutoff") ?? "45")
  const bandsQ = useReachBands(region, urbanRural, country)
  const reachQ = useReach(region, urbanRural, dest, cutoff, country)
  const scoreQ = useScore(region, urbanRural, country)
  const packReady = COUNTRIES.find((c) => c.code === country)?.packReady ?? false
  const studioJob = params.get("studio_job")

  if (!packReady) {
    return (
      <div data-testid="reach-page">
        <h1 className="text-2xl font-semibold mb-2">Reach</h1>
        <p className="text-sm text-muted-foreground max-w-xl">
          The {countryName} pack is not built yet. England and Ireland are live; the Netherlands and
          France use the same method (waves 7 and 9).
        </p>
      </div>
    )
  }

  if (londonRural) {
    return (
      <div data-testid="reach-page">
        <h1 className="text-2xl font-semibold mb-2">Reach</h1>
        <p className="text-sm text-muted-foreground max-w-xl">
          London has no rural LSOAs under the official urban/rural classification — this filter is empty.
        </p>
      </div>
    )
  }

  const bands = bandsQ.data
  const packQs = new URLSearchParams({
    region,
    urban_rural: urbanRural,
    dest_type: dest,
    cutoff: String(cutoff),
  })
  if (studioJob) packQs.set("studio_job", studioJob)

  return (
    <div data-testid="reach-page">
      <p className="text-xs text-muted-foreground mb-2 md:hidden">
        Wider screen for the map if the choropleth feels cramped (~390px still lists people by band).
      </p>
      <h1 className="text-2xl sm:text-3xl font-semibold tracking-tight">
        Reach — {place}
      </h1>
      <p className="text-sm text-muted-foreground mt-1 max-w-2xl">
        Aequitas access / service bands for {place}. Not official PTAL.
        {ireland
          ? " Not 45-minute jobs unless a Republic travel-time parquet exists (it does not in this pack)."
          : netherlands
            ? " 15/30/45 is not run for the Netherlands in this checkout — honest empty, not England bands."
            : country === "france"
              ? " 15/30/45 is not run for France in this checkout — honest empty, not England bands."
            : " Not TfL. Not 45-minute jobs unless r5py has written destination counts for this ITL1."}
      </p>
      <p className="text-sm mt-2">
        In-country score {formatInCountryScore(scoreQ.data?.score ?? null)}
        {scoreQ.data?.n_areas != null ? ` · ${scoreQ.data.n_areas.toLocaleString("en-GB")} areas` : ""}.
      </p>

      <div className="flex flex-wrap gap-3 mt-3 text-sm">
        <Link className="underline" to={withSearch(appPath(country, "access"), params.toString())}>
          Access (400 m)
        </Link>
        <Link className="underline" to={withSearch(appPath(country, "studio"), params.toString())}>
          Studio
        </Link>
        <a className="underline" href={`/api/export/pack.csv?${packQs}`} data-testid="pack-csv">
          Download briefing pack (CSV)
        </a>
        <a className="underline" href={`/api/export/pack.html?${packQs}`} data-testid="pack-html">
          Printable pack (HTML)
        </a>
      </div>

      {bandsQ.isLoading ? (
        <div className="h-[min(50vh,400px)] app-glass animate-pulse rounded-2xl mt-6" />
      ) : bands?.empty ? (
        <p className="text-sm text-muted-foreground mt-6 max-w-xl">{bands.empty_reason}</p>
      ) : bands ? (
        <section className="mt-6">
          <h2 className="text-lg font-semibold">{bands.label}</h2>
          <p className="text-sm mt-2 max-w-2xl" data-testid="reach-narrative">
            {bands.narrative}
          </p>
          <p className="text-xs text-muted-foreground mt-2 max-w-2xl">{bands.formula}</p>
          {bands.map?.data && bands.map.data.length > 0 ? (
            <div className="hidden sm:block mt-4">
              <Suspense fallback={<div className="h-[min(50vh,400px)] app-glass animate-pulse rounded-2xl" />}>
                <ChoroplethMap
                  chartData={{
                    type: "choropleth",
                    geography: bands.map.geography,
                    metric_label: bands.map.metric_label,
                    color_mode: bands.map.color_mode ?? "band",
                    data: bands.map.data,
                    title: `Bands — ${place}`,
                  }}
                />
              </Suspense>
            </div>
          ) : (
            <p className="text-sm text-muted-foreground mt-4 max-w-xl" data-testid="map-unavailable">
              No map areas match this filter — the table below still applies.
            </p>
          )}
          {bands.map_aggregation ? (
            <p className="text-xs text-muted-foreground mt-2 max-w-2xl">{bands.map_aggregation}</p>
          ) : null}
          {bands.unmatched_note ? (
            <p className="text-xs text-muted-foreground mt-1 max-w-2xl">{bands.unmatched_note}</p>
          ) : null}
          <div className="flex flex-wrap gap-2 mt-3 text-xs">
            {[1, 2, 3, 4, 5, 6].map((b) => (
              <span
                key={b}
                className="px-2 py-1 rounded-full border border-border inline-flex items-center gap-1.5"
              >
                <span
                  className="inline-block h-2.5 w-2.5 rounded-sm shrink-0"
                  style={{ background: BAND_SWATCH[b].color }}
                  aria-hidden
                />
                {BAND_SWATCH[b].meaning}
              </span>
            ))}
          </div>
          <h3 className="text-sm font-semibold mt-6">People by band × {indexLabel} decile</h3>
          <BandDecileHeatmap
            rows={bands.people_by_band_decile ?? []}
            indexLabel={indexLabel}
            areaNoun={areaNoun}
          />
        </section>
      ) : null}

      <div className="mt-8">
        <AccessReachPanel />
      </div>
      {reachQ.data && !reachQ.data.available ? (
        <p className="text-xs text-muted-foreground mt-2 max-w-2xl">
          {netherlands
            ? "15/30/45 has not been run for the Netherlands (no r5py / Geofabrik parquet)."
            : country === "france"
              ? "15/30/45 has not been run for France (no r5py / Geofabrik parquet)."
            : `ITL1s with 15/30/45 in this pack: ${
                reachQ.data.geographies.length ? reachQ.data.geographies.join(", ") : "none"
              }.`}
        </p>
      ) : null}
    </div>
  )
}
