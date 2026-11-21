import { ChartInsights } from '@/components/dimension/ChartInsights'
import type { SectionItem } from '@/api/types'
import { CoverageProportion } from '@/components/access/CoverageProportion'
import { finiteObservation as finite, serviceNumber as number } from '@/lib/serviceData'
import { Users, Coins, Leaf } from 'lucide-react'

interface Tile { label:string; value:number|null; unit:string }
interface Series { data?:unknown[]; values?:unknown[] }
export function ScenarioModel({section}:{section:SectionItem}) {
  const raw=section.stats.scenario
  const scenario=raw&&typeof raw==='object'&&!Array.isArray(raw)?raw as Record<string,unknown>:{}
  const tiles=Array.isArray(section.chart_data.tiles)?section.chart_data.tiles as Tile[]:[]
  const proportion=section.chart_data.proportion as {series?:Series[]}|undefined
  const parts=proportion?.series?.map(row=>(row.data??row.values??[])[0])??[]
  const affected=parts[0],remaining=parts[1]
  const share=finite(affected)&&finite(remaining)&&affected>=0&&remaining>=0&&affected+remaining>0?100*affected/(affected+remaining):null
  const value=(tile:Tile)=>`${tile.unit.includes('£')&&finite(tile.value)?'£':''}${number(tile.value,finite(tile.value)&&Number.isInteger(tile.value)?0:1)}`
  return <div className='scenario-model'>
    <div className='scenario-model-metrics'>{tiles.map(tile=><section className='app-panel' key={tile.label}><h2>{tile.label}</h2><strong>{value(tile)}</strong><p>{tile.unit.replace('£','')}</p></section>)}</div>
    <section className='app-panel scenario-population-impact'><h2>Population impact</h2><p>Share of the population supplied in this stored model.</p>{share===null?<p>No population proportion is stored for this model.</p>:<CoverageProportion country='england' covered={share} labels={['Population affected','Population remaining']} values={[number(affected),number(remaining)]} colors={['#d65b2d','#afb1b3']} />}</section>
    <div className='scenario-model-summary'><section className='app-panel'><ChartInsights items={[...(share!==null?[`The paired population model targets **${number(affected)}** of **${number(Number(affected)+Number(remaining))}** people; these are not newly gained access.`]:[]),'Indicative model estimates; no live Studio result or approved BCR.']} /><h2>Scenario summary</h2><h3>{typeof scenario.name==='string'?scenario.name:'Stored scenario model'}</h3><p>{typeof scenario.scope==='string'?scenario.scope:'Scope unavailable'}</p><p>{typeof scenario.confidence==='string'?scenario.confidence:'Source confidence unavailable'}</p></section><section className='app-panel'><h2>Key metrics</h2>{tiles.map((tile,index)=>{const Icon=[Users,Coins,Leaf][index%3];return <div className='scenario-model-key' key={tile.label}><Icon size={22} aria-hidden='true' /><div><strong>{value(tile)}</strong><p>{tile.label} · {tile.unit.replace('£','')}</p></div></div>})}</section></div>
  </div>
}
