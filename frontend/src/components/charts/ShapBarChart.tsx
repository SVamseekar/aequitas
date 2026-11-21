import { useRef, useEffect, useMemo } from 'react'
import * as Plot from '@observablehq/plot'
import { CATEGORICAL } from '@/lib/colours'
import { useChartWidth } from '@/hooks/useChartWidth'
import { modelFeatureLabel as label } from '@/lib/modelLabels'

interface FeatureDatum { name: string; importance?: number | null; r?: number | null; note?: string }
const finite = (value: unknown): value is number => typeof value === 'number' && Number.isFinite(value)

export default function ShapBarChart({ chartData }: { chartData: Record<string,unknown> }) {
  const container = useRef<HTMLDivElement>(null), target = useRef<HTMLDivElement>(null)
  const width = useChartWidth(container,700)
  const raw = useMemo(() => (chartData.features ?? []) as FeatureDatum[],[chartData])
  const features = useMemo(() => raw.flatMap(feature => finite(feature.importance) ? [{ ...feature, importance:feature.importance }] : []),[raw])
  const highest = features.reduce<typeof features[number] | undefined>((best, feature) => !best || feature.importance > best.importance ? feature : best,undefined)
  useEffect(() => {
    if (!target.current) return
    if (!features.length) { target.current.replaceChildren(); return }
    const wrap = (name: string) => {
      const text = label(name), length = width < 500 ? 16 : 24
      const at = text.lastIndexOf(' ',length)
      return text.length > length && at > 0 ? `${text.slice(0,at)}\n${text.slice(at+1)}` : text
    }
    const chart = Plot.plot({ width, height:finite(chartData.height)?Math.max(220,Math.min(600,chartData.height)):Math.max(300,features.length*30+55), marginLeft:Math.min(190,Math.max(105,width*0.32)), marginRight:48,
      x:{label:'Mean absolute SHAP value'}, y:{label:null,tickFormat:wrap},
      subtitle:chartData.show_summary!==false&&finite(chartData.model_r2) ? `Model R² = ${chartData.model_r2.toFixed(4)}` : undefined,
      marks:[Plot.barX(features,{y:'name',x:'importance',fill:typeof chartData.bar_color==='string'?chartData.bar_color:CATEGORICAL[0],sort:{y:'x',reverse:true},tip:true,title:feature=>`${label(feature.name)} (${feature.name})\nImportance: ${feature.importance.toFixed(4)}`}),Plot.text(features,{y:'name',x:'importance',text:feature=>feature.importance.toFixed(4),dx:4,textAnchor:'start',fontSize:10})],
    })
    target.current.replaceChildren(chart)
    return () => chart.remove()
  },[chartData,features,width])
  return <div ref={container}>
    {highest && chartData.show_summary!==false&&<p className='text-xs text-muted-foreground mb-2'>Highest stored importance: {label(highest.name)} — {highest.importance.toFixed(4)}. Predictive association, not a causal effect.</p>}
    <div ref={target} role={features.length ? 'img' : undefined} aria-label={features.length ? typeof chartData.title === 'string' ? chartData.title : 'Feature importance' : undefined} />
    {!features.length && (raw.length ? <><p className='text-sm text-muted-foreground mb-3'>This pack supplies feature correlations, rather than SHAP importance. Missing associations remain unavailable.</p><div className='access-table-scroll'><table aria-label='Stored feature associations'><thead><tr><th>Feature</th><th>Stored correlation r</th><th>Source note</th></tr></thead><tbody>{raw.map(feature=><tr key={feature.name}><th scope='row'>{label(feature.name)}</th><td>{finite(feature.r)?feature.r.toFixed(4):'—'}</td><td>{feature.note ?? '—'}</td></tr>)}</tbody></table></div></> : <p className='text-sm text-muted-foreground'>No feature observations are available for this chart.</p>)}
  </div>
}
