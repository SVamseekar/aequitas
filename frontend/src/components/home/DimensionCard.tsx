import { Link } from "react-router"
import {
  Scale, MapPin, Bus, Network, BarChart3, PoundSterling, FileText, Sliders,
  type LucideIcon,
} from "lucide-react"
import type { DimensionOverview } from "@/api/types"
import { SEVERITY } from "@/lib/colours"

const DIMENSION_ICONS: Record<string, LucideIcon> = {
  equity: Scale,
  accessibility: MapPin,
  service_quality: Bus,
  route_network: Network,
  correlations: BarChart3,
  economic: PoundSterling,
  bus_services_act: FileText,
  scenarios: Sliders,
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
  const Icon = DIMENSION_ICONS[dim.id] ?? Scale
  const severityColor = (dim.headline_stat.severity in SEVERITY
    ? SEVERITY[dim.headline_stat.severity as keyof typeof SEVERITY]
    : SEVERITY.low)

  return (
    <Link
      to={dim.route.slice(1)}
      className="group block text-left p-5 rounded-lg border border-border bg-card/40 hover:border-indigo-400/30 hover:bg-card/60 transition-colors duration-300"
    >
      <h3 className="flex items-center gap-2 text-sm font-semibold text-foreground group-hover:text-indigo-400 transition-colors">
        <Icon className="w-4 h-4 text-indigo-400 shrink-0" />
        {dim.name}
      </h3>
      <p className="text-2xl font-bold font-mono mt-1" style={{ color: severityColor }}>
        {formatHeadline(dim)}
      </p>
      <p className="text-xs text-muted-foreground mt-0.5">{dim.headline_stat.label}</p>
    </Link>
  )
}
