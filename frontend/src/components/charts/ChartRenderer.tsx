import { lazy, Suspense, Component, type ReactNode } from "react"
import { DataTable } from "./DataTable"

const HorizontalBarChart = lazy(() => import("./HorizontalBarChart"))
const ScatterRegressionChart = lazy(() => import("./ScatterRegressionChart"))
const LorenzCurveChart = lazy(() => import("./LorenzCurveChart"))
const ShapBarChart = lazy(() => import("./ShapBarChart"))
const ChoroplethMap = lazy(() => import("./ChoroplethMap"))
const HeatmapChart = lazy(() => import("./HeatmapChart"))
const BoxViolinChart = lazy(() => import("./BoxViolinChart"))
const ScatterClustersChart = lazy(() => import("./ScatterClustersChart"))

class ChartErrorBoundary extends Component<{ children: ReactNode }, { hasError: boolean }> {
  state = { hasError: false }
  static getDerivedStateFromError() { return { hasError: true } }
  render() {
    if (this.state.hasError) {
      return <p className="text-gray-400 text-sm py-4">Chart could not be rendered</p>
    }
    return this.props.children
  }
}

interface Props {
  chartData: Record<string, unknown>
}

export function ChartRenderer({ chartData }: Props) {
  if (!chartData || Object.keys(chartData).length === 0) {
    return null
  }
  const type = chartData.type as string | undefined
  const fallback = <div className="h-64 bg-gray-100 animate-pulse rounded" />

  let chart: ReactNode
  switch (type) {
    case "horizontal_bar":
    case "grouped_bar":
    case "stacked_bar":
      chart = <HorizontalBarChart chartData={chartData} />
      break
    case "scatter_regression":
      chart = <ScatterRegressionChart chartData={chartData} />
      break
    case "lorenz_curve":
      chart = <LorenzCurveChart chartData={chartData} />
      break
    case "shap_bar":
      chart = <ShapBarChart chartData={chartData} />
      break
    case "choropleth":
      chart = <ChoroplethMap chartData={chartData} />
      break
    case "heatmap":
      chart = <HeatmapChart chartData={chartData} />
      break
    case "box_violin":
      chart = <BoxViolinChart chartData={chartData} />
      break
    case "scatter_clusters":
      chart = <ScatterClustersChart chartData={chartData} />
      break
    default:
      return <DataTable chartData={chartData} />
  }

  return (
    <ChartErrorBoundary>
      <Suspense fallback={fallback}>{chart}</Suspense>
    </ChartErrorBoundary>
  )
}
