interface GaugeBand {
  label: string
  min: number
  max: number | null
  color_hint: string
}

interface GaugeMarker {
  label: string
  value: number
}

interface Props {
  chartData: Record<string, unknown>
}

const COLOR_MAP: Record<string, string> = {
  red: "bg-red-200 dark:bg-red-900/50",
  orange: "bg-orange-200 dark:bg-orange-900/50",
  yellow: "bg-yellow-200 dark:bg-yellow-900/50",
  green: "bg-green-200 dark:bg-green-900/50",
  blue: "bg-blue-200 dark:bg-blue-900/50",
}

/** Open-ended bands (max: null) are drawn out to this multiple of their min. */
const OPEN_BAND_EXTENT_FACTOR = 1.5

/** Resolve the numeric scale max, expanding open-ended bands and marker values. */
function resolveScaleMax(bands: GaugeBand[], markers: GaugeMarker[]): number {
  const bandMax = bands.map((b) => b.max ?? b.min * OPEN_BAND_EXTENT_FACTOR)
  const markerMax = markers.map((m) => m.value)
  return Math.max(...bandMax, ...markerMax, 1)
}

/** Convert a data value to a left-offset percentage along the gauge track. */
function toPercent(value: number, scaleMax: number): number {
  return Math.min(100, Math.max(0, (value / scaleMax) * 100))
}

/**
 * Renders a horizontal banded gauge: colored threshold zones, marker pins for
 * each value, and optional reference lines (e.g. BCR break-even at 1.0).
 *
 * Used for headline "is this good or bad" metrics (j2_bcr VfM bands,
 * bsa2_operator_concentration HHI bands) where the value's position relative
 * to standard thresholds is the policy question.
 */
export default function GaugeChart({ chartData }: Props) {
  const bands = (chartData.bands ?? []) as GaugeBand[]
  const markers = (chartData.markers ?? []) as GaugeMarker[]
  const referenceLines = (chartData.reference_lines ?? []) as number[]
  const title = chartData.title as string | undefined
  const unit = chartData.unit as string | undefined

  if (bands.length === 0 || markers.length === 0) {
    return <p className="text-muted-foreground text-sm">No data available</p>
  }

  const scaleMax = resolveScaleMax(bands, markers)

  return (
    <div role="img" aria-label={title ?? "Threshold gauge"}>
      {title && <p className="text-sm font-medium text-foreground mb-2">{title}</p>}
      <div className="relative h-6 w-full rounded overflow-hidden border border-border flex">
        {bands.map((band) => {
          const start = toPercent(band.min, scaleMax)
          const end = toPercent(band.max ?? scaleMax, scaleMax)
          return (
            <div
              key={band.label}
              className={`${COLOR_MAP[band.color_hint] ?? "bg-muted"} h-full`}
              style={{ width: `${end - start}%` }}
              title={`${band.label}: ${band.min}${band.max !== null ? `-${band.max}` : "+"}`}
            />
          )
        })}
        {referenceLines.map((ref) => (
          <div
            key={`ref-${ref}`}
            className="absolute top-0 h-full w-px bg-foreground/60"
            style={{ left: `${toPercent(ref, scaleMax)}%` }}
          />
        ))}
        {markers.map((marker) => (
          <div
            key={marker.label}
            className="absolute top-0 h-full w-0.5 bg-foreground"
            style={{ left: `${toPercent(marker.value, scaleMax)}%` }}
            title={`${marker.label}: ${marker.value} ${unit ?? ""}`}
          />
        ))}
      </div>
      <div className="flex justify-between text-xs text-muted-foreground mt-1">
        {bands.map((band) => (
          <span key={band.label}>{band.label}</span>
        ))}
      </div>
      <ul className="mt-3 space-y-1 text-sm">
        {markers.map((marker) => (
          <li key={marker.label} className="flex justify-between">
            <span className="text-foreground">{marker.label}</span>
            <span className="text-muted-foreground">
              {marker.value} {unit ?? ""}
            </span>
          </li>
        ))}
      </ul>
    </div>
  )
}
