import { useEffect, useMemo, useRef } from 'react'
import * as Plot from '@observablehq/plot'
import { useChartWidth } from '@/hooks/useChartWidth'

interface Band { label:string; min:number; max:number|null; color_hint:string }
interface Marker { label:string; value:number }
const finite=(value:unknown):value is number=>typeof value==='number'&&Number.isFinite(value)
const COLORS:Record<string,string>={red:'#e6b2a6',orange:'#efc38f',yellow:'#eadc91',green:'#a7c6a3',blue:'#94b8d1'}

/** Thresholds describe the supplied model. Open-ended bands remain explicitly open-ended. */
export default function GaugeChart({chartData}:{chartData:Record<string,unknown>}) {
  const container=useRef<HTMLDivElement>(null),target=useRef<HTMLDivElement>(null)
  const width=useChartWidth(container,700)
  const bands=useMemo(()=>((chartData.bands??[]) as Band[]).filter(row=>finite(row.min)&&(row.max===null||finite(row.max)&&row.max>row.min)),[chartData])
  const unit=typeof chartData.unit==='string'?chartData.unit:''
  const ring=chartData.variant==='ring'
  const hhi=unit.includes('HHI')||unit.includes('10,000')
  const markers=useMemo(()=>{
    const supplied=((chartData.markers??[]) as Marker[]).filter(row=>finite(row.value))
    return supplied.length?supplied:finite(chartData.value)?[{label:hhi?'HHI':'Selected value',value:chartData.value}]:[]
  },[chartData,hhi])
  const references=useMemo(()=>((chartData.reference_lines??[]) as unknown[]).filter(finite),[chartData])
  const maximum=hhi?10000:Math.max(5,...bands.map(row=>row.max??row.min+1),...markers.map(row=>row.value))
  useEffect(()=>{
    if(!target.current)return
    if(ring&&markers.length===1){
      const arc=(fraction:number)=>{const length=Math.max(2,Math.ceil(fraction*360)+1);return Array.from({length},(_,i)=>{const angle=-Math.PI/2+2*Math.PI*fraction*i/(length-1);return {x:Math.cos(angle),y:-Math.sin(angle)}})}
      const marker=markers[0],fraction=Math.max(0,Math.min(1,marker.value/maximum))
      const plot=Plot.plot({width:Math.min(width,250),height:160,margin:12,x:{axis:null,domain:[-1.4,1.4]},y:{axis:null,domain:[-1.4,1.4]},marks:[Plot.line(arc(1),{x:'x',y:'y',stroke:'#e7e4df',strokeWidth:13}),...(fraction>0?[Plot.line(arc(fraction),{x:'x',y:'y',stroke:'#759d73',strokeWidth:13})]:[]),Plot.text([{x:0,y:.1,label:marker.value.toLocaleString('en-GB',{maximumFractionDigits:1})}],{x:'x',y:'y',text:'label',fontSize:26,fontWeight:650}),Plot.text([{x:0,y:-.32,label:`/ ${maximum.toLocaleString('en-GB')}`}],{x:'x',y:'y',text:'label',fontSize:11,fill:'#625d55'})]})
      target.current.replaceChildren(plot);return()=>plot.remove()
    }
    if(!bands.length||!markers.length){target.current.replaceChildren();return}
    const plot=Plot.plot({width,height:155,marginLeft:20,marginRight:20,marginTop:35,marginBottom:45,
      x:{label:hhi?'HHI (0–10,000)':unit||'Model value',domain:[0,maximum],ticks:hhi?(width<400?[0,5000,10000]:[0,2500,5000,7500,10000]):width<500?4:6},y:{axis:null,domain:[0,1.8]},
      marks:[Plot.rect(bands,{x1:'min',x2:row=>row.max??maximum,y1:0,y2:1,fill:row=>COLORS[row.color_hint]??'#dedbd6',tip:true,title:row=>`${row.label}: ${row.min}${row.max===null?'+':`–${row.max}`}`}),
        Plot.ruleX(references,{y1:0,y2:1,stroke:'#555',strokeDasharray:'3,3',ariaLabel:'Reference thresholds'}),
        Plot.ruleX(markers,{x:'value',y1:0,y2:1.25,stroke:'#222',strokeWidth:2}),
        Plot.dot(markers,{x:'value',y:0.5,fill:'#222',r:4,tip:true,title:row=>`${row.label}: ${row.value} ${unit}`})]})
    target.current.replaceChildren(plot)
    return()=>plot.remove()
  },[bands,markers,references,maximum,width,unit,hhi,ring])
  return <div ref={container}>
    {bands.length&&markers.length?<><div ref={target} role='img' aria-label={typeof chartData.title==='string'?chartData.title:'Threshold gauge'} />{typeof chartData.title==='string'&&<p className='sr-only'>{chartData.title}</p>}
      <div className={ring?'gauge-ring-labels':'gauge-band-labels'}>{(ring?bands.filter(row=>markers.length===1&&markers[0].value>=row.min&&(row.max===null||markers[0].value<row.max)):bands).map(row=><span key={row.label}>{row.label}<small>{row.min}{row.max===null?'+':`–${row.max}`}</small></span>)}</div>
      <dl className={ring?'sr-only':'network-summary'}>{markers.map(row=><div key={row.label}><dt>{row.label}</dt><dd>{row.value.toLocaleString('en-GB',{maximumFractionDigits:hhi?1:4})} {unit}</dd></div>)}</dl>
    </>:<p className='text-muted-foreground text-sm'>No data available</p>}
  </div>
}
