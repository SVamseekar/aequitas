import { ChartInsights } from '@/components/dimension/ChartInsights'
import type {SectionItem} from '@/api/types'
import {ChartRenderer} from '@/components/charts/ChartRenderer'
import {finiteObservation,serviceNumber} from '@/lib/serviceData'

export function NetworkRelationship({section}:{section:SectionItem}){
 const {r,n,p_value:p,strength,direction}=section.stats
 const association=[strength,direction].filter(value=>typeof value==='string').join(' ')
 const probability=finiteObservation(p)?p<0.0001?'< 0.0001':serviceNumber(p,4):'Unavailable'
 return <div className='network-relationship'>
  <section className='app-panel'><h2>Route length vs stop count</h2><p>Route length and stops per route; each point is a supplied route observation.</p>
   <ChartRenderer chartData={{...section.chart_data,title:'Route length vs stop count',x_label:'Route length (km)',y_label:'Stops per route (stop count)',height:260,show_summary:false}} />
  </section>
  <div className='network-relationship-statistics'>
   <section className='app-panel'><h3>Correlation (r)</h3><strong>{finiteObservation(r)?serviceNumber(r,4):'Unavailable'}</strong>{association&&<p>{association} relationship</p>}</section>
   <section className='app-panel'><h3>Sample size</h3><strong>{finiteObservation(n)?serviceNumber(n):'Unavailable'}</strong><p>routes in the selected filter</p></section>
   <section className='app-panel'><h3>Significance (p)</h3><strong>{probability}</strong><p>Stored probability</p></section>
  </div>
  <section className='app-panel'><ChartInsights section={section} title='What this relationship shows' /><h3>Stop count proxy, not measured frequency</h3><p>The y-axis counts stops per route. It does not measure vehicles per hour, departures or passenger demand. Points are the supplied display sample; correlation and sample size describe the full selected filter. Correlation does not establish causation.</p></section>
 </div>
}
