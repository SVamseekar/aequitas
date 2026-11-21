import { useQuery } from "@tanstack/react-query"
import { useNavigate, useParams, useSearchParams } from "react-router"
import { fetchJson } from "./client"
import type {
  OverviewResponse,
  SectionsResponse,
  ProvenanceResponse,
  LsoaResponse,
  ScoreResponse,
  MapResponse,
  DestinationsResponse,
  ReachResponse,
  ReachBandsResponse,
  TimeSeriesResponse,
  PacksResponse,
  OpsResponse,
} from "./types"
import { COUNTRIES } from "@/lib/constants"
import { appPath } from "@/lib/appRoutes"

/** Read global filters from URL search params + country path. */
export function useFilters() {
  const [params, setParams] = useSearchParams()
  const { country: countryParam } = useParams<{ country?: string }>()
  const navigate = useNavigate()
  const region = params.get("region") ?? "all"
  const urbanRural = params.get("urban_rural") ?? "all"
  const pack = params.get("pack") ?? params.get("as_of") ?? ""
  const modeRaw = (params.get("mode") ?? "bus").toLowerCase()
  const mode = modeRaw === "all" ? "all" : "bus"
  const country =
    COUNTRIES.find((c) => c.code === countryParam)?.code ?? "england"

  const keepMode = (next: URLSearchParams) => {
    for (const key of ['view', 'exhibit', 'metric', 'a', 'b', 'dest', 'cutoff', 'cells', 'freq_pct', 'last_bus', 'drt_cov', 'franchise', 'lad', 'rank', 'sort', 'cluster', 'point']) {
      const value = params.get(key)
      if (value) next.set(key, value)
    }
    if (country === "netherlands" && !next.has('mode')) next.set("mode", mode)
  }

  const setRegion = (r: string) => {
    const next = new URLSearchParams()
    next.set("region", r)
    next.set("urban_rural", urbanRural === "urban" || urbanRural === "rural" ? urbanRural : "all")
    if (pack) next.set("pack", pack)
    keepMode(next)
    setParams(next)
  }
  const setUrbanRural = (u: string) => {
    const next = new URLSearchParams()
    next.set("region", region.startsWith("E12") && country === "ireland" ? "all" : region)
    next.set("urban_rural", u)
    if (pack) next.set("pack", pack)
    keepMode(next)
    setParams(next)
  }
  const setPack = (nextPack: string) => {
    const next = new URLSearchParams()
    next.set("region", region)
    next.set("urban_rural", urbanRural === "urban" || urbanRural === "rural" ? urbanRural : "all")
    if (nextPack && nextPack !== "current") next.set("pack", nextPack)
    keepMode(next)
    setParams(next)
  }
  const setMode = (nextMode: string) => {
    const next = new URLSearchParams()
    next.set("region", region)
    next.set("urban_rural", urbanRural === "urban" || urbanRural === "rural" ? urbanRural : "all")
    if (pack) next.set("pack", pack)
    next.set("mode", nextMode === "all" ? "all" : "bus")
    keepMode(next)
    setParams(next)
  }
  const setCountry = (nextCountry: string) => {
    const slug = window.location.pathname.split("/").slice(3).join("/")
    const next = new URLSearchParams()
    next.set("region", "all")
    next.set("urban_rural", urbanRural === "urban" || urbanRural === "rural" ? urbanRural : "all")
    if (nextCountry === "netherlands") next.set("mode", "bus")
    navigate(`${appPath(nextCountry, slug || undefined)}?${next.toString()}`)
  }

  return { country, region, urbanRural, pack, mode, setCountry, setRegion, setUrbanRural, setPack, setMode }
}

function packParams(pack?: string): Record<string, string> {
  return pack ? { pack } : {}
}

export function useOverview(
  region: string,
  urbanRural: string,
  country = "england",
  pack = "",
  mode = "",
) {
  return useQuery({
    queryKey: ["overview", country, region, urbanRural, pack, mode],
    queryFn: () =>
      fetchJson<OverviewResponse>("/overview", {
        region,
        urban_rural: urbanRural,
        country,
        ...packParams(pack),
        ...(country === "netherlands" ? { mode: mode || "bus" } : {}),
      }),
    staleTime: Infinity,
    retry: pack ? false : 1,
  })
}

export function useScore(region: string, urbanRural: string, country = "england", pack = "", mode = "") {
  return useQuery({
    queryKey: ["score", country, region, urbanRural, pack, mode],
    queryFn: () =>
      fetchJson<ScoreResponse>("/score", {
        region,
        urban_rural: urbanRural,
        country,
        ...packParams(pack),
        ...(country === "netherlands" ? { mode: mode || "bus" } : {}),
      }),
    staleTime: Infinity,
  })
}

export function useMapLayer(
  region: string,
  urbanRural: string,
  country = "england",
  pack = "",
  mode = "",
  metric = "deserts",
) {
  return useQuery({
    queryKey: ["map", country, region, urbanRural, pack, mode, metric],
    queryFn: () =>
      fetchJson<MapResponse>("/map", {
        metric,
        region,
        urban_rural: urbanRural,
        country,
        ...packParams(pack),
        ...(country === "netherlands" ? { mode: mode || "bus" } : {}),
      }),
    staleTime: Infinity,
    retry: pack ? false : 1,
  })
}

