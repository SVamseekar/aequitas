import { ChartInsights } from '@/components/dimension/ChartInsights'
import { useDestinations, useFilters } from '@/api/hooks'
import { filterSentence } from '@/lib/scoreFormat'
import { AREA_TYPES, COUNTRIES, regionsForCountry } from '@/lib/constants'

import { BriefcaseBusiness, Stethoscope, GraduationCap } from 'lucide-react'

const DEST = [{ id: 'jobs', label: 'Jobs' }, { id: 'gp', label: 'GP (general practice)' }, { id: 'school', label: 'School' }] as const
const count = (value: unknown) => typeof value === 'number' && Number.isFinite(value) ? value.toLocaleString('en-GB') : '—'
const share = (value: unknown) => typeof value === 'number' && Number.isFinite(value) ? `${(value * 100).toFixed(1)}%` : '—'

export function FacilityAccessPanel() {
  const { country, region, urbanRural } = useFilters()
  const query = useDestinations(country)
  const data = query.data
  const name = COUNTRIES.find(item => item.code === country)?.name ?? country
  const regionName = regionsForCountry(country).find(item => item.code === region)?.name ?? region
  const areaName = AREA_TYPES.find(item => item.code === urbanRural)?.name ?? urbanRural
  const facility = data?.facility_400m ?? {}
  return <div className='access-facilities'>
    <section className='app-panel'><h2>Access to key facilities</h2><p>Small-area centroids within 400 m of an official destination. This is separate from distance to a bus stop and from travel time.</p>
      <p className='access-inventory-scope'>Inventory scope: national — {name}. Selected context: {filterSentence(regionName, areaName)}. The region, area and network-date controls do not subset this inventory.</p>
      {query.isPending ? <p role='status'>Loading official destination inventory…</p> : query.error ? <div role='alert'><p>Official destination inventory could not be loaded.</p><button type='button' className='app-panel-button' onClick={() => void query.refetch()}>Retry destination inventory</button></div> : <>
        <div className='access-facility-cards'>{DEST.map(destination => {
          const row = facility[destination.id]
          const Icon = destination.id === 'jobs' ? BriefcaseBusiness : destination.id === 'gp' ? Stethoscope : GraduationCap
          return <article key={destination.id}><span className='access-facility-icon'><Icon size={24} aria-hidden='true' /></span><h3>{destination.id === 'jobs' ? country === 'england' ? 'Jobs (employment-centroid proxy)' : 'Jobs (destination inventory)' : destination.label}</h3><strong>{row?.available ? share(row.people_share) : '—'}</strong><p>{row?.available ? `${count(row.n_within_400m)} of ${count(row.n_areas)} areas` : 'No facility-proximity observations in this inventory'}</p>{row?.available && typeof row.people_share === 'number' && Number.isFinite(row.people_share) && row.people_share >= 0 && row.people_share <= 1 && <meter min={0} max={1} value={row.people_share} aria-label={`${destination.label} population proximity share`} />}{row?.note && <p className='access-proxy-note'>{row.note}</p>}</article>
        })}</div>
        {data?.note && <p>{data.note}</p>}
      </>}
    </section>
    <div className='access-facility-notes'><section className='app-panel'><ChartInsights items={DEST.flatMap(destination=>{const row=facility[destination.id];return row?.available&&typeof row.people_share==='number'&&Number.isFinite(row.people_share)?[`${destination.label}: **${(row.people_share*100).toFixed(1)}%** population proximity to this destination.`]:[]})} /><h2>What this shows</h2><p>Centroid proximity to official destinations, population-weighted where weights exist. This is not a walking route, bus-stop measure or travel time. Employment proxies may match their own origin. Missing source files or weights remain unavailable.</p></section>
      <section className='app-panel'><h2>Data sources and coverage</h2><div className='access-table-scroll'><table aria-label='Destination source inventory'><thead><tr><th>Facility</th><th>Stored source</th><th>Extract rows</th><th>Source vintage</th></tr></thead><tbody>{DEST.map(destination => { const row = data?.destinations[destination.id]; return <tr key={destination.id}><th scope='row'>{destination.label}</th><td>{row?.available ? row.source?.split('?')[0].split('#')[0] ?? 'Source name not supplied' : 'Unavailable'}</td><td>{row?.available ? count(row.rows) : '—'}</td><td>Not supplied</td></tr> })}</tbody></table></div><p>Network-date selection does not date this separate destination extract.</p>{data?.official_distances?.available && <p>Official CBS proximity table: {count(data.official_distances.rows)} buurten. Distances use kilometres; they are not public-transport travel times.</p>}</section>
    </div>
  </div>
}
