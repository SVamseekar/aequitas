import {useState} from 'react'
import {Link,useSearchParams} from 'react-router'
import {useMutation} from '@tanstack/react-query'
import {apiDelete} from '@/api/client'
import {useTenantCollection} from '@/hooks/useTenantCollection'
import {savedContextLabels,savedContextHref,type SavedAnalysis} from '@/lib/workspace'
import {Markdown} from '@/components/shared/Markdown'
import {WorkspaceState} from './WorkspaceState'
import {PolicyNoteForm} from './PolicyNoteForm'

export function SavedAnalyses(){
 const query=useTenantCollection<SavedAnalysis>('/saved-analyses')
 const [params,setParams]=useSearchParams(),[confirm,setConfirm]=useState<string|null>(null),[noteSaved,setNoteSaved]=useState(false)
 const search=params.get('q')??'',records=query.data??[]
 const filtered=records.filter(row=>`${row.title} ${row.dimension??''} ${(row.tags??[]).join(' ')} ${savedContextLabels(row.view_context).country}`.toLowerCase().includes(search.toLowerCase()))
 const selected=records.find(row=>row.id===params.get('analysis')),scope=savedContextLabels(selected?.view_context)
 const choose=(id:string)=>{const next=new URLSearchParams(params);next.set('analysis',id);setParams(next);setNoteSaved(false)}
 const remove=useMutation({mutationFn:(id:string)=>apiDelete(`/saved-analyses/${encodeURIComponent(id)}`),onSuccess:()=>{setConfirm(null);void query.refetch()}})
 return <div><label className='workspace-search'>Search analyses<input type='search' value={search} onChange={event=>{const next=new URLSearchParams(params);if(event.target.value)next.set('q',event.target.value);else next.delete('q');setParams(next)}} placeholder='Title, topic, country or tag' /></label>
  <WorkspaceState loading={query.isPending} error={query.error} retry={()=>void query.refetch()} empty={!query.isPending&&!query.error&&!records.length?'No saved analyses yet':undefined} />
  {!query.error&&records.length>0&&<section className='app-panel'><h2>Saved analyses</h2><div className='access-table-scroll'><table aria-label='Saved analyses'><thead><tr><th>Topic</th><th>Country</th><th>Network date</th><th>Tags</th><th>Actions</th></tr></thead><tbody>{filtered.map(row=>{const context=savedContextLabels(row.view_context);return <tr key={row.id} aria-selected={selected?.id===row.id}><th scope='row'>{row.title}</th><td>{context.country}</td><td>{context.network}</td><td>{(row.tags??[]).length?(row.tags??[]).join(', '):'—'}</td><td><div className='workspace-actions'><button type='button' className='app-panel-button' onClick={()=>choose(row.id)}>Open {row.title}</button>{confirm===row.id?<><button type='button' className='app-panel-button' disabled={remove.isPending} onClick={()=>remove.mutate(row.id)}>Confirm delete</button><button type='button' className='app-panel-button' onClick={()=>setConfirm(null)}>Cancel</button></>:<button type='button' className='app-panel-button' onClick={()=>setConfirm(row.id)} aria-label={`Delete ${row.title}`}>Delete</button>}</div></td></tr>})}</tbody></table></div>{!filtered.length&&<p>No saved analyses match this search.</p>}</section>}
  {remove.error&&<p role='alert'>{remove.error.message}</p>}
  {params.get('analysis')&&!query.isPending&&!selected&&<p className='app-panel'>The selected analysis is unavailable in this workspace.</p>}
  {selected&&<section className='app-panel mt-4'><div className='workspace-section-heading'><h2>{selected.title}</h2>{scope.context?<Link className='app-panel-button' to={savedContextHref(scope.context)}>Open original view</Link>:<span>Original view unavailable: context was not stored.</span>}</div><div className='workspace-detail-grid'><div><h3>Details</h3><dl className='network-summary'><div><dt>Country</dt><dd>{scope.country}</dd></div><div><dt>Region</dt><dd>{scope.region}</dd></div><div><dt>Network date</dt><dd>{scope.network}</dd></div><div><dt>Topic</dt><dd>{selected.dimension??'Not stored'}</dd></div></dl><div className='workspace-saved-content'><Markdown content={selected.content} /></div></div><div>{noteSaved?<p role='status'>Policy note saved to this workspace.</p>:<PolicyNoteForm key={selected.id} initialContext={scope.context} initialDimension={selected.dimension} onSaved={()=>setNoteSaved(true)} />}</div></div></section>}
 </div>
}
