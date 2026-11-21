import {useState} from 'react'
import {Link} from 'react-router'
import {useMutation} from '@tanstack/react-query'
import {apiDelete} from '@/api/client'
import {useTenantCollection} from '@/hooks/useTenantCollection'
import {savedContextLabels,savedContextHref,type PolicyNote} from '@/lib/workspace'
import {PolicyNoteForm} from './PolicyNoteForm'
import {WorkspaceState} from './WorkspaceState'

export function PolicyNotes(){
 const query=useTenantCollection<PolicyNote>('/policy-notes')
 const [search,setSearch]=useState(''),[editing,setEditing]=useState<PolicyNote|null>(null),[adding,setAdding]=useState(false),[confirm,setConfirm]=useState<string|null>(null)
 const records=query.data??[],rows=records.filter(row=>`${row.dimension} ${row.thesis} ${row.stance??''} ${savedContextLabels(row.view_context).country}`.toLowerCase().includes(search.toLowerCase()))
 const remove=useMutation({mutationFn:(id:string)=>apiDelete(`/policy-notes/${encodeURIComponent(id)}`),onSuccess:()=>{setConfirm(null);void query.refetch()}})
 const saved=()=>{setEditing(null);setAdding(false);void query.refetch()}
 return <div><div className='workspace-section-heading'><label className='workspace-search'>Search notes<input type='search' value={search} onChange={event=>setSearch(event.target.value)} /></label><button type='button' className='app-btn-primary' onClick={()=>{setAdding(true);setEditing(null)}}>New note</button></div>
  {(adding||editing)&&<section className='app-panel mb-4'><PolicyNoteForm key={editing?.id??'new'} note={editing??undefined} onSaved={saved} onCancel={()=>{setAdding(false);setEditing(null)}} /></section>}
  <WorkspaceState loading={query.isPending} error={query.error} retry={()=>void query.refetch()} empty={!query.isPending&&!query.error&&!records.length&&!adding?'No policy notes yet':undefined} />
  {!query.error&&rows.map(row=>{const scope=savedContextLabels(row.view_context);return <article className='app-panel mb-3' key={row.id}><div className='workspace-section-heading'><div><h2>{row.dimension.replaceAll('_',' ')}</h2><p>{scope.country} · {scope.region} · {scope.network}</p><span className='workspace-stance'>{row.stance??'Stance not stored'}</span></div><div className='workspace-actions'>{scope.context&&<Link className='app-panel-button' to={savedContextHref(scope.context)}>Open note context</Link>}<button type='button' className='app-panel-button' onClick={()=>{setEditing(row);setAdding(false)}}>Edit note</button>{confirm===row.id?<><button type='button' className='app-panel-button' disabled={remove.isPending} onClick={()=>remove.mutate(row.id)}>Confirm delete</button><button type='button' className='app-panel-button' onClick={()=>setConfirm(null)}>Cancel</button></>:<button type='button' className='app-panel-button' onClick={()=>setConfirm(row.id)}>Delete note</button>}</div></div><p className='workspace-note-body'>{row.thesis}</p>{row.critique&&<details><summary>Stored critique</summary><p>{row.critique}</p></details>}<p>Updated {new Date(row.updated_at).toLocaleDateString('en-GB')}</p></article>})}
  {!query.error&&records.length>0&&!rows.length&&<p className='app-panel'>No notes match this search.</p>}{remove.error&&<p role='alert'>{remove.error.message}</p>}
 </div>
}
