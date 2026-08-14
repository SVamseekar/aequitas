import { useRef, useEffect } from "react"
import * as Plot from "@observablehq/plot"
import { useChartWidth } from "@/hooks/useChartWidth"

interface CurvePoint {
  cum_pop: number
  cum_service: number
}

interface Props {
  chartData: Record<string, unknown>
}

export default function LorenzCurveChart({ chartData }: Props) {
  const containerRef = useRef<HTMLDivElement>(null)
  const ref = useRef<HTMLDivElement>(null)
  const width = useChartWidth(containerRef, 600)

  useEffect(() => {
    if (!ref.current) return
    const points = (chartData.curve_points ?? chartData.data ?? []) as CurvePoint[]
    if (points.length < 2) {
      ref.current.replaceChildren()
      const p = document.createElement("p")
      p.className = "text-sm text-foreground py-4"
      p.textContent = "Lorenz curve needs population-weighted trips for this filter."
      ref.current.appendChild(p)
      return
    }
    const gini = chartData.gini as number | undefined
    const refGini = chartData.reference_gini as number | undefined
    const refLabel = chartData.reference_label as string | undefined

    const equality: CurvePoint[] = [
      { cum_pop: 0, cum_service: 0 },
      { cum_pop: 1, cum_service: 1 },
    ]

    const subtitle = gini !== undefined
      ? `Gini = ${gini.toFixed(3)}${refGini !== undefined ? ` (${refLabel ?? "reference"}: ${refGini.toFixed(3)})` : ""}`
      : ""

    const chart = Plot.plot({
      width,
      height: 500,
      x: { label: "Cumulative population share", domain: [0, 1] },
      y: { label: "Cumulative service share", domain: [0, 1] },
      subtitle,
      marks: [
        Plot.line(equality, { x: "cum_pop", y: "cum_service", stroke: "#999", strokeDasharray: "4,3", strokeWidth: 1 }),
        Plot.line(points, {
          x: "cum_pop", y: "cum_service", stroke: "#4e79a7", strokeWidth: 2,
          tip: true,
          title: (d: CurvePoint) =>
            `Population: ${(d.cum_pop * 100).toFixed(1)}%\nService: ${(d.cum_service * 100).toFixed(1)}%`,
        }),
        Plot.areaY(points, { x: "cum_pop", y1: "cum_service", y2: "cum_pop", fill: "#4e79a7", fillOpacity: 0.1 }),
      ],
    })

    ref.current.replaceChildren(chart)
    return () => chart.remove()
  }, [chartData, width])

  return (
    <div ref={containerRef}>
      <div ref={ref} aria-label={(chartData.title as string | undefined) ?? "Lorenz curve"} role="img" />
    </div>
  )
}
