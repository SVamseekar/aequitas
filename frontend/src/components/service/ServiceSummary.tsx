import { ChartInsights } from '@/components/dimension/ChartInsights'
import type { SectionItem } from '@/api/types'
import { ChartRenderer } from '@/components/charts/ChartRenderer'
import { useFilters, useScore } from '@/api/hooks'
import { coveragePresentation } from '@/lib/coverage'
import { finiteObservation as finite, serviceNumber as number } from '@/lib/serviceData'

export function ServiceSummary({ section, sections }: { section: SectionItem; sections: SectionItem[] }) {
  const { country, region, urbanRural, pack, mode } = useFilters()
  const score = useScore(region, urbanRural, country, pack, mode)
  const sunday = section.section_id === 'b3_weekend_penalty'
  const hours = sections.find(item => item.section_id === 'b2_operating_hours')
  const coverage = score.data?.components.find(item => item.id === 'pop_within_400m')?.value
  const metrics = sunday ? [
    ['Sunday service reduction', finite(section.stats.sunday_pct_drop) ? `${number(section.stats.sunday_pct_drop, 1)}%` : '—'],
    ['Sunday-desert areas', finite(section.stats.pct_sunday_desert) ? `${number(section.stats.pct_sunday_desert, 1)}% · ${number(section.stats.n_sunday_desert)} areas` : '—'],
  ] : [
    ['Mean service quality (SQI)', finite(section.stats.national_avg) ? `${number(section.stats.national_avg, 2)} / 100` : '—'],
    [coveragePresentation(country).shortLabel, finite(coverage) ? `${number(coverage * 100, 1)}%` : '—'],
    ['Evening-isolated areas', finite(hours?.stats.pct_evening_isolated) ? `${number(hours.stats.pct_evening_isolated, 1)}%` : '—'],
    ['In-country score', finite(score.data?.score) ? `${number(score.data.score, 1)} / 100` : '—'],
  ]
  const chartData = { ...section.chart_data,height:210, title: sunday ? 'Weekday and Sunday departures by region' : 'Service quality by region',
    x_label: sunday ? 'Mean daily departures per area' : 'Service Quality Index (points)',
    ...(sunday ? { orientation: 'vertical', palette: ['#6a98b6', '#d65b2d'] } : { palette: ['#819d79'], x_domain: [0,100] }),
  }
  const regions = Array.isArray(section.chart_data.data) ? section.chart_data.data as { label: string; value: unknown }[] : []
  const regionTable=(<section className='app-panel mt-4'><h2>Regional SQI table</h2><div className='access-table-scroll'><table aria-label='Regional service quality'><thead><tr><th>Region</th><th>SQI points</th><th>Difference from filter mean (points)</th></tr></thead><tbody>{regions.map(row => <tr key={row.label}><th scope='row'>{row.label}</th><td>{number(row.value, 2)}</td><td>{finite(row.value) && finite(section.stats.national_avg) ? number(row.value - section.stats.national_avg, 2) : '—'}</td></tr>)}</tbody></table></div></section>)
  return <div className='service-page'>
    <div className={`service-metrics${sunday ? ' service-metrics-pair' : ''}`}>{metrics.map(([label, value]) => <section className='app-panel' key={label}><h2>{label}</h2><strong>{value}</strong></section>)}</div>
    {!sunday && score.isPending && <p role='status'>Loading score context…</p>}{!sunday && score.error && <p role='alert'>Additional score context could not be loaded. No score or coverage is inferred.</p>}
    <div className='service-main'><div className='service-primary-column'><section className='app-panel'><h2>{chartData.title}</h2><p>{sunday ? 'Paired means of daily departures per small area. Sunday reduction describes departures; Sunday-desert share counts areas with no Sunday service.' : 'SQI points summarise scheduled service quality. Higher is better; these are not buses per hour.'}</p><ChartRenderer chartData={chartData} /></section>{!sunday&&regionTable}</div>
      <aside className='app-panel'><ChartInsights section={section} country={country} />{!sunday&&<><h2>About service quality</h2><p>The stored service quality index summarises scheduled timetable service. It does not measure passenger use, delays or reliability.</p><p>{coveragePresentation(country).definition}</p><p>Source context: BODS schedules, Census 2021 LSOAs and IMD 2025. Network dates and source vintages are distinct.</p></>}</aside></div>
    {sunday && <div className='service-notes'><section className='app-panel'><h2>What this shows</h2><p>The overall Sunday reduction compares total Sunday and weekday departures in this filter. The plotted regional means are separate summaries.</p><p>{number(section.stats.n_sunday_desert)} areas have no scheduled Sunday departures. This is distinct from the zero-stop subset.</p></section><section className='app-panel'><h2>Source and scope</h2><p>BODS departures and Census 2021 small areas. The source has no Saturday departure figure; no Saturday penalty is fabricated.</p></section></div>}
  </div>
}
