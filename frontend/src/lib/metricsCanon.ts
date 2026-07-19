/**
 * Single source of truth for marketing and UI headline metrics.
 * Sourced from data/audit/ground_truth.json + national section_results
 * (warehouse built 2026-06-14; pack locked 2026-07-19).
 *
 * Do not drift: change only after re-running warehouse / Phase 0 audit.
 */

export const METRICS_CANON = {
  asOf: "2026-07-19",
  warehouseBuiltAt: "2026-06-14",
  trips: 1_752_443,
  tripsDisplay: "1.75M",
  routes: 13_099,
  stops: 274_719,
  lsoas: 33_755,
  population: 56_490_056,
  populationDisplay: "56.5M",
  qualityChecks: 103,
  qualityFails: 0,
  qualityWarns: 14,
  spatialJoinPct: 99.9993,
  gini: 0.5741,
  palma: 5.702,
  concentrationIndex: 0.1358,
  zeroStopLsoas: 4_245,
  tripleDeprivedLsoas: 612,
  eveningIsolatedLsoas: 5_189,
  eveningIsolatedPct: 15.4,
  sundayDesertLsoas: 6_745,
  sundayDesertPct: 20.0,
  rfR2: 0.472,
  sections: 55, // was marketed as 51
  dimensions: 8,
  filterCombos: 30,
} as const

export type MetricsCanon = typeof METRICS_CANON

/** Gini display: always four decimal places (0.5741). */
export function formatGini(value: number = METRICS_CANON.gini): string {
  return value.toFixed(4)
}

/** Palma display with × suffix (5.702×). */
export function formatPalma(value: number = METRICS_CANON.palma): string {
  return `${value.toFixed(3)}×`
}

/** Concentration index with sign (+0.1358). */
export function formatConcentrationIndex(
  value: number = METRICS_CANON.concentrationIndex,
): string {
  const sign = value >= 0 ? "+" : ""
  return `${sign}${value.toFixed(4)}`
}

/** One-line scale summary for README / marketing. */
export function scaleLine(): string {
  const m = METRICS_CANON
  return `${m.tripsDisplay} GTFS trips · ${m.routes.toLocaleString("en-GB")} routes · ${m.stops.toLocaleString("en-GB")} stops · ${m.lsoas.toLocaleString("en-GB")} LSOAs (${m.populationDisplay} population)`
}

/** Headline inequality stats for landing / auth branding. */
export function headlineInequalityStats(): ReadonlyArray<{
  label: string
  value: string
  sub: string
}> {
  const m = METRICS_CANON
  return [
    {
      label: "Gini coefficient",
      value: formatGini(m.gini),
      sub: "Bus service inequality",
    },
    {
      label: "Palma ratio",
      value: formatPalma(m.palma),
      sub: "Top 10% vs bottom 40%",
    },
    {
      label: "Evening isolated",
      value: `${m.eveningIsolatedPct.toFixed(1)}%`,
      sub: "of LSOAs",
    },
    {
      label: "Sunday deserts",
      value: `${m.sundayDesertPct.toFixed(1)}%`,
      sub: "of LSOAs",
    },
  ]
}

/** Scale metrics strip (trips / stops / routes / LSOAs). */
export function scaleStats(): ReadonlyArray<{
  label: string
  value: string
  sub: string
}> {
  const m = METRICS_CANON
  return [
    {
      label: "GTFS trips",
      value: m.tripsDisplay,
      sub: m.trips.toLocaleString("en-GB"),
    },
    {
      label: "Bus stops",
      value: m.stops.toLocaleString("en-GB"),
      sub: "active NaPTAN",
    },
    {
      label: "Routes",
      value: m.routes.toLocaleString("en-GB"),
      sub: "BODS unique",
    },
    {
      label: "LSOAs",
      value: m.lsoas.toLocaleString("en-GB"),
      sub: `${m.populationDisplay} population`,
    },
  ]
}

/** Auth page compact stats (3 tiles). */
export function authHeadlineStats(): ReadonlyArray<{
  label: string
  value: string
  note: string
}> {
  const m = METRICS_CANON
  return [
    {
      label: "GINI COEFF",
      value: formatGini(m.gini),
      note: "bus service",
    },
    {
      label: "PALMA RATIO",
      value: formatPalma(m.palma),
      note: "top 10% vs bottom 40%",
    },
    {
      label: "EVENING ISO",
      value: `${m.eveningIsolatedPct.toFixed(1)}%`,
      note: "of LSOAs",
    },
  ]
}

/**
 * Pack warehouse equity floats to GT display when they are clearly the
 * truncated national values (section_results may store 5.7 / 0.1344).
 * Only remaps known equity keys; other stats pass through.
 */
export function packEquityDisplayValue(
  key: string,
  value: number,
): string | null {
  const k = key.toLowerCase()
  const near = (a: number, b: number, tol: number) => Math.abs(a - b) <= tol

  if (k === "gini" || k.endsWith("_gini")) {
    if (near(value, METRICS_CANON.gini, 0.002)) return formatGini(METRICS_CANON.gini)
  }
  if (k === "palma" || k.includes("palma")) {
    if (near(value, METRICS_CANON.palma, 0.05)) return formatPalma(METRICS_CANON.palma)
  }
  if (k === "concentration_index" || k.includes("concentration")) {
    if (near(value, METRICS_CANON.concentrationIndex, 0.002)) {
      return formatConcentrationIndex(METRICS_CANON.concentrationIndex)
    }
  }
  return null
}

/** Ticker fallback rows (mirrors API ground-truth packing). */
export function tickerFallbackMetrics(): ReadonlyArray<{
  key: string
  label: string
  value: string
  sub: string
}> {
  const m = METRICS_CANON
  return [
    {
      key: "gini",
      label: "Gini Coefficient",
      value: formatGini(m.gini),
      sub: "bus service inequality",
    },
    {
      key: "palma",
      label: "Palma Ratio",
      value: formatPalma(m.palma),
      sub: "top 10% vs bottom 40%",
    },
    {
      key: "concentration_index",
      label: "Concentration Index",
      value: formatConcentrationIndex(m.concentrationIndex),
      sub: "pro-rich bias",
    },
    {
      key: "evening_isolated",
      label: "Evening Isolated",
      value: `${m.eveningIsolatedPct.toFixed(1)}%`,
      sub: `${m.eveningIsolatedLsoas.toLocaleString("en-GB")} LSOAs`,
    },
    {
      key: "sunday_deserts",
      label: "Sunday Deserts",
      value: `${m.sundayDesertPct.toFixed(1)}%`,
      sub: `${m.sundayDesertLsoas.toLocaleString("en-GB")} LSOAs`,
    },
    {
      key: "mean_sqi",
      label: "Mean SQI",
      value: "65.4",
      sub: "out of 100",
    },
  ]
}
