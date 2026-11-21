import { describe, expect, it } from 'vitest'
import { evidenceView } from '../evidenceViews'

describe('shareable evidence selection', () => {
  it('resolves warehouse exhibit IDs to their view without changing analytical data', () => {
    expect(evidenceView('correlations', 'd3_coverage_car')?.id).toBe('relationships')
    expect(evidenceView('equity', 'f6_equitable_regions')?.label).toBe('Regions')
    expect(evidenceView('accessibility', 'facilities')?.panel).toBe('facilities')
  })
  it('recovers an unknown or cross-page view to a valid default', () => {
    expect(evidenceView('equity', 'custom')?.id).toBe('f1_gini')
    expect(evidenceView('missing', null)).toBeUndefined()
  })
  it('preserves legacy domain and operator exhibit URLs after grouping the views',()=>{
    expect(evidenceView('correlations','relationships','d9c_crime_access')?.id).toBe('domains')
    expect(evidenceView('bus_services_act','readiness','bsa2_operator_concentration')?.id).toBe('operators')
    expect(evidenceView('correlations','d5_coverage_income')?.panel).toBe('domains')
  })
})
