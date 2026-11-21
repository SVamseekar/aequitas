import {fireEvent,render,screen,waitFor} from '@testing-library/react'
import {afterEach,beforeEach,describe,expect,it,vi} from 'vitest'
import {QueryClient,QueryClientProvider} from '@tanstack/react-query'
import {MemoryRouter} from 'react-router'
import {AuthContext} from '@/contexts/AuthContext'
import {SavedAnalyses} from '../SavedAnalyses'
import {SavedConversations} from '../SavedConversations'
import {PolicyNoteForm} from '../PolicyNoteForm'
import {WorkspaceMembers} from '@/components/account/WorkspaceMembers'

const api=vi.hoisted(()=>({fetchJson:vi.fn(),apiPost:vi.fn(),apiPatch:vi.fn(),apiDelete:vi.fn()}))
vi.mock('@/api/client',()=>api)
vi.mock('@/api/hooks',()=>({usePackDates:()=>({data:{ireland:{dates:[{pack_id:'2026-08-01',as_of:'2026-08-01',current:true}]}}})}))
const base={user:{id:'unit-user',email:'unit@example.test',display_name:'Unit user'},activeTenant:{id:'unit-a',name:'Unit workspace',slug:'unit'},memberships:[],role:'member',loading:false,signOut:vi.fn(),refresh:vi.fn()}
const stored={id:'unit-record',title:'Stored finding',content:'Saved actual text',dimension:'accessibility',section_id:'a1',tags:[],created_at:'2026-10-24T00:00:00Z'}
function view(children:React.ReactNode,auth=base,path='/saved'){
 const client=new QueryClient({defaultOptions:{queries:{retry:false},mutations:{retry:false}}})
 return {client,...render(<QueryClientProvider client={client}><AuthContext.Provider value={auth}><MemoryRouter initialEntries={[path]}>{children}</MemoryRouter></AuthContext.Provider></QueryClientProvider>)}
}
describe('Workspace records and roles (isolated fixtures)',()=>{
 beforeEach(()=>{Object.values(api).forEach(mock=>mock.mockReset())})
 afterEach(()=>vi.clearAllMocks())
 it('keeps legacy country/date unavailable and asks confirmation before deletion',async()=>{
  api.fetchJson.mockResolvedValue([stored]);api.apiDelete.mockResolvedValue(undefined)
  view(<SavedAnalyses />)
  await screen.findByRole('button',{name:'Open Stored finding'})
  expect(screen.getByText('Not stored')).toBeInTheDocument()
  expect(screen.getByText('Date not stored')).toBeInTheDocument()
  fireEvent.click(screen.getByRole('button',{name:'Open Stored finding'}))
  expect(screen.queryByRole('link',{name:'Open original view'})).not.toBeInTheDocument()
  fireEvent.click(screen.getByRole('button',{name:'Delete Stored finding'}))
  expect(api.apiDelete).not.toHaveBeenCalled()
  fireEvent.click(screen.getByRole('button',{name:'Confirm delete'}))
  await waitFor(()=>expect(api.apiDelete).toHaveBeenCalledWith('/saved-analyses/unit-record'))
 })
 it('does not reuse previous tenant rows during a workspace switch',async()=>{
  api.fetchJson.mockResolvedValueOnce([stored]).mockReturnValueOnce(new Promise(()=>{}))
  const client=new QueryClient({defaultOptions:{queries:{retry:false}}})
  const tree=(id:string)=><QueryClientProvider client={client}><AuthContext.Provider value={{...base,activeTenant:{...base.activeTenant,id}}}><MemoryRouter><SavedAnalyses /></MemoryRouter></AuthContext.Provider></QueryClientProvider>
  const rendered=render(tree('unit-a'))
  await screen.findByText('Stored finding')
  rendered.rerender(tree('unit-b'))
  expect(screen.queryByText('Stored finding')).not.toBeInTheDocument()
  expect(screen.getByRole('status')).toHaveTextContent('Loading')
  await waitFor(()=>expect(api.fetchJson).toHaveBeenCalledTimes(2))
 })
 it('shows an error with retry, then a distinct empty state',async()=>{
  api.fetchJson.mockRejectedValueOnce(new Error('Offline')).mockResolvedValueOnce([])
  view(<SavedAnalyses />)
  await screen.findByRole('alert')
  expect(screen.queryByText('No saved analyses yet')).not.toBeInTheDocument()
  fireEvent.click(screen.getByRole('button',{name:'Retry workspace records'}))
  await screen.findByText('No saved analyses yet')
 })
 it('replaces stale as_of when saving the chosen network and retains genuine region',async()=>{
  api.apiPost.mockResolvedValue({id:'note'});const saved=vi.fn()
  view(<PolicyNoteForm initialContext={{country:'ireland',page:'access',query:{region:'dublin',as_of:'2026-07-01',urban_rural:'urban'}}} onSaved={saved} />)
  fireEvent.change(screen.getByLabelText('Network'),{target:{value:'2026-08-01'}})
  fireEvent.change(screen.getByLabelText('Your note'),{target:{value:'Actual note'}})
  fireEvent.click(screen.getByRole('button',{name:'Priority'}))
  fireEvent.click(screen.getByRole('button',{name:'Save note'}))
  await waitFor(()=>expect(saved).toHaveBeenCalled())
  const body=api.apiPost.mock.calls[0][1]
  expect(body).toMatchObject({region:'dublin',stance:'priority',thesis:'Actual note',view_context:{country:'ireland',query:{region:'dublin',urban_rural:'urban',pack:'2026-08-01'}}})
  expect(body.view_context.query.as_of).toBeUndefined()
 })
 it('does not fetch another tenant conversation ID from a URL',async()=>{
  api.fetchJson.mockResolvedValue([])
  view(<SavedConversations />,base,'/conversations?conversation=other-tenant')
  await screen.findByText('No saved conversations yet')
  expect(api.fetchJson).toHaveBeenCalledTimes(1)
  expect(api.fetchJson).toHaveBeenCalledWith('/conversations')
 })
 it('hides admin actions for members and never fetches a member list',()=>{
  view(<WorkspaceMembers />)
  expect(screen.getByText(/available to workspace admins/)).toBeInTheDocument()
  expect(screen.queryByRole('button',{name:'Create invite'})).not.toBeInTheDocument()
  expect(api.fetchJson).not.toHaveBeenCalled()
 })
 it('only creates an invite after explicit form submission and reports delivery accurately',async()=>{
  api.fetchJson.mockResolvedValue([{user_id:'unit-user',email:'unit@example.test',display_name:null,role:'admin'}])
  api.apiPost.mockResolvedValue({link:'https://example.test/invite/unit-only',email_sent:false})
  view(<WorkspaceMembers />,{...base,role:'admin'})
  await screen.findByText('Your account')
  expect(screen.queryByRole('button',{name:'Remove member'})).not.toBeInTheDocument()
  fireEvent.change(screen.getByLabelText('Email'),{target:{value:'colleague@example.test'}})
  expect(api.apiPost).not.toHaveBeenCalled()
  fireEvent.click(screen.getByRole('button',{name:'Create invite'}))
  await screen.findByText(/Email was not sent/)
  expect(api.apiPost).toHaveBeenCalledWith('/tenants/unit-a/invites',{email:'colleague@example.test',role:'member'})
 })
})
