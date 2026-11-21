import {render,screen,within} from '@testing-library/react'
import {MemoryRouter} from 'react-router'
import {describe,it,expect,vi} from 'vitest'
import type {SectionItem} from '@/api/types'
import {EquityEvidence} from '../EquityEvidence'
vi.mock('@/components/charts/ChartRenderer',()=>({ChartRenderer:()=>null}))
const source:SectionItem={section_id:'f1_gini',dimension:'equity',stats:{gini:0,palma:1,concentration_index:0,n_lsoas:12},chart_data:{},narrative:'Guaranteed policy effects',suppressed:false}
describe('reference equity composition',()=>{
 it('retains actual zero measures, source count and working provenance entry',()=>{
  render(<MemoryRouter><EquityEvidence section={source} /></MemoryRouter>)
  expect(screen.getByRole('heading',{name:'Gini coefficient'}).parentElement).toHaveTextContent('0.0000')
  expect(screen.getByText('12')).toBeVisible()
  expect(screen.getByRole('button',{name:'Show Gini coefficient provenance'})).toBeVisible()
  expect(screen.queryByText('Guaranteed policy effects')).toBeNull()
  expect(within(screen.getByRole('region',{name:'Key points'})).getAllByText('0.0000')).toHaveLength(2)
 })
 it('keeps suppressed observations unavailable',()=>{
  render(<MemoryRouter><EquityEvidence section={{...source,suppressed:true}} /></MemoryRouter>)
  expect(screen.getByText('Not available for this filter')).toBeVisible()
  expect(screen.queryByText('12')).toBeNull()
 })
 it('does not fill a missing source count with another population or zero',()=>{
  render(<MemoryRouter><EquityEvidence section={{...source,stats:{gini:0}}} /></MemoryRouter>)
  const count=screen.getByRole('heading',{name:'Small area count'}).parentElement!
  expect(count).toHaveTextContent('—')
 })
})
