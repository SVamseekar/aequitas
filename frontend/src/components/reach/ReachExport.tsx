import { useQuery } from '@tanstack/react-query'
import { useSearchParams } from 'react-router'
import { fetchJson } from '@/api/client'
import { useFilters } from '@/api/hooks'
import type { ReachBandsResponse, ReachResponse, ScoreResponse } from '@/api/types'
import { reachSelection } from '@/lib/reach'
import { COUNTRIES, regionsForCountry, AREA_TYPES } from '@/lib/constants'
import { ReachControls } from './ReachControls'

interface ResearchPack {
  place: string
  filter: { country: string; region: string; urban_rural: string }
  vintages: Record<string, string>
  score: ScoreResponse
  bands: ReachBandsResponse
  reach: ReachResponse
  caveats: string[]
}
export function ReachExport() {
  const { country, region, urbanRural, pack } = useFilters()
  const [params] = useSearchParams()
  const { dest, cutoff } = reachSelection(params)
  const countryName = COUNTRIES.find(item => item.code === country)?.name ?? country
  const regionName = regionsForCountry(country).find(item => item.code === region)?.name ?? region
  const areaName = AREA_TYPES.find(item => item.code === urbanRural)?.name ?? urbanRural
  const context = { country, region, urban_rural: urbanRural, dest_type: dest.id, cutoff: String(cutoff), ...(pack ? { pack } : {}) }
  const query = useQuery({ queryKey: ['research-pack', context], queryFn: () => fetchJson<ResearchPack>('/export/pack.json', context), enabled: country !== 'netherlands', staleTime: Infinity, retry: false })
  const search = new URLSearchParams(context)
  return <>
    <ReachControls />
    <div className='reach-export-layout'>
      <section className='app-panel'><h2>Configure research export</h2><p>Review the selected geography, source vintages and calculated evidence before downloading.</p>
        <dl className='reach-export-scope'><div><dt>Country</dt><dd>{countryName}</dd></div><div><dt>Region</dt><dd>{regionName}</dd></div><div><dt>Area</dt><dd>{areaName}</dd></div><div><dt>Network</dt><dd>{pack || 'Current registered network'}</dd></div><div><dt>Destination</dt><dd>{dest.unit}</dd></div><div><dt>Cutoff</dt><dd>{cutoff} minutes</dd></div></dl>
        <p>Use the context controls above to change geography and network. Current-only caches cannot be exported under a historical date.</p>
        {country === 'netherlands' ? <p className='reach-notice'>A Netherlands research pack is not available yet.</p> : query.isPending ? <p role='status'>Loading actual pack contents…</p> : query.error ? <div role='alert'><p>Research pack could not be loaded. Select the current network and a valid geography.</p><button type='button' className='app-panel-button' onClick={() => void query.refetch()}>Retry research pack</button></div> : <details className='reach-method'><summary>Source vintages</summary><dl className='reach-vintages'>{Object.entries(query.data.vintages).map(([key, value]) => <div key={key}><dt>{key.replaceAll('_', ' ')}</dt><dd>{value}</dd></div>)}</dl></details>}
      </section>
      <aside className='app-panel'><h2>Export options</h2><p>A research data file or printable HTML report. Contents reflect the evidence below.</p>
        {query.data && <div className='reach-export-buttons'><a className='app-panel-button reach-primary' href={`/api/export/pack.csv?${search}`} data-testid='pack-csv'>Download CSV</a><a className='app-panel-button' href={`/api/export/pack.html?${search}`} data-testid='pack-html'>Download printable HTML</a></div>}
        <div className='reach-method'><h3>Export includes</h3><ul><li>Selected geography and destination configuration</li><li>In-country score components</li><li>Band totals and deprivation cells</li><li>Computed travel-time distribution where available</li><li>Source vintages and method caveats</li></ul></div><p>Research pack, not a statutory submission. Missing calculations stay unavailable.</p>
      </aside>
    </div>
    {query.data && <section className='app-panel mt-3'><h2>Preview — actual report contents</h2><p>{query.data.place}</p><div className='reach-preview-cards'><article><h3>Score and stop proximity</h3><strong>{query.data.score.score ?? '—'}</strong><p>In-country score. 400 m coverage is stop proximity, not travel time.</p></article><article><h3>Reach bands</h3><strong>{query.data.bands.empty ? 'Unavailable' : query.data.bands.n_areas.toLocaleString('en-GB')}</strong><p>Classified areas, with band totals and linked deprivation cells.</p></article><article><h3>Travel-time destinations</h3><strong>{query.data.reach.available ? query.data.reach.median?.toLocaleString('en-GB') ?? '—' : 'Unavailable'}</strong><p>{dest.unit} · median within {cutoff} minutes.</p></article><article><h3>Methodology and sources</h3><p>{query.data.caveats.join(' ')}</p></article></div></section>}
  </>
}
