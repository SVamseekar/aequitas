import {act,fireEvent,render,screen,waitFor} from '@testing-library/react'
import {beforeEach,describe,expect,it,vi} from 'vitest'
import {QueryClient,QueryClientProvider} from '@tanstack/react-query'
import {MemoryRouter} from 'react-router'
import {useEffect} from 'react'
import {ResearchExport} from '../ResearchExport'
const state=vi.hoisted(()=>({country:'ireland' as 'ireland'|'netherlands',region:'dublin',urbanRural:'urban',pack:'2026-08-01',mode:'bus',fetch:vi.fn(),mapReady:true,finishMap:()=>undefined as void}))
vi.mock('@/api/client',()=>({fetchJson:state.fetch}))
vi.mock('@/api/hooks',()=>({
 useFilters:()=>state,
 usePackDates:()=>({data:{ireland:{dates:[{pack_id:'2026-08-01',as_of:'2026-08-01',current:true}]}}}),
 useSections:()=>({data:{sections:[{section_id:'b3_weekend_penalty',stats:{pct_sunday_desert:0}}]}}),
 useMapLayer:()=>({data:{geography:'ireland_county',data:[{area_code:'dublin',area_name:'Dublin',value:0}]}}),
}))
vi.mock('@/components/charts/ChoroplethMap',()=>({default:function MapFixture({onStatus}:{onStatus?:(status:'ready'|'unavailable')=>void}){useEffect(()=>{state.finishMap=()=>onStatus?.('ready');if(state.mapReady)onStatus?.('ready')},[onStatus]);return <div>Actual map renderer fixture</div>}}))
const source={place:'Dublin · urban',filter:{country:'ireland',region:'dublin',urban_rural:'urban'},vintages:{network:'Stored network source',census:'Stored census source'},score:{score:0,components:[{id:'pop_within_400m',value:0},{id:'weekday_frequency',value:null},{id:'evening_served',value:0.5}],n_areas:12,note:null},reach:{available:false,note:'No stored calculation'},caveats:['Source caveat']}
function mount(){render(<QueryClientProvider client={new QueryClient({defaultOptions:{queries:{retry:false}}})}><MemoryRouter initialEntries={['/app/ireland?view=export&region=dublin&urban_rural=urban&pack=2026-08-01']}><ResearchExport /></MemoryRouter></QueryClientProvider>)}
describe('Research preview from stored data',()=>{
 beforeEach(()=>{state.country='ireland';state.region='dublin';state.pack='2026-08-01';state.mapReady=true;state.fetch.mockReset()})
 it('waits for the newly selected map before permitting print after a scope change',async()=>{
  state.fetch.mockImplementation((_path:string,context:{region:string})=>Promise.resolve({...source,filter:{...source.filter,region:context.region}}))
  const client=new QueryClient({defaultOptions:{queries:{retry:false}}})
  const content=()=> <QueryClientProvider client={client}><MemoryRouter initialEntries={['/app/ireland?view=export']}><ResearchExport /></MemoryRouter></QueryClientProvider>
  const view=render(content())
  await waitFor(()=>expect(screen.getByRole('button',{name:'Print this preview'})).toBeEnabled())
  const finishPreviousMap=state.finishMap
  state.mapReady=false;state.region='cork';view.rerender(content())
  await waitFor(()=>expect(state.fetch).toHaveBeenLastCalledWith('/export/pack.json',expect.objectContaining({region:'cork'})))
  await screen.findByRole('heading',{name:'Aequitas research briefing — Ireland'})
  expect(screen.getByRole('button',{name:'Print this preview'})).toBeDisabled()
  const finishCurrentMap=state.finishMap
  act(()=>finishPreviousMap())
  expect(screen.getByRole('button',{name:'Print this preview'})).toBeDisabled()
  act(()=>finishCurrentMap())
  expect(screen.getByRole('button',{name:'Print this preview'})).toBeEnabled()
 })
 it('retains exact scope, zero, missing values and genuine source metadata',async()=>{
  state.fetch.mockResolvedValue(source);mount()
  await screen.findByRole('heading',{name:'Aequitas research briefing — Ireland'})
  expect(state.fetch).toHaveBeenCalledWith('/export/pack.json',expect.objectContaining({country:'ireland',region:'dublin',urban_rural:'urban',pack:'2026-08-01'}))
  expect(screen.getByText('Stored census source')).toBeInTheDocument()
  expect(screen.getByText('0.0 / 100')).toBeInTheDocument()
  expect(screen.getByText('0.0%')).toBeInTheDocument()
  expect(screen.getByText('Unavailable')).toBeInTheDocument()
  const link=screen.getByRole('link',{name:'Printable HTML (tables)'})
  expect(new URL(link.getAttribute('href')!,'http://localhost').searchParams.get('country')).toBe('ireland')
  expect(screen.getByText('No stored calculation')).toBeInTheDocument()
 })
 it('does not fetch or export a historical pack under current results',()=>{
  state.pack='2020-01-01';mount()
  expect(screen.getByText(/Historical research packs are unavailable/)).toBeInTheDocument()
  expect(state.fetch).not.toHaveBeenCalled()
  expect(screen.queryByRole('link',{name:'Printable HTML (tables)'})).not.toBeInTheDocument()
 })
 it('does not fall back to England for an unavailable Netherlands pack',()=>{
  state.country='netherlands';mount()
  expect(screen.getByText(/Netherlands research pack is not available/)).toBeInTheDocument()
  expect(state.fetch).not.toHaveBeenCalled()
 })
 it('retains scope on load failure and permits retry',async()=>{
  state.fetch.mockRejectedValueOnce(new Error('Offline')).mockResolvedValueOnce(source);mount()
  await screen.findByRole('alert')
  expect(screen.queryByRole('button',{name:'Print this preview'})).not.toBeInTheDocument()
  fireEvent.click(screen.getByRole('button',{name:'Retry research pack'}))
  await waitFor(()=>expect(screen.getByRole('button',{name:'Print this preview'})).toBeEnabled())
 })
})
