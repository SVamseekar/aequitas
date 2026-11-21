import {render,screen,within} from '@testing-library/react'
import {MemoryRouter} from 'react-router'
import {describe,expect,it} from 'vitest'
import type {SectionItem} from '@/api/types'
import {SectionCard} from '../SectionCard'
const section:SectionItem={section_id:'a1_route_density',dimension:'accessibility',stats:{best:{name:'Actual high region',value:12},worst:{name:'Actual low region',value:0},national_avg:6,unit:'routes'},chart_data:{},narrative:'Unsupported: this proves a guaranteed benefit-cost ratio of 3.',suppressed:false}
describe('Visible chart findings',()=>{
 it('shows actual findings beside the chart without replacing them with method text',()=>{
  render(<MemoryRouter><SectionCard section={section} featured /></MemoryRouter>)
  const findings=screen.getByRole('region',{name:'Key points'})
  expect(findings).toBeVisible()
  expect(within(findings).getByText('Actual high region')).toBeVisible()
  expect(findings).toHaveTextContent('12.00')
  expect(findings).toHaveTextContent('0.00')
  expect(findings.closest('details')).toBeNull()
  expect(screen.queryByText(/guaranteed benefit-cost/)).toBeNull()
 })
})
