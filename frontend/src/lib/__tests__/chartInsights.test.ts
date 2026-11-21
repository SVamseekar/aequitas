import {describe,expect,it} from 'vitest'
import type {SectionItem} from '@/api/types'
import {chartInsights} from '../chartInsights'
const base:SectionItem={section_id:'a3_walking_distance',dimension:'accessibility',stats:{},chart_data:{},narrative:'Unverified claim: policy causes the unexplained variance.',suppressed:false}
describe('Source-backed chart findings',()=>{
 it('uses England area coverage, separate population counts and preserves observed zero',()=>{
  const findings=chartInsights({...base,stats:{pct_covered:0,n_zero_access:8,pct_zero_access:100,pop_zero_access:0}}).join(' ')
  expect(findings).toContain('**0.0**% of LSOAs')
  expect(findings).toContain('**0** residents')
  expect(findings).not.toContain('0.0**% of the population')
  expect(findings).not.toContain('policy causes')
 })
 it('does not substitute missing measurements or unsupported model conclusions',()=>{
  const findings=chartInsights({...base,section_id:'g3_coverage_model',stats:{r2:0.4719,top_feature:'nocar_pct',top_importance:0.083,n_features:9}}).join(' ')
  expect(findings).toContain('0.4719')
  expect(findings).toContain('log1p(trips per capita)')
  expect(findings).toContain('Car-free households')
  expect(findings).toContain('cannot be assigned to policy choices')
  expect(findings).not.toContain('53%')
  expect(chartInsights({...base,stats:{pct_covered:null,n_zero_access:null}})).toEqual([])
 })
 it('keeps stop-count associations distinct from measured temporal frequency',()=>{
  const findings=chartInsights({...base,section_id:'c5_length_vs_frequency',stats:{r:0,n:27,strength:'negligible',direction:'none'},chart_data:{x_label:'Route length',y_label:'Frequency proxy'}}).join(' ')
  expect(findings).toContain('stops per route')
  expect(findings).toContain('**0.0000**')
  expect(findings).toContain('27')
  expect(findings).toContain('not measured service frequency')
 })
 it('retains zero-valued heatmap cells and never fills null cells',()=>{
  const findings=chartInsights({...base,section_id:'d7_deprivation_urban_rural',chart_data:{type:'heatmap',values:[[0,null],[80,100]]}},'ireland').join(' ')
  expect(findings).toContain('0.0%')
  expect(findings).toContain('100.0%')
  expect(findings).toContain('not a national average')
 })
 it('never exposes a finding from a suppressed or omitted exhibit',()=>{
  expect(chartInsights({...base,suppressed:true,stats:{pct_covered:79}})).toEqual([])
  expect(chartInsights({...base,stats:{omit:true,pct_covered:79}})).toEqual([])
 })
})

describe('Country-native insight contracts',()=>{
 it('does not turn a foreign people gap into an English currency estimate',()=>{
  const lines=chartInsights({...base,section_id:'a7_investment_gap',stats:{people_gap:0,local_pct_covered:55,national_pct_covered:55,currency:null}},'ireland').join(' ')
  expect(lines).toContain('**0** residents')
  expect(lines).toContain('no currency cost')
  expect(lines).not.toContain('£')
 })
 it('keeps stop mass distinct from route shares and agency inventory distinct from trips',()=>{
  const stops=chartInsights({...base,section_id:'c4_urban_rural_routes',stats:{urban_stops:0,rural_stops:10}},'france').join(' ')
  expect(stops).toContain('**0** stops')
  expect(stops).toContain('not route shares')
  const agency=chartInsights({...base,section_id:'b4_route_frequency',stats:{agencies:[{name:'Actual agency',n_routes:12,share:.3}]}},'netherlands').join(' ')
  expect(agency).toContain('12')
  expect(agency).toContain('distinct from scheduled trips')
 })
 it('does not relabel feature correlations as SHAP or foreign flags as an English learned model',()=>{
  const features=chartInsights({...base,section_id:'g4_shap',stats:{features:[{name:'hp_relative',r:0},{name:'urban',r:null}]}},'ireland').join(' ')
  expect(features).toContain('**0.0000**')
  expect(features).toContain('not numerical SHAP')
  const flags=chartInsights({...base,section_id:'g2_anomalies',stats:{n_flagged:9,rule:'Actual local rule'}},'netherlands').join(' ')
  expect(flags).toContain('**9**')
  expect(flags).toContain('Actual local rule')
  expect(flags).toContain('Rule-based')
 })
 it('uses country-specific area tiers without inventing district eligibility',()=>{
  const lines=chartInsights({...base,section_id:'bsa3_tier_distribution',stats:{tiers:{'Urban AOM':0,'Unserved (400 m)':10}}},'france').join(' ')
  expect(lines).toContain('**Urban AOM**: **0**')
  expect(lines).toContain('not England district-readiness tiers')
 })
})
