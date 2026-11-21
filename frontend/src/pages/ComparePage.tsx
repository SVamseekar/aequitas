import { Link, useSearchParams } from 'react-router'
import { AREA_TYPES, COUNTRIES, regionsForCountry } from '@/lib/constants'
import { useFilters } from '@/api/hooks'
import { COMPARE_METRICS, type CompareMetricId } from '@/lib/compareLabels'
import { compareDefinitions as defaultDefinitions, compareShortLabels as defaultLabels, compareUnits as defaultUnits, formatCompareMetric, sideValues } from '@/lib/compareData'
import { coveragePresentation } from '@/lib/coverage'
import { isLondonRural } from '@/lib/uniqueExhibits'
import { useCompareSide } from '@/hooks/useCompareSide'
import { BriefingActions } from '@/components/shared/BriefingActions'
import SelectedRegionsMap from '@/components/shared/SelectedRegionsMap'
import CompareMetricPlot from '@/components/charts/CompareMetricPlot'

const views = [
  { id: 'summary', label: 'Summary', metrics: null },
  { id: 'coverage', label: 'Coverage', metrics: ['pct_within_400m'] },
  { id: 'service', label: 'Service quality', metrics: ['gini'] },
  { id: 'evening', label: 'Evening service', metrics: ['evening_isolated'] },
  { id: 'jobs', label: 'Access to jobs', metrics: ['jobs_45'] },
] as const
const order: CompareMetricId[] = ['in_country_score', 'pct_within_400m', 'evening_isolated', 'jobs_45', 'gini']
const defaults: Record<string, [string, string]> = { england: ['E12000002', 'E12000007'], ireland: ['cork', 'dublin'], netherlands: ['groningen', 'noord-holland'], france: ['ile-de-france', 'occitanie'] }

