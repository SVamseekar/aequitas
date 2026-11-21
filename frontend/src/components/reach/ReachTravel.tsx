import { useQueries } from '@tanstack/react-query'
import { useSearchParams } from 'react-router'
import { fetchJson } from '@/api/client'
import { useFilters } from '@/api/hooks'
import type { ReachResponse } from '@/api/types'
import { regionsForCountry } from '@/lib/constants'
import { REACH_CUTOFFS, REACH_DESTINATIONS, reachSelection } from '@/lib/reach'
import { ReachControls } from './ReachControls'
import { ReachHistogram } from './ReachPlot'

export function ReachTravel({ areaNoun }: { areaNoun: string }) {
  const { country, region, urbanRural, pack } = useFilters()
  const [params, setParams] = useSearchParams()
  const { dest, cutoff } = reachSelection(params)
  const combinations = REACH_DESTINATIONS.flatMap(destination => REACH_CUTOFFS.map(minutes => ({ destination, minutes })))
  const queries = useQueries({ queries: combinations.map(({ destination, minutes }) => ({
    queryKey: ['reach', country, region, urbanRural, destination.id, minutes, pack],
    queryFn: () => fetchJson<ReachResponse>('/reach', { country, region, urban_rural: urbanRural, dest_type: destination.id, cutoff: String(minutes), ...(pack ? { pack } : {}) }),
    staleTime: Infinity, retry: false,
  })) })
  const selectedIndex = combinations.findIndex(item => item.destination.id === dest.id && item.minutes === cutoff)
  const selected = queries[selectedIndex]
  const select = (destination: string, minutes: number) => { const next = new URLSearchParams(params); next.set('dest', destination); next.set('cutoff', String(minutes)); setParams(next) }
  const geographies = selected.data?.geographies.map(code => regionsForCountry(country).find(item => item.code === code)?.name ?? code)
  return <>
    <ReachControls />
    <div className='reach-travel-layout'>
      <section className='app-panel'><h2>Availability by destination and travel time</h2><p>Median reachable destination count per origin, including zero-count origins.</p>
        <div className='reach-table-scroll'><table aria-label='Destination availability' className='reach-matrix'><thead><tr><th>Destination</th>{REACH_CUTOFFS.map(minutes => <th key={minutes}>{minutes} minutes</th>)}</tr></thead><tbody>{REACH_DESTINATIONS.map((destination, i) => <tr key={destination.id}><th scope='row'>{destination.label}</th>{REACH_CUTOFFS.map((minutes, j) => {
          const query = queries[i * 3 + j], data = query.data
          return <td key={minutes}><button type='button' aria-label={`${destination.label} · ${minutes} minutes`} aria-pressed={dest.id === destination.id && cutoff === minutes} onClick={() => select(destination.id, minutes)}>
            <strong>{query.isPending ? 'Loading…' : query.error ? 'Could not load' : data?.available && data.median !== null ? data.median.toLocaleString('en-GB', { maximumFractionDigits: 1 }) : 'Unavailable'}</strong>
            {data?.available && <small>n = {data.n_areas.toLocaleString('en-GB')}</small>}
          </button></td>
        })}</tr>)}</tbody></table></div>
        <p>Employment points are a proxy, not total accessible jobs. GP and school counts use their own destination inventories.</p>
        <div className='reach-method'><h3>Geographic coverage</h3><p>{geographies?.length ? `Computed geographies: ${geographies.join(', ')}.` : 'No computed geographies are available for this configuration.'} A national selection describes computed origins only.</p><p>Stop proximity at 400 m is separate from walk + public transport travel times. No isochrone is inferred from these counts.</p></div>
      </section>
      <section className='app-panel'><h2>Selected configuration</h2><p>{dest.unit} within {cutoff} minutes</p>
        {selected.isPending ? <p role='status'>Loading selected travel times…</p> : selected.error ? <div role='alert'><p>Travel times could not be loaded for this filter. Reach uses the current network only; historical caches are unavailable.</p><button type='button' className='app-panel-button' onClick={() => { queries.forEach(query => { if (query.error) void query.refetch() }) }}>Retry travel times</button></div> : selected.data?.available ? <>
          <p className='reach-big-number'>{selected.data.median?.toLocaleString('en-GB', { maximumFractionDigits: 1 }) ?? '—'}<small>median destination count</small></p>
          <h3>Covered origins: {selected.data.n_areas.toLocaleString('en-GB')} {areaNoun}</h3>
          <p>All computed origins in the selected scope, including those with no reachable destinations.</p>
          <div className='reach-method'><h3>Distribution across {areaNoun}</h3><ReachHistogram rows={selected.data.histogram} unit={dest.unit} areaNoun={areaNoun} /></div>
        </> : <p className='reach-notice'>{selected.data?.note ?? 'This configuration is unavailable.'}</p>}
      </section>
    </div>
  </>
}
