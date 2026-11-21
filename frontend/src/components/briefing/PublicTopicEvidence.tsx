import { useSearchParams } from 'react-router'
import { Link } from 'react-router'
import { useSections } from '@/api/hooks'
import { ChartRenderer } from '@/components/charts/ChartRenderer'
import { Markdown } from '@/components/shared/Markdown'
import { DIMENSION_API_IDS, sectionTitle } from '@/lib/constants'
import { EVIDENCE_VIEWS } from '@/lib/evidenceViews'
import type { CountryCode } from '@/lib/briefingCatalog'
import { sectionPresentation } from '@/lib/sectionPresentation'

export function PublicTopicEvidence({ slug, country }: { slug: string; country: CountryCode }) {
  const dimension = DIMENSION_API_IDS[slug]
  const query = useSections(dimension, 'all', 'all', country, '', 'bus')
  const [params] = useSearchParams()
  const requested = params.get('exhibit')
  const sections = query.data?.sections ?? []
  const defaultId = EVIDENCE_VIEWS[dimension]?.[0]?.sections[0]
  const selected = sections.find(section => section.section_id === requested) ?? sections.find(section => section.section_id === defaultId) ?? sections[0]
  const number = (value: unknown, digits: number, suffix = '') => typeof value === 'number' && Number.isFinite(value) ? `${value.toFixed(digits)}${suffix}` : '—'
  if (query.isPending) return <p role='status' className='public-topic-evidence'>Loading selected country evidence…</p>
  if (query.error) return <div role='alert' className='public-topic-evidence'><p>Evidence could not be loaded for this country.</p><button type='button' className='app-panel-button' onClick={() => void query.refetch()}>Retry evidence</button></div>
  if (!selected) return <p className='public-topic-evidence'>No observations are available for this topic and country.</p>
  const presentation = sectionPresentation(selected, country)
  const title = presentation.title ?? sectionTitle(selected.section_id, country) ?? (typeof selected.chart_data?.title === 'string' ? selected.chart_data.title : 'Selected evidence')
  return <section className='public-topic-evidence'>
    <div className='public-topic-main'>
      {slug === 'equity' && selected.section_id === 'f1_gini' ? <div className='public-topic-primary'><h2>Service inequality (Gini)</h2><strong>{number(selected.stats.gini, 4)}</strong><p>Selected country · current reference pack</p><dl><div><dt>Palma ratio</dt><dd>{number(selected.stats.palma ?? selected.stats.palma_ratio, 3, '×')}</dd></div><div><dt>Concentration index</dt><dd>{number(selected.stats.concentration_index, 4)}</dd></div></dl><p>Distinct distribution measures. Deprivation association alone does not establish causality.</p></div> : null}
      <div className='public-topic-chart'><h2>{title}</h2>{selected.suppressed || selected.stats?.omit ? <p>This exhibit is unavailable for the selected country.</p> : Object.keys(selected.chart_data ?? {}).length ? <ChartRenderer chartData={presentation.chartData} /> : <p>No chart observations are available for this exhibit.</p>}</div>
    </div>
    {(presentation.interpretation || selected.narrative) && <div className='public-topic-interpretation'><Markdown content={presentation.interpretation ?? selected.narrative} /></div>}
    <div className='public-topic-exhibits'><h2>Explore this evidence</h2>{sections.map(section => { const next = new URLSearchParams(params); next.set('exhibit', section.section_id); return <Link key={section.section_id} to={{ search: `?${next}` }} aria-current={selected.section_id === section.section_id ? 'page' : undefined}>{sectionTitle(section.section_id, country) ?? section.section_id.replaceAll('_', ' ')}</Link> })}</div>
    <p>Ranks stay within the selected country. {country === 'netherlands' ? 'Network: bus only. ' : ''}Missing results remain unavailable.</p>
  </section>
}
