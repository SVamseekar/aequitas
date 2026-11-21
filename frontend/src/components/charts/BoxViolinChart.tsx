import { useRef, useEffect, useMemo } from 'react'
import * as Plot from '@observablehq/plot'
import { useChartWidth } from '@/hooks/useChartWidth'

interface BoxGroup { label: string; min: number; q1: number; median: number; q3: number; max: number; outliers?: unknown[] }
const finite = (value: unknown): value is number => typeof value === 'number' && Number.isFinite(value)

/** Render supplied quartiles/extrema. A violin density cannot be recovered from summaries. */
export default function BoxViolinChart({ chartData }: { chartData: Record<string, unknown> }) {
  const container = useRef<HTMLDivElement>(null), target = useRef<HTMLDivElement>(null)
  const width = useChartWidth(container, 700)
  const raw = useMemo(() => (chartData.groups ?? chartData.data ?? []) as BoxGroup[], [chartData])
  const data = useMemo(() => raw.filter(row => [row.min,row.q1,row.median,row.q3,row.max].every(finite) && row.min <= row.q1 && row.q1 <= row.median && row.median <= row.q3 && row.q3 <= row.max), [raw])
  const outliers = useMemo(() => raw.flatMap(row => (Array.isArray(row.outliers) ? row.outliers : []).flatMap(value => finite(value) ? [{ label: row.label, value }] : [])), [raw])
  useEffect(() => {
    if (!target.current) return
    if (!data.length && !outliers.length) { target.current.replaceChildren(); return }
    const vertical = width >= 500
    const unit = typeof chartData.unit === 'string' ? chartData.unit : typeof chartData.x_label === 'string' ? chartData.x_label : 'Value'
    const title = (row: BoxGroup) => `${row.label}\nMinimum: ${row.min}\n25th percentile: ${row.q1}\nMedian: ${row.median}\n75th percentile: ${row.q3}\nMaximum: ${row.max} ${unit}`
    const color = chartData.unit === 'stops' ? '#6a98b6' : '#819d79'
    const marks = vertical ? [
      Plot.ruleX(data,{x:'label',y1:'min',y2:'max',stroke:'#666',tip:true,title}),
      Plot.rectY(data,{x:'label',y1:'q1',y2:'q3',fill:color,fillOpacity:0.6,insetLeft:12,insetRight:12}),
      Plot.tickY(data,{x:'label',y:'median',stroke:'#333',strokeWidth:2,insetLeft:12,insetRight:12}),
      Plot.dot(outliers,{x:'label',y:'value',fill:'#c6602d',r:2.5,tip:true,title:row=>`${row.label}\nStored outlier: ${row.value} ${unit}`}),
    ] : [
      Plot.ruleY(data,{y:'label',x1:'min',x2:'max',stroke:'#666',tip:true,title}),
      Plot.rectX(data,{y:'label',x1:'q1',x2:'q3',fill:color,fillOpacity:0.6,insetTop:7,insetBottom:7}),
      Plot.tickX(data,{y:'label',x:'median',stroke:'#333',strokeWidth:2,insetTop:7,insetBottom:7}),
      Plot.dot(outliers,{y:'label',x:'value',fill:'#c6602d',r:2.5,tip:true,title:row=>`${row.label}\nStored outlier: ${row.value} ${unit}`}),
    ]
    const wrap = (value: unknown) => String(value).replace('Yorkshire and The Humber','Yorkshire and\nthe Humber').replace('East of England','East of\nEngland').replace(' Midlands','\nMidlands').replace(' West','\nWest').replace(' East','\nEast')
    const labels = [...new Set([...data.map(row=>row.label),...outliers.map(row=>row.label)])]
    const chart = Plot.plot({width,height:vertical?330:Math.max(260,labels.length*40+60),marginLeft:vertical?58:Math.min(140,width*0.4),marginRight:20,marginBottom:vertical?65:45,
      x:vertical?{label:null,domain:labels,tickFormat:wrap}:{label:unit,zero:true,grid:true},
      y:vertical?{label:unit,zero:true,grid:true}:{label:null,domain:labels,tickFormat:wrap},marks})
    target.current.replaceChildren(chart)
    return()=>chart.remove()
  },[chartData,data,outliers,width])
  return <div ref={container}>
    <div ref={target} role={data.length || outliers.length?'img':undefined} aria-label={typeof chartData.title==='string'?chartData.title:'Route distribution'} />
    {!data.length && !outliers.length?<p className='text-sm text-muted-foreground'>No complete distribution observations are available.</p>:<p className='text-xs text-muted-foreground mt-2'>Boxes: supplied 25th–75th percentiles; line: median; whiskers: stored minimum and maximum. Orange points: supplied outliers, not errors. No density curve is inferred.</p>}
    {raw.length>data.length&&<p className='text-xs text-muted-foreground mt-2'>Incomplete or inconsistent quartile summaries are unavailable; no missing quartile is filled with zero.</p>}
  </div>
}
