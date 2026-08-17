import { lazy, Suspense } from "react"
import { Link, useNavigate, useSearchParams } from "react-router"
import { useFilters, useMapLayer, useOps, useOverview } from "@/api/hooks"
import { AREA_TYPES, COUNTRIES, regionsForCountry } from "@/lib/constants"
import { appPath, withSearch } from "@/lib/appRoutes"
import { filterSentence, formatInCountryScore } from "@/lib/scoreFormat"
import { DimensionCard } from "./DimensionCard"

const ChoroplethMap = lazy(() => import("@/components/charts/ChoroplethMap"))

export function HomePage() {
  const { country, region, urbanRural, pack, mode } = useFilters()
  const countryName = COUNTRIES.find((c) => c.code === country)?.name ?? country
  const regionName = regionsForCountry(country).find((r) => r.code === region)?.name ?? region
  const areaName = AREA_TYPES.find((a) => a.code === urbanRural)?.name ?? urbanRural
  const packReady = COUNTRIES.find((c) => c.code === country)?.packReady ?? false
  const { data, isLoading, error } = useOverview(region, urbanRural, country, pack, mode)
  const mapQ = useMapLayer(region, urbanRural, country, pack, mode)
  const [params] = useSearchParams()
  const navigate = useNavigate()
  const place = filterSentence(regionName, areaName)
  const londonRural = region === "E12000007" && urbanRural === "rural"

  if (!packReady) {
    return (
      <p className="text-sm text-muted-foreground py-8 max-w-xl">
        The {countryName} pack is not built yet. England, Ireland, the Netherlands, and France
        use the same method.
      </p>
    )
  }

  const packMiss =
    (error as { status?: number } | null)?.status === 404 ||
    (mapQ.error as { status?: number } | null)?.status === 404

  if (packMiss || error) {
    const status = (error as { status?: number } | undefined)?.status
      ?? (mapQ.error as { status?: number } | undefined)?.status
    if (status === 404 || packMiss) {
      return (
        <p className="text-sm text-muted-foreground py-8 max-w-xl" data-testid="unknown-pack-home">
          Unknown pack {pack || "date"} for {countryName}. This checkout has one network date —
          it does not silently show the current briefing.
        </p>
      )
    }
    return (
      <p className="text-destructive text-sm">Unable to load overview — try refreshing.</p>
    )
  }

  if (isLoading || mapQ.isLoading) {
    return (
      <div data-testid="home-loading">
        <h1 className="text-2xl font-semibold mb-4">Loading {countryName} briefing…</h1>
        <div className="h-[min(62vh,520px)] app-glass animate-pulse rounded-2xl mb-6" />
      </div>
    )
  }

  const score = data?.score ?? null
  const scoreLabel = formatInCountryScore(score)

  return (
    <div>
      <h1 className="text-2xl sm:text-3xl font-semibold text-foreground tracking-tight mb-1">
        Where the bus fails people — {place}
      </h1>
      <p className="text-sm text-muted-foreground mb-4 max-w-2xl">
        In-country briefing for {place}. Ranks stay inside {countryName}. Never one Europe-wide index.
      </p>

      <div className="mb-4">
        <p className="text-[11px] font-mono uppercase tracking-wide text-muted-foreground">
          In-country score
        </p>
        <p className="text-5xl sm:text-6xl font-bold tabular-nums tracking-tight text-foreground">
          {scoreLabel}
        </p>
        <p className="text-sm text-muted-foreground mt-1 max-w-xl">
          {data?.score_note
            ?? "0–100 for this filter: 400 m coverage, evening service, weekday quality, inverted deprivation gap."}
        </p>
      </div>

      {londonRural ? (
        <p className="text-sm text-muted-foreground py-6 max-w-xl">
          London has no rural LSOAs under the official urban/rural classification — this filter is empty.
        </p>
      ) : mapQ.data?.empty ? (
        <p className="text-sm text-muted-foreground py-6 max-w-xl">
          {mapQ.data.empty_reason ?? "No map layer for this filter."}
        </p>
      ) : mapQ.data && Array.isArray(mapQ.data.data) && mapQ.data.data.length > 0 ? (
        <Suspense fallback={<div className="h-[min(62vh,520px)] app-glass animate-pulse rounded-2xl mb-4" />}>
          <ChoroplethMap
            chartData={{
              type: "choropleth",
              geography:
                country === "ireland"
                  ? "ireland_county"
                  : country === "netherlands"
                    ? "netherlands_provincie"
                    : country === "france"
                      ? "france_region"
                      : (mapQ.data.geography ?? "region"),
              metric_label: mapQ.data.metric_label ?? "People with no nearby stop",
              data: mapQ.data.data,
              title: `Deserts — ${place}`,
            }}
            onAreaClick={(code) => {
              const next = new URLSearchParams(params)
              if (code.startsWith("E12") || country === "ireland" || country === "netherlands" || country === "france") {
                next.set("region", code)
              }
              navigate(withSearch(appPath(country, "access"), next.toString()))
            }}
          />
        </Suspense>
      ) : (
        <p className="text-sm text-muted-foreground py-6 max-w-xl">
          {mapQ.error
            ? "Map layer could not be loaded for this filter."
            : "No map layer for this filter."}
        </p>
      )}

      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 sm:gap-4 mt-6">
        {data?.dimensions.map((d) => (
          <DimensionCard key={d.id} dim={d} />
        ))}
        <Link
          to={withSearch(appPath(country, "reach"), params.toString())}
          className="app-glass-strong group block text-left p-5 rounded-2xl hover:border-primary/30 transition-all duration-200 hover:-translate-y-0.5"
          data-testid="reach-door"
        >
          <h3 className="flex items-center gap-2 text-sm font-semibold text-foreground group-hover:text-primary transition-colors">
            Reach
          </h3>
          <p className="text-2xl font-bold tabular-nums mt-2">Bands</p>
          <p className="text-sm text-muted-foreground mt-1 leading-snug">
            Access / service bands and 15/30/45
          </p>
        </Link>
        <Link
          to={withSearch(appPath(country, "time"), params.toString())}
          className="app-glass-strong group block text-left p-5 rounded-2xl hover:border-primary/30 transition-all duration-200 hover:-translate-y-0.5"
          data-testid="time-door"
        >
          <h3 className="flex items-center gap-2 text-sm font-semibold text-foreground group-hover:text-primary transition-colors">
            Time
          </h3>
          <p className="text-2xl font-bold tabular-nums mt-2">Network dates</p>
          <p className="text-sm text-muted-foreground mt-1 leading-snug">
            Same score across monthly snapshots — Census / deprivation frozen
          </p>
        </Link>
        <OpsDoor />
        <Link
          to={withSearch(appPath(country, "studio"), params.toString())}
          className="app-glass-strong group block text-left p-5 rounded-2xl hover:border-primary/30 transition-all duration-200 hover:-translate-y-0.5"
          data-testid="studio-door"
        >
          <h3 className="flex items-center gap-2 text-sm font-semibold text-foreground group-hover:text-primary transition-colors">
            Studio
          </h3>
          <p className="text-2xl font-bold tabular-nums mt-2">Draw</p>
          <p className="text-sm text-muted-foreground mt-1 leading-snug">
            Patch a route — who gains and who loses
          </p>
        </Link>
      </div>

      <p className="mt-6 text-xs text-muted-foreground leading-relaxed">
        {country === "ireland"
          ? "Network / GTFS: TFI GTFS_All.zip. CSO Small Areas 2022. Pobal HP Deprivation Index 2022. Republic only — Northern Ireland is out of scope."
          : country === "netherlands"
            ? "Network / GTFS: OVapi gtfs-nl.zip. CBS buurten 2024. SES-WOA 2023 (voorlopig). Bus-only is the default; mode=all adds rail/tram/metro. SES join is 70.5% at buurt — remaining SES scores are null."
            : country === "france"
              ? "Network / GTFS: NAP harvest (441 merged / 111 skipped). IGN IRIS. F-EDI 2021. Metropolitan France only — DOM out. 58 unmatched IRIS have no région slug and are excluded from région bars."
            : "Network / GTFS: BODS bulk (pack vintage, not the warehouse clock). Census 2021 LSOAs. IMD 2025 ranks. These are three dates — not one “data as of warehouse build.”"}
      </p>
    </div>
  )
}

