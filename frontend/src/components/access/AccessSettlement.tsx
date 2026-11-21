import { ChartInsights } from '@/components/dimension/ChartInsights'
import { useEffect, useRef } from 'react'
import * as Plot from '@observablehq/plot'
import type { SectionItem } from '@/api/types'
import { useChartWidth } from '@/hooks/useChartWidth'
import { ChartRenderer } from '@/components/charts/ChartRenderer'
import { sectionPresentation } from '@/lib/sectionPresentation'

const observed = (value: unknown): value is number => typeof value === 'number' && Number.isFinite(value)
const number = (value: unknown, digits = 0) => observed(value) ? value.toLocaleString('en-GB', { minimumFractionDigits: digits, maximumFractionDigits: digits }) : '—'

/** The headline and regional exhibit have different grains; keep both explicit. */
export function AccessSettlement({ section }: { section: SectionItem }) {
  const container = useRef<HTMLDivElement>(null), target = useRef<HTMLDivElement>(null)
  const width = useChartWidth(container, 650)
  useEffect(() => {
    if (!target.current) return
    const rows = [
      { settlement: 'Urban', value: section.stats.urban_value, count: section.stats.n_urban },
      { settlement: 'Rural', value: section.stats.rural_value, count: section.stats.n_rural },
    ].flatMap(row => observed(row.value) ? [{ ...row, value: row.value }] : [])
    if (!rows.length) { target.current.replaceChildren(); return }
    const plot = Plot.plot({ width, height: 300, marginLeft: 58, marginBottom: 58, marginTop: 25,
      x: { label: null, domain: ['Urban', 'Rural'], tickSize: 0, tickFormat: value => `${value}\nn = ${number(rows.find(row => row.settlement === value)?.count)}` },
      y: { label: 'Mean trips per capita', zero: true, grid: true, ticks: 5 },
      color: { domain: ['Urban', 'Rural'], range: ['#6a98b6', '#819d79'] },
      marks: [Plot.barY(rows, { x: 'settlement', y: 'value', fill: 'settlement', insetLeft: width * 0.08, insetRight: width * 0.08, tip: true, title: row => `${row.settlement}\nMean trips per capita: ${row.value}\nAreas: ${number(row.count)}` }),
        Plot.text(rows, { x: 'settlement', y: 'value', text: row => number(row.value, 2), dy: -10, fontWeight: 600 })],
    })
    target.current.replaceChildren(plot)
    return () => plot.remove()
  }, [section, width])
  const hasValues = observed(section.stats.urban_value) || observed(section.stats.rural_value)
  return <div className='access-settlement'>
    <section className='app-panel'><h2>Urban/rural service gap</h2><p>Mean scheduled trips per capita for the selected filter, by settlement type.</p>
      <div className='access-settlement-main'><div ref={container}><div ref={target} role={hasValues ? 'img' : undefined} aria-label={hasValues ? 'Urban and rural mean trips per capita' : undefined} />{!hasValues && <p>No settlement averages are stored for this filter.</p>}</div>
        <aside><ChartInsights section={section} /><h3>Relative rural gap</h3><strong>{number(section.stats.gap_pct, 1)}{observed(section.stats.gap_pct) ? '%' : ''}</strong><p>Relative difference between the supplied urban and rural means. This is not a percentage-point coverage gap.</p><dl><div><dt>Urban mean trips per capita</dt><dd>{number(section.stats.urban_value, 2)}</dd></div><div><dt>Rural mean trips per capita</dt><dd>{number(section.stats.rural_value, 2)}</dd></div><div><dt>Urban areas</dt><dd>{number(section.stats.n_urban)}</dd></div><div><dt>Rural areas</dt><dd>{number(section.stats.n_rural)}</dd></div></dl></aside></div>
    </section>
    <div className='access-facility-notes'><section className='app-panel'><h2>What this shows</h2><p>Scheduled trips per capita differ from 400 m stop coverage, destination travel times and the service quality index.</p><p>The stored relative gap uses the underlying observations; it need not equal a calculation from the rounded displayed means.</p></section><section className='app-panel'><h2>Methods and data</h2><p>Source: BODS scheduled trips and Census 2021 population. Settlement classification: ONS Rural–Urban Classification 2011, applied to 2021 LSOAs.</p><p>Means describe the selected filter. Missing settlement observations remain unavailable.</p></section></div>
    <details className='app-panel mt-4'><summary>Regional settlement detail</summary><p>Regional observations use the same trips-per-capita unit. London has no rural LSOAs; its rural value is unavailable.</p><ChartRenderer chartData={sectionPresentation(section, 'england').chartData} /></details>
  </div>
}
