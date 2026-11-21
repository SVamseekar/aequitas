import {fireEvent,render,screen,waitFor} from '@testing-library/react'
import {beforeEach,describe,expect,it,vi} from 'vitest'
import {QueryClient,QueryClientProvider} from '@tanstack/react-query'
import {MemoryRouter} from 'react-router'
import {AuthContext} from '@/contexts/AuthContext'
import {ChatFindingActions} from '../ChatFindingActions'
import {ChatConversationSave} from '../ChatConversationSave'
import type {Message} from '@/hooks/useChat'
const request=vi.hoisted(()=>vi.fn())
vi.mock('@/api/client',()=>({apiPost:request}))
const context={country:'ireland',page:'access',query:{region:'dublin',urban_rural:'urban',pack:'2026-08-01'}}
const answer:Message={id:'unit-answer',role:'assistant',content:'Isolated saved answer',sources:['a1_route_density','unknown-source'],viewContext:context}
const auth={user:{id:'unit',email:'unit@example.test',display_name:null},activeTenant:{id:'unit-workspace',name:'Unit',slug:'unit'},memberships:[],role:'member',loading:false,signOut:vi.fn(),refresh:vi.fn()}
function mount(content:React.ReactNode,user=true){return render(<QueryClientProvider client={new QueryClient()}><AuthContext.Provider value={{...auth,user:user?auth.user:null}}><MemoryRouter>{content}</MemoryRouter></AuthContext.Provider></QueryClientProvider>)}
describe('Explicit assistant saving (isolated fixtures)',()=>{
 beforeEach(()=>{request.mockReset()})
 it('links known sources with original scope and saves actual answer only on click',async()=>{
  request.mockResolvedValue({id:'saved'})
  mount(<ChatFindingActions message={answer} question='Actual question' streaming={false} />)
  const href=screen.getByRole('link',{name:'Open source a1_route_density'}).getAttribute('href')!
  expect(href).toContain('/app/ireland/access?')
  expect(new URL(href,'http://localhost').searchParams.get('region')).toBe('dublin')
  expect(screen.getByText('unknown-source').tagName).toBe('LI')
  expect(request).not.toHaveBeenCalled()
  fireEvent.click(screen.getByRole('button',{name:'Save finding'}))
  await screen.findByRole('button',{name:'Finding saved'})
  expect(request).toHaveBeenCalledWith('/saved-analyses',expect.objectContaining({content:answer.content,title:'Actual question',view_context:context,section_id:'a1_route_density'}))
 })
 it('does not offer saving to anonymous users or while an answer is incomplete',()=>{
  const mounted=mount(<ChatFindingActions message={answer} question='Question' streaming={true} />)
  expect(screen.queryByRole('button',{name:'Save finding'})).not.toBeInTheDocument()
  mounted.unmount()
  mount(<ChatFindingActions message={answer} question='Question' streaming={false} />,false)
  expect(screen.getByRole('link',{name:'Sign in to save this finding'})).toBeInTheDocument()
  expect(request).not.toHaveBeenCalled()
 })
 it('stores an atomic conversation copy with completed messages and returned record link',async()=>{
  request.mockResolvedValue({id:'unit-conversation'})
  const messages:Message[]=[{id:'unit-question',role:'user',content:'Actual question',viewContext:context},answer]
  mount(<ChatConversationSave messages={messages} streaming={false} />)
  fireEvent.click(screen.getByRole('button',{name:'Save conversation copy'}))
  await screen.findByRole('button',{name:'Conversation saved'})
  expect(request).toHaveBeenCalledWith('/conversations',{title:'Actual question',messages:[{role:'user',content:'Actual question'},{role:'assistant',content:answer.content}],view_context:context})
  expect(screen.getByRole('link',{name:'Open saved conversation'})).toHaveAttribute('href','/conversations?conversation=unit-conversation')
  expect(screen.getByRole('button',{name:'Conversation saved'})).toBeDisabled()
 })
 it('retains the transcript and permits retry when saving fails',async()=>{
  request.mockRejectedValue(new Error('Save failed'))
  mount(<ChatConversationSave messages={[answer]} streaming={false} />)
  fireEvent.click(screen.getByRole('button',{name:'Save conversation copy'}))
  await waitFor(()=>expect(screen.getByRole('alert')).toHaveTextContent('Save failed'))
  expect(screen.getByRole('button',{name:'Save conversation copy'})).toBeEnabled()
 })
 it('does not save an incomplete finding or silently persist its partial text',async()=>{
  request.mockResolvedValue({id:'unit-copy'})
  const partial:Message={...answer,status:'error'}
  const finding=mount(<ChatFindingActions message={partial} question='Question' streaming={false} />)
  expect(screen.getByText(/Answer incomplete/)).toBeInTheDocument()
  expect(screen.queryByRole('button',{name:'Save finding'})).not.toBeInTheDocument()
  finding.unmount()
  mount(<ChatConversationSave messages={[{id:'question',role:'user',content:'Question'},partial]} streaming={false} />)
  expect(screen.getByText('Incomplete answers are excluded from saved copies.')).toBeInTheDocument()
  fireEvent.click(screen.getByRole('button',{name:'Save conversation copy'}))
  await screen.findByRole('button',{name:'Conversation saved'})
  expect(request.mock.calls[0][1].messages).toEqual([{role:'user',content:'Question'}])
 })
})
