import { useRef, useEffect } from "react"
import * as Plot from "@observablehq/plot"
import { CATEGORICAL } from "@/lib/colours"
import ClusterSizeBar from "./ClusterSizeBar"

interface ClusterPoint {
  x: number
  y: number
  cluster: string | number
  id?: string
}

interface Props {
  chartData: Record<string, unknown>
}

export default function ScatterClustersChart({ chartData }: Props) {
  const ref = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (!ref.current) return
    const data = (chartData.data ?? []) as ClusterPoint[]
    const clusters = (chartData.clusters ?? []) as { label: string; n: number }[]

    const subtitle = clusters.length > 0
      ? clusters.map((c) => `${c.label}: ${c.n}`).join(" | ")
      : undefined

    const chart = Plot.plot({
      width: 700,
      height: 450,
      x: { label: (chartData.x_label as string | undefined) ?? "X" },
      y: { label: (chartData.y_label as string | undefined) ?? "Y" },
      subtitle,
      color: {
        legend: true,
        range: [...CATEGORICAL],
        label: "Cluster",
      },
      marks: [
        Plot.dot(data, {
          x: "x",
          y: "y",
          fill: (d: ClusterPoint) => String(d.cluster),
          opacity: 0.45,
          r: 2.5,
          tip: true,
          title: (d: ClusterPoint) => {
            const clusterLabel = clusters.find((c) => String(c.label) === String(d.cluster))?.label ?? d.cluster
            const xLbl = (chartData.x_label as string | undefined) ?? "X"
            const yLbl = (chartData.y_label as string | undefined) ?? "Y"
            return `${d.id ? d.id + "\n" : ""}Cluster: ${clusterLabel}\n${xLbl}: ${Number(d.x).toFixed(3)}\n${yLbl}: ${Number(d.y).toFixed(3)}`
          },
        }),
        Plot.crosshairX(data, { x: "x", y: "y" }),
      ],
    })

    ref.current.replaceChildren(chart)
    return () => chart.remove()
  }, [chartData])

  const clusterSizes = (chartData.cluster_sizes ?? []) as { label: string; n: number }[]

  return (
    <div className="flex flex-col gap-4 md:flex-row md:items-start">
      <div ref={ref} aria-label={(chartData.title as string | undefined) ?? "Cluster scatter"} role="img" />
      {clusterSizes.length > 0 && (
        <div>
          <p className="mb-1 text-sm font-medium text-muted-foreground">Cluster sizes</p>
          <ClusterSizeBar clusterSizes={clusterSizes} />
        </div>
      )}
    </div>
  )
}
