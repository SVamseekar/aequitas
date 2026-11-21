import { ChartInsights } from '@/components/dimension/ChartInsights'
import { useSearchParams } from 'react-router'
import type { SectionItem } from '@/api/types'
import { ChartRenderer } from '@/components/charts/ChartRenderer'
import { serviceNumber as number } from '@/lib/serviceData'
import ClusterSizeBar from '@/components/charts/ClusterSizeBar'

interface Cluster { id: number; n: number; pct?: number; description?: string }
export function NetworkArchetypes({ section }: { section: SectionItem }) {
  const [params,setParams]=useSearchParams()
  const clusters=Array.isArray(section.stats.clusters)?section.stats.clusters as Cluster[]:[]
  const selected=clusters.find(cluster=>String(cluster.id)===params.get('cluster'))
  const choose=(value:string)=>{const next=new URLSearchParams(params);if(value)next.set('cluster',value);else next.delete('cluster');setParams(next)}
  if(section.section_id==='g1_route_clusters'){
    const colours=Array.isArray(section.chart_data.clusters)?section.chart_data.clusters as {id:number;colour?:string}[]:[]
    return <div className='route-cluster-page'><section className='app-panel'><h2>Route clustering</h2><p>{number(section.stats.n_clusters)} stored clusters by route length and stop count. Point positions are the actual display sample.</p><ChartRenderer chartData={{...section.chart_data,compact_layout:true,cluster_entity:'routes',show_counts:false}} /></section>
      <div className='route-cluster-summary'><section className='app-panel'><h2>Routes per cluster</h2><ClusterSizeBar vertical clusterSizes={[...clusters].sort((a,b)=>a.id-b.id).map(cluster=>({label:`C${cluster.id}`,n:cluster.n,colour:colours.find(row=>row.id===cluster.id)?.colour}))} /></section><section className='app-panel'><ChartInsights section={section} /><h2>About this analysis</h2><p>BODS route geometry; counts describe the full model sample, not demand or frequency. Missing positions stay unavailable.</p></section></div>
      <details className='route-cluster-inspector app-panel' open={Boolean(selected)}><summary>Inspect a stored archetype</summary><label className='service-sort'>Stored cluster<select aria-label='Inspect route archetype' value={selected?String(selected.id):''} onChange={event=>choose(event.target.value)}><option value=''>Choose an archetype</option>{clusters.map(cluster=><option value={cluster.id} key={cluster.id}>{cluster.id} · {cluster.description??'Description unavailable'}</option>)}</select></label>{selected&&<><h3>Cluster {selected.id}</h3><p>{selected.description}</p><p>{number(selected.n)} routes · {number(selected.pct,1)}% of the stored sample.</p></>}</details>
    </div>
  }
  return <div className='network-page network-archetypes'>
    <div className='network-main'><section className='app-panel'><h2>Route archetypes</h2><p>Route length and stop count, coloured by the stored cluster. These are geometric characteristics, not measured demand.</p><ChartRenderer chartData={{...section.chart_data,compact_layout:true,cluster_entity:'archetypes',show_counts:false}} /></section>
    <aside className='app-panel'><h2>Archetype counts</h2><dl className='network-summary'>{clusters.map(cluster=><div key={cluster.id}><dt>{cluster.id} · {cluster.description??'Stored archetype'}</dt><dd>{number(cluster.n)}</dd></div>)}</dl><h2>Inspect an archetype</h2><label className='service-sort'>Stored cluster<select aria-label='Inspect route archetype' value={selected?String(selected.id):''} onChange={event=>choose(event.target.value)}><option value=''>Choose an archetype</option>{clusters.map(cluster=><option value={cluster.id} key={cluster.id}>{cluster.id} · {cluster.description??'Description unavailable'}</option>)}</select></label>
      {selected?<><h3>Cluster {selected.id}</h3><p>{selected.description??'No description supplied.'}</p><p>{number(selected.n)} routes · {number(selected.pct,1)}% of the stored cluster sample.</p></>:<p>{params.get('cluster')?'That cluster is unavailable for the selected filter. Choose a stored cluster.':'Select a cluster to inspect its supplied description and count.'}</p>}
    </aside></div><div className='network-archetype-notes'><section className='app-panel'><ChartInsights section={section} /></section><section className='app-panel'><h2>Source and sample</h2><p>{number(section.stats.n_clusters)} stored route clusters. The plot is a supplied display sample; counts describe the full model. No missing point positions are inferred.</p><p>BODS schedules · local-authority geography. Clusters are descriptive, not causal or a route-planning prescription.</p></section></div>
  </div>
}
