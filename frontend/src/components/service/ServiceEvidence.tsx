import { Link, useSearchParams } from 'react-router'
import type { SectionItem } from '@/api/types'
import { useFilters } from '@/api/hooks'
import { downloadCsv } from '@/lib/downloadCsv'
import { finiteObservation, serviceNumber } from '@/lib/serviceData'
import { SectionCard } from '@/components/dimension/SectionCard'

interface Row { id?: string; x: unknown; y: unknown }
export function ServiceEvidence({ section, table }: { section?: SectionItem; table: boolean }) {
  const [params, setParams] = useSearchParams()
  const { country, region, urbanRural, pack, mode } = useFilters()
  const search = (view: string) => { const next = new URLSearchParams(params); next.set('view', view); next.delete('page'); return `?${next}` }
  const raw = Array.isArray(section?.chart_data.data) ? section.chart_data.data as Row[] : []
  const sort = params.get('sort') ?? 'code'
  const rows = [...raw].sort((a, b) => sort === 'x-high' || sort === 'y-high' ? compareNumber(a[sort === 'x-high' ? 'x' : 'y'], b[sort === 'x-high' ? 'x' : 'y']) : String(a.id ?? '').localeCompare(String(b.id ?? '')))
  const pages = Math.max(1, Math.ceil(rows.length / 25)), requestedPage = Number(params.get('page') ?? '1')
  const page = Number.isInteger(requestedPage) ? Math.max(1, Math.min(pages, requestedPage)) : 1
  const update = (key: string, value: string) => { const next = new URLSearchParams(params); next.set(key, value); if (key === 'sort') next.delete('page'); setParams(next) }
  const xLabel = typeof section?.chart_data.x_label === 'string' ? section.chart_data.x_label : 'Deprivation measure'
  const yLabel = typeof section?.chart_data.y_label === 'string' ? section.chart_data.y_label : 'Service quality'
  const exportData = () => downloadCsv('aequitas-service-sample.csv', ['country', 'region', 'area', 'network', 'mode', 'small_area_code', xLabel, yLabel], rows.map(row => [country, region, urbanRural, pack || 'current', mode, row.id, finiteObservation(row.x) ? row.x : null, finiteObservation(row.y) ? row.y : null]))
  return <div className='service-page'>
    <nav className='service-display-controls' aria-label='Service evidence display'><Link to={{ search: search('b5_frequency_deprivation') }} aria-current={!table ? 'page' : undefined}>Chart</Link><Link to={{ search: search('table') }} aria-current={table ? 'page' : undefined}>Table</Link></nav>
    {!section ? <p className='app-panel'>No deprivation/service exhibit is stored for this filter.</p> : !table ? <SectionCard section={section} featured /> : <section className='app-panel'><h2>Small-area service evidence</h2><p>{rows.length.toLocaleString('en-GB')} supplied sample rows from {serviceNumber(section.chart_data.sample_size ?? section.stats.n)} observations in the selected filter. This is the chart's sample, not the full warehouse.</p>
      <div className='service-section-heading'><label className='service-sort'>Sort sample <select aria-label='Sort service sample' value={sort} onChange={event => update('sort', event.target.value)}><option value='code'>Small-area code</option><option value='x-high'>{xLabel}: high to low</option><option value='y-high'>{yLabel}: high to low</option></select></label><button type='button' className='app-panel-button' disabled={!rows.length} onClick={exportData}>Download service sample CSV</button></div>
      <div className='access-table-scroll'><table aria-label='Small-area service sample'><thead><tr><th>Small-area code</th><th>{xLabel}</th><th>{yLabel}</th></tr></thead><tbody>{rows.slice((page - 1) * 25, page * 25).map((row, index) => <tr key={`${row.id}-${index}`}><th scope='row'>{row.id ?? 'Unavailable code'}</th><td>{serviceNumber(row.x, 3)}</td><td>{serviceNumber(row.y, 3)}</td></tr>)}</tbody></table></div>{!rows.length && <p>No individual sample rows are supplied for this filter. No records are invented.</p>}
      <div className='service-pagination'><span>{rows.length ? (page - 1) * 25 + 1 : 0}–{Math.min(page * 25, rows.length)} of {rows.length.toLocaleString('en-GB')} · 25 rows per page</span><button type='button' className='app-panel-button' disabled={page <= 1} onClick={() => update('page', String(page - 1))}>Previous sample page</button><button type='button' className='app-panel-button' disabled={page >= pages} onClick={() => update('page', String(page + 1))}>Next sample page</button></div>
    </section>}
    <details className='app-panel mt-4'><summary>Interpretation and sources</summary><p>Association is at small-area level within the selected country; it does not establish causation. Sampled chart rows do not represent a separate census or a full downloadable warehouse.</p><p>Axis names and values come from the selected warehouse exhibit. Network selection identifies its registered snapshot; population and deprivation sources retain their own vintages.</p></details>
  </div>
}

function compareNumber(a: unknown, b: unknown) {
  if (!finiteObservation(a)) return finiteObservation(b) ? 1 : 0
  if (!finiteObservation(b)) return -1
  return b - a
}
