import { ChartInsights } from '@/components/dimension/ChartInsights'
import { useCallback } from 'react'
import { useSearchParams } from 'react-router'
import type { SectionItem } from '@/api/types'
import ScatterClustersChart, { type ClusterPoint } from '@/components/charts/ScatterClustersChart'
import { finiteObservation as finite, serviceNumber as number } from '@/lib/serviceData'

interface Cluster { id?: string|number; label: string; n?: number }
export function CorrelationGroups({ section }: { section: SectionItem }) {
  const [params,setParams]=useSearchParams()
  const anomaly=section.section_id==='g2_anomalies'
  const points=(Array.isArray(section.chart_data.data)?section.chart_data.data as ClusterPoint[]:[]).filter(row=>finite(row.x)&&finite(row.y)&&typeof row.id==='string')
  const clusters=Array.isArray(section.chart_data.clusters)?section.chart_data.clusters as Cluster[]:[]
  const selected=points.find(row=>row.id===params.get('point'))
  const select=useCallback((point:ClusterPoint)=>{if(!point.id)return;const next=new URLSearchParams(params);next.set('point',point.id);setParams(next)},[params,setParams])
  const selectedCluster=clusters.find(row=>String(row.id??row.label)===String(selected?.cluster))
  const populationClusters=Array.isArray(section.stats.clusters)?section.stats.clusters as {id:string;n:number;pct?:number;description?:string}[]:[]
  return <div className={`network-page correlation-groups ${anomaly?'anomaly-groups':'poverty-groups'}`}>
    {anomaly&&<div className='service-metrics'>{[['Model anomalies',`${number(section.stats.n_anomalies)} · ${number(section.stats.pct_anomalies,2)}%`],['Positive category',number(section.stats.n_positive)],['Inefficiency category',number(section.stats.n_inefficiency)],['Policy-failure category',number(section.stats.n_policy_failure)]].map(([label,value])=><section className='app-panel' key={label}><h2>{label}</h2><strong>{value}</strong></section>)}</div>}
    <section className='app-panel'><h2>{anomaly?'Service anomalies':'Transport poverty groups'}</h2><p>{anomaly?'Each plotted point is one LSOA in the supplied display sample. Categories describe stored model classifications.':'Groups describe demographic and scheduled-service patterns, not individual poverty status or a poverty prevalence estimate.'}</p><ScatterClustersChart chartData={{...section.chart_data,compact_layout:true,show_counts:false}} onPointSelect={select} /></section>
    <section className='app-panel mt-4'><ChartInsights section={section} /><h2>Inspect a plotted area</h2><label className='service-sort'>Actual sample area<select aria-label='Inspect plotted area' value={selected?.id??''} onChange={event=>{const point=points.find(row=>row.id===event.target.value);if(point)select(point)}}><option value=''>Choose an area or click a plotted point</option>{points.map((row,index)=><option key={`${row.id}-${index}`} value={row.id}>{row.id}</option>)}</select></label>{selected?<dl className='network-summary'><div><dt>Small-area code</dt><dd>{selected.id}</dd></div><div><dt>{String(section.chart_data.x_label??'X')}</dt><dd>{number(selected.x,3)}</dd></div><div><dt>{String(section.chart_data.y_label??'Y')}</dt><dd>{number(selected.y,3)}</dd></div><div><dt>Stored category</dt><dd>{selectedCluster?.label??String(selected.cluster)}</dd></div></dl>:<p>No area selected. A missing sample row is not invented.</p>}</section>
    {!anomaly&&<section className='app-panel mt-4'><h2>Full source groups, including noise</h2><div className='access-table-scroll'><table aria-label='Population cluster summary'><thead><tr><th>Source group</th><th>Areas</th><th>Share of areas</th></tr></thead><tbody>{populationClusters.map(row=><tr key={row.id}><th scope='row'>{row.id}</th><td>{number(row.n)}</td><td>{number(row.pct,1)}%</td></tr>)}</tbody></table></div><p>Noise/unclustered areas are retained, including when omitted from the plotted sample.</p><details className='source-group-descriptions'><summary>Stored group descriptions</summary><dl>{populationClusters.map(row=><div key={row.id}><dt>{row.id}</dt><dd>{row.description??'Unavailable'}</dd></div>)}</dl></details></section>}
    <section className='app-panel mt-4'><h2>Interpretation and sources</h2>{anomaly&&<p>Model flags and descriptive categories use different definitions. Categories overlap and do not sum to the flagged anomaly count.</p>}{anomaly?<p>BODS schedules · Census 2021 · IMD 2025. Descriptive associations, not causal effects.</p>:<p>Source: England BODS schedules, Census 2021 LSOAs and IMD 2025. Point coordinates are the supplied display sample. Categories describe an analytical model; they do not establish causes, individual outcomes or policy effects.</p>}</section>
  </div>
}
