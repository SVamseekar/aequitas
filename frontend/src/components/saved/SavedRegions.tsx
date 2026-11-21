import {useState} from 'react'
import {Link} from 'react-router'
import {useMutation} from '@tanstack/react-query'
import {apiDelete,apiPost} from '@/api/client'
import {usePackDates} from '@/api/hooks'
import {useTenantCollection} from '@/hooks/useTenantCollection'
import {COUNTRIES,regionsForCountry} from '@/lib/constants'
import {savedContextLabels,savedContextHref,type SavedRegion,type SavedViewContext} from '@/lib/workspace'
import {WorkspaceState} from './WorkspaceState'

export function SavedRegions(){
 const query=useTenantCollection<SavedRegion>('/saved-regions'),packs=usePackDates()
 const [search,setSearch]=useState(''),[adding,setAdding]=useState(false),[country,setCountry]=useState(''),[region,setRegion]=useState('all'),[notes,setNotes]=useState(''),[confirm,setConfirm]=useState<string|null>(null)
 const code=COUNTRIES.find(row=>row.code===country)?.code
 const rows=(query.data??[]).filter(row=>`${row.region_name} ${row.region_code} ${row.notes??''} ${savedContextLabels(row.view_context).country}`.toLowerCase().includes(search.toLowerCase()))
 const create=useMutation({mutationFn:async()=>{
  if(!code)throw new Error('Choose the country for this region.')
  const selected=regionsForCountry(code).find(row=>row.code===region)
  if(!selected)throw new Error('Choose an available region.')
  const date=packs.data?.[code]?.dates?.find(row=>row.current)?.pack_id
  const context:SavedViewContext={country:code,page:'overview',query:{region,urban_rural:'all',...(date?{pack:date}:{})}}
  return apiPost('/saved-regions',{region_code:region,region_name:selected.name,notes:notes.trim()||null,view_context:context})
 },onSuccess:()=>{setAdding(false);setNotes('');void query.refetch()}})
 const remove=useMutation({mutationFn:(id:string)=>apiDelete(`/saved-regions/${encodeURIComponent(id)}`),onSuccess:()=>{setConfirm(null);void query.refetch()}})
 return <div><div className='workspace-section-heading'><label className='workspace-search'>Search regions<input type='search' value={search} onChange={event=>setSearch(event.target.value)} /></label><button type='button' className='app-btn-primary' onClick={()=>setAdding(!adding)}>Save a region</button></div>
  {adding&&<form className='app-panel workspace-note-form mb-4' onSubmit={event=>{event.preventDefault();create.mutate()}}><h2>Save a region</h2><div className='workspace-form-grid'><label>Country<select required value={country} onChange={event=>{setCountry(event.target.value);setRegion('all')}}><option value=''>Choose country</option>{COUNTRIES.map(row=><option value={row.code} key={row.code}>{row.name}</option>)}</select></label><label>Region<select disabled={!code} value={region} onChange={event=>setRegion(event.target.value)}>{regionsForCountry(code??'england').map(row=><option value={row.code} key={row.code}>{row.name}</option>)}</select></label></div><label>Notes<textarea rows={3} value={notes} onChange={event=>setNotes(event.target.value)} maxLength={1000} /></label><p>Uses the registered current network date when available; a missing date remains unavailable.</p>{create.error&&<p role='alert'>{create.error.message}</p>}<div className='workspace-actions'><button type='submit' className='app-btn-primary' disabled={create.isPending||!code}>{create.isPending?'Saving…':'Save region'}</button><button type='button' className='app-panel-button' onClick={()=>setAdding(false)}>Cancel</button></div></form>}
  <WorkspaceState loading={query.isPending} error={query.error} retry={()=>void query.refetch()} empty={!query.isPending&&!query.error&&!query.data?.length?'No saved regions yet':undefined} />
  {!query.error&&rows.length>0&&<section className='app-panel'><h2>Saved regions</h2><div className='access-table-scroll'><table aria-label='Saved regions'><thead><tr><th>Region</th><th>Country</th><th>Network date</th><th>Notes</th><th>Actions</th></tr></thead><tbody>{rows.map(row=>{const scope=savedContextLabels(row.view_context);return <tr key={row.id}><th scope='row'>{row.region_name}<small className='block'>{row.region_code}</small></th><td>{scope.country}</td><td>{scope.network}</td><td>{row.notes??'—'}</td><td><div className='workspace-actions'>{scope.context?<Link className='app-panel-button' to={savedContextHref(scope.context)}>Open region</Link>:<span>Original context not stored</span>}{confirm===row.id?<><button type='button' className='app-panel-button' disabled={remove.isPending} onClick={()=>remove.mutate(row.id)}>Confirm delete</button><button type='button' className='app-panel-button' onClick={()=>setConfirm(null)}>Cancel</button></>:<button type='button' className='app-panel-button' onClick={()=>setConfirm(row.id)}>Delete region</button>}</div></td></tr>})}</tbody></table></div></section>}
  {!query.error&&Boolean(query.data?.length)&&!rows.length&&<p className='app-panel'>No saved regions match this search.</p>}{remove.error&&<p role='alert'>{remove.error.message}</p>}
 </div>
}
