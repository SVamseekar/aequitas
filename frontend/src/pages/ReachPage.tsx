import { Link, useSearchParams } from 'react-router'
import { useFilters, useReachBands } from '@/api/hooks'
import { AREA_TYPES, COUNTRIES, regionsForCountry } from '@/lib/constants'
import { filterSentence } from '@/lib/scoreFormat'
import { isLondonRural } from '@/lib/uniqueExhibits'
import { BriefingActions } from '@/components/shared/BriefingActions'
import { ReachBands } from '@/components/reach/ReachBands'
import { ReachTravel } from '@/components/reach/ReachTravel'
import { ReachExport } from '@/components/reach/ReachExport'

const views = [{ id: 'bands', label: 'Bands' }, { id: 'deprivation', label: 'Deprivation' }, { id: 'travel-time', label: 'Travel time' }, { id: 'export', label: 'Export' }]
export default function ReachPage() {
  const { country, region, urbanRural, pack } = useFilters()
  const [params] = useSearchParams()
  const view = views.find(item => item.id === params.get('view')) ?? views[0]
  const countryName = COUNTRIES.find(item => item.code === country)?.name ?? country
  const regionName = regionsForCountry(country).find(item => item.code === region)?.name ?? region
  const areaName = AREA_TYPES.find(item => item.code === urbanRural)?.name ?? urbanRural
  const place = filterSentence(regionName, areaName)
  const areaNoun = country === 'ireland' ? 'Small Areas' : country === 'netherlands' ? 'buurten' : country === 'france' ? 'IRIS' : 'LSOAs'
  const indexLabel = country === 'ireland' ? 'HP' : country === 'netherlands' ? 'SES-WOA' : country === 'france' ? 'F-EDI' : 'IMD'
  const bandsQ = useReachBands(region, urbanRural, country, pack)
  const exportParams = new URLSearchParams(params); exportParams.set('view', 'export')
  return <div className={`reach-page reach-view-${view.id}`} data-testid='reach-page'>
    <div className='reach-heading'><div><h1>Reach: {view.label === 'Travel time' ? 'travel time to key destinations' : view.label === 'Export' ? 'research export' : view.label}</h1><p>{countryName} · {place} · access / service classification</p></div><div className='flex gap-2'><BriefingActions /><Link className='app-panel-button reach-primary' to={{ search: `?${exportParams}` }}>Export briefing</Link></div></div>
    <nav className='evidence-tabs' aria-label='Reach views'>{views.map(item => { const next = new URLSearchParams(params); next.set('view', item.id); return <Link key={item.id} to={{ search: `?${next}` }} aria-current={view.id === item.id ? 'page' : undefined}>{item.label}</Link> })}</nav>
    <p className='reach-disclaimer'>Not official PTAL. Stop proximity, service bands and travel-time destination counts measure different things.</p>
    {isLondonRural(region, urbanRural) ? <p className='reach-notice'>London has no rural LSOAs under the official urban/rural classification — this filter is empty.</p> : view.id === 'travel-time' ? <ReachTravel areaNoun={areaNoun} /> : view.id === 'export' ? <ReachExport /> : bandsQ.isLoading ? <p className='app-panel' role='status'>Loading reach classifications…</p> : bandsQ.error ? <div className='app-panel' role='alert'><p>Bands could not be loaded. Select the current network and a valid geography. Historical band caches are unavailable.</p><button type='button' className='app-panel-button' onClick={() => void bandsQ.refetch()}>Retry reach bands</button></div> : bandsQ.data?.empty ? <p className='reach-notice'>{bandsQ.data.empty_reason}</p> : bandsQ.data ? <ReachBands key={`${country}-${region}-${urbanRural}-${pack}`} data={bandsQ.data} view={view.id} areaNoun={areaNoun} indexLabel={indexLabel} /> : null}
  </div>
}
