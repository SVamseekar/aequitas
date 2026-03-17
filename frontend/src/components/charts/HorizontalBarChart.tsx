import { useRef, useEffect } from "react"
import * as Plot from "@observablehq/plot"
import { CATEGORICAL } from "@/lib/colours"

interface BarDatum {
  label: string
  value: number
}

interface GroupedDatum {
  label: string
  group: string
  value: number
}

interface Props {
  chartData: Record<string, unknown>
}

/** Transform categories/series format to flat GroupedDatum[] */
function normalizeGroupedData(chartData: Record<string, unknown>): GroupedDatum[] {
  // Already flat format
  if (Array.isArray(chartData.data) && chartData.data.length > 0 && "group" in (chartData.data[0] as Record<string, unknown>)) {
    return chartData.data as GroupedDatum[]
  }
  // categories/series format → flatten
  const categories = chartData.categories as string[] | undefined
  const series = chartData.series as { name: string; values: number[] }[] | undefined
  if (categories && series) {
    const flat: GroupedDatum[] = []
    for (const s of series) {
      for (let i = 0; i < categories.length; i++) {
        flat.push({ label: categories[i], group: s.name, value: s.values[i] ?? 0 })
      }
    }
    return flat
  }
  return (chartData.data ?? []) as GroupedDatum[]
}

export default function HorizontalBarChart({ chartData }: Props) {
  const ref = useRef<HTMLDivElement>(null)
  const variant = (chartData.type as string | undefined) ?? "horizontal_bar"

  useEffect(() => {
    if (!ref.current) return
    const xLabel = (chartData.x_label as string | undefined) ?? "Value"
    const nationalAvg = chartData.national_avg as number | undefined

    const marks: Plot.Markish[] = []

    if (variant === "grouped_bar") {
      const data = normalizeGroupedData(chartData)
      if (data.length === 0) { ref.current.replaceChildren(); return }
      marks.push(
        Plot.barX(data, Plot.groupY({ x: "sum" }, {
          y: "label", x: "value", fill: "group",
          sort: { y: "x", reverse: true },
        })),
      )
    } else if (variant === "stacked_bar") {
      const data = normalizeGroupedData(chartData)
      if (data.length === 0) { ref.current.replaceChildren(); return }
      marks.push(
        Plot.barX(data, Plot.stackX({
          y: "label", x: "value", fill: "group",
          sort: { y: "x", reverse: true },
        })),
      )
    } else {
      const data = (chartData.data ?? []) as BarDatum[]
      if (data.length === 0) { ref.current.replaceChildren(); return }
      marks.push(
        Plot.barX(data, {
          y: "label", x: "value", fill: CATEGORICAL[0],
          sort: { y: "x", reverse: true },
        }),
        Plot.text(data, {
          y: "label", x: "value",
          text: (d: BarDatum) => d.value.toLocaleString(undefined, { maximumFractionDigits: 1 }),
          dx: 4, textAnchor: "start", fontSize: 11,
        }),
      )
    }

    if (nationalAvg !== undefined) {
      marks.push(
        Plot.ruleX([nationalAvg], { stroke: "#e15759", strokeWidth: 1.5, strokeDasharray: "4,3" }),
        Plot.text([nationalAvg], {
          x: (d: number) => d,
          text: (d: number) => `Avg: ${d.toFixed(1)}`,
          dy: -8, fill: "#e15759", fontSize: 10,
        })
      )
    }

    const allData = (chartData.data ?? []) as unknown[]
    const chart = Plot.plot({
      marginLeft: 140,
      marginRight: 60,
      width: 700,
      height: Math.max(300, allData.length * 28),
      x: { label: xLabel },
      y: { label: null },
      color: variant !== "horizontal_bar" ? { legend: true, range: [...CATEGORICAL] } : undefined,
      marks,
    })

    ref.current.replaceChildren(chart)
    return () => chart.remove()
  }, [chartData, variant])

  return (
    <div>
      <div ref={ref} aria-label={(chartData.title as string | undefined) ?? "Bar chart"} role="img" />
    </div>
  )
}
