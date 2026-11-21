import { useQuery } from '@tanstack/react-query'
import { fetchJson } from '@/api/client'
import type { ReachResponse, ScoreResponse, SectionsResponse } from '@/api/types'
import type { CompareSide } from '@/lib/compareData'

export function useCompareSide(region: string, urbanRural: string, country: string, pack: string, mode: string, enabled: boolean) {
  return useQuery({
    queryKey: ['compare-side', country, region, urbanRural, pack, mode],
    queryFn: async (): Promise<CompareSide> => {
      const context = { region, urban_rural: urbanRural, country, ...(pack ? { pack } : {}), ...(country === 'netherlands' ? { mode } : {}) }
      const [access, service, score, reach, equity] = await Promise.all([
        fetchJson<SectionsResponse>('/sections', { ...context, dimension: 'accessibility' }),
        fetchJson<SectionsResponse>('/sections', { ...context, dimension: 'service_quality' }),
        fetchJson<ScoreResponse>('/score', context),
        fetchJson<ReachResponse>('/reach', { ...context, dest_type: 'jobs', cutoff: '45' }).catch((error: unknown): ReachResponse => {
          // Dated score/exhibits remain usable without a historical Reach cache.
          if (error instanceof Error && 'status' in error && error.status === 400) return {
            available: false, geographies: [], dest_type: 'jobs', cutoff: 45, median: null,
            n_areas: 0, histogram: [], ranked: [], note: 'Historical travel-time counts are unavailable.',
          }
          throw error
        }),
        fetchJson<SectionsResponse>('/sections', { ...context, dimension: 'equity' }),
      ])
      return { access, service, score, reach, equity }
    },
    staleTime: 60_000,
    retry: 1,
    enabled,
  })
}
