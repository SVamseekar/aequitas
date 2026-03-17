import { useRef, useEffect } from "react"
import * as Plot from "@observablehq/plot"
import { CATEGORICAL } from "@/lib/colours"

interface BoxDatum {
  group: string
  min: number
  q1: number
  median: number
  q3: number
  max: number
}

interface Props {
  chartData: Record<string, unknown>
}

export default function BoxViolinChart({ chartData }: Props) {
  const ref = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (!ref.current) return
    const data = (chartData.data ?? []) as BoxDatum[]

    // Build flat arrays for link/rect marks — keep orig BoxDatum reference for tooltips
    const whiskers = data.map((d) => ({ ...d, y: d.group, x1: d.min, x2: d.max }))
    const boxes = data.map((d) => ({ y: d.group, x1: d.q1, x2: d.q3 }))
    const medians = data.map((d) => ({ y: d.group, x: d.median }))

    const chart = Plot.plot({
      marginLeft: 140,
      width: 700,
      height: Math.max(250, data.length * 50),
      x: { label: (chartData.x_label as string | undefined) ?? "Value" },
      y: { label: null },
      marks: [
        // Whisker lines (min to max) — carries tooltip for full quartile stats
        Plot.link(whiskers, {
          x1: "x1", x2: "x2", y1: "y", y2: "y",
          stroke: "#666", strokeWidth: 1,
          tip: true,
          title: (d: BoxDatum & { y: string; x1: number; x2: number }) =>
            `${d.group}\nMin: ${d.min.toFixed(2)}\nQ1: ${d.q1.toFixed(2)}\nMedian: ${d.median.toFixed(2)}\nQ3: ${d.q3.toFixed(2)}\nMax: ${d.max.toFixed(2)}`,
        }),
        // Boxes (Q1 to Q3)
        Plot.rectX(boxes, {
          x1: "x1", x2: "x2", y: "y",
          fill: CATEGORICAL[0], fillOpacity: 0.7, rx: 3,
        }),
        // Median markers
        Plot.dot(medians, {
          x: "x", y: "y",
          fill: "#333", r: 4,
        }),
        // Median labels
        Plot.text(data, {
          x: "median", y: "group",
          text: (d: BoxDatum) => d.median.toFixed(1),
          dy: -14, fontSize: 10, fill: "#333",
        }),
      ],
    })

    ref.current.replaceChildren(chart)
    return () => chart.remove()
  }, [chartData])

  return <div ref={ref} aria-label={(chartData.title as string | undefined) ?? "Box plot"} role="img" />
}
