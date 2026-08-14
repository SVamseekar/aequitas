import { lazy, Suspense, useMemo, useState } from "react"
import { useFilters, useTimeSeries } from "@/api/hooks"
import { AREA_TYPES, COUNTRIES, regionsForCountry } from "@/lib/constants"
import { filterSentence } from "@/lib/scoreFormat"
import { isLondonRural } from "@/lib/uniqueExhibits"

const TimeLineChart = lazy(() => import("@/components/charts/TimeLineChart"))

const METRICS = [
  { id: "score", label: "In-country score" },
  { id: "pct_400m", label: "% within 400 m" },
  { id: "evening_isolated_pct", label: "Evening isolated %" },
  { id: "mean_sqi", label: "Mean SQI" },
] as const

export default function TimePage() {
  const { country, region, urbanRural, pack } = useFilters()
  const countryName = COUNTRIES.find((c) => c.code === country)?.name ?? country
  const regionName = regionsForCountry(country).find((r) => r.code === region)?.name ?? region
  const areaName = AREA_TYPES.find((a) => a.code === urbanRural)?.name ?? urbanRural
  const place = filterSentence(regionName, areaName)
  const packReady = COUNTRIES.find((c) => c.code === country)?.packReady ?? false
  const areaNoun =
    country === "ireland" ? "Small Areas" : country === "netherlands" ? "buurten" : "LSOAs"
  const [metric, setMetric] = useState<(typeof METRICS)[number]["id"]>("score")
  const series = useTimeSeries(country, region, urbanRural, metric, pack)
  const londonRural = isLondonRural(region, urbanRural)

  const points = series.data?.points ?? []
  const compare = useMemo(() => {
    const numbered = points.filter((p) => typeof p.value === "number")
    if (numbered.length < 2) return null
    const a = numbered[0]
    const b = numbered[numbered.length - 1]
    return {
      from: a.as_of,
      to: b.as_of,
      delta: Number(((b.value as number) - (a.value as number)).toFixed(2)),
    }
  }, [points])

  if (!packReady) {
    return (
      <div data-testid="time-page">
        <h1 className="text-2xl font-semibold mb-2">Time</h1>
        <p className="text-sm text-muted-foreground max-w-xl">
          The {countryName} pack is not built yet. England and Ireland are live; the Netherlands and
          France use the same method (waves 7 and 9).
        </p>
      </div>
    )
  }

  if (londonRural) {
    return (
      <div data-testid="time-page">
        <h1 className="text-2xl font-semibold mb-2">Time — {place}</h1>
        <p className="text-sm text-muted-foreground max-w-xl">
          London has no rural LSOAs under the official classification — this filter is empty.
        </p>
      </div>
    )
  }

  return (
    <div data-testid="time-page">
      <h1 className="text-2xl sm:text-3xl font-semibold tracking-tight mb-1">
        Network dates — {place}
      </h1>
      <p className="text-sm text-muted-foreground mb-4 max-w-2xl">
        Same metric for {countryName} ({areaNoun}), many network dates.{" "}
        {country === "ireland"
          ? "CSO Small Areas 2022 and Pobal HP 2022 stay frozen. Only TFI network dates time-travel."
          : country === "netherlands"
            ? "CBS buurten / SES-WOA stay frozen. Only OVapi network dates time-travel."
            : "Census 2021 and IMD 2025 stay frozen. Only BODS-derived metrics time-travel."}
      </p>

      <div className="flex flex-wrap gap-2 mb-4">
        {METRICS.map((m) => (
          <button
            key={m.id}
            type="button"
            onClick={() => setMetric(m.id)}
            className={`px-3 py-1.5 text-sm rounded-xl border ${
              metric === m.id
                ? "border-primary bg-primary/10 text-foreground"
                : "border-white/50 text-muted-foreground"
            }`}
          >
            {m.label}
          </button>
        ))}
      </div>

      {series.isLoading ? (
        <div className="h-64 app-glass animate-pulse rounded-2xl" />
      ) : (series.error as { status?: number } | null)?.status === 404 ||
        String(series.error?.message ?? "").includes("API 404") ? (
        <p className="text-sm text-muted-foreground max-w-xl" data-testid="unknown-pack">
          Unknown pack {pack || "date"} for {countryName}. This checkout has one network date —
          it does not silently show the current point.
        </p>
      ) : series.data?.empty ? (
        <p className="text-sm text-muted-foreground max-w-xl">{series.data.empty_reason}</p>
      ) : (
        <>
          {series.data?.one_date ? (
            <p className="text-sm text-foreground mb-3" data-testid="one-date-note">
              Only one network date in this checkout.
            </p>
          ) : null}
          <p className="text-sm text-muted-foreground mb-3">{series.data?.note}</p>
          <Suspense fallback={<div className="h-64 app-glass animate-pulse rounded-2xl" />}>
            <TimeLineChart
              points={points}
              metricLabel={METRICS.find((m) => m.id === metric)?.label ?? metric}
              areaNoun={areaNoun}
            />
          </Suspense>
          {compare ? (
            <p className="text-sm mt-4" data-testid="time-delta">
              {compare.from} → {compare.to}: Δ {compare.delta > 0 ? "+" : ""}
              {compare.delta} on {METRICS.find((m) => m.id === metric)?.label}.
            </p>
          ) : null}
        </>
      )}
    </div>
  )
}
