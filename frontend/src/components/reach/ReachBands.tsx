import { lazy, Suspense } from 'react'
import { Link, useSearchParams } from 'react-router'
import { useFilters } from '@/api/hooks'
import type { ReachBandsResponse } from '@/api/types'
import { downloadReachCsv } from '@/lib/reach'
import { ReachHeatmap } from './ReachPlot'

const ChoroplethMap = lazy(() => import('@/components/charts/ChoroplethMap'))
const format = (value: number | undefined) => value == null ? '—' : value.toLocaleString('en-GB')

export function ReachBands({ data, view, areaNoun, indexLabel }: { data: ReachBandsResponse; view: string; areaNoun: string; indexLabel: string }) {
  const { country, region, urbanRural, pack } = useFilters()
  const [params, setParams] = useSearchParams()
  const allCells = params.get('cells') === 'all'
  const toggleCells = () => { const next = new URLSearchParams(params); if (allCells) next.delete('cells'); else next.set('cells', 'all'); setParams(next) }
  const tableParams = new URLSearchParams(params); tableParams.set('view', 'deprivation'); tableParams.set('cells', 'all')
  const travelParams = new URLSearchParams(params); travelParams.set('view', 'travel-time')
  const context = [country, region, urbanRural, pack || 'current']
  const linked = data.people_by_band_decile.filter(row => row.imd_decile >= 1 && row.imd_decile <= 10)
  const unlinked = data.people_by_band_decile.filter(row => row.imd_decile < 1 || row.imd_decile > 10)
  const worst = data.band_totals.length ? data.band_totals.filter(row => row.band <= 2).reduce((total, row) => total + row.people, 0) : undefined
  const exportCells = () => downloadReachCsv('aequitas-reach-band-deciles.csv', ['country', 'region', 'area', 'network', 'band', 'deprivation_decile', 'people', 'areas'], data.people_by_band_decile.map(row => [...context, row.band, row.imd_decile, row.people, row.n_areas]))
  const exportRegions = () => downloadReachCsv('aequitas-reach-regional-data.csv', ['country', 'region', 'area', 'network', 'area_code', 'area_name', data.map.metric_label ?? 'value', 'value'], data.map.data.map(row => [...context, row.area_code, row.area_name, data.map.metric_label ?? '', row.value]))
  if (view === 'deprivation') return <>
    <section className='app-panel'><h2>Population by reach band and {indexLabel} decile</h2><p>People in each reach band and deprivation decile. Decile 1 = most deprived within this country.</p>
      {linked.length ? <ReachHeatmap rows={linked} indexLabel={indexLabel} /> : <p className='reach-notice'>No linked deprivation observations for this scope.</p>}
      {unlinked.length > 0 && <p>{format(unlinked.reduce((sum, row) => sum + row.people, 0))} people have no linked deprivation decile. They remain in the download.</p>}
    </section>
    <section className='app-panel mt-3'><div className='reach-section-heading'><div><h2>All cells: people and {areaNoun}</h2><p>Population and area counts for every stored band × decile observation.</p></div><button type='button' className='app-panel-button' data-testid='band-decile-toggle' aria-expanded={allCells} onClick={toggleCells}>{allCells ? 'Hide all cells' : 'All cells'}</button></div>
      {allCells && <div className='reach-table-scroll'><table aria-label='All reach band and deprivation cells' data-testid='band-decile-table'><thead><tr><th>Band</th><th>{indexLabel} decile</th><th>People</th><th>{areaNoun}</th></tr></thead><tbody>{data.people_by_band_decile.map(row => <tr key={`${row.band}-${row.imd_decile}`}><td>{row.band}</td><td>{row.imd_decile >= 1 && row.imd_decile <= 10 ? row.imd_decile : 'Unlinked'}</td><td>{format(row.people)}</td><td>{format(row.n_areas)}</td></tr>)}</tbody></table></div>}
      <p>Absent cells are unavailable; observed zero counts remain zero. Band 1 is lowest, band 6 highest.</p>
    </section>
    <div className='reach-source-footer'><p>Deprivation: {indexLabel} · in-country ranks only.<br />Classification: {data.mode === 'mixed' ? 'mixed travel-time and service bands' : data.mode.replace('_', ' ')}</p><button type='button' className='app-panel-button' onClick={exportCells} disabled={!data.people_by_band_decile.length}>Download detailed table</button></div>
  </>
  return <>
    <div className='reach-mobile-bands'>
      <nav className='reach-mobile-view-tabs' aria-label='Mobile band views'><span aria-current='page'>Summary</span><Link to={{ search: `?${tableParams}` }}>Table</Link></nav>
      <section className='app-panel'><h2>People in lowest two reach bands</h2><p>{data.mode === 'mixed' ? 'Mixed service / travel-time methods in this pack' : 'Stored reach classification for this pack'}</p><strong className='reach-mobile-percentage'>{data.pct_worst_two == null ? '—' : `${data.pct_worst_two.toFixed(1)}%`}</strong><p className='reach-mobile-people'>{format(worst)} people</p></section>
      <section className='app-panel'><h2>{data.mode === 'travel_time' ? 'Travel-time band meaning' : 'Service-band meaning'}</h2>{data.band_totals.map(row => <div className='reach-mobile-band-row' key={row.band}><strong>Band {row.band}</strong><span>{row.label.replace(/^\d\s*[—–-]\s*/, '')}</span></div>)}<details><summary>Classification methods</summary><p>{data.formula}</p></details></section>
      <section className='app-panel'><h2>Travel times to key destinations</h2><p>Computed destination counts only, with geographic coverage shown separately.</p><Link className='app-panel-button mt-3' to={{ search: `?${travelParams}` }}>Travel time analysis</Link></section>
    </div>
    <div className='reach-desktop-bands'>
    <div className='reach-stat-cards'>
      <section className='app-panel'><h2>People in lowest two bands</h2><strong>{format(worst)}</strong><p>{data.pct_worst_two != null ? `${data.pct_worst_two.toFixed(1)}% of the classified population` : 'Population share unavailable'}</p></section>
      <section className='app-panel'><h2>Total {areaNoun}</h2><strong>{format(data.n_areas)}</strong><p>Areas assigned a reach band</p></section>
      <section className='app-panel'><h2>Reach classification</h2><strong className='reach-classification'>{data.mode === 'mixed' ? 'Mixed classification' : data.mode === 'travel_time' ? 'Travel-time bands' : 'Service bands'}</strong><p>{data.mode === 'mixed' ? data.n_travel_time == null ? 'Travel-time and service classifications coexist.' : `${data.n_travel_time.toLocaleString('en-GB')} travel-time areas; other areas use service bands.` : 'Uses the stored classification for this scope.'}</p></section>
      <section className='app-panel'><h2>Band meaning</h2><p>1 = lowest reach<br />6 = highest reach</p><p>Not official PTAL.</p></section>
    </div>
    <div className='reach-bands-layout'>
      <section className='app-panel'><h2>{data.map.metric_label ?? 'Reach bands by area'}</h2><p>{data.map.metric_label?.includes('%') ? 'Percent of people in access / service classification bands 1–2' : 'Stored reach classification for the selected geography'}</p>
        {data.map.data.length ? <Suspense fallback={<p role='status'>Loading band map…</p>}><ChoroplethMap className='reach-map' chartData={{ ...data.map, ...(data.map.metric_label?.includes('%') ? { color_mode: 'reach_rate' } : {}), type: 'choropleth', title: 'Reach classification by area' }} /></Suspense> : <p className='reach-notice' data-testid='map-unavailable'>No map areas match this filter — the band totals still apply.</p>}
        {data.map.metric_label?.includes('%') && <div className='reach-map-legend' aria-label='Percent of people in bands 1–2'><span>0%</span><i /><span>50%+</span><small>People in bands 1–2 · lower is better</small></div>}
      </section>
      <aside className='app-panel'><h2>About this map</h2><p data-testid='reach-narrative'>{data.narrative}</p><p>{data.unmatched_note}</p>
        <div className='reach-method'><h3>Classification and sources</h3><p>The national England layer shows the share of people in bands 1–2. Regional layers retain their stored aggregation.</p><details><summary>How bands are assigned</summary><p>{data.formula}</p>{data.mode === 'mixed' && <p>Travel-time bands use actual 15/30/45-minute destination counts. These are not all service classifications.</p>}<p>{data.hansen_note}</p><p>{data.map_aggregation}</p></details></div>
        <button type='button' className='app-panel-button mt-3' disabled={!data.map.data.length} onClick={exportRegions}>Download regional data</button>
      </aside>
    </div>
    <section className='app-panel mt-3'><h2>People by reach band</h2><div className='reach-band-totals'>{data.band_totals.map(row => <div key={row.band}><span>Band {row.band}</span><strong>{format(row.people)}</strong><small>{format(row.n_areas)} {areaNoun}</small></div>)}</div></section>
    </div>
  </>
}
