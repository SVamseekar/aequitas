import { useRef, useEffect, useMemo } from "react"
import * as Plot from "@observablehq/plot"
import { CATEGORICAL } from "@/lib/colours"
import { useChartWidth, useViewportHeight } from "@/hooks/useChartWidth"

interface ScatterDatum {
  x: number
  y: number
  id: string
}

interface RegressionLine {
  slope: number
  intercept: number
}

interface Props {
  chartData: Record<string, unknown>
}

export default function ScatterRegressionChart({ chartData }: Props) {
  const containerRef = useRef<HTMLDivElement>(null)
  const ref = useRef<HTMLDivElement>(null)
  const width = useChartWidth(containerRef, 700)
  const viewportHeight=useViewportHeight()
  const data = useMemo(() => ((chartData.data ?? []) as ScatterDatum[]).filter(row => typeof row.x === 'number' && Number.isFinite(row.x) && typeof row.y === 'number' && Number.isFinite(row.y)), [chartData])

  useEffect(() => {
    if (!ref.current) return
    if (data.length === 0) { ref.current.replaceChildren(); return }
    const r = chartData.r as number | undefined
    const pValue = chartData.p_value as number | undefined
    const regression = chartData.regression_line as RegressionLine | undefined

    const xLabel = (chartData.x_label as string | undefined) ?? "X"
    const yLabel = (chartData.y_label as string | undefined) ?? "Y"

    const marks: Plot.Markish[] = [
      Plot.dot(data, {
        x: "x", y: "y", fill: typeof chartData.point_color==='string'?chartData.point_color:CATEGORICAL[0],
        opacity: typeof chartData.point_opacity==='number'?Math.max(.1,Math.min(1,chartData.point_opacity)):.6,
        r: typeof chartData.point_radius==='number'?Math.max(1,Math.min(5,chartData.point_radius)):3,
        tip: true,
        title: (d: ScatterDatum) =>
          `${d.id ? d.id + "\n" : ""}${xLabel}: ${Number(d.x).toFixed(3)}\n${yLabel}: ${Number(d.y).toFixed(3)}`,
      }),
      Plot.crosshairX(data, { x: "x", y: "y" }),
    ]

    if (regression && typeof regression.slope === 'number' && Number.isFinite(regression.slope) && typeof regression.intercept === 'number' && Number.isFinite(regression.intercept)) {
      const xs = data.map((d) => d.x)
      const xMin = Math.min(...xs)
      const xMax = Math.max(...xs)
      const lineData = [
        { x: xMin, y: regression.slope * xMin + regression.intercept },
        { x: xMax, y: regression.slope * xMax + regression.intercept },
      ]
      marks.push(Plot.line(lineData, { x: "x", y: "y", stroke: typeof chartData.line_color==='string'?chartData.line_color:'#e15759', strokeWidth: 2 }))
    }

    const subtitle = chartData.show_summary !== false && typeof r === 'number' && Number.isFinite(r)
      ? `r = ${r.toFixed(4)}${typeof pValue === 'number' && Number.isFinite(pValue) ? pValue < 0.0001 ? ', p < 0.0001' : `, p = ${pValue.toFixed(4)}` : ''}`
      : ""

    const chart = Plot.plot({
      width,
      height: Math.round(Math.min(440, Math.max(220, typeof chartData.height==='number'&&Number.isFinite(chartData.height)?chartData.height:width * 0.7),Math.max(220,viewportHeight-250))),
      marginLeft: 70,
      marginRight: 20,
      x: { label: xLabel,labelAnchor:'center',labelArrow:false,grid:true,line:true },
      y: { label: yLabel,labelAnchor:'center',labelArrow:false,grid:true,line:true,labelOffset:48 },
      subtitle,
      marks,
    })

    ref.current.replaceChildren(chart)
    return () => chart.remove()
  }, [chartData, data, width,viewportHeight])

  return (
    <div ref={containerRef}>
      <div ref={ref} aria-label={(chartData.title as string | undefined) ?? "Scatter plot"} role="img" />
      {data.length === 0 ? <p className='text-sm text-muted-foreground py-3'>No paired observations available for this plot.</p> : null}
    </div>
  )
}
