import {useState} from 'react'
import {Link} from 'react-router'
import {useMutation,useQueryClient} from '@tanstack/react-query'
import {apiPost} from '@/api/client'
import {useAuth} from '@/contexts/AuthContext'
import type {Message} from '@/hooks/useChat'
import {savedContext} from '@/lib/workspace'

export function ChatConversationSave({messages,streaming}:{messages:Message[];streaming:boolean}){
 const {user,activeTenant}=useAuth(),client=useQueryClient()
 const [saved,setSaved]=useState<{id:string;fingerprint:string}|null>(null)
 const rows=messages.filter(row=>row.content.trim()&&row.status!=='error'&&row.status!=='streaming'),fingerprint=rows.map(row=>`${row.id}:${row.content.length}`).join('|')
 const save=useMutation({throwOnError:false,mutationFn:async(snapshot:{rows:Message[];fingerprint:string})=>{
  const context=savedContext(snapshot.rows[0]?.viewContext)
  return apiPost<{id:string}>('/conversations',{title:(snapshot.rows.find(row=>row.role==='user')?.content??'Conversation').slice(0,160),messages:snapshot.rows.map(row=>({role:row.role,content:row.content})),...(context?{view_context:context}:{})})
 },onSuccess:(result,snapshot)=>{setSaved({id:result.id,fingerprint:snapshot.fingerprint});void client.invalidateQueries({queryKey:['workspace',user?.id,activeTenant?.id,'/conversations']})}})
 if(!user||!rows.length)return null
 return <div className='chat-conversation-save'><button type='button' className='app-panel-button' disabled={streaming||save.isPending||saved?.fingerprint===fingerprint||rows.length>200} onClick={()=>save.mutate({rows:[...rows],fingerprint})}>{save.isPending?'Saving conversation…':saved?.fingerprint===fingerprint?'Conversation saved':'Save conversation copy'}</button>{saved&&<Link className='app-text-link' to={`/conversations?conversation=${encodeURIComponent(saved.id)}`}>Open saved conversation</Link>}{messages.some(row=>row.status==='error')&&<p>Incomplete answers are excluded from saved copies.</p>}{rows.length>200&&<p>Saving a conversation copy supports up to 200 messages.</p>}{save.error&&<p role='alert'>{save.error.message}</p>}</div>
}
