import { useRef, useEffect } from "react"
import * as Plot from "@observablehq/plot"
import { CATEGORICAL } from "@/lib/colours"

interface FeatureDatum {
  name: string
  importance: number
}

interface Props {
  chartData: Record<string, unknown>
}

export default function ShapBarChart({ chartData }: Props) {
  const ref = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (!ref.current) return
    const features = (chartData.features ?? []) as FeatureDatum[]
    const r2 = chartData.model_r2 as number | undefined
    const topFeature = features[0] as FeatureDatum | undefined

    const chart = Plot.plot({
      marginLeft: 160,
      width: 700,
      height: Math.max(300, features.length * 28),
      x: { label: "SHAP Importance" },
      y: { label: null },
      subtitle: r2 !== undefined ? `Model R² = ${r2.toFixed(3)}` : undefined,
      marks: [
        Plot.barX(features, {
          y: "name",
          x: "importance",
          fill: (d: FeatureDatum) => (d.name === topFeature?.name ? CATEGORICAL[0] : CATEGORICAL[1]),
          sort: { y: "x", reverse: true },
          tip: true,
          title: (d: FeatureDatum) => `${d.name}\nImportance: ${d.importance.toFixed(4)}`,
        }),
        Plot.text(features, {
          y: "name",
          x: "importance",
          text: (d: FeatureDatum) => d.importance.toFixed(3),
          dx: 4,
          textAnchor: "start",
          fontSize: 11,
        }),
      ],
    })

    ref.current.replaceChildren(chart)
    return () => chart.remove()
  }, [chartData])

  const features = (chartData.features ?? []) as FeatureDatum[]
  const topFeature = features[0] as FeatureDatum | undefined

  return (
    <div>
      {topFeature && (
        <p className="text-sm font-medium text-muted-foreground mb-1">
          Top driver: <span className="text-foreground">{topFeature.name}</span> — {topFeature.importance.toFixed(3)}
        </p>
      )}
      <div ref={ref} aria-label={(chartData.title as string | undefined) ?? "SHAP importance"} role="img" />
    </div>
  )
}
