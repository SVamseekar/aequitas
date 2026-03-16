import { lazy, Suspense } from "react"
import { DataTable } from "./DataTable"

const HorizontalBarChart = lazy(() => import("./HorizontalBarChart"))
const ScatterRegressionChart = lazy(() => import("./ScatterRegressionChart"))
const LorenzCurveChart = lazy(() => import("./LorenzCurveChart"))
const ShapBarChart = lazy(() => import("./ShapBarChart"))
const ChoroplethMap = lazy(() => import("./ChoroplethMap"))

interface Props {
  chartData: Record<string, unknown>
}

export function ChartRenderer({ chartData }: Props) {
  const type = chartData.type as string | undefined
  const fallback = <div className="h-64 bg-gray-100 animate-pulse rounded" />

  switch (type) {
    case "horizontal_bar":
    case "grouped_bar":
    case "stacked_bar":
      return <Suspense fallback={fallback}><HorizontalBarChart chartData={chartData} /></Suspense>
    case "scatter_regression":
      return <Suspense fallback={fallback}><ScatterRegressionChart chartData={chartData} /></Suspense>
    case "lorenz_curve":
      return <Suspense fallback={fallback}><LorenzCurveChart chartData={chartData} /></Suspense>
    case "shap_bar":
      return <Suspense fallback={fallback}><ShapBarChart chartData={chartData} /></Suspense>
    case "choropleth":
      return <Suspense fallback={fallback}><ChoroplethMap chartData={chartData} /></Suspense>
    default:
      return <DataTable chartData={chartData} />
  }
}
