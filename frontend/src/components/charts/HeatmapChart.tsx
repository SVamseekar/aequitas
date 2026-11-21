import { useRef, useEffect, useMemo } from "react"
import * as Plot from "@observablehq/plot"
import { useChartWidth } from "@/hooks/useChartWidth"

interface Props {
  chartData: Record<string, unknown>
}

export default function HeatmapChart({ chartData }: Props) {
  const containerRef = useRef<HTMLDivElement>(null)
  const ref = useRef<HTMLDivElement>(null)
  const width = useChartWidth(containerRef, 700)
  const cells = useMemo(() => {
    const xLabels = (chartData.x_labels ?? []) as string[]
    const yLabels = (chartData.y_labels ?? []) as string[]
    const values = (chartData.values ?? chartData.z ?? []) as unknown[][]
    return yLabels.flatMap((y, yi) => xLabels.flatMap((x, xi) => {
      const value = values[yi]?.[xi]
      return typeof value === 'number' && Number.isFinite(value) ? [{ x, y, value }] : []
    }))
  }, [chartData])

  useEffect(() => {
    if (!ref.current) return
    if (cells.length === 0) { ref.current.replaceChildren(); return }
    const xLabels = (chartData.x_labels ?? []) as string[]
    const yLabels = (chartData.y_labels ?? []) as string[]
    const coverage = chartData.measure === 'population_400m_pct'
    const valueLabel = coverage ? 'People within 400 m (%)' : 'Value'

    const chart = Plot.plot({
      marginLeft: Math.min(120, Math.max(55, width * 0.2)),
      marginTop: coverage ? 6 : undefined,
      marginBottom: coverage ? 30 : 60,
      width,
      height: typeof chartData.height === 'number' && Number.isFinite(chartData.height) ? Math.max(100, Math.min(1000, chartData.height)) : Math.max(300, yLabels.length * 40 + 80),
      x: { label: null, tickRotate: coverage && xLabels.length <= 3 ? 0 : -30, domain: xLabels },
      y: { label: null, domain: yLabels },
      color: { type: coverage ? 'linear' : undefined, scheme: coverage ? 'RdYlGn' : 'YlOrRd', domain: coverage ? [0, 100] : undefined, legend: true, label: valueLabel },
      marks: [
        Plot.cell(cells, {
          x: "x", y: "y", fill: "value",
          tip: true,
          title: (d: { x: string; y: string; value: number }) =>
            `${d.x} × ${d.y}\n${valueLabel}: ${d.value.toFixed(2)}${coverage ? '%' : ''}`,
        }),
        Plot.text(cells, {
          x: "x",
          y: "y",
          text: (d: { value: number }) => d.value.toFixed(1),
          fontSize: 11,
          fill: (d: { value: number }) => coverage ? d.value < 20 || d.value > 80 ? 'white' : 'black' : d.value > 50 ? 'white' : 'black',
        }),
      ],
    })

    ref.current.replaceChildren(chart)
    return () => chart.remove()
  }, [chartData, cells, width])

  return (
    <div ref={containerRef}>
      <div ref={ref} aria-label={(chartData.title as string | undefined) ?? "Heatmap"} role="img" />
      {cells.length === 0 ? <p className='text-sm text-muted-foreground py-3'>No observations available for this heatmap.</p> : null}
    </div>
  )
}
