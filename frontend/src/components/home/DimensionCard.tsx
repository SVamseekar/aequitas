import { Link } from "react-router"
import type { DimensionOverview } from "@/api/types"
import { Severity } from "@/components/shared/Severity"

interface Props {
  dim: DimensionOverview
}

export function DimensionCard({ dim }: Props) {
  return (
    <Link
      to={dim.route}
      className="block bg-white rounded-lg border border-gray-200 p-5 hover:shadow-md transition-shadow"
    >
      <h3 className="text-sm font-semibold text-gray-900 mb-2">{dim.name}</h3>
      <Severity severity={dim.headline_stat.severity}>
        {dim.headline_stat.value.toLocaleString(undefined, { maximumFractionDigits: 3 })}
      </Severity>
      <p className="text-xs text-gray-500 mt-1">{dim.headline_stat.label}</p>
      {dim.summary && <p className="text-sm text-gray-600 mt-2">{dim.summary}</p>}
    </Link>
  )
}
