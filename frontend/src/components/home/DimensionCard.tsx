import { Link } from "react-router"
import type { DimensionOverview } from "@/api/types"
import { SEVERITY } from "@/lib/colours"

const DIMENSION_ICONS: Record<string, string> = {
  equity: "F",
  accessibility: "A",
  service_quality: "B",
  route_network: "C",
  correlations: "D",
  economic: "J",
  bus_services_act: "BSA",
  scenarios: "PS",
}

function formatHeadline(dim: DimensionOverview): string {
  const v = dim.headline_stat.value
  if (v === 0) return "—"
  if (v >= 10000) return v.toLocaleString(undefined, { maximumFractionDigits: 0 })
  if (dim.headline_stat.label.includes("%")) return `${v.toFixed(1)}%`
  if (v < 10) return v.toFixed(v < 1 ? 3 : 1)
  return v.toLocaleString(undefined, { maximumFractionDigits: 1 })
}

interface Props {
  dim: DimensionOverview
}

export function DimensionCard({ dim }: Props) {
  const icon = DIMENSION_ICONS[dim.id] ?? dim.id[0].toUpperCase()
  const severityColor = (dim.headline_stat.severity in SEVERITY
    ? SEVERITY[dim.headline_stat.severity as keyof typeof SEVERITY]
    : SEVERITY.low)

  return (
    <Link
      to={dim.route.slice(1)}
      className="group block bg-card rounded border border-border p-5 hover:border-indigo-500/40 hover:bg-card/80 transition-all"
    >
      <div className="flex items-start gap-3">
        <span className="inline-flex items-center justify-center w-8 h-8 rounded bg-indigo-500/10 text-indigo-400 text-xs font-bold shrink-0 font-mono">
          {icon}
        </span>
        <div className="min-w-0">
          <h3 className="text-sm font-semibold text-foreground group-hover:text-indigo-400 transition-colors">
            {dim.name}
          </h3>
          <p className="text-2xl font-bold font-mono mt-1" style={{ color: severityColor }}>
            {formatHeadline(dim)}
          </p>
          <p className="text-xs text-muted-foreground mt-0.5">{dim.headline_stat.label}</p>
        </div>
      </div>
    </Link>
  )
}
