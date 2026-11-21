import { useRef, useEffect, useMemo } from 'react'
import * as Plot from '@observablehq/plot'
import { CATEGORICAL } from '@/lib/colours'
import { useChartWidth } from '@/hooks/useChartWidth'

interface ClusterSize { label: string; n: number; colour?: string }
/** Actual stored cluster counts; missing counts never become zero. */
export default function ClusterSizeBar({clusterSizes,vertical=false}:{clusterSizes:ClusterSize[];vertical?:boolean}) {
  const container=useRef<HTMLDivElement>(null),target=useRef<HTMLDivElement>(null)
  const width=useChartWidth(container,320)
  const data=useMemo(()=>clusterSizes.filter(row=>typeof row.n==='number'&&Number.isFinite(row.n)),[clusterSizes])
  useEffect(()=>{
    if(!target.current)return
    if(!data.length){target.current.replaceChildren();return}
    const wrap=(value:unknown)=>{
      const lines:string[]=[]
      for(const word of String(value).split(' ')){
        if(lines.length&&lines[lines.length-1].length+word.length+1<=(width<500?23:34))lines[lines.length-1]+=` ${word}`
        else lines.push(word)
      }
      return lines.join('\n')
    }
    if(vertical){
      const plot=Plot.plot({width,height:180,marginLeft:48,marginRight:12,marginBottom:34,
        x:{label:null,domain:data.map(row=>row.label),tickSize:0},y:{label:'Routes',zero:true,grid:true,ticks:4},
        marks:[Plot.barY(data,{x:'label',y:'n',fill:row=>row.colour??CATEGORICAL[0],tip:true,title:row=>`${row.label}\nStored count: ${row.n.toLocaleString('en-GB')}`})]})
      target.current.replaceChildren(plot)
      return()=>plot.remove()
    }
    const marginLeft=Math.min(200,width*0.55),marginRight=50
    const plot=Plot.plot({width,height:Math.max(160,data.length*54+55),marginLeft,marginRight,
      x:{label:'Stored count',zero:true,ticks:Math.max(2,Math.floor((width-marginLeft-marginRight)/65))},y:{label:null,tickFormat:wrap},
      marks:[Plot.barX(data,{y:'label',x:'n',fill:row=>row.colour??CATEGORICAL[0],tip:true,title:row=>`${row.label}\nStored count: ${row.n.toLocaleString('en-GB')}`}),Plot.text(data,{y:'label',x:'n',text:row=>row.n.toLocaleString('en-GB'),dx:4,textAnchor:'start',fontSize:10})]})
    target.current.replaceChildren(plot)
    return()=>plot.remove()
  },[data,width,vertical])
  return <div ref={container}><div ref={target} role={data.length?'img':undefined} aria-label='Cluster sizes' />{!data.length&&<p className='text-xs text-muted-foreground'>No cluster counts are supplied.</p>}</div>
}
