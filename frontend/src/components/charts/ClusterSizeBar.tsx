import { useRef, useEffect } from "react"
import * as Plot from "@observablehq/plot"
import { CATEGORICAL } from "@/lib/colours"

interface ClusterSize {
  label: string
  n: number
}

interface Props {
  clusterSizes: ClusterSize[]
}

/** Small horizontal bar chart showing the number of routes/items per cluster. */
export default function ClusterSizeBar({ clusterSizes }: Props) {
  const ref = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (!ref.current) return
    if (clusterSizes.length === 0) {
      ref.current.replaceChildren()
      return
    }

    const chart = Plot.plot({
      marginLeft: 140,
      width: 320,
      height: Math.max(80, clusterSizes.length * 32),
      x: { label: "Routes" },
      y: { label: null },
      marks: [
        Plot.barX(clusterSizes, {
          y: "label", x: "n", fill: CATEGORICAL[0],
          sort: { y: "x", reverse: true },
          tip: true,
          title: (d: ClusterSize) => `${d.label}: ${d.n}`,
        }),
        Plot.text(clusterSizes, {
          y: "label", x: "n",
          text: (d: ClusterSize) => String(d.n),
          dx: 4, textAnchor: "start", fontSize: 11,
        }),
      ],
    })

    ref.current.replaceChildren(chart)
    return () => chart.remove()
  }, [clusterSizes])

  return <div ref={ref} aria-label="Cluster sizes" role="img" />
}