export function useReachBands(region: string, urbanRural: string, country = "england", pack = "") {
  return useQuery({
    queryKey: ["reach-bands", country, region, urbanRural, pack],
    queryFn: () =>
      fetchJson<ReachBandsResponse>("/reach/bands", {
        region,
        urban_rural: urbanRural,
        country,
        ...packParams(pack),
      }),
    staleTime: Infinity,
  })
}

export function useDestinations(country = "england") {
  return useQuery({
    queryKey: ["destinations", country],
    queryFn: () => fetchJson<DestinationsResponse>("/destinations", { country }),
    staleTime: Infinity,
  })
}

export function useReach(
  region: string,
  urbanRural: string,
  destType: string,
  cutoff: number,
  country = "england",
  pack = "",
) {
  return useQuery({
    queryKey: ["reach", country, region, urbanRural, destType, cutoff, pack],
    queryFn: () =>
      fetchJson<ReachResponse>("/reach", {
        region,
        urban_rural: urbanRural,
        dest_type: destType,
        cutoff: String(cutoff),
        country,
        ...packParams(pack),
      }),
    staleTime: Infinity,
  })
}

export function useSections(
  dimension: string,
  region: string,
  urbanRural: string,
  country = "england",
  pack = "",
  mode = "",
) {
  return useQuery({
    queryKey: ["sections", country, dimension, region, urbanRural, pack, mode],
    queryFn: () =>
      fetchJson<SectionsResponse>("/sections", {
        dimension,
        region,
        urban_rural: urbanRural,
        country,
        ...packParams(pack),
        ...(country === "netherlands" ? { mode: mode || "bus" } : {}),
      }),
    staleTime: Infinity,
  })
}

export function useTimeSeries(
  country: string,
  region: string,
  urbanRural: string,
  metric = "score",
  pack = "",
) {
  return useQuery({
    queryKey: ["time", country, region, urbanRural, metric, pack],
    queryFn: () =>
      fetchJson<TimeSeriesResponse>("/time", {
        country,
        region,
        urban_rural: urbanRural,
        metric,
        ...packParams(pack),
      }),
    staleTime: Infinity,
    retry: (count, err) => {
      const status = (err as { status?: number })?.status
      if (status === 404) return false
      return count < 1
    },
  })
}

export function useOps(country: string, pack = "") {
  return useQuery({
    queryKey: ["ops", country, pack],
    queryFn: () =>
      fetchJson<OpsResponse>("/ops", {
        country,
        ...packParams(pack),
      }),
    staleTime: 60_000,
    retry: (count, err) => {
      const status = (err as { status?: number })?.status
      if (status === 404) return false
      return count < 1
    },
  })
}

export function usePackDates() {
  return useQuery({
    queryKey: ["packs"],
    queryFn: () => fetchJson<PacksResponse>("/packs"),
    staleTime: 60_000,
  })
}

export function useProvenance(metricId: string | null, country = 'england', pack = '') {
  return useQuery({
    queryKey: ["provenance", metricId, country, pack],
    queryFn: () => fetchJson<ProvenanceResponse>(`/provenance/${metricId}`, { country, ...packParams(pack) }),
    enabled: !!metricId,
    staleTime: Infinity,
  })
}

export function useLsoa(table: string, region?: string) {
  return useQuery({
    queryKey: ["lsoa", table, region],
    queryFn: () => {
      const params: Record<string, string> = {}
      if (region && region !== "all") params.region = region
      return fetchJson<LsoaResponse>(`/lsoa/${table}`, params)
    },
    staleTime: Infinity,
  })
}

/** Shareable illustrative controls. Impacts require a separate supported model run. */
export function useScenarioSettings() {
  const [params, setParams] = useSearchParams()
  const bounded = (key: string, fallback: number, min: number, max: number) => {
    const value = Number(params.get(key) ?? fallback)
    return Number.isFinite(value) ? Math.round(Math.min(max, Math.max(min, value))) : fallback
  }
  const freqPct = bounded('freq_pct', 10, 0, 50)
  const lastBusHour = bounded('last_bus', 22, 19, 23)
  const drtCoverage = bounded('drt_cov', 0, 0, 100)
  const raw = params.get('franchise')
  const franchise = raw === 'partial' || raw === 'full' ? raw : 'none'
  const setSettings = (settings: { freqPct?: number; lastBusHour?: number; drtCoverage?: number; franchise?: 'none' | 'partial' | 'full' }) => {
    const next = new URLSearchParams(params)
    if (settings.freqPct !== undefined) next.set('freq_pct', String(settings.freqPct))
    if (settings.lastBusHour !== undefined) next.set('last_bus', String(settings.lastBusHour))
    if (settings.drtCoverage !== undefined) next.set('drt_cov', String(settings.drtCoverage))
    if (settings.franchise !== undefined) next.set('franchise', settings.franchise)
    setParams(next)
  }
  return { freqPct, lastBusHour, drtCoverage, franchise, setSettings }
}
