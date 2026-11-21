import { lazy, Suspense, useMemo } from "react"
import { useSearchParams } from 'react-router'
import { useFilters, useTimeSeries } from "@/api/hooks"
import { AREA_TYPES, COUNTRIES, regionsForCountry } from "@/lib/constants"
import { filterSentence } from "@/lib/scoreFormat"
import { isLondonRural } from "@/lib/uniqueExhibits"
import { BriefingActions } from '@/components/shared/BriefingActions'
import { downloadCsv } from '@/lib/downloadCsv'
import { coveragePresentation } from '@/lib/coverage'

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
    country === "ireland"
      ? "Small Areas"
      : country === "netherlands"
        ? "buurten"
        : country === "france"
          ? "IRIS"
          : "LSOAs"
  const [params, setParams] = useSearchParams()
  const metric = METRICS.find(m => m.id === params.get('metric'))?.id ?? 'score'
  const setMetric = (value: string) => { const next = new URLSearchParams(params); next.set('metric', value); setParams(next) }
  const series = useTimeSeries(country, region, urbanRural, metric, pack)
  const londonRural = isLondonRural(region, urbanRural)

  const points = useMemo(() => series.data?.points ?? [], [series.data?.points])
  const metricLabel = metric === 'pct_400m' ? coveragePresentation(country).shortLabel : METRICS.find(m => m.id === metric)?.label ?? metric
  const unit = metric === 'pct_400m' || metric === 'evening_isolated_pct' ? '%' : ' / 100'
  const digits = metric === 'mean_sqi' ? 2 : 1
  const deltaUnit = unit === '%' ? ' pp' : ' points'
  const exportObservations = () => downloadCsv('aequitas-network-observations.csv', ['country', 'region', 'area', 'metric', 'network_date', 'value', 'areas', 'current'], points.map(point => [country, region, urbanRural, metric, point.as_of, point.value, point.n_areas, point.current ? 'true' : 'false']))
  const latest = points.at(-1)
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
    <div data-testid="time-page" className='time-page'>
      <div className='time-heading'><div>
      <h1 className="text-2xl sm:text-3xl font-semibold tracking-tight mb-1">
        Time — {metricLabel}
      </h1>
      <p className="text-sm text-muted-foreground mb-4 max-w-2xl">
        {countryName} · {place === countryName ? '' : `${place} · `}{areaNoun} · registered network dates.
      </p>
      </div><div className='flex gap-2'><BriefingActions /><button type='button' className='app-panel-button' disabled={!points.length || Boolean(series.error)} onClick={exportObservations}>Export observations CSV</button></div></div>

      <div className="time-metric-tabs" role='group' aria-label='Time metric'>
        {METRICS.map((m) => (
          <button
            key={m.id}
            type="button"
            onClick={() => setMetric(m.id)}
            aria-pressed={metric === m.id}
            className={`px-3 py-1.5 text-sm rounded-xl border ${
              metric === m.id
                ? "border-primary bg-primary/10 text-foreground"
                : "border-white/50 text-muted-foreground"
            }`}
          >
            {m.id === 'pct_400m' ? coveragePresentation(country).shortLabel : m.label}
          </button>
        ))}
      </div>

      {series.isLoading ? (
        <div className="h-64 app-glass animate-pulse rounded-2xl" />
      ) : (series.error as { status?: number } | null)?.status === 404 ||
        String(series.error?.message ?? "").includes("API 404") ? (
        <p className="text-sm text-muted-foreground max-w-xl" data-testid="unknown-pack">
          Unknown pack {pack || "date"} for {countryName}. This network date is not registered;
          it does not silently show the current point.
        </p>
      ) : series.error ? <p role='alert' className='text-destructive text-sm'>Network observations could not be loaded. Try refreshing.</p> : series.data?.empty ? (
        <p className="text-sm text-muted-foreground max-w-xl">{series.data.empty_reason}</p>
      ) : (
        <>
          {series.data?.one_date ? (
            <p className="text-sm text-foreground mb-3" data-testid="one-date-note">
              Only one network date in this checkout.
            </p>
          ) : null}
          <p className="text-sm text-muted-foreground mb-3">{series.data?.note}</p>
          <div className='app-time-grid'>
          <section className='app-panel'>
          <h2>{metricLabel} over time</h2>
          <Suspense fallback={<div className="h-64 app-glass animate-pulse rounded-2xl" />}>
            <TimeLineChart
              points={points}
              metricLabel={metricLabel}
              areaNoun={areaNoun}
            />
          </Suspense>
          <p className='mt-2'>{points.length === 2 ? 'Two observations; no trend conclusion.' : 'Registered observations only; no forecast.'}</p>
          </section>
          <aside className='app-panel'>
            <h2>Latest value</h2><p>{latest?.as_of ?? 'No dated observation'}</p>
            <p className='app-score-number'>{latest?.value == null ? '—' : latest.value.toFixed(digits)}<span>{unit}</span></p>
          {compare ? (
            <p className="text-sm mt-4" data-testid="time-delta">
              Δ from {compare.from}: {compare.delta > 0 ? "+" : ""}
              {compare.delta.toFixed(1)}{deltaUnit}.
            </p>
          ) : null}
          <h3 className='mt-6 mb-3'>Registered observations</h3>
          <dl>{points.map(point => <div key={point.pack_id} className='flex justify-between gap-4 py-3 border-t border-border text-sm'><dt>{point.as_of}{point.current ? ' (current)' : ''}</dt><dd>{point.value == null ? '—' : `${point.value.toFixed(digits)}${unit}`}</dd></div>)}</dl>
          <p className='mt-5'>{metric === 'pct_400m' ? coveragePresentation(country).definition : metric === 'evening_isolated_pct' ? 'Share of areas with no service after 19:00 on a typical weekday.' : metric === 'mean_sqi' ? 'Mean scheduled service quality index.' : 'Composite in-country score; missing components are dropped and weights renormalised.'}</p>
          </aside></div>
        </>
      )}
    </div>
  )
}
