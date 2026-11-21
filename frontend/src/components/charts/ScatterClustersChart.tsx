import { useRef, useEffect, useMemo } from 'react'
import * as Plot from '@observablehq/plot'
import { CATEGORICAL } from '@/lib/colours'
import { useChartWidth } from '@/hooks/useChartWidth'
import { finiteObservation as finite } from '@/lib/serviceData'
import ClusterSizeBar from './ClusterSizeBar'

export interface ClusterPoint { x: number; y: number; cluster: string | number; id?: string }
interface Cluster { id?: string | number; label: string; n?: number; colour?: string }
const key = (cluster: Cluster) => String(cluster.id ?? cluster.label)
const shortLabel = (cluster: Cluster) => `${cluster.id === undefined ? '' : `${cluster.id} · `}${cluster.label.split(' routes averaging ')[0]}`

export default function ScatterClustersChart({ chartData, onPointSelect }: { chartData: Record<string, unknown>; onPointSelect?: (point: ClusterPoint) => void }) {
  const container = useRef<HTMLDivElement>(null), target = useRef<HTMLDivElement>(null)
  const width = useChartWidth(container,700)
  const clusters = useMemo(() => (chartData.clusters ?? []) as Cluster[],[chartData])
  const points = useMemo(() => ((chartData.data ?? []) as ClusterPoint[]).filter(row=>finite(row.x)&&finite(row.y)),[chartData])
  const sizes = useMemo(() => (chartData.cluster_sizes ?? []) as {label:string;n:number}[],[chartData])
  const suppressed = chartData.scatter_suppressed === true || !points.length
  const compact = chartData.compact_layout === true
  useEffect(()=>{
    if(!target.current)return
    if(suppressed){target.current.replaceChildren();return}
    const domain=[...new Set([...clusters.map(key),...points.map(point=>String(point.cluster))])]
    const colors=domain.map((id,index)=>clusters.find(cluster=>key(cluster)===id)?.colour??[...CATEGORICAL,'#8c63bb'][index%7])
    const name=(id:unknown)=>{const cluster=clusters.find(item=>key(item)===String(id));return cluster?shortLabel(cluster):String(id)}
    const plot=Plot.plot({width,height:compact?260:Math.min(450,Math.max(300,width*0.7)),marginLeft:62,marginRight:20,
      x:{label:typeof chartData.x_label==='string'?chartData.x_label:'X',zero:true},y:{label:typeof chartData.y_label==='string'?chartData.y_label:'Y',zero:true},
      color:{domain,range:colors,legend:!compact,tickFormat:name,label:'Stored cluster'},
      marks:[Plot.dot(points,{x:'x',y:'y',fill:row=>String(row.cluster),opacity:0.55,r:2.5,tip:true,
        title:row=>`${row.id??'Source identifier unavailable'}\n${clusters.find(cluster=>key(cluster)===String(row.cluster))?.label??`Cluster ${row.cluster}`}\n${chartData.x_label??'X'}: ${row.x}\n${chartData.y_label??'Y'}: ${row.y}`})]})
    if (onPointSelect) plot.querySelectorAll('[aria-label="dot"] circle').forEach((circle,index)=>{
      circle.addEventListener('click',()=>onPointSelect(points[index]))
      ;(circle as SVGElement).style.cursor='pointer'
    })
    target.current.replaceChildren(plot)
    return()=>plot.remove()
  },[chartData,clusters,points,suppressed,width,onPointSelect,compact])
  return <><div className={`cluster-evidence-grid${compact?' compact-cluster-grid':''}`}><div ref={container}>
    <div ref={target} role={!suppressed?'img':undefined} aria-label={typeof chartData.title==='string'?chartData.title:'Cluster scatter'} />
    {suppressed&&<p className='text-sm text-muted-foreground'>Individual point positions are unavailable for this exhibit. No scatter positions are inferred from cluster counts.</p>}
    {!points.length&&!sizes.length&&<p className='text-sm text-muted-foreground'>No cluster observations are available for this filter.</p>}
  </div>{compact&&!suppressed&&<ul className='compact-cluster-legend' aria-label='Stored cluster legend'>{clusters.map((cluster,index)=><li key={key(cluster)} title={cluster.label}><i style={{background:cluster.colour??[...CATEGORICAL,'#8c63bb'][index%7]}} aria-hidden='true' /><span>{chartData.cluster_entity==='routes'?`Cluster ${key(cluster)}`:chartData.cluster_entity==='archetypes'?shortLabel(cluster):cluster.label}</span></li>)}</ul>}{sizes.length>0&&chartData.show_counts!==false&&<section className='cluster-count-plot'><h3>Stored cluster counts</h3><ClusterSizeBar vertical={compact&&chartData.cluster_entity==='routes'} clusterSizes={sizes.map(row=>{const cluster=clusters.find(item=>item.label===row.label);return {...row,label:compact&&chartData.cluster_entity==='routes'&&cluster?`C${key(cluster)}`:cluster?shortLabel(cluster):row.label,colour:cluster?.colour}})} /></section>}</div>
    {sizes.length>0&&<details className='mt-3'><summary>Cluster count table</summary><div className='access-table-scroll'><table aria-label='Stored cluster counts'><thead><tr><th>Cluster</th><th>Count</th></tr></thead><tbody>{sizes.map((row,index)=><tr key={`${row.label}-${index}`}><th scope='row'>{row.label}</th><td>{finite(row.n)?row.n.toLocaleString('en-GB'):'—'}</td></tr>)}</tbody></table></div></details>}
  </>
}
