import { ChartInsights } from '@/components/dimension/ChartInsights'
import { useSearchParams } from 'react-router'
import type { SectionItem } from '@/api/types'
import { ChartRenderer } from '@/components/charts/ChartRenderer'
import { rankedRoutes, serviceNumber } from '@/lib/serviceData'

export function ServiceRoutes({ section }: { section: SectionItem }) {
  const [params, setParams] = useSearchParams()
  const lowest = params.get('rank') === 'lowest'
  const rows = rankedRoutes(section, lowest)
  const change = (value: string) => { const next = new URLSearchParams(params); next.set('rank', value); setParams(next) }
  return <div className='service-page'>
    <div className='service-metrics service-metrics-pair'><section className='app-panel'><h2>Routes in frequency analysis</h2><strong>{serviceNumber(section.stats.n_routes)}</strong><p>{typeof section.stats.scope_label === 'string' ? section.stats.scope_label : 'Selected filter'}</p></section><section className='app-panel'><h2>Measure</h2><strong>Trips per day</strong><p>Stored scheduled daily trip counts. These are not punctuality, passenger counts or live bus frequency.</p></section></div>
    <div className='service-main'><section className='app-panel'><div className='service-section-heading'><div><h2>{lowest ? 'Lowest-frequency routes' : 'Highest-frequency routes'}</h2><p>Only the stored highest/lowest route samples are available, rather than a complete searchable route list.</p></div><div className='reach-segmented' role='group' aria-label='Route frequency ranking'><button type='button' aria-pressed={!lowest} onClick={() => change('highest')}>Highest frequency</button><button type='button' aria-pressed={lowest} onClick={() => change('lowest')}>Lowest frequency</button></div></div>
      {rows.length ? <ChartRenderer chartData={{ type: 'horizontal_bar', title: lowest ? 'Lowest route trip counts' : 'Highest route trip counts', x_label: 'Scheduled trips per day', order: lowest ? 'ascending' : 'descending', palette: ['#819d79'], data: rows.map((row, index) => ({ label: `${index + 1}. ${row.route_short_name}`, value: row.n_trips_per_day })) }} /> : <p>No {lowest ? 'lowest' : 'highest'}-frequency route observations are stored for this filter.</p>}
    </section><aside className='app-panel'><ChartInsights section={section} /></aside></div>
    <section className='app-panel mt-4'><h2>Route ranking detail</h2><label className='service-sort'>Rank order <select aria-label='Route ranking order' value={lowest ? 'lowest' : 'highest'} onChange={event => change(event.target.value)}><option value='highest'>Trips per day: highest first</option><option value='lowest'>Trips per day: lowest first</option></select></label><div className='access-table-scroll'><table aria-label='Scheduled route ranking'><thead><tr><th>Rank</th><th>Supplied route name</th><th>Operator</th><th>Primary region</th><th>Trips per day</th></tr></thead><tbody>{rows.map((row, index) => <tr key={`${row.route_short_name}-${row.agency_name}-${index}`}><td>{index + 1}</td><th scope='row'>{row.route_short_name}</th><td>{row.agency_name ?? '—'}</td><td>{row.primary_region ?? '—'}</td><td>{serviceNumber(row.n_trips_per_day)}</td></tr>)}</tbody></table></div><p>Source identifiers and operator names are shown as supplied. A route name need not be unique across operators.</p></section>
  </div>
}
