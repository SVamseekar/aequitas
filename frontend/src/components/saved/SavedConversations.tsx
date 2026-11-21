import {useState} from 'react'
import {Link,useSearchParams} from 'react-router'
import {useQuery,useMutation} from '@tanstack/react-query'
import {fetchJson,apiDelete} from '@/api/client'
import {useAuth} from '@/contexts/AuthContext'
import {useTenantCollection} from '@/hooks/useTenantCollection'
import {Markdown} from '@/components/shared/Markdown'
import {WorkspaceState} from './WorkspaceState'
import {savedContextLabels,savedContextHref} from '@/lib/workspace'
interface Conversation {id:string;title:string;updated_at:string;view_context?:unknown}
interface StoredMessage {id:string;role:string;content:string;created_at?:string}

export function SavedConversations(){
 const {user,activeTenant}=useAuth()
 const query=useTenantCollection<Conversation>('/conversations')
 const [params,setParams]=useSearchParams(),selected=params.get('conversation')
 const [search,setSearch]=useState(''),[page,setPage]=useState(0),[confirm,setConfirm]=useState<string|null>(null)
 const setSelected=(id:string|null)=>{const next=new URLSearchParams(params);if(id)next.set('conversation',id);else next.delete('conversation');setParams(next)}
 const record=query.data?.find(row=>row.id===selected)
 const context=savedContextLabels(record?.view_context)
 const messages=useQuery({queryKey:['workspace',user?.id,activeTenant?.id,'conversation',selected,page],queryFn:()=>fetchJson<StoredMessage[]>(`/conversations/${encodeURIComponent(selected!)}/messages`,{offset:String(page*100),limit:'100'}),enabled:Boolean(user&&activeTenant&&record),retry:false})
 const remove=useMutation({mutationFn:(id:string)=>apiDelete(`/conversations/${encodeURIComponent(id)}`),onSuccess:()=>{setConfirm(null);setSelected(null);void query.refetch()}})
 const rows=(query.data??[]).filter(row=>row.title.toLowerCase().includes(search.toLowerCase()))
 return <div><label className='workspace-search'>Search conversations<input type='search' value={search} onChange={event=>setSearch(event.target.value)} /></label><WorkspaceState loading={query.isPending} error={query.error} retry={()=>void query.refetch()} empty={!query.isPending&&!query.error&&!query.data?.length?'No saved conversations yet':undefined} />
  {!query.error&&rows.length>0&&<section className='app-panel'><h2>Conversations</h2><div className='access-table-scroll'><table aria-label='Saved conversations'><thead><tr><th>Title</th><th>Updated</th><th>Actions</th></tr></thead><tbody>{rows.map(row=><tr key={row.id}><th scope='row'>{row.title}</th><td>{new Date(row.updated_at).toLocaleDateString('en-GB')}</td><td><div className='workspace-actions'><button type='button' className='app-panel-button' onClick={()=>{setSelected(row.id);setPage(0)}}>Open conversation</button>{confirm===row.id?<><button type='button' className='app-panel-button' disabled={remove.isPending} onClick={()=>remove.mutate(row.id)}>Confirm delete</button><button type='button' className='app-panel-button' onClick={()=>setConfirm(null)}>Cancel</button></>:<button type='button' className='app-panel-button' onClick={()=>setConfirm(row.id)}>Delete conversation</button>}</div></td></tr>)}</tbody></table></div></section>}
  {!query.error&&Boolean(query.data?.length)&&!rows.length&&<p className='app-panel'>No conversations match this search.</p>}{remove.error&&<p role='alert'>{remove.error.message}</p>}
  {record&&<section className='app-panel mt-4'><h2>{record.title}</h2>{context.context?<p>Starting context: {context.country} · {context.region} · {context.network}. <Link className='app-text-link' to={savedContextHref(context.context)}>Open starting view</Link></p>:<p>Original context was not stored. No country or network date is inferred.</p>}<WorkspaceState loading={messages.isPending} error={messages.error} retry={()=>void messages.refetch()} />{messages.data?.map(message=><article key={message.id} className='workspace-stored-message'><h3>{message.role==='assistant'?'Aequitas':message.role==='user'?'User':message.role}</h3><Markdown content={message.content} /></article>)}{messages.data?.length===0&&<p>No stored messages in this page.</p>}<div className='service-pagination'><span>Message page {page+1} · up to 100 stored messages</span><button type='button' className='app-panel-button' disabled={page===0||messages.isFetching} onClick={()=>setPage(page-1)}>Previous message page</button><button type='button' className='app-panel-button' disabled={messages.data?.length!==100||messages.isFetching} onClick={()=>setPage(page+1)}>Next message page</button></div></section>}
 </div>
}
