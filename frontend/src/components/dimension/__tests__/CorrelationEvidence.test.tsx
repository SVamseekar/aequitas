import {fireEvent,render,screen} from '@testing-library/react'
import {MemoryRouter} from 'react-router'
import {describe,expect,it} from 'vitest'
import type {SectionItem} from '@/api/types'
import {CorrelationGroups} from '../CorrelationGroups'
import {CorrelationModel} from '../CorrelationModel'
const base:SectionItem={section_id:'g3_coverage_model',dimension:'correlations',stats:{},chart_data:{},narrative:'',suppressed:false}
describe('Correlation evidence limits',()=>{
  it('does not reconstruct a fit scatter from R² or imply a causal policy explanation',()=>{
    render(<CorrelationModel section={{...base,stats:{r2:0.4719,n_features:9,top_feature:'nocar_pct',top_importance:0.083}}} />)
    expect(screen.getByText('Fit scatter not stored for this pack')).toBeInTheDocument()
    expect(screen.getAllByText('0.4719').length).toBeGreaterThan(0)
    expect(screen.queryByRole('img')).toBeNull()
    expect(screen.getAllByText(/log1p\(trips per capita\)/).length).toBeGreaterThan(0)
  })
  it('inspects supplied area coordinates and keeps model anomaly counts separate from categories',()=>{
    render(<MemoryRouter><CorrelationGroups section={{...base,section_id:'g2_anomalies',stats:{n_anomalies:382,pct_anomalies:1.13,n_positive:476,n_inefficiency:345,n_policy_failure:10},chart_data:{data:[{id:'E01000001',x:0,y:25,cluster:1}],clusters:[{id:1,label:'Actual stored category',n:476}]}}} /></MemoryRouter>)
    fireEvent.change(screen.getByRole('combobox',{name:'Inspect plotted area'}),{target:{value:'E01000001'}})
    expect(screen.getByText('0.000')).toBeInTheDocument()
    expect(screen.getByText('25.000')).toBeInTheDocument()
    expect(screen.getByText('Stored category').parentElement).toHaveTextContent('Actual stored category')
    expect(screen.getByText(/do not sum to the flagged anomaly count/)).toBeInTheDocument()
  })
})
