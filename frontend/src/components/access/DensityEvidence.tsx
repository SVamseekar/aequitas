import {Link,useSearchParams} from 'react-router'
import type {SectionItem} from '@/api/types'
import {ChartRenderer} from '@/components/charts/ChartRenderer'
import {ChartInsights} from '@/components/dimension/ChartInsights'
import {sectionPresentation} from '@/lib/sectionPresentation'
import {useFilters} from '@/api/hooks'

export function DensityEvidence({sections}:{sections:SectionItem[]}){
 const {country}=useFilters(),[params]=useSearchParams(),next=new URLSearchParams(params);next.set('view','a3_walking_distance');next.delete('exhibit')
 return <div className='density-evidence'><div className='access-density-layout'>{sections.map(section=>{const p=sectionPresentation(section,country);return <section className='app-panel' key={section.section_id}><h2>{p.title??section.chart_data.title as string}</h2><p>{section.section_id==='a1_route_density'?'Number of scheduled routes in the source region.':'Number of stops per 1,000 residents.'}</p><ChartRenderer chartData={{...p.chartData,height:300}} /><ChartInsights section={section} country={country} /></section>})}</div><div className='density-source-row app-panel'><section><h3>Notes and source</h3><p>Route count and stop density describe different inventory measures. Neither measures service frequency or passenger demand. Native source values and units are retained.</p><p>Network dates, population and deprivation vintages are separate.</p></section><section><h3>Related view</h3><p>Stop proximity is a different measure from route and stop inventories.</p><Link className='app-text-link' to={{search:`?${next}`}}>Open stop coverage</Link></section></div></div>
}
