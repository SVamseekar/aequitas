import type { ReachResponse, ScoreResponse, SectionsResponse } from '@/api/types'
import type { CompareMetricId } from './compareLabels'

export interface CompareSide { access: SectionsResponse; service: SectionsResponse; score: ScoreResponse; reach: ReachResponse; equity: SectionsResponse }
export function sideValues(bundle: CompareSide | undefined): Record<CompareMetricId, number | null> {
  const number = (sections: SectionsResponse | undefined, id: string, key: string) => {
    const value = sections?.sections.find(section => section.section_id === id)?.stats?.[key]
    return typeof value === 'number' && Number.isFinite(value) ? value : null
  }
  return {
    pct_within_400m: number(bundle?.access, 'a3_walking_distance', 'pct_covered'),
    evening_isolated: number(bundle?.service, 'b2_operating_hours', 'pct_evening_isolated'),
    in_country_score: bundle?.score.score ?? null,
    jobs_45: bundle?.reach.available ? bundle.reach.median : null,
    gini: number(bundle?.equity, 'f1_gini', 'gini'),
  }
}
export function formatCompareMetric(id: CompareMetricId, value: number | null) {
  if (value === null || !Number.isFinite(value)) return '—'
  if (id === 'in_country_score') return value.toFixed(1)
  if (id === 'gini') return value.toFixed(4)
  if (id === 'jobs_45') return Math.round(value).toLocaleString('en-GB')
  return `${value.toFixed(1)}%`
}
export const compareDefinitions: Record<CompareMetricId, string> = {
  in_country_score: 'Points · 0–100 · available score components',
  pct_within_400m: '% of population · within 400 m of a stop',
  evening_isolated: '% of areas · no service after 19:00',
  gini: '0–1 · inequality in service distribution',
  jobs_45: 'Destination points · median reachable within 45 minutes',
}
export const compareShortLabels: Record<CompareMetricId, string> = {
  in_country_score: 'In-country score', pct_within_400m: 'Population within 400 m',
  evening_isolated: 'Evening isolated areas', gini: 'Service inequality Gini', jobs_45: 'Access within 45 minutes',
}
export const compareUnits: Record<CompareMetricId, string> = {
  in_country_score: 'Points · 0–100', pct_within_400m: '% of population',
  evening_isolated: '% of areas · after 19:00', gini: '0–1', jobs_45: 'Median destination points',
}
