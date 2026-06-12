interface KpiTile {
  label: string
  value: number
  unit: string
}

interface Props {
  chartData: Record<string, unknown>
}

/** Format a tile value for display: large counts get thousands separators. */
function formatValue(value: number): string {
  if (Number.isInteger(value)) {
    return value.toLocaleString("en-GB")
  }
  return value.toLocaleString("en-GB", { maximumFractionDigits: 2 })
}

/**
 * Renders a row of independent KPI tiles, each with its own number and unit.
 *
 * Used for single-scenario policy summaries (ps1-ps4, g5) where population,
 * cost, and CO2 figures have incompatible units and must not share an axis.
 */
export default function KpiTiles({ chartData }: Props) {
  const tiles = (chartData.tiles ?? []) as KpiTile[]
  const title = chartData.title as string | undefined

  if (tiles.length === 0) {
    return <p className="text-muted-foreground text-sm">No data available</p>
  }

  return (
    <div role="img" aria-label={title ?? "Key figures"}>
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        {tiles.map((tile) => (
          <div
            key={tile.label}
            className="rounded-lg border border-border bg-muted/30 p-4 text-center"
          >
            <p className="text-sm text-muted-foreground">{tile.label}</p>
            <p className="text-2xl font-semibold text-foreground mt-1">
              {formatValue(tile.value)}
            </p>
            <p className="text-xs text-muted-foreground mt-1">{tile.unit}</p>
          </div>
        ))}
      </div>
    </div>
  )
}
