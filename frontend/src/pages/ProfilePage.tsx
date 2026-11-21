import {useState} from 'react'
import {useNavigate} from 'react-router'
import {useMutation,useQuery,useQueryClient} from '@tanstack/react-query'
import {useAuth} from '@/contexts/AuthContext'
import {fetchJson,apiPatch,apiPost} from '@/api/client'
import {WorkspaceMembers} from '@/components/account/WorkspaceMembers'
import {User} from 'lucide-react'

const INTERESTS=['Equity & Deprivation','Accessibility','Service Quality','Route Network','Socio-Economic & ML','Economic Appraisal','Bus Services Act 2025','Policy Scenarios']
interface Profile {policy_interests:string[]}

export default function ProfilePage(){
 const {user,activeTenant,role,memberships,signOut,refresh}=useAuth(),navigate=useNavigate(),client=useQueryClient()
 const [draft,setDraft]=useState<string[]|null>(null)
 const key=['profile',user?.id]
 const profile=useQuery({queryKey:key,queryFn:()=>fetchJson<Profile>('/profile'),enabled:Boolean(user),retry:false})
 const selected=draft??profile.data?.policy_interests??[]
 const save=useMutation({mutationFn:()=>apiPatch<Profile>('/profile',{policy_interests:selected}),onSuccess:result=>{client.setQueryData(key,result);setDraft(null)}})
 const switchWorkspace=useMutation({mutationFn:async(id:string)=>{await apiPost('/session/switch-tenant',{tenant_id:id});await refresh();await client.invalidateQueries({queryKey:['workspace']})}})
 const signout=useMutation({mutationFn:signOut,onSuccess:()=>{client.removeQueries({queryKey:['workspace']});client.removeQueries({queryKey:['members']});client.removeQueries({queryKey:['profile']});navigate('/auth')}})
 if(!user)return null
 return <div className='account-page'><div className='app-page-heading'><div><h1>Account & workspace</h1><p>Manage your account, policy interests and workspace members.</p></div></div>
  <section className='app-panel mb-4'><h2>Account</h2><div className='account-identity'><span className='account-avatar'><User aria-hidden='true' /></span><div><h3>{user.display_name??user.email}</h3><p>{user.email}</p><p>{activeTenant?.name??'Workspace'} · {role==='admin'?'Admin':role==='member'?'Member':role??'Role unavailable'}</p></div></div>
   <div className='account-interests'><h2>Policy interests</h2><p>Choose the topics you work on. Existing saved interests remain available.</p>{profile.isPending?<p role='status'>Loading policy interests…</p>:profile.error?<div role='alert'><p>Policy interests could not be loaded.</p><button type='button' className='app-panel-button' onClick={()=>void profile.refetch()}>Retry profile</button></div>:<><div className='account-interest-options'>{[...new Set([...INTERESTS,...selected])].map(interest=><button key={interest} type='button' aria-pressed={selected.includes(interest)} disabled={save.isPending} onClick={()=>setDraft(selected.includes(interest)?selected.filter(value=>value!==interest):[...selected,interest])}>{interest}</button>)}</div><div className='workspace-actions'><button type='button' className='app-btn-primary' disabled={save.isPending||draft===null} onClick={()=>save.mutate()}>{save.isPending?'Saving…':'Save interests'}</button>{draft!==null&&<button type='button' className='app-panel-button' disabled={save.isPending} onClick={()=>setDraft(null)}>Cancel changes</button>}</div></>}{save.error&&<p role='alert'>{save.error.message}</p>}{save.isSuccess&&draft===null&&<p role='status'>Policy interests saved.</p>}</div>
  </section>
  {memberships.length>1&&<section className='app-panel mb-4'><h2>Workspaces</h2><div className='account-workspaces'>{memberships.map(member=><button key={member.tenant_id} type='button' className='app-panel-button' aria-pressed={member.tenant_id===activeTenant?.id} disabled={switchWorkspace.isPending} onClick={()=>switchWorkspace.mutate(member.tenant_id)}>{member.tenant_name} · {member.role==='admin'?'Admin':member.role==='member'?'Member':member.role}</button>)}</div>{switchWorkspace.error&&<p role='alert'>{switchWorkspace.error.message}</p>}</section>}
  <WorkspaceMembers key={activeTenant?.id??'none'} /><div className='mt-4'><button type='button' className='app-panel-button' disabled={signout.isPending} onClick={()=>signout.mutate()}>{signout.isPending?'Signing out…':'Sign out'}</button>{signout.error&&<p role='alert'>{signout.error.message}</p>}</div>
 </div>
}