export default function ComparePage() {
  const { country, pack, mode, urbanRural } = useFilters()
  const coverageMeaning = coveragePresentation(country)
  const compareDefinitions = { ...defaultDefinitions, pct_within_400m: `${coverageMeaning.unit} · ${coverageMeaning.definition}` }
  const compareShortLabels = { ...defaultLabels, pct_within_400m: coverageMeaning.shortLabel }
  const compareUnits = { ...defaultUnits, pct_within_400m: coverageMeaning.unit }
  const [params, setParams] = useSearchParams()
  const regions = regionsForCountry(country).filter(region => region.code !== 'all')
  const [defaultA, defaultB] = defaults[country]
  const regionA = params.get('a') ?? defaultA
  const regionB = params.get('b') ?? defaultB
  const nameA = regions.find(region => region.code === regionA)?.name ?? regionA
  const nameB = regions.find(region => region.code === regionB)?.name ?? regionB
  const valid = regions.some(region => region.code === regionA) && regions.some(region => region.code === regionB)
  const same = regionA === regionB
  const empty = isLondonRural(regionA, urbanRural) || isLondonRural(regionB, urbanRural)
  const enabled = valid && !same && !empty
  const aQ = useCompareSide(regionA, urbanRural, country, pack, mode, enabled)
  const bQ = useCompareSide(regionB, urbanRural, country, pack, mode, enabled)
  const a = sideValues(aQ.data), b = sideValues(bQ.data)
  const view = views.find(item => item.id === params.get('view')) ?? views[0]
  const metrics = order.filter(id => !view.metrics || (view.metrics as readonly string[]).includes(id))
  const loading = enabled && (aQ.isLoading || bQ.isLoading)
  const error = aQ.error || bQ.error
  const available = enabled && !loading && !error && Boolean(aQ.data && bQ.data)
  const countryName = COUNTRIES.find(item => item.code === country)?.name ?? country
  const label = (id: CompareMetricId) => id === 'pct_within_400m' ? coverageMeaning.title : COMPARE_METRICS.find(item => item.id === id)?.label ?? id
  const set = (key: string, value: string) => { const next = new URLSearchParams(params); next.set(key, value); setParams(next) }
  const exportComparison = () => {
    const quote = (text: string) => `"${text.replace(/"/g, '""')}"`
    const context = [country, pack || 'current', urbanRural, country === 'netherlands' ? mode : '', nameA, nameB]
    const rows = metrics.map(id => [...context, label(id), compareDefinitions[id], a[id] === null ? '' : String(a[id]), b[id] === null ? '' : String(b[id])].map(quote).join(','))
    const body = ['country,network,area,mode,region_a,region_b,metric,definition,value_a,value_b', ...rows].join('\n')
    const href = URL.createObjectURL(new Blob([body], { type: 'text/csv;charset=utf-8' }))
    const anchor = document.createElement('a'); anchor.href = href; anchor.download = 'aequitas-region-comparison.csv'; anchor.click()
    window.setTimeout(() => URL.revokeObjectURL(href), 1000)
  }
  return <div className='compare-page'>
    <div className='compare-heading'><div><h1>Compare — {same ? 'Choose two different regions' : `${nameA} vs ${nameB}`}</h1><p>{countryName} · matched measures within one country</p></div><div className='flex gap-2'><BriefingActions /><button type='button' className='app-panel-button' disabled={!available} onClick={exportComparison}>Export comparison CSV</button></div></div>
    <nav className='compare-view-tabs' aria-label='Comparison views'>{views.map(item => { const next = new URLSearchParams(params); next.set('view', item.id); return <Link key={item.id} to={{ search: `?${next}` }} aria-current={view.id === item.id ? 'page' : undefined}>{item.label}</Link> })}</nav>
    <div className='compare-selectors'>{(['a', 'b'] as const).map((key, index) => <label key={key}>Region {index === 0 ? 'A' : 'B'}<select aria-label={`Region ${index === 0 ? 'A' : 'B'}`} value={key === 'a' ? regionA : regionB} onChange={event => set(key, event.target.value)}>{!regions.some(region => region.code === (key === 'a' ? regionA : regionB)) ? <option value={key === 'a' ? regionA : regionB}>{key === 'a' ? nameA : nameB}</option> : null}{regions.map(region => <option key={region.code} value={region.code}>{region.name}</option>)}</select></label>)}<label>Area<select aria-label='Area type' value={urbanRural} onChange={event => set('urban_rural', event.target.value)}>{AREA_TYPES.map(area => <option key={area.code} value={area.code}>{area.name}</option>)}</select></label></div>
    {!valid ? <p className='compare-notice'>Select valid regions within {countryName}.</p> : same ? <><p className='compare-notice'>Choose two different regions to compare transport equity metrics.</p><div className='compare-same-maps'><div><SelectedRegionsMap country={country} regionA={regionA} regionB={regionB} nameA={nameA} nameB={nameB} highlight='a' /></div><h2>Select different regions</h2><div><SelectedRegionsMap country={country} regionA={regionA} regionB={regionB} nameA={nameA} nameB={nameB} highlight='b' /></div></div><section className='app-panel mt-5'><h2>How to compare regions</h2><ol className='compare-help'><li>Select a region in Region A.</li><li>Select a different region in Region B.</li><li>Choose an area scope and network date.</li></ol><p>Country scores and deprivation ranks stay within {countryName}.</p></section></> : empty ? <p className='compare-notice'>London has no rural LSOAs — this combination is empty. Choose an urban or all-area scope.</p> : loading ? <p role='status' className='app-panel'>Loading matched regional measures…</p> : error ? <div role='alert' className='compare-notice'><p>Comparison could not be loaded for this network and filter.</p><button type='button' className='app-panel-button mt-3' onClick={() => { void aQ.refetch(); void bQ.refetch() }}>Retry comparison</button></div> : available ? <>
      <div className='compare-metric-cards'>{metrics.map(id => <section className='app-panel' key={id}><h2>{compareShortLabels[id]}</h2><p>{compareUnits[id]}</p><dl><div><dt>{nameA}</dt><dd>{formatCompareMetric(id, a[id])}</dd></div><div><dt>{nameB}</dt><dd>{formatCompareMetric(id, b[id])}</dd></div></dl></section>)}</div>
      <div className='compare-summary-layout'>
        <section className='app-panel'><h2>Selected regions</h2><p>{countryName}</p><SelectedRegionsMap key={country} country={country} regionA={regionA} regionB={regionB} nameA={nameA} nameB={nameB} /></section>
        <div className='min-w-0'><section className='app-panel'><div className='compare-plot-heading'><h2>Key metrics comparison</h2><p><span className='compare-a'>● {nameA}</span> <span className='compare-b'>● {nameB}</span></p></div>{metrics.map(id => <div className='compare-metric-row' key={id}><div><h3>{compareShortLabels[id]}</h3><p>{compareUnits[id]}</p></div><CompareMetricPlot id={id} left={a[id]} right={b[id]} nameA={nameA} nameB={nameB} /><div className='compare-values'><span className='compare-a'>{formatCompareMetric(id, a[id])}</span><span className='compare-b'>{formatCompareMetric(id, b[id])}</span></div></div>)}</section>
        <section className='app-panel mt-4'><h2>Metrics by region</h2><div className='compare-table-scroll'><table><thead><tr><th>Metric</th><th>{nameA}</th><th>{nameB}</th><th>Denominator / definition</th></tr></thead><tbody>{metrics.map(id => <tr key={id}><td>{label(id)}</td><td>{formatCompareMetric(id, a[id])}</td><td>{formatCompareMetric(id, b[id])}</td><td>{compareDefinitions[id]}</td></tr>)}</tbody></table></div><p>— means unavailable. Destination points are not employment totals. These comparisons do not imply causal effects.</p></section></div>
      </div>
    </> : null}
  </div>
}
