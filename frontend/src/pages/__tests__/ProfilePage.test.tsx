import {fireEvent,render,screen,waitFor} from '@testing-library/react'
import {beforeEach,describe,expect,it,vi} from 'vitest'
import {QueryClient,QueryClientProvider} from '@tanstack/react-query'
import {MemoryRouter} from 'react-router'
import {AuthContext} from '@/contexts/AuthContext'
import ProfilePage from '../ProfilePage'
const api=vi.hoisted(()=>({fetchJson:vi.fn(),apiPost:vi.fn(),apiPatch:vi.fn()}))
vi.mock('@/api/client',()=>api)
const auth={user:{id:'unit',email:'unit@example.test',display_name:'Unit user'},activeTenant:{id:'unit-workspace',name:'Unit workspace',slug:'unit'},memberships:[],role:'member',loading:false,signOut:vi.fn(),refresh:vi.fn()}
function mount(){render(<QueryClientProvider client={new QueryClient({defaultOptions:{queries:{retry:false}}})}><AuthContext.Provider value={auth}><MemoryRouter><ProfilePage /></MemoryRouter></AuthContext.Provider></QueryClientProvider>)}
describe('Account editing (isolated fixtures)',()=>{
 beforeEach(()=>Object.values(api).forEach(mock=>mock.mockReset()))
 it('preserves existing interests and saves only an explicit selection',async()=>{
  api.fetchJson.mockResolvedValue({policy_interests:['Stored custom interest']})
  api.apiPatch.mockResolvedValue({policy_interests:['Stored custom interest','Accessibility']})
  mount()
  await screen.findByRole('button',{name:'Stored custom interest'})
  expect(screen.getByText('unit@example.test')).toBeInTheDocument()
  fireEvent.click(screen.getByRole('button',{name:'Accessibility'}))
  expect(api.apiPatch).not.toHaveBeenCalled()
  fireEvent.click(screen.getByRole('button',{name:'Save interests'}))
  await screen.findByText('Policy interests saved.')
  expect(api.apiPatch).toHaveBeenCalledWith('/profile',{policy_interests:['Stored custom interest','Accessibility']})
  expect(screen.getByRole('button',{name:'Save interests'})).toBeDisabled()
 })
 it('reports a load failure and retries without replacing saved choices with empty data',async()=>{
  api.fetchJson.mockRejectedValueOnce(new Error('Offline')).mockResolvedValueOnce({policy_interests:['Accessibility']})
  mount()
  await screen.findByRole('button',{name:'Retry profile'})
  expect(screen.queryByRole('button',{name:'Save interests'})).not.toBeInTheDocument()
  fireEvent.click(screen.getByRole('button',{name:'Retry profile'}))
  await waitFor(()=>expect(screen.getByRole('button',{name:'Accessibility'})).toHaveAttribute('aria-pressed','true'))
  expect(api.apiPatch).not.toHaveBeenCalled()
 })
})
