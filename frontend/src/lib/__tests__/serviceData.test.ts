import { describe, expect, it } from 'vitest'
import type { SectionItem } from '@/api/types'
import { operatingHours, rankedRoutes, serviceClock } from '../serviceData'

describe('Scheduled service contracts', () => {
  it('retains midnight, missing endpoints and next-day service minutes distinctly', () => {
    expect(serviceClock(0)).toBe('00:00')
    expect(serviceClock(1467)).toBe('00:27 (+1d)')
    expect(serviceClock(null)).toBe('—')
    expect(operatingHours({ categories: ['Observed', 'Missing'], series: [{ name: 'First service (min)', values: [0, null] }, { name: 'Last service (min)', data: [1467] }] })).toEqual([{ label: 'Observed', first: 0, last: 1467 }, { label: 'Missing', first: null, last: undefined }])
  })
  it('selects actual lowest routes without substituting highest or imputing missing counts', () => {
    const section: SectionItem = { section_id: 'b4_route_frequency', dimension: 'service_quality', suppressed: false, narrative: '', chart_data: {}, stats: { top_routes: [{ route_short_name: 'Busy', n_trips_per_day: 100 }], bottom_routes: [{ route_short_name: 'Low', n_trips_per_day: 1 }, { route_short_name: 'Observed zero', n_trips_per_day: 0 }, { route_short_name: 'Missing', n_trips_per_day: null }] } }
    expect(rankedRoutes(section, true).map(row => row.route_short_name)).toEqual(['Observed zero', 'Low'])
    expect(rankedRoutes({ ...section, stats: { top_routes: section.stats.top_routes } }, true)).toEqual([])
  })
})
