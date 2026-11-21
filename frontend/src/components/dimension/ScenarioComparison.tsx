import { ChartInsights } from './ChartInsights'
import type { SectionItem } from '@/api/types'
import { ScenarioPlot } from './ScenarioPlot'
interface ScenarioRow { name: string; population: number | null; cost: number | null; co2: number | null; sourceId?: string }
export function ScenarioComparison({ section, country, sources = [] }: { section: SectionItem; country: string; sources?: SectionItem[] }) {
  const finite = (value: unknown) => typeof value === 'number' && Number.isFinite(value) ? value : null
  const raw = Array.isArray(section.stats.scenarios) ? section.stats.scenarios : Array.isArray(section.stats.rows) ? section.stats.rows : []
  const rows: ScenarioRow[] = raw.flatMap(value => {
    if (!value || typeof value !== 'object') return []
    const record = value as Record<string, unknown>
    const name = record.name ?? record.title
    if (typeof name !== 'string') return []
    return [{ name, population: finite(record.population ?? record.people), cost: finite(record.cost_m), co2: finite(record.co2_t), sourceId: typeof record.id === 'string' ? record.id : undefined }]
  })
  const currency = country === 'england' ? '£' : '€'
  const format = (value: number | null) => value == null ? '—' : value.toLocaleString('en-GB', { maximumFractionDigits: 1 })
  const conflicts = rows.flatMap(row => {
    const source = sources.find(item => row.sourceId ? item.section_id.startsWith(`${row.sourceId}_`) : (item.stats.scenario as Record<string, unknown> | undefined)?.name === row.name)
    const scenario = source?.stats.scenario as Record<string, unknown> | undefined
    const individual = finite(scenario?.population_affected)
    return row.population !== null && individual !== null && Math.abs(row.population - individual) > 0.05 ? [`${row.name}: comparison stores ${format(row.population)} people; the individual scenario stores ${format(individual)}.`] : []
  })
  return <div className='scenario-comparison'>
    <section className='app-panel'><h2>Scenario comparison</h2><p>Compare stored target populations, indicative annual costs and estimated CO₂ changes. Target populations are not newly gained stop access.</p>
      {rows.length ? <div className='ops-table-scroll'><table aria-label='Stored scenario comparison'><thead><tr><th>Scenario</th><th>Target population affected</th><th>Cost ({currency}m / year)</th><th>CO₂ (t / year)</th></tr></thead><tbody>{rows.map(row => <tr key={row.name}><th scope='row'>{row.name}</th><td>{format(row.population)}</td><td>{format(row.cost)}</td><td>{format(row.co2)}</td></tr>)}</tbody></table></div> : <p>Scenario comparisons are unavailable for this scope.</p>}
      {conflicts.length > 0 && <div role='alert' className='scenario-source-conflict'><h3>Source records disagree</h3>{conflicts.map(conflict => <p key={conflict}>{conflict}</p>)}<p>Values are retained as supplied. Reconcile these source records before using the comparison.</p></div>}
    </section>
    <div className='scenario-comparison-plots'>{([{ key: 'population', label: 'Target population affected', unit: 'Population (millions)' }, { key: 'cost', label: `Cost (${currency}m / year)`, unit: `${currency}m / year` }, { key: 'co2', label: 'CO₂ (tonnes / year)', unit: 'Tonnes / year' }] as const).map(metric => <section className='app-panel' key={metric.key}><h2>{metric.label}</h2>{rows.some(row => row[metric.key] !== null) ? <ScenarioPlot rows={rows} metric={metric.key} unit={metric.unit} /> : <p>No stored values for this measure.</p>}</section>)}</div>
    <ChartInsights section={section} country={country} className='app-panel' /><p className='scenario-comparison-note'>Compare target populations and model assumptions; these figures are indicative. — = not modelled; no mark is drawn for unavailable values. No approved benefit-cost ratio or calculated network access impact is inferred.</p>
  </div>
}
