import { describe, expect, it } from 'vitest'
import { coveragePresentation } from '../coverage'
describe('coverage source denominators', () => {
  it('identifies England legacy area share without claiming population weighting', () => {
    expect(coveragePresentation('england').unit).toBe('% of LSOAs')
    expect(coveragePresentation('england').title).toBe('LSOAs with non-zero access score')
  })
  it.each(['ireland', 'netherlands', 'france'])('retains %s population coverage', country => {
    expect(coveragePresentation(country).unit).toBe('% of population')
  })
})
