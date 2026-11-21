import {useState} from 'react'
import {Link,useParams} from 'react-router'
import {useQuery,useMutation} from '@tanstack/react-query'
import {useAuth} from '@/contexts/AuthContext'
import {fetchJson,apiPost} from '@/api/client'
import {Seo} from '@/components/shared/Seo'

export default function InviteAcceptPage(){
 const {token}=useParams<{token:string}>(),{user,loading,refresh}=useAuth()
 const [accepted,setAccepted]=useState(false)
 const invitation=useQuery({queryKey:['invitation',token],queryFn:()=>fetchJson<{tenant_name:string;role:string}>(`/invites/${encodeURIComponent(token!)}`),enabled:Boolean(token),retry:false})
 const accept=useMutation({mutationFn:async()=>{await apiPost(`/invites/${encodeURIComponent(token!)}/accept`);await refresh()},onSuccess:()=>setAccepted(true)})
 const returnTo=`/invite/${encodeURIComponent(token??'')}`
 const unavailable=!token||invitation.error
 return <div className='app-redesign invite-layout'>
  <Seo title='Accept invitation — Aequitas' path='/auth' noindex />
  <Link to='/' className='app-wordmark'>Aequitas</Link>
  <main className='app-panel invite-panel'>
   {loading||invitation.isPending?<p role='status'>Checking invitation…</p>:unavailable?<><h1>Invitation unavailable</h1><p>This invitation link is no longer available or could not be loaded.</p><p>Ask your workspace admin for a new link.</p><button type='button' className='app-panel-button' onClick={()=>void invitation.refetch()}>Retry invitation</button></>:accepted?<><h1>Accept invitation</h1><p>You’re joining {invitation.data?.tenant_name} as a {invitation.data?.role}.</p><p className='invite-success' role='status'>Invitation accepted</p><Link to='/saved' className='app-btn-primary'>Open your workspace</Link></>:<><h1>{user?'Accept invitation':'You’re invited'}</h1><p>Join {invitation.data?.tenant_name}</p><p className='invite-role'>Invited role <strong>{invitation.data?.role==='admin'?'Admin':invitation.data?.role==='member'?'Member':invitation.data?.role}</strong></p><p>You’ve been invited to join this workspace as a {invitation.data?.role}.</p>
    {user?<button type='button' className='app-btn-primary' disabled={accept.isPending} onClick={()=>accept.mutate()}>{accept.isPending?'Accepting…':'Accept invitation'}</button>:<Link className='app-btn-primary' to={`/auth?${new URLSearchParams({returnTo})}`}>Continue with Google</Link>}
    {accept.error&&<p role='alert'>{accept.error.message}</p>}<p className='invite-terms'>By continuing, you agree to our <Link className='app-text-link' to='/privacy'>Privacy Policy</Link> and <Link className='app-text-link' to='/terms'>Terms of Service</Link>.</p></>}
  </main>
 </div>
}
