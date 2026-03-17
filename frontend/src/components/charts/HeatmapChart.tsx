import { useRef, useEffect } from "react"
import * as Plot from "@observablehq/plot"

interface Props {
  chartData: Record<string, unknown>
}

export default function HeatmapChart({ chartData }: Props) {
  const ref = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (!ref.current) return
    const xLabels = (chartData.x_labels ?? []) as string[]
    const yLabels = (chartData.y_labels ?? []) as string[]
    const values = (chartData.values ?? []) as number[][]

    // Flatten to cell data
    const cells: { x: string; y: string; value: number }[] = []
    for (let yi = 0; yi < yLabels.length; yi++) {
      for (let xi = 0; xi < xLabels.length; xi++) {
        cells.push({
          x: xLabels[xi],
          y: yLabels[yi],
          value: values[yi]?.[xi] ?? 0,
        })
      }
    }

    const chart = Plot.plot({
      marginLeft: 120,
      marginBottom: 60,
      width: 700,
      height: Math.max(300, yLabels.length * 40 + 80),
      x: { label: null, tickRotate: -30 },
      y: { label: null },
      color: { scheme: "YlOrRd", legend: true, label: "Value" },
      marks: [
        Plot.cell(cells, { x: "x", y: "y", fill: "value" }),
        Plot.text(cells, {
          x: "x",
          y: "y",
          text: (d: { value: number }) => d.value.toFixed(1),
          fontSize: 11,
          fill: (d: { value: number }) => (d.value > 50 ? "white" : "black"),
        }),
      ],
    })

    ref.current.replaceChildren(chart)
    return () => chart.remove()
  }, [chartData])

  return <div ref={ref} aria-label={(chartData.title as string | undefined) ?? "Heatmap"} role="img" />
}
