import {useState} from 'react'
import {useMutation} from '@tanstack/react-query'
import {apiPatch,apiPost} from '@/api/client'
import {usePackDates} from '@/api/hooks'
import {COUNTRIES,DIMENSION_API_IDS,dimensionsForCountry,regionsForCountry} from '@/lib/constants'
import {savedContext,type PolicyNote,type SavedViewContext} from '@/lib/workspace'

export function PolicyNoteForm({note,initialContext,initialDimension,onSaved,onCancel}:{note?:PolicyNote;initialContext?:SavedViewContext|null;initialDimension?:string|null;onSaved:()=>void;onCancel?:()=>void}){
 const original=savedContext(note?.view_context)??initialContext??null
 const [country,setCountry]=useState(original?.country??'')
 const [dimension,setDimension]=useState(note?.dimension??initialDimension??'equity')
 const [region,setRegion]=useState(original?.query.region??note?.region??'all')
 const [network,setNetwork]=useState(original?.query.pack??original?.query.as_of??'')
 const [stance,setStance]=useState(note?.stance??'monitor')
 const [thesis,setThesis]=useState(note?.thesis??'')
 const packs=usePackDates(),code=COUNTRIES.find(row=>row.code===country)?.code
 const dates=code?packs.data?.[code]?.dates??[]:[]
 const selectedNetwork=network||dates.find(row=>row.current)?.pack_id||''
 const topics=dimensionsForCountry(code??'england').map(row=>({id:DIMENSION_API_IDS[row.id]??row.id,label:row.name,page:row.id}))
 const submit=useMutation({mutationFn:async()=>{
  if(!code||!thesis.trim())throw new Error('Choose a country and enter a note.')
  const context:SavedViewContext={country:code,page:topics.find(row=>row.id===dimension)?.page??'overview',query:{...(original?.country===code?original.query:{}),region,...(selectedNetwork?{pack:selectedNetwork}:{}),urban_rural:original?.country===code?original.query.urban_rural??'all':'all'}}
  if(selectedNetwork)delete context.query.as_of
  if(context.page!==original?.page){delete context.query.view;delete context.query.exhibit}
  const body={dimension,region,stance,thesis:thesis.trim(),view_context:context}
  return note?apiPatch(`/policy-notes/${encodeURIComponent(note.id)}`,body):apiPost('/policy-notes',body)
 },onSuccess:onSaved})
 return <form className='workspace-note-form' onSubmit={event=>{event.preventDefault();submit.mutate()}}>
  <h2>{note?'Edit policy note':'Add a policy note'}</h2><div className='workspace-form-grid'>
  <label>Country<select required value={country} onChange={event=>{setCountry(event.target.value);setRegion('all');setNetwork('')}}><option value=''>Choose country</option>{COUNTRIES.map(row=><option key={row.code} value={row.code}>{row.name}</option>)}</select></label>
  <label>Topic<select value={dimension} onChange={event=>setDimension(event.target.value)}>{!topics.some(row=>row.id===dimension)&&<option value={dimension}>{dimension} (stored topic)</option>}{topics.map(row=><option key={row.id} value={row.id}>{row.label}</option>)}</select></label>
  <label>Region<select value={region} onChange={event=>setRegion(event.target.value)}>{!regionsForCountry(code??'england').some(row=>row.code===region)&&<option value={region}>{region} (stored region)</option>}{regionsForCountry(code??'england').map(row=><option key={row.code} value={row.code}>{row.name}</option>)}</select></label>
  <label>Network<select value={selectedNetwork} onChange={event=>setNetwork(event.target.value)}><option value=''>Date unavailable</option>{selectedNetwork&&!dates.some(row=>row.pack_id===selectedNetwork)&&<option value={selectedNetwork}>{selectedNetwork} (stored)</option>}{dates.map(row=><option key={row.pack_id} value={row.pack_id}>{row.as_of}{row.current?' · current':''}</option>)}</select></label></div>
  <fieldset><legend>Stance</legend><div className='reach-segmented'>{(['priority','monitor','adequate'] as const).map(value=><button type='button' key={value} aria-pressed={stance===value} onClick={()=>setStance(value)}>{value[0].toUpperCase()+value.slice(1)}</button>)}</div></fieldset>
  <label>Your note<textarea required rows={5} maxLength={Math.max(1000,note?.thesis.length??0)} value={thesis} onChange={event=>setThesis(event.target.value)} /></label><p>{thesis.length.toLocaleString('en-GB')} characters</p>
  {submit.error&&<p role='alert'>{submit.error.message}</p>}<div className='workspace-actions'><button type='submit' className='app-btn-primary' disabled={submit.isPending||!code||!thesis.trim()}>{submit.isPending?'Saving…':'Save note'}</button>{onCancel&&<button type='button' className='app-panel-button' disabled={submit.isPending} onClick={onCancel}>Cancel</button>}</div>
 </form>
}
