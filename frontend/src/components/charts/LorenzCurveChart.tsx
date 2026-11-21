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

    const equality: CurvePoint[] = [
      { cum_pop: 0, cum_service: 0 },
      { cum_pop: 1, cum_service: 1 },
    ]


    const chart = Plot.plot({
      width,
      height: Math.round(Math.min(440, Math.max(280, width * 0.68))),
      marginLeft: 54, marginBottom: 42,
      x: { labelAnchor:'center',labelArrow:false,grid:true,ticks:6,label: "Cumulative share of population (%)", domain: [0, 1], tickFormat: d => `${Number(d) * 100}` },
      y: { labelAnchor:'center',labelArrow:false,labelOffset:40,ticks:6,label: "Cumulative share of service (%)", domain: [0, 1], tickFormat: d => `${Number(d) * 100}`, grid: true },
      marks: [
        Plot.line(equality, { x: "cum_pop", y: "cum_service", stroke: "#666d78", strokeDasharray: "4,3", strokeWidth: 1 }),
        Plot.line(points, {
          x: "cum_pop", y: "cum_service", stroke: "#d34321", strokeWidth: 2,
          tip: true,
          title: (d: CurvePoint) =>
            `Population: ${(d.cum_pop * 100).toFixed(1)}%\nService: ${(d.cum_service * 100).toFixed(1)}%`,
        }),
        Plot.areaY(points, { x: "cum_pop", y1: 0, y2: "cum_service", fill: "#b84e1f", fillOpacity: 0.08 }),
      ],
    })

    ref.current.replaceChildren(chart)
    return () => chart.remove()
  }, [chartData, width])

  return (
    <div ref={containerRef}>
      <div ref={ref} aria-label={(chartData.title as string | undefined) ?? "Lorenz curve"} role="img" />
      <div className="lorenz-legend"><span><i />Line of equality (equal distribution)</span><span><i />Selected filter (bus service)</span></div></div>
  )
}
