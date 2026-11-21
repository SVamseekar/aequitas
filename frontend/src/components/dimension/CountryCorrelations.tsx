import { ChartInsights } from './ChartInsights'
import { useSearchParams } from 'react-router'
import { useFilters, useSections } from '@/api/hooks'
import type { SectionItem } from '@/api/types'
import { ChartRenderer } from '@/components/charts/ChartRenderer'
import { COUNTRY_BRIEFS } from '@/lib/briefingCatalog'
import { sectionPresentation } from '@/lib/sectionPresentation'
import { sectionTitle, statLabel } from '@/lib/constants'
import { SectionCard } from './SectionCard'

export function CountryCorrelations({ sections }: { sections: SectionItem[] }) {
  const { country, region, urbanRural, pack, mode, setMode } = useFilters()
  const [params, setParams] = useSearchParams()
  const originQuery = useSections('equity', region, urbanRural, country, pack, mode)
  const origin = originQuery.data?.sections.find(section => section.section_id === 'f3_ethnic_access')
  const heatmap = sections.find(section => section.section_id === 'd7_deprivation_urban_rural')
  const brief = COUNTRY_BRIEFS.find(item => item.code === country)
  const index = country === 'ireland' ? 'HP' : country === 'netherlands' ? 'SES-WOA' : 'F-EDI'
  const originLabel = country === 'ireland' ? 'Ethnicity' : 'Origin share'
  const requested = params.get('view')
  const extra = sections.find(section => section.section_id === requested && section !== heatmap)
  const current = requested === 'origin' || requested === 'sources' ? requested : extra ? 'more' : 'matrix'
  const setView = (view: string) => { const next = new URLSearchParams(params); next.set('view', view); next.delete('exhibit'); setParams(next) }
  const title = (section: SectionItem) => typeof section.stats.title === 'string' ? section.stats.title : sectionTitle(section.section_id, country) ?? section.section_id.replaceAll('_', ' ')
  const facts = Object.entries(heatmap?.stats ?? {}).filter(([key, value]) => typeof value === 'number' && ['n_with_ses', 'n_without_ses', 'n_with_fedi', 'n_without_fedi'].includes(key))
  const unavailableOrigin = !origin || origin.suppressed || Boolean(origin.stats.omit)
  return <div className='country-correlations'>
    <nav className='evidence-tabs' aria-label='Country correlation views'>{[
      ['matrix', `${index} × urban/rural`], ['origin', originLabel], ['sources', 'Notes & sources'], ['more', 'More evidence'],
    ].map(([id, label]) => <button type='button' key={id} aria-pressed={current === id} onClick={() => setView(id === 'matrix' ? 'd7_deprivation_urban_rural' : id === 'more' ? sections.find(section => section !== heatmap)?.section_id ?? 'sources' : id)}>{label}</button>)}</nav>
    {current === 'origin' ? <>
      <section className='app-panel mb-4'><h2>{originLabel} and access</h2><p>{country === 'netherlands' ? 'CBS herkomst buiten Europa is an origin measure, rather than England ethnicity.' : country === 'france' ? 'INSEE immigrés share describes origin, rather than ethnicity.' : 'Small Area ethnicity evidence is displayed only when it exists in the selected Irish pack.'} Associations at area level do not establish causation.</p></section>
      {originQuery.isPending ? <p role='status'>Loading selected-country evidence…</p> : originQuery.error ? <div role='alert'><p>Origin evidence could not be loaded.</p><button className='app-panel-button' type='button' onClick={() => void originQuery.refetch()}>Retry origin evidence</button></div> : unavailableOrigin ? <p className='app-panel'>{typeof origin?.stats.reason === 'string' ? origin.stats.reason : 'No origin or ethnicity observations are stored for this selected country and pack.'}</p> : <SectionCard section={origin} featured />}
    </> : current === 'sources' ? <section className='app-panel'><h2>Notes and sources — {brief?.name}</h2><dl className='country-source-facts'>{[['Transport', brief?.network], ['Population and geography', brief?.geography], ['Deprivation', brief?.deprivation], ['Network date', pack || 'Current registered network']].map(([label,value]) => <div key={label}><dt>{label}</dt><dd>{value ?? 'Unavailable'}</dd></div>)}</dl><p>Coverage is the share of population within 400 m of a stop. Geography and deprivation vintages stay separate from network dates. Deciles stay within {brief?.name}; do not compare indices across countries.</p>{country === 'france' && <p>Metropolitan France only; overseas coverage is not inferred.</p>}</section>
      : current === 'more' ? <><label className='country-exhibit-control'>Additional warehouse exhibit<select aria-label='Additional warehouse exhibit' value={extra?.section_id ?? ''} onChange={event => setView(event.target.value)}>{sections.filter(section => section !== heatmap).map(section => <option key={section.section_id} value={section.section_id}>{title(section)}</option>)}</select></label>{extra && <SectionCard section={extra} featured />}</>
        : <>
          <div className='country-correlation-layout'><section className='app-panel'><h2>Population coverage within 400 m of stops</h2><p>Share of population by {index} decile and the stored urban/rural grouping.</p>{heatmap && !heatmap.suppressed && !heatmap.stats.insufficient_data ? <ChartRenderer chartData={sectionPresentation(heatmap, country).chartData} /> : <p>No coverage cells are stored for this filter.</p>}<p>Blank cells are unavailable. Observed zero remains zero.</p></section>
            <aside>{country === 'netherlands' && <section className='app-panel'><h2>Service type</h2><div className='country-mode-controls'>{[['bus','Bus'],['all','All public transport']].map(([value,label]) => <button type='button' key={value} aria-pressed={mode === value} onClick={() => setMode(value)}>{label}</button>)}</div></section>}
              <section className='app-panel'>{heatmap&&<ChartInsights section={heatmap} country={country} />}<details className='country-view-scope'><summary>View scope</summary><dl className='country-source-facts'><div><dt>Coverage measure</dt><dd>400 m population coverage</dd></div><div><dt>Geography</dt><dd>Stored urban/rural grouping</dd></div><div><dt>Index</dt><dd>{brief?.deprivation}</dd></div></dl></details></section>
              {facts.length > 0 && <section className='app-panel'><h2>Index observations</h2><dl className='country-source-facts'>{facts.map(([key,value]) => <div key={key}><dt>{statLabel(key,country)}</dt><dd>{Number(value).toLocaleString('en-GB')}</dd></div>)}</dl></section>}
              {country==='ireland'&&<section className='app-panel'><h2>{originLabel} evidence</h2><p>{originQuery.isPending ? 'Checking this pack…' : unavailableOrigin ? 'Unavailable in this selected pack.' : 'Stored observations available in this pack.'}</p><button className='app-text-link' type='button' onClick={() => setView('origin')}>Open {originLabel.toLowerCase()}</button></section>}
            </aside></div>
          <div className='country-correlation-notes'><section className='app-panel'><h2>About this view</h2><p>Higher population coverage is shown in greener cells. {index} deciles belong to {brief?.name}; the indices are not comparable across countries.</p></section><section className='app-panel'><h2>Data sources</h2><p>{brief?.network} · {brief?.geography} · {brief?.deprivation}</p></section></div>
        </>}
  </div>
}
