import { useQuery } from "@tanstack/react-query"
import { useSearchParams } from "react-router"
import { fetchJson } from "./client"
import type { OverviewResponse, SectionsResponse, ProvenanceResponse, LsoaResponse } from "./types"

/** Read global filters from URL search params. */
export function useFilters() {
  const [params, setParams] = useSearchParams()
  const region = params.get("region") ?? "all"
  const urbanRural = params.get("urban_rural") ?? "all"

  const setRegion = (r: string) => {
    const next = new URLSearchParams(params)
    next.set("region", r)
    setParams(next)
  }
  const setUrbanRural = (u: string) => {
    const next = new URLSearchParams(params)
    next.set("urban_rural", u)
    setParams(next)
  }

  return { region, urbanRural, setRegion, setUrbanRural }
}

export function useOverview(region: string, urbanRural: string) {
  return useQuery({
    queryKey: ["overview", region, urbanRural],
    queryFn: () => fetchJson<OverviewResponse>("/overview", { region, urban_rural: urbanRural }),
    staleTime: Infinity,
  })
}

export function useSections(dimension: string, region: string, urbanRural: string) {
  return useQuery({
    queryKey: ["sections", dimension, region, urbanRural],
    queryFn: () =>
      fetchJson<SectionsResponse>("/sections", { dimension, region, urban_rural: urbanRural }),
    staleTime: Infinity,
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
