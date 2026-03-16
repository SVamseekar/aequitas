import { useRef, useEffect } from "react"
import * as Plot from "@observablehq/plot"
import { CATEGORICAL } from "@/lib/colours"

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
  const ref = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (!ref.current) return
    const data = (chartData.data ?? []) as ScatterDatum[]
    const r = chartData.r as number | undefined
    const pValue = chartData.p_value as number | undefined
    const regression = chartData.regression_line as RegressionLine | undefined

    const marks: Plot.Markish[] = [
      Plot.dot(data, { x: "x", y: "y", fill: CATEGORICAL[0], opacity: 0.6, r: 3 }),
    ]

    if (regression && data.length > 0) {
      const xs = data.map((d) => d.x)
      const xMin = Math.min(...xs)
      const xMax = Math.max(...xs)
      const lineData = [
        { x: xMin, y: regression.slope * xMin + regression.intercept },
        { x: xMax, y: regression.slope * xMax + regression.intercept },
      ]
      marks.push(Plot.line(lineData, { x: "x", y: "y", stroke: "#e15759", strokeWidth: 2 }))
    }

    const subtitle = r !== undefined
      ? `r = ${r.toFixed(3)}${pValue !== undefined ? `, p = ${pValue.toFixed(4)}` : ""}`
      : ""

    const chart = Plot.plot({
      width: 700,
      height: 450,
      x: { label: (chartData.x_label as string | undefined) ?? "X" },
      y: { label: (chartData.y_label as string | undefined) ?? "Y" },
      subtitle,
      marks,
    })

    ref.current.replaceChildren(chart)
    return () => chart.remove()
  }, [chartData])

  return <div ref={ref} aria-label={(chartData.title as string | undefined) ?? "Scatter plot"} role="img" />
}
