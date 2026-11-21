import type { OpsResponse } from '@/api/types'
import { OpsPlot } from './OpsPlot'
import { OpsCountryScope } from './OpsCountryScope'
import { OpsSources } from './OpsSources'
const number = (value: number | null | undefined) => value == null ? '—' : value.toLocaleString('en-GB')
export function OpsEvidence({ data, country, view }: { data: OpsResponse; country: string; view: string }) {
  const rows = data.by_region ?? []
  const deciles = (data.by_imd_decile ?? []).filter(row => row.n_updates > 0)
  const indexLabel = country === 'england' ? 'IMD' : country === 'ireland' ? 'HP' : country === 'netherlands' ? 'SES-WOA' : 'F-EDI'
  return <>
    {country !== 'england' ? <div className='ops-stat-grid ops-country-stat-grid'>
      <Stat label='Snapshot updates' value={number(data.n_updates)} />
      <Stat label='Delay field present' value={number(data.n_with_delay)} />
      <Stat label='Late %' value={data.pct_late == null ? '—' : `${data.pct_late.toFixed(1)}%`} />
      <Stat label='Skipped' value={number(data.n_skipped)} />
      <Stat label='Cancelled' value={number(data.n_cancelled)} />
      <Stat label='Coverage' value={data.coverage_pct == null ? '—' : `${data.coverage_pct.toFixed(1)}%`} />
      {country === 'france' && <><Stat label='Listed feeds' value={number(data.n_gtfs_rt_listed)} /><Stat label='Sampled feeds' value={number(data.n_sampled)} /></>}
    </div> : <div className='ops-stat-grid'>
      <Stat label='Snapshot vintage' value={data.vintage || 'Unavailable'} />
      <Stat label='Total snapshot updates' value={number(data.n_updates)} />
      <Stat label='Routes with updates' value={`${number(data.n_routes_with_update)} / ${number(data.n_static_routes)}`} note={data.coverage_pct == null ? 'Route coverage unavailable' : `${data.coverage_pct.toFixed(2)}% coverage`} />
      <Stat label='Updates with delay field' value={number(data.n_with_delay)} note={`Punctuality: ${data.pct_late == null ? '—' : `${data.pct_late.toFixed(1)}% late`}`} />
    </div>}
    {view === 'sources' ? <OpsSources data={data} /> : view === 'snapshot' && country !== 'england' ? <OpsCountryScope data={data} country={country} /> : view === 'deprivation' ? <div className='ops-join-layout'>
      <section className='app-panel'><h2>Snapshot updates by deprivation decile ({indexLabel})</h2><p>Number of joined updates in this snapshot.</p>{country === 'england' && deciles.length ? <OpsPlot rows={deciles.map(row => ({ name: String(row.imd_decile), n_updates: row.n_updates }))} label='Updates by deprivation decile' /> : <div className='ops-empty-join'><h3>No {country === 'england' ? 'IMD' : 'deprivation'}-decile join in this snapshot</h3><p>This snapshot has no stored joined observations. Counts are unavailable and no bars are inferred.</p></div>}</section>
      <aside className='app-panel'><h2>About the deprivation join</h2><p>Collector updates join through stop or small-area location to the country's deprivation index. Decile 1 is most deprived within that country.</p><h3 className='mt-4'>Join scope</h3><p>National collector scope retained independently of static region and area filters.</p><p>Outside-country and unmatched observations are excluded from the joined distribution.</p><p>Deprivation scale: {indexLabel}.</p></aside>
    </div> : <section className='app-panel' data-testid='ops-strip'><h2>Snapshot updates by region</h2><p>Number of stored updates, rather than a punctuality rate.</p>{rows.length ? <><OpsPlot rows={rows} label='Stored updates by region' /><div className='ops-table-scroll'><table aria-label='Regional update summary'><thead><tr><th>Region</th><th>Updates</th><th>Updates with delay</th><th>Late %</th></tr></thead><tbody>{rows.map(row => <tr key={row.code}><td>{row.name}</td><td>{number(row.n_updates)}</td><td>{number(row.n_with_delay)}</td><td>{row.pct_late == null ? '—' : `${row.pct_late.toFixed(1)}%`}</td></tr>)}</tbody></table></div></> : <p>No region join on this snapshot. Stop IDs or static geography did not match; no regional distribution is inferred.</p>}</section>}
    <div className='ops-evidence-footer'><p data-testid='ops-late-rule'>{data.pct_late == null ? `Late is — because n_with_delay = ${data.n_with_delay}.` : `${number(data.n_with_delay)} updates carried a delay field.`} Late means delay &gt; {data.late_threshold_seconds ?? 300} seconds, only when that field exists. {country === 'england' ? 'This is not a DfT punctuality statistic.' : 'Collector delay shares are separate from the static equity score.'}</p><p data-testid='ops-coverage'>{data.coverage_sentence}</p><p data-testid='ops-vintage'>Rollup vintage {data.vintage}. {data.window_note} {data.late_threshold_note}</p></div>
  </>
}
function Stat({ label, value, note }: { label: string; value: string; note?: string }) {
  return <section className='app-panel'><h2>{label}</h2><strong>{value}</strong>{note && <p>{note}</p>}</section>
}
