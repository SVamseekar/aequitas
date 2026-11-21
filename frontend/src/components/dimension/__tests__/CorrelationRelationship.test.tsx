import { render, screen, within } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import type { SectionItem } from '@/api/types'
import { CorrelationRelationship } from '../CorrelationRelationship'
const section:SectionItem={section_id:'d1_coverage_deprivation',dimension:'correlations',stats:{r:0,n:300,p_value:0,strength:'negligible',direction:'none'},chart_data:{type:'scatter_regression',x_label:'IMD score',y_label:'Stops per 1,000 residents',data:[{id:'actual-area',x:0,y:0}]},narrative:'',suppressed:false}
describe('Relationship reference summary',()=>{
 it('keeps full-filter count separate from sample points and retains observed zero',async()=>{
  render(<CorrelationRelationship section={section} />)
  const plot=await screen.findByRole('img',{name:'IMD score and Stops per 1,000 residents'})
  expect(plot.querySelectorAll('[aria-label="dot"] circle')).toHaveLength(1)
  const aside=screen.getByRole('complementary')
  expect(aside.querySelector('.correlation-value')).toHaveTextContent('0.0000')
  expect(within(aside).getByText('300')).toBeInTheDocument()
  expect(within(aside).getByText('< 0.0001')).toBeInTheDocument()
  expect(aside).toHaveTextContent('full selected filter')
  expect(aside).toHaveTextContent('display sample')
 })
 it('leaves missing correlation, count and p-value unavailable',()=>{
  render(<CorrelationRelationship section={{...section,stats:{r:null,n:null,p_value:null}}} />)
  expect(within(screen.getByRole('complementary')).getAllByText('—')).toHaveLength(3)
 })
 it('does not display points or statistics when the source suppresses the relationship',()=>{
  render(<CorrelationRelationship section={{...section,suppressed:true}} />)
  expect(screen.queryByRole('img')).not.toBeInTheDocument()
  expect(screen.queryByText('300')).not.toBeInTheDocument()
  expect(screen.getByText(/unavailable for the selected filter/)).toBeInTheDocument()
 })
})
