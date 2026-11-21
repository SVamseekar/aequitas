/** The England legacy percentage counts LSOAs; the other packs weight population. */
export function coveragePresentation(country: string) {
  return country === 'england' ? {
    title: 'LSOAs with non-zero access score', shortLabel: 'Area coverage', unit: '% of LSOAs',
    definition: 'Share of LSOAs with a non-zero stored access score. England’s existing percentage is area-based, rather than population-weighted.',
  } : {
    title: 'People within 400 m of a stop', shortLabel: 'Population within 400 m', unit: '% of population',
    definition: 'Share of population within 400 m of a stop. Stop proximity, without a regular-service requirement.',
  }
}
