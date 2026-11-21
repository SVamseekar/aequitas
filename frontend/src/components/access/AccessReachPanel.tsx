import { ChartInsights } from '@/components/dimension/ChartInsights'
import { Link, useSearchParams } from 'react-router'
import { useFilters, useReach } from '@/api/hooks'
import { AREA_TYPES, regionsForCountry } from '@/lib/constants'
import { appPath } from '@/lib/appRoutes'
import { filterSentence } from '@/lib/scoreFormat'
import { reachSelection } from '@/lib/reach'
import { ReachControls } from '@/components/reach/ReachControls'
import { ReachHistogram } from '@/components/reach/ReachPlot'
import { EvidenceState } from '@/components/shared/EvidenceState'

export function AccessReachPanel() {
  const { country, region, urbanRural, pack } = useFilters()
  const [params] = useSearchParams()
  const { dest, cutoff } = reachSelection(params)
  const query = useReach(region, urbanRural, dest.id, cutoff, country, pack)
  const data = query.data
  const regionName = regionsForCountry(country).find(item => item.code === region)?.name ?? region
  const areaName = AREA_TYPES.find(item => item.code === urbanRural)?.name ?? urbanRural
  const place = filterSentence(regionName, areaName)
  const areaNoun = country === 'ireland' ? 'Small Areas' : country === 'netherlands' ? 'buurten' : country === 'france' ? 'IRIS' : 'LSOAs'
  const bands = new URLSearchParams(params); bands.set('view', 'bands')
  const reach = new URLSearchParams(params); reach.set('view', 'travel-time')
  const heading = dest.id === 'jobs' ? 'Employment destination points' : `${dest.label} destination points`
  if (!query.isPending && !query.error && !data?.available) return <div className='access-travel'>
    <EvidenceState kind='unavailable' title='Not available in this pack' description={data?.note ?? 'No computed travel-time observations for this country and filter.'} action={<Link className='app-panel-button' to={{ pathname: appPath(country, 'reach'), search: `?${bands}` }}>View service bands</Link>} />
    <details className='app-panel mt-4'><summary>Change destination or travel-time cutoff</summary><ReachControls segmentedCutoff /></details>
  </div>
  return <div className='access-travel'>
    <section className='app-panel'><h2>Travel time to key destinations</h2><p>Counts of destination points by origin area; R5 walk + bus. Stop proximity at 400 m is a separate measure.</p><ReachControls segmentedCutoff /></section>
    {query.isPending ? <p className='app-panel mt-4' role='status'>Loading selected travel times…</p> : query.error ? <div className='app-panel mt-4' role='alert'><h2>Travel times unavailable for this request</h2><p>Travel-time caches use the current network. Historical results are unavailable; no current counts are shown as dated results.</p><button type='button' className='app-panel-button' onClick={() => void query.refetch()}>Retry travel times</button></div> : <div className='access-travel-layout'>
      <section className='app-panel'><h2>{heading}</h2><p>Reachable destination points for {place}, within {cutoff} minutes.</p>{data && data.histogram.length > 0 ? <ReachHistogram rows={data.histogram} unit={`${dest.unit} within ${cutoff} minutes`} areaNoun={areaNoun} /> : <p>No histogram observations are stored for this configuration.</p>}</section>
      <aside><section className='app-panel'><h2>Destination points (median origin)</h2><strong>{data?.available && typeof data.median === 'number' && Number.isFinite(data.median) ? data.median.toLocaleString('en-GB', { maximumFractionDigits: 1 }) : '—'}</strong><p>{dest.unit}. These are destination counts, rather than total accessible jobs or Hansen scores.</p></section>
        <section className='app-panel'><h2>Areas covered by travel-time calculation</h2><strong>{data?.available ? data.n_areas.toLocaleString('en-GB') : '—'}</strong><p>{data?.available ? `${areaNoun} in the computed scope, including origins with zero reachable destinations.` : 'Not available in this pack.'}</p></section>
        <section className='app-panel'><ChartInsights items={data?.available?[...(typeof data.median==='number'&&Number.isFinite(data.median)?[`The median computed origin reaches **${data.median.toLocaleString('en-GB')} ${dest.unit}** within **${cutoff} minutes**.`]:[]),`The calculation covers **${data.n_areas.toLocaleString('en-GB')} ${areaNoun}**, including origins with zero reachable destinations.`]:[]} /><h2>Method and scope</h2><p>Origin-centroid travel times use the stored R5 walk + public transport computation. A national filter describes computed origins only, and does not imply nationwide calculation.</p><p>Employment points may be an area-centroid proxy. No isochrone or uncomputed journey time is inferred.</p><Link className='app-text-link' to={{ pathname: appPath(country, 'reach'), search: `?${reach}` }}>Open all nine configurations in Reach</Link></section>
      </aside>
    </div>}
  </div>
}
