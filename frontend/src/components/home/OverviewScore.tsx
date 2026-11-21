import { Link, useSearchParams } from 'react-router'
import { useFilters, useScore } from '@/api/hooks'
import { formatInCountryScore } from '@/lib/scoreFormat'
import { coveragePresentation } from '@/lib/coverage'

const labels: Record<string, string> = { pop_within_400m: 'Coverage (400 m)', evening_served: 'Evening service', weekday_frequency: 'Weekday service quality', deprivation_service: 'Service equity' }

export function OverviewScore({ fallbackScore, expanded = false,details=false }: { fallbackScore: number | null; expanded?: boolean;details?:boolean }) {
  const { country, region, urbanRural, pack, mode } = useFilters()
  const score = useScore(region, urbanRural, country, pack, mode)
  const componentLabel = (id: string, fallback: string) => id === 'pop_within_400m' ? coveragePresentation(country).shortLabel : labels[id] ?? fallback
  const [params] = useSearchParams()
  const next = new URLSearchParams(params)
  next.set('view', expanded ? 'map' : 'score')
  if(details)return <section className='app-panel overview-component-details'><h2>Component details</h2>
    {score.isLoading?<p role='status'>Loading score components…</p>:score.isError?<p role='alert'>Component details unavailable for this selection.</p>:score.data?<dl>{score.data.components.map(component=><div key={component.id}><dt>{componentLabel(component.id,component.label)}</dt><dd>{component.value==null?'Unavailable':`${(component.value*100).toFixed(2)} / 100`}</dd><p>{(component.weight_used*100).toFixed(0)}% weight used</p></div>)}</dl>:<p>Component details unavailable.</p>}
    <p>Missing inputs are dropped and remaining weights renormalised. Service equity is separate from Gini.</p>
  </section>
  if (expanded) return (
    <section className='app-panel'>
      <h2>How the in-country score is calculated</h2>
      <p>Weighted sum of four components. Missing components are dropped and the remaining weights are renormalised.</p>
      {score.isLoading && <p role='status'>Loading score components…</p>}
      {score.isError && <p role='alert'>Score components could not be loaded.</p>}
      {score.data && <>
        <p className='mt-5 bg-muted p-4'>{score.data.formula}</p>
        <div className='overflow-x-auto mt-5'><table className='w-full text-sm text-left border-collapse'>
          <caption className='sr-only'>Score components and their actual weights for the selected filter</caption>
          <thead><tr className='border-b border-border'><th className='p-3'>Component</th><th className='p-3'>Weight used</th><th className='p-3'>Value / 100</th><th className='p-3'>Contribution</th></tr></thead>
          <tbody>{score.data.components.map(c => <tr key={c.id} className='border-b border-border'><th className='p-3 font-normal'>{componentLabel(c.id, c.label)}</th><td className='p-3'>{(c.weight_used * 100).toFixed(0)}%</td><td className='p-3'>{c.value == null ? 'Unavailable' : (c.value * 100).toFixed(2)}</td><td className='p-3'>{c.value == null ? '—' : (c.value * c.weight_used * 100).toFixed(2)}</td></tr>)}</tbody>
        </table></div>
        <p className='mt-4'>Service equity is one minus the absolute deprivation–service correlation. It is distinct from the Gini coefficient.</p>
        <p className='mt-3'>{coveragePresentation(country).definition}{country === 'england' ? ' The legacy formula identifier pop_within_400m_share retains this area-based input; the calculation is unchanged.' : ''}</p>
        {score.data.note && <p className='mt-3'>{score.data.note}</p>}
      </>}
      <Link to={{ search: `?${next}` }} className='app-text-link inline-block mt-5'>Return to map</Link>
    </section>
  )
  return (
    <section className='app-panel overview-score-summary'>
      <h3><Link to={{ search: `?${next}` }} aria-label='How the score works'>In-country score</Link></h3>
      <p className='app-score-number'>{formatInCountryScore(score.data?.score ?? fallbackScore)} <span>/ 100</span></p>
      <p>Coverage, evening service, weekday quality and service equity.</p>
      {score.isLoading && <p role='status' className='mt-3'>Loading components…</p>}
      {score.isError && <p className='mt-3'>Component details unavailable.</p>}
    </section>
  )
}
