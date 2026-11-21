import {render,screen} from '@testing-library/react'
import {describe,expect,it} from 'vitest'
import {ScenarioModel} from '../ScenarioModel'
import type {SectionItem} from '@/api/types'
const section:SectionItem={section_id:'g5_scenario_model',dimension:'correlations',stats:{scenario:{name:'Actual stored scenario',population_affected:999}},chart_data:{tiles:[{label:'Population affected',value:0,unit:'people'},{label:'Annual cost',value:null,unit:'£m/yr'}],proportion:{series:[{data:[0]},{data:[100]}]}},narrative:'',suppressed:false}
describe('Stored scenario composition',()=>{
 it('derives the share only from the paired source observations, retaining observed zero and unavailable cost',()=>{
  render(<ScenarioModel section={section} />)
  expect(screen.getByRole('img',{name:'Population affected: 0.0%; Population remaining: 100.0%'})).toBeInTheDocument()
  expect(screen.queryByText('999')).not.toBeInTheDocument()
  expect(screen.getAllByText('—')).toHaveLength(2)
 })
 it('does not invent a national denominator from the targeting population',()=>{
  render(<ScenarioModel section={{...section,chart_data:{tiles:[]}}} />)
  expect(screen.getByText('No population proportion is stored for this model.')).toBeInTheDocument()
  expect(screen.queryByRole('img')).not.toBeInTheDocument()
 })
})
