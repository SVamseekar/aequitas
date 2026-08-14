import { COUNTRIES, DIMENSION_API_IDS, DIMENSIONS, type CountryCode } from "@/lib/constants"

export const APP_ROOT = "/app"

export function isCountry(value: string | undefined): value is CountryCode {
  return COUNTRIES.some((c) => c.code === value)
}

export function appHome(country: string): string {
  return `${APP_ROOT}/${country}`
}

export function appPath(country: string, slug?: string): string {
  if (!slug) return appHome(country)
  return `${APP_ROOT}/${country}/${slug}`
}

/** Keep region / urban_rural when moving between app pages. Drop leftover compare/UK keys. */
export function withSearch(pathname: string, search: string): { pathname: string; search: string } {
  const raw = search.startsWith("?") ? search.slice(1) : search
  const src = new URLSearchParams(raw)
  const ireland = pathname.includes("/ireland")
  const netherlands = pathname.includes("/netherlands")
  const next = new URLSearchParams()
  let region = src.get("region") ?? "all"
  if ((ireland || netherlands) && region.startsWith("E12")) region = "all"
  if (!ireland && !netherlands && !region.startsWith("E12") && region !== "all") {
    const looksCounty = !/^E\d/.test(region)
    if (looksCounty && region !== "all") region = "all"
  }
  if (ireland && ["groningen", "noord-holland", "zeeland", "utrecht"].includes(region)) region = "all"
  if (netherlands && ["dublin", "cork"].includes(region)) region = "all"
  next.set("region", region)
  const ur = src.get("urban_rural") ?? "all"
  next.set("urban_rural", ur === "urban" || ur === "rural" ? ur : "all")
  const pack = src.get("pack") ?? src.get("as_of")
  if (pack) next.set("pack", pack)
  if (netherlands) {
    const mode = (src.get("mode") ?? "bus").toLowerCase()
    next.set("mode", mode === "all" ? "all" : "bus")
  }
  return { pathname, search: `?${next.toString()}` }
}

export function dimensionSlugFromApiRoute(route: string): string {
  const cleaned = route.startsWith("/") ? route.slice(1) : route
  const dim = DIMENSIONS.find((d) => d.id === cleaned || d.route.slice(1) === cleaned)
  if (dim) return dim.route.slice(1)
  const mapped = Object.entries(DIMENSION_API_IDS).find(([, api]) => api === cleaned)
  return mapped?.[0] ?? cleaned
}

/** Warehouse ids that must not stay in the URL (tab bar uses product slugs). */
export const WAREHOUSE_DIMENSION_SLUGS = [
  "accessibility",
  "service_quality",
  "route_network",
  "bus_services_act",
  "economic",
] as const

export function productSlugOrNull(slug: string): string | null {
  const product = dimensionSlugFromApiRoute(slug)
  if (product !== slug) return product
  if ((WAREHOUSE_DIMENSION_SLUGS as readonly string[]).includes(slug)) return product
  return null
}

export function legacyDashboardToApp(pathname: string, search: string): string {
  const rest = pathname.replace(/^\/dashboard\/?/, "")
  if (!rest) return `${appHome("england")}${search}`
  if (rest === "compare") return `${appPath("england", "compare")}${search}`
  return `${appPath("england", dimensionSlugFromApiRoute(rest))}${search}`
}
