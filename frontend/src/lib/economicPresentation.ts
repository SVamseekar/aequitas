import type { SectionItem } from '@/api/types'
import { finiteObservation as finite, serviceNumber as number } from './serviceData'
export interface EconomicMetric { label:string; value:string; unit:string }
const scaled=(value:unknown,divisor:number,digits:number,prefix='')=>finite(value)?`${prefix}${number(value/divisor,digits)}`:'—'

/** Display unit conversions only. The appraisal calculation remains in the warehouse. */
export function economyMetrics(section:SectionItem):EconomicMetric[] {
  const s=section.stats
  switch(section.section_id){
    case 'j1_economic_value':return [{label:'Annual modelled benefit',value:scaled(s.annual_benefit,1e6,1,'£'),unit:'million / year'},{label:'Trips benefiting',value:scaled(s.n_trips,1e6,1),unit:'million / year'},{label:'Value of time',value:scaled(s.vot,1,2,'£'),unit:'per hour'}]
    case 'j2_bcr':return [{label:'Benefit-cost ratio',value:scaled(s.bcr,1,2),unit:typeof s.vfm_band==='string'?`${s.vfm_band} model band`:'Band unavailable'},{label:'Total investment',value:scaled(s.investment_m,1,1,'£'),unit:'million present value'},{label:'Appraisal period',value:scaled(s.appraisal_years,1,0),unit:'years'}]
    case 'j3_carbon':return [{label:'Net CO₂ saved',value:scaled(s.co2_saving_tonnes,1,1),unit:'tonnes / year'},{label:'Carbon price (source)',value:scaled(s.carbon_price,1,2,'£'),unit:'per tonne'},{label:'Indicative carbon value',value:scaled(s.co2_value_k,1,2,'£'),unit:'thousand / year'}]
    default:return [{label:'Average investment gap',value:scaled(s.national_avg,1,2,'£'),unit:'per year'},{label:'Measure',value:'Annual investment gap',unit:'pounds / year; additional warehouse exhibit'}]
  }
}
