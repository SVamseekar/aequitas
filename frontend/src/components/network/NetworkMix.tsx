import { ChartInsights } from '@/components/dimension/ChartInsights'
import type { SectionItem } from '@/api/types'
import { ChartRenderer } from '@/components/charts/ChartRenderer'
import { finiteObservation as finite, serviceNumber as number } from '@/lib/serviceData'

export function NetworkMix({ section }: { section: SectionItem }) {
  const parts = [{name:'Urban',value:section.stats.urban_value,count:section.stats.n_urban},{name:'Rural',value:section.stats.rural_value,count:section.stats.n_rural},{name:'Mixed',value:section.stats.pct_mixed,count:section.stats.n_mixed}]
  const complete = parts.every(part=>finite(part.value))
  return <div className='network-page'>
    <section className='app-panel'><h2>Urban, rural and mixed routes</h2><p>Route classification for the selected filter. Shares count routes, rather than people or departures.</p>{complete?<ChartRenderer chartData={{type:'stacked_bar',title:'Selected-filter route mix',height:180,categories:['Routes'],series:parts.map(part=>({name:part.name,values:[part.value]})),palette:['#6a98b6','#819d79','#e79558'],x_label:'Share of routes (%)',x_domain:[0,100]}} />:<p>A complete three-category route share is unavailable for this filter.</p>}</section>
    <div className='network-metrics network-metrics-three'>{parts.map(part=><section className='app-panel' key={part.name}><h2>{part.name} routes</h2><strong>{number(part.value,1)}{finite(part.value)?'%':''}</strong><p>{number(part.count)} routes</p></section>)}</div>
    <section className='app-panel mt-4'><ChartInsights section={section} /><h2>About route types</h2><p>Urban routes operate primarily in urban areas, rural routes in rural areas, and mixed routes span both. The geographic classification does not establish passenger use or the regularity of service.</p><p>Cross-local-authority routes are a separate classification: {number(section.stats.n_cross_la)} routes ({number(section.stats.pct_cross_la,1)}%). A mixed route need not cross an authority boundary.</p></section>
    <details className='app-panel mt-4'><summary>Regional route mix</summary><ChartRenderer chartData={{...section.chart_data,title:'Regional route mix',palette:['#6a98b6','#819d79','#e79558'],x_label:'Share of routes (%)',x_domain:[0,100]}} /></details>
  </div>
}
