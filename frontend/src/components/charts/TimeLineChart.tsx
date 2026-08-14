import { useEffect, useRef } from "react"
import * as Plot from "@observablehq/plot"
import { useChartWidth } from "@/hooks/useChartWidth"
import type { TimePoint } from "@/api/types"

export default function TimeLineChart({
  points,
  metricLabel,
  areaNoun,
}: {
  points: TimePoint[]
  metricLabel: string
  areaNoun: string
}) {
  const containerRef = useRef<HTMLDivElement>(null)
  const ref = useRef<HTMLDivElement>(null)
  const width = useChartWidth(containerRef, 640)

  useEffect(() => {
    if (!ref.current) return
    const rows = points
      .filter((p) => p.as_of)
      .map((p) => ({
        date: p.as_of,
        value: p.value,
        n: p.n_areas,
      }))
    ref.current.replaceChildren()
    if (rows.length === 0) {
      const p = document.createElement("p")
      p.className = "text-sm text-muted-foreground py-4"
      p.textContent = "No dated packs registered yet."
      ref.current.appendChild(p)
      return
    }
    const chart = Plot.plot({
      width,
      height: 320,
      x: { label: "Network date", type: "band" },
      y: {
        label: metricLabel,
        grid: true,
        nice: true,
        domain: /score/i.test(metricLabel) ? [0, 100] : undefined,
      },
      marks: [
        Plot.line(rows, {
          x: "date",
          y: "value",
          stroke: "#4e79a7",
          strokeWidth: 2,
          tip: true,
          title: (d: { date: string; value: number | null; n: number | null }) =>
            `${d.date}\n${metricLabel}: ${d.value ?? "—"}\n${d.n ?? "—"} ${areaNoun}`,
        }),
        Plot.dot(rows, {
          x: "date",
          y: "value",
          fill: "#4e79a7",
          r: 5,
          tip: true,
          title: (d: { date: string; value: number | null; n: number | null }) =>
            `${d.date}\n${metricLabel}: ${d.value ?? "—"}\n${d.n ?? "—"} ${areaNoun}`,
        }),
      ],
    })
    ref.current.appendChild(chart)
    return () => chart.remove()
  }, [points, metricLabel, areaNoun, width])

  return (
    <div ref={containerRef} className="app-glass rounded-2xl p-3 overflow-x-auto">
      <div ref={ref} data-testid="time-chart" />
    </div>
  )
}
