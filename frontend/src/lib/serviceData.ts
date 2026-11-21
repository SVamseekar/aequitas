import type { SectionItem } from '@/api/types'

export const finiteObservation = (value: unknown): value is number => typeof value === 'number' && Number.isFinite(value)
export const serviceNumber = (value: unknown, digits = 0) => finiteObservation(value) ? value.toLocaleString('en-GB', { minimumFractionDigits: digits, maximumFractionDigits: digits }) : '—'

export function serviceClock(value: unknown): string {
  if (!finiteObservation(value) || value < 0) return '—'
  const minutes = Math.round(value), day = Math.floor(minutes / 1440)
  return `${String(Math.floor(minutes % 1440 / 60)).padStart(2, '0')}:${String(minutes % 60).padStart(2, '0')}${day ? ` (+${day}d)` : ''}`
}

export function operatingHours(chart: Record<string, unknown>) {
  const categories = Array.isArray(chart.categories) ? chart.categories as string[] : []
  const series = Array.isArray(chart.series) ? chart.series as { name: string; values?: unknown[]; data?: unknown[] }[] : []
  const first = series.find(row => row.name === 'First service (min)')
  const last = series.find(row => row.name === 'Last service (min)')
  return categories.map((label, index) => ({ label, first: (first?.values ?? first?.data)?.[index], last: (last?.values ?? last?.data)?.[index] }))
}

export interface RankedRoute { route_short_name: string; agency_name?: string; n_trips_per_day: number; primary_region?: string }
export function rankedRoutes(section: SectionItem, lowest: boolean): RankedRoute[] {
  const raw = section.stats[lowest ? 'bottom_routes' : 'top_routes']
  if (!Array.isArray(raw)) return []
  return (raw as RankedRoute[]).filter(row => typeof row.route_short_name === 'string' && finiteObservation(row.n_trips_per_day))
    .sort((a, b) => lowest ? a.n_trips_per_day - b.n_trips_per_day : b.n_trips_per_day - a.n_trips_per_day)
}
