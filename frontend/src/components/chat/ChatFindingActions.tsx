import {Link} from 'react-router'
import {useMutation,useQueryClient} from '@tanstack/react-query'
import {apiPost} from '@/api/client'
import {useAuth} from '@/contexts/AuthContext'
import {savedContext,savedContextHref} from '@/lib/workspace'
import {EVIDENCE_VIEWS} from '@/lib/evidenceViews'
import {DIMENSION_API_IDS} from '@/lib/constants'
import type {Message} from '@/hooks/useChat'

function sourcePage(id:string):string|null {
 for(const [dimension,views]of Object.entries(EVIDENCE_VIEWS))if(views.some(view=>view.sections.includes(id)))return Object.entries(DIMENSION_API_IDS).find(([page,api])=>api===dimension&&!page.includes('_'))?.[0]??(dimension==='equity'||dimension==='correlations'||dimension==='scenarios'?dimension:null)
 return null
}
export function ChatFindingActions({message,question,streaming}:{message:Message;question:string;streaming:boolean}){
 const {user,activeTenant}=useAuth(),client=useQueryClient(),context=savedContext(message.viewContext)
 const save=useMutation({mutationFn:()=>apiPost('/saved-analyses',{title:(question||message.content).slice(0,160),content:message.content,dimension:context?DIMENSION_API_IDS[context.page]??context.page:null,section_id:message.sources?.[0]??null,tags:[],...(context?{view_context:context}:{})}),onSuccess:()=>{void client.invalidateQueries({queryKey:['workspace',user?.id,activeTenant?.id,'/saved-analyses']})}})
 if(!message.content.trim()||streaming)return null
 if(message.status==='error')return <p className='text-xs' role='status'>Answer incomplete. It cannot be saved as a finding.</p>
 return <div className='chat-finding-actions'>{Boolean(message.sources?.length)&&<section><h3>Source exhibits</h3><ul>{message.sources?.map(id=>{const page=sourcePage(id);return <li key={id}>{context&&page?<Link className='app-text-link' to={savedContextHref({...context,page,query:{...context.query,view:id,exhibit:id}})}>Open source {id}</Link>:id}</li>})}</ul></section>}
  {user?<button type='button' className='app-panel-button' disabled={save.isPending||save.isSuccess} onClick={()=>save.mutate()}>{save.isSuccess?'Finding saved':save.isPending?'Saving…':'Save finding'}</button>:<Link className='app-text-link' to='/auth'>Sign in to save this finding</Link>}{save.error&&<p role='alert'>{save.error.message}</p>}
 </div>
}
