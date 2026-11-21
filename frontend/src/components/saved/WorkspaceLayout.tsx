import {NavLink} from 'react-router'
import type {ReactNode} from 'react'
import {useAuth} from '@/contexts/AuthContext'

export function WorkspaceLayout({children}:{children:ReactNode}){
 const {activeTenant}=useAuth()
 return <div className='workspace-page'><div className='app-page-heading'><div><p>{activeTenant?.name??'Workspace'}</p><h1>Saved work</h1><p>Analyses, policy notes, regions and conversations for your workspace.</p></div></div><nav className='evidence-tabs' aria-label='Saved work'>{[['/saved','Analyses'],['/notes','Policy notes'],['/regions','Regions'],['/conversations','Conversations']].map(([path,label])=><NavLink key={path} to={path}>{label}</NavLink>)}</nav>{children}</div>
}
