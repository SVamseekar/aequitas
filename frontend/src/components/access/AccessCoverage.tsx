import { Link, useSearchParams } from 'react-router'
import type { SectionItem } from '@/api/types'
import { useFilters, useMapLayer } from '@/api/hooks'
import { CoverageProportion } from './CoverageProportion'
import { coveragePresentation } from '@/lib/coverage'
import { downloadCsv } from '@/lib/downloadCsv'
import { ChartInsights } from '@/components/dimension/ChartInsights'
const finite = (value: unknown) => typeof value === 'number' && Number.isFinite(value) ? value : null
const format = (value: unknown, digits = 0, suffix = '') => { const observed = finite(value); return observed === null ? '—' : `${observed.toLocaleString('en-GB', { minimumFractionDigits: digits, maximumFractionDigits: digits })}${suffix}` }

export function AccessCoverage({ section }: { section: SectionItem }) {
  const { country, region, urbanRural, pack, mode } = useFilters()
  const [params] = useSearchParams()
  const meaning = coveragePresentation(country)
  const map = useMapLayer(region, urbanRural, country, pack, mode, 'coverage')
  const covered = finite(section.stats.pct_covered)
  const beyond = covered !== null && covered >= 0 && covered <= 100 ? 100 - covered : null
  const areaNoun = country === 'ireland' ? 'Small Areas' : country === 'netherlands' ? 'buurten' : country === 'france' ? 'IRIS' : 'LSOAs'
  const facilities = new URLSearchParams(params); facilities.set('view','facilities')
  const exportData = () => downloadCsv('aequitas-coverage.csv', ['country','region','area','network','mode','geography','coverage','complement','basis'], (map.data?.data ?? []).map(row => [country,region,urbanRural,pack || 'current',mode,row.area_name,row.value,finite(row.value) === null ? null : 100-row.value,meaning.unit]))
  return <div className='access-coverage'>
    <div className='access-metrics'>{[
      [meaning.title,format(covered,1,'%')], [country === 'england' ? 'LSOAs with zero access score' : 'Population beyond 400 m',format(beyond,1,'%')],
      ['Population with zero access',format(section.stats.pop_zero_access)], [`Zero-access ${areaNoun}`,format(section.stats.n_zero_access)],
    ].map(([label,value]) => <section className='app-panel' key={label}><h2>{label}</h2><strong>{value}</strong></section>)}</div>
    <section className='app-panel access-coverage-main'><div><h2>{meaning.title}</h2><p>{meaning.definition}</p>{covered !== null && beyond !== null ? <CoverageProportion covered={covered} country={country} /> : <p>No coverage observation is stored for this scope.</p>}</div><aside><ChartInsights section={section} country={country} /><Link className='app-text-link' to={{search:`?${facilities}`}}>Inspect destination proximity</Link></aside></section>
    <div className='access-coverage-detail'><section className='app-panel'><div className='access-table-heading'><h2>Coverage by geography</h2><button type='button' className='app-panel-button' disabled={!map.data?.data.length || Boolean(map.error)} onClick={exportData}>Download coverage CSV</button></div>{map.isPending ? <p role='status'>Loading geographic coverage…</p> : map.error ? <div role='alert'><p>Geographic coverage could not be loaded.</p><button type='button' className='app-panel-button' onClick={() => void map.refetch()}>Retry geographic coverage</button></div> : !map.data?.data.length ? <p>No geographic coverage values for this scope.</p> : <div className='access-table-scroll'><table aria-label='Geographic coverage'><thead><tr><th>Geography</th><th>Covered ({meaning.unit})</th><th>Complement ({meaning.unit})</th><th>Population with zero access</th></tr></thead><tbody>{map.data.data.map(row => <tr key={row.area_code}><th scope='row'>{row.area_name}</th><td>{format(row.value,1,'%')}</td><td>{format(finite(row.value) === null ? null : 100-row.value,1,'%')}</td><td>—</td></tr>)}</tbody></table></div>}<p>Per-geography zero-access population counts are unavailable here. No missing count is filled with zero.</p></section><aside className='app-panel'><h2>Zero-access {areaNoun}</h2><strong>{format(section.stats.n_zero_access)}</strong><p>{country === 'england' ? 'Areas with zero stored access score.' : 'Areas beyond the stored stop-proximity threshold.'}</p><p>These may be urban or rural. This count does not describe Sunday service or journey time.</p></aside></div>
  </div>
}
