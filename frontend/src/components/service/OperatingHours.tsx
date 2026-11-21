import { ChartInsights } from '@/components/dimension/ChartInsights'
import { useEffect, useRef } from 'react'
import * as Plot from '@observablehq/plot'
import type { SectionItem } from '@/api/types'
import { useChartWidth } from '@/hooks/useChartWidth'
import { finiteObservation as finite, operatingHours, serviceClock, serviceNumber } from '@/lib/serviceData'

export function OperatingHours({ section }: { section: SectionItem }) {
  const container = useRef<HTMLDivElement>(null), target = useRef<HTMLDivElement>(null)
  const width = useChartWidth(container, 700)
  const rows = operatingHours(section.chart_data)
  useEffect(() => {
    if (!target.current) return
    const observations = operatingHours(section.chart_data)
    const ranges = observations.flatMap(row => finite(row.first) && finite(row.last) && row.first >= 0 && row.last >= row.first ? [{ ...row, first: row.first, last: row.last }] : [])
    const points = observations.flatMap(row => [
      ...(finite(row.first) && row.first >= 0 ? [{ label: row.label, value: row.first, endpoint: 'First service' }] : []),
      ...(finite(row.last) && row.last >= 0 ? [{ label: row.label, value: row.last, endpoint: 'Last service' }] : []),
    ])
    if (!points.length) { target.current.replaceChildren(); return }
    const maximum = Math.max(1440, ...points.map(point => point.value))
    const chart = Plot.plot({ width, height: Math.max(190, observations.length * 16 + 46), marginLeft: Math.min(145, width * 0.36), marginBottom: 50, marginRight: 24,
      x: { label: 'Time of day (next day marked +1d)', domain: [0, Math.ceil(maximum / 120) * 120], ticks: width < 500 ? [0,480,960,1440] : [0,240,480,720,960,1200,1440], tickFormat: value => Number(value) === 1440 ? '24:00' : serviceClock(Number(value)), grid: true },
      y: { label: null, domain: observations.map(row => row.label), tickFormat: value => String(value).replace('Yorkshire and The Humber','Yorkshire & Humber').replace('East of England','East of England') },
      color: { domain: ['First service', 'Last service'], range: ['#64885d', '#c6602d'], legend: true },
      marks: [Plot.link(ranges, { x1: 'first', x2: 'last', y1: 'label', y2: 'label', stroke: '#d8ded4', strokeWidth: 8 }),
        Plot.dot(points, { x: 'value', y: 'label', fill: 'endpoint', r: 4, tip: true, title: point => `${point.label}\n${point.endpoint}: ${serviceClock(point.value)}` })],
    })
    target.current.replaceChildren(chart)
    return () => chart.remove()
  }, [section, width])
  const regionTable=(<section className='app-panel mt-4'><h2>Regional operating hours</h2><div className='access-table-scroll'><table aria-label='Regional operating hours'><thead><tr><th>Region</th><th>First service</th><th>Last service</th><th>Evening-isolated areas</th></tr></thead><tbody>{rows.map(row => <tr key={row.label}><th scope='row'>{row.label}</th><td>{serviceClock(row.first)}</td><td>{serviceClock(row.last)}</td><td>—</td></tr>)}</tbody></table></div><p>Per-region evening-isolated counts are not supplied in this exhibit; the summary above describes the selected filter.</p></section>)
  return <div className='service-page'>
    <div className='service-metrics'>{[
      ['Median first service', typeof section.stats.median_first_service === 'string' ? section.stats.median_first_service : '—'],
      ['Median last service', typeof section.stats.median_last_service === 'string' ? section.stats.median_last_service : '—'],
      ['Evening-isolated areas', serviceNumber(section.stats.n_evening_isolated)],
      ['Share of areas evening-isolated', `${serviceNumber(section.stats.pct_evening_isolated, 1)}${finite(section.stats.pct_evening_isolated) ? '%' : ''}`],
    ].map(([label, value]) => <section className='app-panel' key={label}><h2>{label}</h2><strong>{value}</strong></section>)}</div>
    <div className='service-main'><div className='service-primary-column'><section className='app-panel'><h2>Operating hours by region</h2><p>Stored regional first and last service endpoints; not an interquartile range.</p><div ref={container}><div ref={target} role='img' aria-label='Regional first and last service times' /></div>{!rows.length && <p>No operating-hour observations are stored for this filter.</p>}</section>{regionTable}</div>
      <aside className='app-panel'><ChartInsights section={section} /><h2>About this measure</h2><p>Times describe the stored regional typical first and last service. They do not guarantee a reliable timetable at every stop.</p><p>Evening-isolated areas have no scheduled service after 19:00 on a typical weekday. Area share is separate from a reduction in departures.</p><p>Next-day values remain next-day values. Missing endpoints are unavailable; midnight remains an observed time.</p></aside></div>

  </div>
}
