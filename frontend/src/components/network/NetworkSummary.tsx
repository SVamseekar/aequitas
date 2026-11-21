import { ChartInsights } from '@/components/dimension/ChartInsights'
import type { SectionItem } from '@/api/types'
import { ChartRenderer } from '@/components/charts/ChartRenderer'
import { finiteObservation as finite, serviceNumber as number } from '@/lib/serviceData'

export function NetworkSummary({ section }: { section: SectionItem }) {
  const operators = section.section_id === 'c3_operator_hhi'
  const chartData = {...section.chart_data,title:operators?'Regional operator concentration':'Cross-local-authority routes by region',x_label:operators?'HHI points (0–10,000)':'Cross-local-authority routes',palette:[operators?'#6a98b6':'#819d79'],...(operators?{x_domain:[0,10000],reference_rules:[1500,2500]}:{})}
  const chart=<section className='app-panel'><h2>{chartData.title}</h2><p>{operators?'Regional concentration of scheduled services across operators. The national index is a separate geographic aggregation.':'Routes operating across at least two local-authority areas. Counts describe regions, rather than a route corridor map.'}</p><ChartRenderer chartData={chartData} /></section>
  return <div className='network-page'>
    {operators?<div className='network-main'>{chart}<aside className='app-panel'>
      <ChartInsights section={section} /><h2>Operator concentration</h2><strong className='network-primary'>{number(section.stats.hhi,1)} <small>/ 10,000</small></strong><p>{typeof section.stats.region_name==='string'?section.stats.region_name:'Selected filter'} · Herfindahl–Hirschman Index</p><h3>Top operator by stored share</h3><p>{typeof section.stats.top_operator==='string'?section.stats.top_operator:'Unavailable'}</p><strong className='network-primary'>{number(section.stats.top_operator_share,1)}{finite(section.stats.top_operator_share)?'%':''}</strong><p>Scheduled-service share as supplied by the source. Reference markers at 1,500 and 2,500 provide concentration context; this exhibit does not assess competition-law compliance.</p>
    </aside></div>:<>{chart}<div className='network-metrics network-metrics-four'>
      <section className='app-panel'><h2>Cross-authority routes</h2><strong>{number(section.stats.n_cross_la)}</strong><p>{number(section.stats.pct_cross_la,1)}% of routes</p></section>
      <section className='app-panel'><h2>Highest regional count</h2><strong className='network-region-name'>{typeof section.stats.densest_corridor==='string'?section.stats.densest_corridor:'Unavailable'}</strong><p>{number(section.stats.densest_count)} routes</p></section>
      <section className='app-panel'><h2>Mean route length</h2><strong>{number(section.stats.mean_length,2)} km</strong></section>
      <section className='app-panel'><h2>Median route length</h2><strong>{number(section.stats.median_length,2)} km</strong></section>
    </div></>}
    <section className='app-panel mt-4'>{!operators&&<ChartInsights section={section} />}<h2>Source and limits</h2><p>BODS scheduled route/operator data and England local-authority boundaries. Geographic route classifications do not measure delays, live service performance or passenger demand.</p>{operators&&<p>HHI describes concentration at the selected geography; regional indices cannot be added or averaged to reconstruct the national index.</p>}</section>
  </div>
}
