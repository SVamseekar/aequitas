import { ChartInsights } from '@/components/dimension/ChartInsights'
import type { SectionItem } from '@/api/types'
import { ChartRenderer } from '@/components/charts/ChartRenderer'
import { finiteObservation as finite, serviceNumber as number } from '@/lib/serviceData'

export function NetworkDistribution({ section }: { section: SectionItem }) {
  const stops = section.section_id === 'c2_stops_per_route', unit = stops ? 'stops per route' : 'km'
  const groups = Array.isArray(section.chart_data.groups) ? section.chart_data.groups as { label: string; outliers?: unknown[] }[] : []
  const suppliedOutliers = groups.reduce((total, group) => total + (group.outliers?.filter(finite).length ?? 0), 0)
  const stats: [string,string,unknown][] = [
    ['median',`Median (${unit})`,section.stats.median],['mean',`Mean (${unit})`,section.stats.mean],['p10',`10th percentile (${unit})`,section.stats.p10],['p90',`90th percentile (${unit})`,section.stats.p90],['n_outliers','Summary outliers (routes)',section.stats.n_outliers],
  ]
  return <div className='network-page network-distribution'><div className='network-main'><section className='app-panel'><h2>{stops?'Stops per route':'Route length distribution'}</h2><p>Actual regional quartile summaries and supplied outlier points. Unit: {unit}.</p><ChartRenderer chartData={{...section.chart_data,title:stops?'Stops per route distribution':'Route length distribution'}} />{!stops&&<p>London has no route-length geometry in this extract; its regional distribution remains unavailable.</p>}</section>
    <aside className='app-panel'><ChartInsights section={section} /><h2>Summary for the selected filter</h2><dl className='network-summary'>{stats.map(([key,label,value])=><div key={key}><dt>{label}</dt><dd>{number(value,key==='n_outliers'?0:2)}</dd></div>)}<div><dt>Standard deviation ({unit})</dt><dd>{number(section.stats.std,2)}</dd></div><div><dt>Coefficient of variation</dt><dd>{number(section.stats.cv,4)}</dd></div><div><dt>Interquartile range ({unit})</dt><dd>{number(section.stats.iqr,2)}</dd></div></dl><p>{typeof section.stats.skew_label==='string'?section.stats.skew_label:'Distribution shape unavailable'}</p>    <details className='network-distribution-source'><summary>Source and interpretation</summary><p>Regional boxes use only supplied quartiles and extrema. A smooth violin needs underlying distribution observations and is not invented from these summaries. Outliers are observations, not errors.</p><p>{stops?'Stops per route do not measure temporal frequency or passenger demand.':'Route length is geometric distance, not journey duration. London has no route-length geometry in this extract; its regional distribution remains unavailable.'}</p><p>Plotted outlier entries: {number(suppliedOutliers)}. Stored summary outlier count: {number(section.stats.n_outliers)}. Any difference in selection or aggregation remains unresolved; points are not dropped or invented to reconcile the counts.</p></details></aside></div>
    <div className='network-metrics'>{stats.map(([key,label,value])=><section className='app-panel' key={key}><h2>{label}</h2><strong>{number(value,key==='n_outliers'?0:2)}</strong></section>)}</div>

  </div>
}
