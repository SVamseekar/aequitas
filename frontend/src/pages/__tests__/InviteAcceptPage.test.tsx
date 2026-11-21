import {fireEvent,render,screen} from '@testing-library/react'
import {beforeEach,describe,expect,it,vi} from 'vitest'
import {QueryClient,QueryClientProvider} from '@tanstack/react-query'
import {MemoryRouter,Routes,Route} from 'react-router'
import {HelmetProvider} from 'react-helmet-async'
import {AuthContext} from '@/contexts/AuthContext'
import InviteAcceptPage from '../InviteAcceptPage'
const api=vi.hoisted(()=>({fetchJson:vi.fn(),apiPost:vi.fn()}))
vi.mock('@/api/client',()=>api)
const auth={user:{id:'unit',email:'unit@example.test',display_name:null},activeTenant:null,memberships:[],role:null,loading:false,signOut:vi.fn(),refresh:vi.fn()}
function mount(signedIn=true){render(<HelmetProvider><QueryClientProvider client={new QueryClient({defaultOptions:{queries:{retry:false}}})}><AuthContext.Provider value={{...auth,user:signedIn?auth.user:null}}><MemoryRouter initialEntries={['/invite/unit-proof']}><Routes><Route path='/invite/:token' element={<InviteAcceptPage />} /></Routes></MemoryRouter></AuthContext.Provider></QueryClientProvider></HelmetProvider>)}
describe('Invitation states (isolated fixtures)',()=>{
 beforeEach(()=>{api.fetchJson.mockReset();api.apiPost.mockReset();auth.refresh.mockReset()})
 it('waits for real lookup before offering acceptance',()=>{
  api.fetchJson.mockReturnValue(new Promise(()=>{}));mount()
  expect(screen.getByRole('status')).toHaveTextContent('Checking invitation')
  expect(screen.queryByRole('button',{name:'Accept invitation'})).not.toBeInTheDocument()
 })
 it('keeps unavailable invitation and retry distinct from acceptance',async()=>{
  api.fetchJson.mockRejectedValueOnce(new Error('API 404')).mockResolvedValueOnce({tenant_name:'Isolated workspace',role:'member'});mount()
  await screen.findByRole('heading',{name:'Invitation unavailable'})
  expect(api.apiPost).not.toHaveBeenCalled()
  fireEvent.click(screen.getByRole('button',{name:'Retry invitation'}))
  await screen.findByRole('button',{name:'Accept invitation'})
 })
 it('retains the invitation through the sign-in link',async()=>{
  api.fetchJson.mockResolvedValue({tenant_name:'Isolated workspace',role:'member'});mount(false)
  const link=await screen.findByRole('link',{name:'Continue with Google'})
  expect(new URL(link.getAttribute('href')!,'http://localhost').searchParams.get('returnTo')).toBe('/invite/unit-proof')
  expect(api.apiPost).not.toHaveBeenCalled()
 })
 it('accepts only after a click and shows actual successful state',async()=>{
  api.fetchJson.mockResolvedValue({tenant_name:'Isolated workspace',role:'member'});api.apiPost.mockResolvedValue({ok:true});mount()
  fireEvent.click(await screen.findByRole('button',{name:'Accept invitation'}))
  await screen.findByText('Invitation accepted')
  expect(api.apiPost).toHaveBeenCalledWith('/invites/unit-proof/accept')
  expect(auth.refresh).toHaveBeenCalledTimes(1)
  expect(screen.getByRole('link',{name:'Open your workspace'})).toHaveAttribute('href','/saved')
 })
})
