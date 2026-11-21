import { ChartInsights } from '@/components/dimension/ChartInsights'
import { Link, useSearchParams } from 'react-router'
import type { SectionItem } from '@/api/types'
import { useFilters } from '@/api/hooks'
import { ChartRenderer } from '@/components/charts/ChartRenderer'
import SelectedRegionsMap from '@/components/shared/SelectedRegionsMap'
import { COUNTRIES, regionsForCountry, sectionTitle } from '@/lib/constants'
import { appPath, withSearch } from '@/lib/appRoutes'

const finite = (value: unknown) => typeof value === 'number' && Number.isFinite(value) ? value : null
const text = (value: unknown) => typeof value === 'string' ? value : null

export function ScenarioOverview({ section }: { section: SectionItem }) {
  const { country, region } = useFilters()
  const [params] = useSearchParams()
  const source = section.stats.scenario
  const scenario = source && typeof source === 'object' && !Array.isArray(source) ? source as Record<string, unknown> : {}
  const title = text(section.stats.title) ?? text(scenario.name) ?? sectionTitle(section.section_id, country) ?? 'Stored scenario'
  const population = finite(scenario.population_affected)
  const cost = finite(scenario.estimated_annual_cost_m)
  const carbon = finite(scenario.co2_saving_t_yr)
  const currency = country === 'england' ? '£' : '€'
  const name = COUNTRIES.find(item => item.code === country)?.name ?? country
  const regionName = regionsForCountry(country).find(item => item.code === region)?.name ?? region
  const target = text(scenario.scope) ?? text(scenario.who) ?? 'Target definition unavailable'
  const proportion = section.chart_data.proportion
  const primary = section.section_id === 'ps1_freq_restoration' || section.section_id === 'ps2_evening_extension'
  const next = new URLSearchParams(params); next.delete('view'); next.delete('exhibit')
  const access = new URLSearchParams(next); access.set('view', 'a3_walking_distance')
  const values = [
    { label: 'Population affected', value: population, unit: 'people', prefix: '' },
    { label: 'Annual cost', value: cost, unit: 'm / year', prefix: currency },
    { label: 'CO₂ saved', value: carbon, unit: 'tonnes / year', prefix: '' },
  ]
  const populationPanel = <section className='app-panel scenario-population'><h2>Population affected</h2>{proportion && typeof proportion === 'object' && !Array.isArray(proportion) ? <ChartRenderer chartData={{ ...proportion, type: 'stacked_bar', height: 100, x_label: 'People in the stated population' }} /> : <p>No population-proportion breakdown is stored for this scope.</p>}</section>
  return <div className='scenario-overview' data-layout={primary ? 'primary' : 'compact'}>
    <section className='app-panel scenario-headline'><h2 className={primary ? undefined : 'sr-only'}>{title}</h2><p className={primary ? undefined : 'sr-only'}>Indicative precomputed scenario · stored target population, separate from a calculated network edit.</p>
      <div className='scenario-headline-values'>{values.map(item => <article key={item.label}><h3>{item.label}</h3><strong>{item.value === null ? '—' : `${item.prefix}${item.value.toLocaleString('en-GB', { maximumFractionDigits: 1 })}`}</strong><span>{item.value === null ? item.prefix : ''}{item.unit}</span></article>)}</div>
    </section>
    <div className='scenario-detail-layout'>
      <div><section className='app-panel'><h2>Scenario geography</h2><p>{regionName} · {name}. Boundary shows selected geography only; target-area geometries are unavailable in this payload.</p><div className='scenario-geography-map'><SelectedRegionsMap country={country} regionA={region} regionB={region} nameA={regionName} nameB={regionName} highlight='a' /></div><Link className='app-text-link' to={withSearch(appPath(country, 'access'), access.toString())}>Inspect actual stop coverage</Link></section>
        {!primary && populationPanel}
      </div>
      <aside>{primary && populationPanel}<section className='app-panel'><h2>Targeting criterion</h2><p>{target}</p></section>
        <section className='app-panel'><h2>Scenario details</h2><dl><div><dt>Intervention</dt><dd>{title}</dd></div><div><dt>Geographic scope</dt><dd>{name} · {regionName}</dd></div><div><dt>Annual cost</dt><dd>{cost === null ? 'Not modelled' : `${currency}${cost.toLocaleString('en-GB', { maximumFractionDigits: 1 })} million / year`}</dd></div><div><dt>CO₂ saved</dt><dd>{carbon === null ? 'Not modelled' : `${carbon.toLocaleString('en-GB')} tonnes / year`}</dd></div></dl></section>
        <section className='app-panel'><ChartInsights section={section} country={country} /><h2>Assumptions and interpretation</h2><p>Population affected is the population meeting the stored targeting criterion. It does not represent newly gained stop access.</p><p>Cost and carbon figures, where supplied, are indicative annual estimates. Missing estimates remain unavailable. No approved benefit-cost ratio is provided.</p>{text(scenario.confidence) && <p>Source confidence: {text(scenario.confidence)}</p>}{text(section.stats.note) && <p>{text(section.stats.note)}</p>}<Link className='app-text-link' to={withSearch(appPath(country, 'studio'), next.toString())}>Open in network Studio</Link></section>
        <details className='app-panel'><summary>Stored source details</summary><dl>{Object.entries(scenario).filter(([, value]) => typeof value === 'string' || typeof value === 'number').map(([key,value]) => <div key={key}><dt>{key.replaceAll('_', ' ')}</dt><dd>{String(value)}</dd></div>)}</dl></details>
      </aside>
    </div>
  </div>
}
