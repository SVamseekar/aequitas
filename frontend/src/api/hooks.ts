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
    if (country === "netherlands") next.set("mode", mode)
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
) {
  return useQuery({
    queryKey: ["map", country, region, urbanRural, pack, mode],
    queryFn: () =>
      fetchJson<MapResponse>("/map", {
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

export function useReachBands(region: string, urbanRural: string, country = "england") {
  return useQuery({
    queryKey: ["reach-bands", country, region, urbanRural],
    queryFn: () =>
      fetchJson<ReachBandsResponse>("/reach/bands", {
        region,
        urban_rural: urbanRural,
        country,
      }),
    staleTime: Infinity,
  })
}

export function useReach(
  region: string,
  urbanRural: string,
  destType: string,
  cutoff: number,
  country = "england",
) {
  return useQuery({
    queryKey: ["reach", country, region, urbanRural, destType, cutoff],
    queryFn: () =>
      fetchJson<ReachResponse>("/reach", {
        region,
        urban_rural: urbanRural,
        dest_type: destType,
        cutoff: String(cutoff),
        country,
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

export function useProvenance(metricId: string | null) {
  return useQuery({
    queryKey: ["provenance", metricId],
    queryFn: () => fetchJson<ProvenanceResponse>(`/provenance/${metricId}`),
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

const NATIONAL_FALLBACKS = {
  ps1: { population_affected: 5689818, co2_saving_t_yr: 952.0 as number | null, estimated_annual_cost_m: 72.7 as number | null },
  ps2: { population_affected: 8392662, co2_saving_t_yr: 112.0 as number | null, estimated_annual_cost_m: 116.8 as number | null },
  ps3: { population_affected: 5243877, co2_saving_t_yr: 327.0 as number | null, estimated_annual_cost_m: 109.1 as number | null },
  ps4: { population_affected: 760008, co2_saving_t_yr: null as number | null, estimated_annual_cost_m: null as number | null },
}

const FRANCHISE_MULTIPLIERS = {
  none: 1.0,
  partial: 1.3,
  full: 1.7,
}

export function useScenarioCalculation(region: string, urbanRural: string) {
  const [params, setParams] = useSearchParams()
  const freqPct = Number(params.get("freq_pct") ?? "10")
  const lastBusHour = Number(params.get("last_bus") ?? "22")
  const drtCoverage = Number(params.get("drt_cov") ?? "0")
  const franchise = (params.get("franchise") ?? "none") as "none" | "partial" | "full"

  const { data } = useSections("scenarios", region, urbanRural)

  const getScenario = (sectionId: string, fallbackKey: keyof typeof NATIONAL_FALLBACKS) => {
    const section = data?.sections.find((s) => s.section_id === sectionId)
    if (!section || !section.stats || typeof section.stats !== "object") {
      return NATIONAL_FALLBACKS[fallbackKey]
    }
    const statsObj = section.stats as { scenario?: typeof NATIONAL_FALLBACKS[typeof fallbackKey] }
    return statsObj.scenario ?? NATIONAL_FALLBACKS[fallbackKey]
  }

  const ps1 = getScenario("ps1_freq_restoration", "ps1")
  const ps2 = getScenario("ps2_evening_extension", "ps2")
  const ps3 = getScenario("ps3_drt_rural", "ps3")
  const ps4 = getScenario("ps4_franchise", "ps4")

  const lastBusMin = (lastBusHour - 19) * 60
  const multiplier = FRANCHISE_MULTIPLIERS[franchise]

  const freq_pop = (freqPct / 50) * ps1.population_affected
  const evening_pop = (lastBusMin / 240) * ps2.population_affected
  const drt_pop = (drtCoverage / 100) * ps3.population_affected
  const franchise_pop = (franchise === "none" ? 0 : franchise === "partial" ? 0.5 : 1.0) * ps4.population_affected
  const populationAffected = Math.round((freq_pop + evening_pop + drt_pop) * multiplier + franchise_pop)

  const freq_co2 = (freqPct / 50) * ((ps1.co2_saving_t_yr ?? 0) / 1000)
  const evening_co2 = (lastBusMin / 240) * ((ps2.co2_saving_t_yr ?? 0) / 1000)
  const drt_co2 = (drtCoverage / 100) * ((ps3.co2_saving_t_yr ?? 0) / 1000)
  const franchise_co2 = (franchise === "none" ? 0 : franchise === "partial" ? 0.5 : 1.0) * ((ps4.co2_saving_t_yr ?? 0) / 1000)
  const co2Saving = Number(((freq_co2 + evening_co2 + drt_co2) * multiplier + franchise_co2).toFixed(1))

  const freq_cost = (freqPct / 50) * (ps1.estimated_annual_cost_m ?? 0)
  const evening_cost = (lastBusMin / 240) * (ps2.estimated_annual_cost_m ?? 0)
  const drt_cost = (drtCoverage / 100) * (ps3.estimated_annual_cost_m ?? 0)
  const franchise_cost = (franchise === "none" ? 0 : franchise === "partial" ? 0.5 : 1.0) * (ps4.estimated_annual_cost_m ?? 0)
  const total_cost = (freq_cost + evening_cost + drt_cost) * multiplier + franchise_cost

  const freq_benefit = freq_cost * 1.8
  const evening_benefit = evening_cost * 1.4
  const drt_benefit = drt_cost * 1.1
  const franchise_benefit = franchise_cost * 1.8
  const total_benefit = (freq_benefit + evening_benefit + drt_benefit) * multiplier + franchise_benefit
  const bcr = total_cost > 0 ? Number((total_benefit / total_cost).toFixed(2)) : 0.00

  const setSettings = (settings: { freqPct?: number; lastBusHour?: number; drtCoverage?: number; franchise?: "none" | "partial" | "full" }) => {
    const next = new URLSearchParams(params)
    if (settings.freqPct !== undefined) next.set("freq_pct", String(settings.freqPct))
    if (settings.lastBusHour !== undefined) next.set("last_bus", String(settings.lastBusHour))
    if (settings.drtCoverage !== undefined) next.set("drt_cov", String(settings.drtCoverage))
    if (settings.franchise !== undefined) next.set("franchise", settings.franchise)
    setParams(next)
  }

  return {
    freqPct,
    lastBusHour,
    drtCoverage,
    franchise,
    populationAffected,
    co2Saving, // in kt
    total_cost, // in £m
    bcr,
    setSettings,
  }
}
