import {render,screen} from '@testing-library/react'
import {MemoryRouter} from 'react-router'
import {describe,expect,it,vi} from 'vitest'
import {OverviewScore} from '../OverviewScore'
vi.mock('@/api/hooks',()=>({useFilters:()=>({country:'ireland',region:'all',urbanRural:'all',pack:'current',mode:'bus'}),useScore:()=>({data:{score:0,components:[{id:'pop_within_400m',label:'Coverage',value:0,weight_used:0.4},{id:'evening_served',label:'Evening',value:null,weight_used:0}]}})}))
describe('Reference score component details',()=>{
 it('shows the real component values and used weights, preserving observed zero and missing data',()=>{
  render(<MemoryRouter><OverviewScore fallbackScore={null} details /></MemoryRouter>)
  expect(screen.getByRole('heading',{name:'Component details'})).toBeInTheDocument()
  expect(screen.getByText('0.00 / 100')).toBeInTheDocument()
  expect(screen.getByText('Unavailable')).toBeInTheDocument()
  expect(screen.getByText('40% weight used')).toBeInTheDocument()
 })
})
