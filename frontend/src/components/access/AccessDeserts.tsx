import { ChartInsights } from '@/components/dimension/ChartInsights'
import { lazy, Suspense } from 'react'
import { useSearchParams } from 'react-router'
import type { SectionItem } from '@/api/types'
import { useFilters, useSections } from '@/api/hooks'
import { SectionCard } from '@/components/dimension/SectionCard'
const ChoroplethMap = lazy(() => import('@/components/charts/ChoroplethMap'))
const number = (value: unknown, digits = 0, suffix = '') => typeof value === 'number' && Number.isFinite(value) ? `${value.toLocaleString('en-GB', { maximumFractionDigits: digits, minimumFractionDigits: digits })}${suffix}` : '—'

function SundayDeserts({ section }: { section: SectionItem }) {
  const { country, region, urbanRural, pack, mode } = useFilters()
  const [params, setParams] = useSearchParams()
  const query = useSections('service_quality', region, urbanRural, country, pack, mode)
  const stats = query.data?.sections.find(item => item.section_id === 'b3_weekend_penalty')?.stats
  const raw = Array.isArray(section.chart_data.data) ? section.chart_data.data as { area_code: string; area_name: string; value: number | null }[] : []
  const selected = raw.find(item => item.area_code === params.get('lad'))
  const select = (code: string) => { const next = new URLSearchParams(params); if (code) next.set('lad', code); else next.delete('lad'); setParams(next) }
  return <div className='access-deserts'>
    {query.isPending && <p role='status'>Loading Sunday-service summary…</p>}
    {query.error && <div role='alert'><p>Sunday-service summary could not be loaded.</p><button type='button' className='app-panel-button' onClick={() => void query.refetch()}>Retry Sunday summary</button></div>}
    <div className='access-metrics'>{[
      ['Sunday-desert areas (LSOAs)', number(stats?.n_sunday_desert)],
      ['Areas with no Sunday service', number(stats?.pct_sunday_desert,1,'%')],
      ['Population in Sunday-desert areas', '—'], ['Mean IMD of Sunday-desert areas', '—'],
    ].map(([label,value]) => <section className='app-panel' key={label}><h2>{label}</h2><strong>{value}</strong></section>)}</div>
    <div className='access-desert-layout'><section className='app-panel'><h2>Sunday deserts by local authority district</h2><p>Percentage of LSOAs with no Sunday service. District rates use all area types; headline counts follow the selected area filter.</p><div className='access-desert-legend'><span>0% · lower rate</span><i aria-hidden='true' /><span>100% · higher rate</span><span>Grey: unavailable</span></div>{raw.length ? <Suspense fallback={<p role='status'>Loading district boundaries…</p>}><ChoroplethMap onAreaClick={select} chartData={{ ...section.chart_data, title: 'Sunday-desert rate by district', color_mode: 'desert_rate', metric_label: 'LSOAs with no Sunday service (%)' }} /></Suspense> : <p>No district map observations are stored for this filter.</p>}</section>
      <aside><ChartInsights section={{...section,section_id:'b3_weekend_penalty',stats:stats??{}}} className='app-panel' /><section className='app-panel'><h2>Selected district</h2><label className='access-district-control'>District<select aria-label='Inspect district' value={selected?.area_code ?? ''} onChange={event => select(event.target.value)}><option value=''>Choose a district</option>{[...raw].sort((a,b) => a.area_name.localeCompare(b.area_name)).map(item => <option key={item.area_code} value={item.area_code}>{item.area_name}</option>)}</select></label>{selected ? <><h3>{selected.area_name}</h3><strong>{number(selected.value,1,'%')}</strong><p>LSOAs with no Sunday service, all area types.</p></> : <p>{params.get('lad') ? 'That district is outside the current filter. Choose an available district.' : 'Choose a district on the map or in the list to inspect its actual stored rate.'}</p>}</section>
        <section className='app-panel'><h2>Population and deprivation</h2><p>Sunday-desert population is not stored in this summary. A population total or deprivation mean from another subset is not substituted.</p></section>
        <section className='app-panel'><h2>Different desert definitions</h2><p>Sunday deserts have no scheduled Sunday service. Zero-stop areas are a separate measure.</p><p>Separate zero-stop analysis: {number(section.stats.n_desert_lsoas)} LSOAs; {number(section.stats.pop_affected)} residents. This is a different subset.</p></section>
      </aside></div>
  </div>
}
export function AccessDeserts({ section }: { section: SectionItem }) {
  const { country } = useFilters()
  return country === 'england' && section.chart_data.metric === 'pct_sunday_desert' ? <SundayDeserts section={section} /> : <SectionCard section={section} featured />
}