function OpsDoor() {
  const { country } = useFilters()
  const [params] = useSearchParams()
  const ops = useOps(country, params.get("pack") ?? "")
  const headline = ops.data?.empty
    ? "Empty"
    : ops.data?.pct_late != null
      ? `${ops.data.pct_late.toFixed(0)}% late`
      : ops.isError
        ? "No rollup"
        : "Snapshot"
  const blurb =
    country === "ireland"
      ? "NTA GTFS-RT for three operators — honest empty without a key"
      : country === "netherlands"
        ? "OVapi RT if a rollup exists — not a second score"
        : country === "france"
          ? "NAP gtfs-rt union, incomplete by design"
          : "BODS GTFS-RT / SIRI where the timetable is not what ran"
  return (
    <Link
      to={withSearch(appPath(country, "ops"), params.toString())}
      className="app-glass-strong group block text-left p-5 rounded-2xl hover:border-primary/30 transition-all duration-200 hover:-translate-y-0.5"
      data-testid="ops-door"
    >
      <h3 className="flex items-center gap-2 text-sm font-semibold text-foreground group-hover:text-primary transition-colors">
        Ops
      </h3>
      <p className="text-2xl font-bold tabular-nums mt-2">{headline}</p>
      <p className="text-sm text-muted-foreground mt-1 leading-snug">{blurb}</p>
    </Link>
  )
}
