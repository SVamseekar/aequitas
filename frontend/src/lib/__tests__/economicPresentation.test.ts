import {describe,expect,it} from 'vitest'
import type {SectionItem} from '@/api/types'
import {economyMetrics} from '../economicPresentation'
const section=(id:string,stats:Record<string,unknown>):SectionItem=>({section_id:id,dimension:'economic',stats,chart_data:{},narrative:'',suppressed:false})
describe('Economic display units',()=>{
  it('converts source pounds into million pounds only for the annual-benefit display',()=>{
    expect(economyMetrics(section('j1_economic_value',{annual_benefit:1387205664.4825418,n_trips:589409897.59,vot:8.49})).map(row=>row.value)).toEqual(['£1,387.2','589.4','£8.49'])
    expect(economyMetrics(section('j4_investment_priority',{national_avg:34165.4568}))[0]).toEqual({label:'Average investment gap',value:'£34,165.46',unit:'per year'})
  })
  it('retains carbon value in thousands, BCR precision and missing-versus-zero',()=>{
    const carbon=economyMetrics(section('j3_carbon',{co2_value_k:1838.6165,co2_saving_tonnes:0,carbon_price:null}))
    expect(carbon.map(row=>row.value)).toEqual(['0.0','—','£1,838.62'])
    expect(carbon[2].unit).toBe('thousand / year')
    expect(economyMetrics(section('j2_bcr',{bcr:1.15}))[0].value).toBe('1.15')
  })
})
