import { lazy, Suspense } from 'react'
import { useMapLayer, usePackDates, useScore } from '@/api/hooks'
import type { CountryCode } from '@/lib/briefingCatalog'
import { coveragePresentation } from '@/lib/coverage'

const ChoroplethMap = lazy(() => import('@/components/charts/ChoroplethMap'))
const geography: Record<CountryCode, string> = { england: 'region', ireland: 'ireland_county', netherlands: 'netherlands_provincie', france: 'france_region' }
export function PublicCountryEvidence({ code, name }: { code: CountryCode; name: string }) {
  const score = useScore('all', 'all', code, '', 'bus')
  const map = useMapLayer('all', 'all', code, '', 'bus', 'coverage')
  const packs = usePackDates()
  const entry = packs.data?.[code]
  const dates = entry && 'dates' in entry ? entry.dates : undefined
  const date = dates?.find(row => row.current)?.as_of
  const coverage = score.data?.components.find(item => item.id === 'pop_within_400m')?.value
  const meaning = coveragePresentation(code)
  return <section aria-label={`${name} country evidence`} className='public-country-evidence'>
    <div className='public-coverage-card'><h2>{meaning.title}</h2>
      {score.isPending ? <p role='status'>Loading coverage…</p> : score.error ? <div role='alert'><p>Coverage could not be loaded.</p><button type='button' className='app-panel-button' onClick={() => void score.refetch()}>Retry coverage</button></div> : <><strong>{coverage == null ? '—' : `${(coverage * 100).toFixed(1)}%`}</strong><p>{coverage == null ? 'Coverage unavailable' : `${meaning.unit} in ${name}`}</p></>}
      <p className='public-evidence-scope'>Current registered network{date ? ` · ${date}` : ''}{code === 'netherlands' ? ' · Bus only' : ''}</p><p>{meaning.definition} This is not travel-time accessibility.</p>
    </div>
    <div className='public-country-map'>
      {map.isPending ? <p role='status'>Loading coverage map…</p> : map.error ? <p role='alert'>Coverage map could not be loaded.</p> : map.data?.empty || !map.data?.data.length ? <p>{map.data?.empty_reason ?? 'Coverage map unavailable.'}</p> : <Suspense fallback={<p role='status'>Loading boundaries…</p>}><ChoroplethMap chartData={{ ...map.data, geography: geography[code], color_mode: 'coverage', title: `${meaning.shortLabel} in ${name}` }} /></Suspense>}
      <div className='app-coverage-legend'><span>Lower coverage</span><i aria-hidden='true' /><span>Higher coverage</span></div>
    </div>
  </section>
}
