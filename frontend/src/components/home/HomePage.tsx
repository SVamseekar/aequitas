import { lazy, Suspense,useState } from 'react'
import { Link, useNavigate, useSearchParams } from 'react-router'
import { ChevronRight } from 'lucide-react'
import { useFilters, useMapLayer, useOverview, useScore, useSections } from '@/api/hooks'
import { AREA_TYPES, COUNTRIES, regionsForCountry } from '@/lib/constants'
import { appPath, withSearch } from '@/lib/appRoutes'
import { filterSentence } from '@/lib/scoreFormat'
import { OverviewScore } from './OverviewScore'
import { BriefingActions } from '@/components/shared/BriefingActions'
import { coveragePresentation } from '@/lib/coverage'
import {ResearchExport} from './ResearchExport'
import {ProvenancePanel} from '@/components/dimension/ProvenancePanel'
import {EvidenceState} from '@/components/shared/EvidenceState'

const ChoroplethMap = lazy(() => import('@/components/charts/ChoroplethMap'))
const fixed = (value: unknown, digits = 1, suffix = '') => typeof value === 'number' && Number.isFinite(value) ? `${value.toFixed(digits)}${suffix}` : '—'

export function HomePage() {
  const { country, region, urbanRural, pack, mode } = useFilters()
  const countryName = COUNTRIES.find(c => c.code === country)?.name ?? country
  const regionName = regionsForCountry(country).find(r => r.code === region)?.name ?? region
  const areaName = AREA_TYPES.find(a => a.code === urbanRural)?.name ?? urbanRural
  const overview = useOverview(region, urbanRural, country, pack, mode)
  const score = useScore(region, urbanRural, country, pack, mode)
  const equity = useSections('equity', region, urbanRural, country, pack, mode)
  const service = useSections('service_quality', region, urbanRural, country, pack, mode)
  const map = useMapLayer(region, urbanRural, country, pack, mode, 'coverage')
  const [params] = useSearchParams()
  const [provenance,setProvenance]=useState(false)
  const navigate = useNavigate()
  const place = filterSentence(regionName, areaName)
  const coverageMeaning = coveragePresentation(country)
  const expanded = params.get('view') === 'score'
  const link = (slug: string) => { const next=new URLSearchParams(params);next.delete('view');return withSearch(appPath(country, slug), next.toString()) }
  const londonRural = region === 'E12000007' && urbanRural === 'rural'
  const packMiss = (overview.error as { status?: number } | null)?.status === 404 || (map.error as { status?: number } | null)?.status === 404

  if(params.get('view')==='export')return <ResearchExport key={`${country}:${region}:${urbanRural}:${pack}:${mode}`} />
  if (packMiss) return <EvidenceState kind='unavailable' title='Not available in this pack' description={`Unknown pack ${pack || 'date'} for ${countryName}. This checkout does not silently show the current briefing.`} />
  if (overview.error) return <EvidenceState kind='error' title='Could not load evidence' description='Your country and selected filters are retained.' retry={()=>{void overview.refetch();void map.refetch()}} />
  if (overview.isLoading || map.isLoading) return <div data-testid='home-loading'><h1 className='mb-4'>Loading {countryName} briefing…</h1><div className='h-[520px] app-glass animate-pulse' /></div>

  const components = score.data?.components ?? []
  const component = (id: string) => components.find(c => c.id === id)?.value
  const coverage = component('pop_within_400m')
  const quality = component('weekday_frequency')
  const evening = component('evening_served')
  const gini = equity.data?.sections.find(s => s.section_id === 'f1_gini')?.stats?.gini
  const eveningPct = evening == null ? null : (1 - evening) * 100
  const sunday = service.data?.sections.find(s => s.section_id === 'b3_weekend_penalty')?.stats?.pct_sunday_desert
  const mapTitle = `Transport coverage across ${region === 'all' ? countryName : regionName}`
  const exportParams=new URLSearchParams(params);exportParams.set('view','export')
  const exploreParams=new URLSearchParams(params);exploreParams.delete('view')
  if(londonRural)return <EvidenceState kind='empty' title='No areas match this filter' description='London has no rural LSOAs under the official urban/rural classification.' action={<Link className='app-panel-button' to={{search:`?${new URLSearchParams({...Object.fromEntries(params),urban_rural:'all'})}`}}>Reset area filter</Link>} />

  return (
    <div className='app-overview-page'>
      <div className='app-page-heading'>
        <div><h1>Where the bus fails people</h1><p>{place} · official timetables × official need</p></div>
        <div className='flex gap-3 flex-wrap'><BriefingActions /><Link className='app-panel-button' to={{search:`?${exportParams}`}}>Export research pack</Link></div>
      </div>
      <nav className='evidence-tabs overview-explore-tabs' aria-label='Explore briefing'>
        {[['Overview',''],['Equity','equity'],['Access','access'],['Service','service'],['Network','network'],['Correlations','correlations']].map(([label,slug])=><Link key={label} to={withSearch(appPath(country,slug),exploreParams.toString())} aria-current={slug===''?'page':undefined}>{label}</Link>)}
      </nav>
      <div className='app-overview-grid'>
        <div className='app-overview-main'>
          <dl className='app-metric-strip'>
            {[
              [coverageMeaning.shortLabel, coverage == null ? '—' : fixed(coverage * 100, 1, '%')],
              ['Mean service quality', quality == null ? '—' : `${fixed(quality * 100)} / 100`],
              ['Service inequality Gini', fixed(gini, 4)],
              ['Evening isolated', fixed(eveningPct, 1, '%')],
            ].map(([label, value]) => <div className='app-panel' key={label}><dt>{label}</dt><dd>{label==='Service inequality Gini'?<button type='button' className='overview-evidence-value' onClick={()=>setProvenance(true)} aria-label='Show Gini evidence and calculation'>{value}</button>:value}</dd></div>)}
          </dl>
          {expanded ? <OverviewScore expanded fallbackScore={overview.data?.score ?? null} /> : (
            <section className='app-panel app-map-panel'>
              <div className='overview-map-heading'><div><h2>{mapTitle}</h2><p className='overview-map-description' title={coverageMeaning.definition}>{country==='england'?'Area share with a non-zero access score':'Population within 400 m of a stop'}, by {country === 'ireland' ? 'county' : country === 'netherlands' ? 'province' : 'region'}.</p></div>
                <div className='overview-map-key' aria-label='Coverage legend'><strong>{coverageMeaning.shortLabel}</strong><i aria-hidden='true' /><div><span>Lower coverage</span><span>Higher coverage</span></div><small>Grey: unavailable</small></div>
              </div>
              {londonRural ? <p className='py-8'>London has no rural LSOAs under the official urban/rural classification — this filter is empty.</p>
                : map.error ? <p role='alert' className='py-8'>Map layer could not be loaded for this filter.</p>
                : map.data?.empty || !map.data?.data?.length ? <p className='py-8'>{map.data?.empty_reason ?? 'No map layer for this filter.'}</p>
                : <Suspense fallback={<div className='h-[520px] bg-muted animate-pulse' />}><ChoroplethMap chartData={{ type: 'choropleth', geography: country === 'ireland' ? 'ireland_county' : country === 'netherlands' ? 'netherlands_provincie' : country === 'france' ? 'france_region' : map.data.geography, metric_label: map.data.metric_label, data: map.data.data, title: mapTitle, color_mode: 'coverage' }} onAreaClick={code => { const next = new URLSearchParams(params); next.set('region', code); navigate(withSearch(appPath(country, 'access'), next.toString())) }} /></Suspense>}
            </section>
          )}
        </div>
        <aside className='app-overview-aside' aria-label='Briefing summary'>
          <OverviewScore fallbackScore={overview.data?.score ?? null} />
          {expanded?<OverviewScore details fallbackScore={overview.data?.score ?? null} />:<>
          <section className='app-panel'>
            <h2>What needs attention</h2>
            <div className='app-attention-item'><p><strong>{fixed(eveningPct, 1, '%')}</strong> of areas lack evening service</p><p>Service after 19:00 on a typical weekday.</p><Link to={link('service')} className='app-text-link'>View Service</Link></div>
            <div className='app-attention-item'><p><strong>{fixed(sunday, 1, '%')}</strong> of areas are Sunday deserts</p><p>Areas with no service on a typical Sunday.</p><Link to={link('access')} className='app-text-link'>View Access</Link></div>
          </section>
          <section className='app-panel'>
            <h2>Explore the evidence</h2>
            {[['Equity & deprivation', 'equity'], ['Access & coverage', 'access'], ['Service quality', 'service'], ['Network structure', 'network']].map(([label, slug]) => <Link className='app-evidence-link' key={slug} to={link(slug)}>{label}<ChevronRight size={16} /></Link>)}
          </section>
          <Link className='app-panel-button overview-open-access' to={link('access')}>Open Access <ChevronRight size={15} aria-hidden='true' /></Link>
          </>}
        </aside>
      </div>
      {provenance&&<ProvenancePanel metricId='gini_national' onClose={()=>setProvenance(false)} />}
      <details className='mt-5'><summary className='text-sm text-muted-foreground cursor-pointer'>Planning and observation tools</summary><div className='flex flex-wrap gap-5 mt-3 text-sm'>
        {[['Scenarios', 'scenarios'], ['Studio', 'studio'], ['Compare', 'compare'], ['Reach', 'reach'], ['Time', 'time'], ['Ops', 'ops']].map(([label, slug]) => <Link className='app-text-link' key={slug} to={link(slug)}>{label}</Link>)}
      </div></details>
      <p className='mt-5 text-xs text-muted-foreground'>Ranks stay inside {countryName}. {country === 'ireland' ? 'TFI GTFS · CSO Small Areas 2022 · Pobal HP 2022. Republic only.' : country === 'netherlands' ? 'OVapi GTFS · CBS buurten 2024 · SES-WOA 2023. Missing SES ranks are omitted.' : country === 'france' ? 'NAP GTFS · IGN IRIS · F-EDI 2021. Metropolitan France only.' : 'BODS GTFS · Census 2021 LSOAs · IMD 2025.'} Network date selected above; geography and deprivation dates stay separate.</p>
    </div>
  )
}
