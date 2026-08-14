import { Link, useSearchParams } from "react-router"
import { useFilters } from "@/api/hooks"
import { appPath, dimensionSlugFromApiRoute, withSearch } from "@/lib/appRoutes"
import {
  Scale,
  MapPin,
  Bus,
  Network,
  BarChart3,
  Euro,
  PoundSterling,
  FileText,
  Sliders,
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
  if (v == null || Number.isNaN(v)) return "—"
  if (v >= 10000) return v.toLocaleString(undefined, { maximumFractionDigits: 0 })
  if (dim.headline_stat.label.includes("%")) return `${v.toFixed(1)}%`
  if (v < 10) return v.toFixed(v < 1 ? 3 : 1)
  return v.toLocaleString(undefined, { maximumFractionDigits: 1 })
}

interface Props {
  dim: DimensionOverview
}

export function DimensionCard({ dim }: Props) {
  const { country } = useFilters()
  const [params] = useSearchParams()
  const Icon =
    dim.id === "economic" && (country === "ireland" || country === "netherlands")
      ? Euro
      : (DIMENSION_ICONS[dim.id] ?? Scale)
  const severityColor =
    dim.headline_stat.severity in SEVERITY
      ? SEVERITY[dim.headline_stat.severity as keyof typeof SEVERITY]
      : SEVERITY.low

  return (
    <Link
      to={withSearch(appPath(country, dimensionSlugFromApiRoute(dim.route)), params.toString())}
      className="app-glass-strong group block text-left p-5 rounded-2xl hover:border-primary/30 transition-all duration-200 hover:-translate-y-0.5"
    >
      <h3 className="flex items-center gap-2 text-sm font-semibold text-foreground group-hover:text-primary transition-colors">
        <Icon className="w-4 h-4 text-primary shrink-0" />
        {dim.name}
      </h3>
      <p className="text-2xl font-bold tabular-nums mt-2" style={{ color: severityColor }}>
        {formatHeadline(dim)}
      </p>
      <p className="text-sm text-muted-foreground mt-1 leading-snug">{dim.headline_stat.label}</p>
    </Link>
  )
}
