import { Link, useSearchParams } from 'react-router'
import { EVIDENCE_VIEWS, evidenceView } from '@/lib/evidenceViews'
import { sectionTitle } from '@/lib/constants'
import type { SectionItem } from '@/api/types'
import { useEffect, useRef } from 'react'

export function EvidenceNavigation({ dimension, country, sections }: { dimension: string; country: string; sections: SectionItem[] }) {
  const [params, setParams] = useSearchParams()
  const current = evidenceView(dimension,params.get('view'),params.get('exhibit'))
  const navigation = useRef<HTMLElement>(null)
  useEffect(() => {
    const nav = navigation.current, active = nav?.querySelector('[aria-current=page]')
    if (!nav || !active) return
    const item = active.getBoundingClientRect(), frame = nav.getBoundingClientRect()
    nav.scrollLeft += item.left - frame.left - (frame.width - item.width) / 2
  }, [current?.id,params])
  const choices = current?.panel === 'density' || current?.panel === 'domains' ? [] : sections.filter(s => current?.sections.includes(s.section_id))
  if(dimension==='accessibility'){
    const groups=[{label:'Stop coverage',views:['a3_walking_distance']},{label:'Deserts',views:['a5_service_deserts']},{label:'Urban / rural',views:['a6_urban_rural_gap']},{label:'Facilities',views:['facilities']},{label:'Travel time',views:['destinations']},{label:'More evidence',views:['a7_investment_gap','a8_coverage_prediction','density','a4_coverage_equity']}]
    const active=groups.find(group=>group.views.includes(current?.id??''))??groups[0]
    const target=(view:string)=>{const next=new URLSearchParams(params);next.set('view',view);next.delete('exhibit');return {search:`?${next}`}}
    return <div className='access-evidence-navigation'><nav ref={navigation} className='evidence-tabs access-primary-tabs' aria-label='Evidence views'>{groups.map(group=><Link key={group.label} to={target(group.views[0])} aria-current={group===active?'page':undefined}>{group.label}</Link>)}</nav>{active.views.length>1&&<nav className='evidence-tabs access-exhibit-tabs' aria-label='Access exhibits'>{active.views.map(view=><Link key={view} to={target(view)} aria-current={view===current?.id?'page':undefined}>{view==='density'?'Density & distribution':view==='a7_investment_gap'?'Gap estimate':EVIDENCE_VIEWS.accessibility.find(item=>item.id===view)?.label}</Link>)}</nav>}</div>
  }
  if(dimension==='route_network'){
    const groups=[{label:'Geometry',views:['c1_route_length','c2_stops_per_route']},{label:'Operators',views:['c3_operator_hhi']},{label:'Archetypes',views:['c6_route_archetypes']},{label:'Route mix',views:['c4_urban_rural_routes','c5_length_vs_frequency']},{label:'Topology',views:['c7_network_topology']}]
    const active=groups.find(group=>group.views.includes(current?.id??''))??groups[0]
    const target=(view:string)=>{const next=new URLSearchParams(params);next.set('view',view);next.delete('exhibit');return {search:`?${next}`}}
    const children=active.label==='Route mix'?active.views.slice(1):active.views
    return <div className='network-evidence-navigation'><nav ref={navigation} className='evidence-tabs network-evidence-tabs' aria-label='Evidence views'>{groups.map(group=><Link key={group.label} to={target(group.views[0])} aria-current={group===active?'page':undefined}>{group.label}</Link>)}</nav>{active.views.length>1&&<nav className='evidence-tabs network-exhibit-tabs' aria-label='Network exhibits'>{children.map(view=><Link key={view} to={target(view)} aria-current={view===current?.id?'page':undefined}>{EVIDENCE_VIEWS.route_network.find(item=>item.id===view)?.label}</Link>)}</nav>}</div>
  }
  if(dimension==='correlations'&&['g1_route_clusters','g2_anomalies','g5_scenario_model'].includes(current?.id??'')){
    const modelViews=['g1_route_clusters','g2_anomalies','g5_scenario_model']
    return <div className='correlation-model-navigation'><nav ref={navigation} className='evidence-tabs' aria-label='Evidence views'>{EVIDENCE_VIEWS.correlations.filter(view=>modelViews.includes(view.id)).map(view=>{
      const next=new URLSearchParams(params);next.set('view',view.id);next.delete('exhibit')
      return <Link key={view.id} to={{search:`?${next}`}} aria-current={current?.id===view.id?'page':undefined}>{view.label}</Link>
    })}</nav><select aria-label='Other correlation views' value='' onChange={event=>{if(!event.target.value)return;const next=new URLSearchParams(params);next.set('view',event.target.value);next.delete('exhibit');setParams(next)}}><option value=''>More evidence</option>{EVIDENCE_VIEWS.correlations.filter(view=>!modelViews.includes(view.id)).map(view=><option value={view.id} key={view.id}>{view.label}</option>)}</select></div>
  }
  if(dimension==='correlations'&&current?.id==='relationships'){
    const requested=params.get('exhibit')??params.get('view'),active=choices.find(row=>row.section_id===requested)?.section_id??choices[0]?.section_id
    const labels:Record<string,string>={d1_coverage_deprivation:'Deprivation',d2_coverage_unemployment:'Unemployment',d3_coverage_car:'Car-free households',d4_coverage_elderly:'Elderly'}
    return <div className='correlation-core-navigation'><nav ref={navigation} className='evidence-tabs' aria-label='Evidence views'>{choices.map(section=>{
      const next=new URLSearchParams(params);next.set('view',section.section_id);next.delete('exhibit')
      return <Link key={section.section_id} to={{search:`?${next}`}} aria-current={section.section_id===active?'page':undefined}>{labels[section.section_id]??section.section_id}</Link>
    })}</nav><select aria-label='Other correlation views' value='' onChange={event=>{if(!event.target.value)return;const next=new URLSearchParams(params);next.set('view',event.target.value);next.delete('exhibit');setParams(next)}}><option value=''>More evidence</option>{EVIDENCE_VIEWS.correlations.filter(view=>view.id!=='relationships').map(view=><option value={view.id} key={view.id}>{view.label}</option>)}</select></div>
  }
  if(dimension==='correlations'){
    const groups=[{label:'Relationships',views:['relationships']},{label:'Domains',views:['domains']},{label:'Poverty & rural',views:['d6_transport_poverty','d7_deprivation_urban_rural']},{label:'Model',views:['g3_coverage_model','features']},{label:'Route models',views:['g1_route_clusters','g2_anomalies','g5_scenario_model']}]
    const active=groups.find(group=>group.views.includes(current?.id??''))??groups[0]
    const target=(view:string)=>{const next=new URLSearchParams(params);next.set('view',view);next.delete('exhibit');return {search:`?${next}`}}
    return <div className='correlation-group-navigation'><nav ref={navigation} className='evidence-tabs' aria-label='Evidence views'>{groups.map(group=><Link key={group.label} to={target(group.views[0])} aria-current={group===active?'page':undefined}>{group.label}</Link>)}</nav>{active.views.length>1&&<nav className='evidence-tabs' aria-label='Correlation exhibits'>{active.views.map(view=><Link key={view} to={target(view)} aria-current={current?.id===view?'page':undefined}>{EVIDENCE_VIEWS.correlations.find(item=>item.id===view)?.label}</Link>)}</nav>}{choices.length>1&&<label className='correlation-exhibit-control'>Exhibit<select value={choices.some(section=>section.section_id===params.get('exhibit'))?params.get('exhibit')!:choices[0].section_id} onChange={event=>{const next=new URLSearchParams(params);next.set('exhibit',event.target.value);setParams(next)}}>{choices.map(section=><option key={section.section_id} value={section.section_id}>{sectionTitle(section.section_id,country)??section.section_id}</option>)}</select></label>}</div>
  }
  return <>
    <nav ref={navigation} className='evidence-tabs' aria-label='Evidence views'>
      {(EVIDENCE_VIEWS[dimension] ?? []).map(view => {
        const next = new URLSearchParams(params); next.set('view', view.id); next.delete('exhibit')
        return <Link key={view.id} to={{ search: `?${next}` }} aria-current={current?.id === view.id ? 'page' : undefined}>{view.label}</Link>
      })}
    </nav>
    {choices.length > 1 && <label className='block text-sm mb-4'>Exhibit <select className='ml-3 border border-border rounded px-3 py-2 bg-white max-w-full' value={choices.some(s => s.section_id === params.get('exhibit')) ? params.get('exhibit')! : choices[0].section_id} onChange={event => { const next = new URLSearchParams(params); next.set('exhibit', event.target.value); setParams(next) }}>{choices.map(s => <option key={s.section_id} value={s.section_id}>{sectionTitle(s.section_id, country) ?? s.section_id.replaceAll('_', ' ')}</option>)}</select></label>}
  </>
}
