import { ChartInsights } from '@/components/dimension/ChartInsights'
import type { SectionItem } from '@/api/types'
import { ChartRenderer } from '@/components/charts/ChartRenderer'
import { serviceNumber } from '@/lib/serviceData'

export function CorrelationModel({ section }: { section: SectionItem }) {
  const fit=section.section_id==='g3_coverage_model'
  return <div className='network-page correlation-model'>
    {fit&&<div className='service-metrics'>{[['R² (held-out model fit)',serviceNumber(section.stats.r2,4)],['Number of features',serviceNumber(section.stats.n_features)],['Target variable','log1p(trips per capita)'],['Leading feature importance',serviceNumber(section.stats.top_importance,4)]].map(([label,value])=><section className='app-panel' key={label}><h2>{label}</h2><strong>{value}</strong></section>)}</div>}
    <div className='network-main'><section className='app-panel'><h2>{fit?'Model fit: predicted versus observed':'Feature importance (SHAP)'}</h2>{fit?<div className='model-fit-unavailable'><h3>Fit scatter not stored for this pack</h3><p>No predicted-versus-observed point payload is supplied. Summary R² does not provide enough information to reconstruct a fit plot.</p></div>:<ChartRenderer chartData={{...section.chart_data,title:'National predictive feature importance',height:260,show_summary:false,bar_color:'#819d79'}} />}</section>
      <aside><section className='app-panel'><ChartInsights section={section} /></section><section className='app-panel mt-4'><h2>Model scope and sources</h2><p>National Random Forest regression on log1p(trips per capita). Region and area filters do not refit this model.</p><p>Feature importance describes predictive associations, not causal policy effects.</p><p>England BODS schedules · Census 2021 LSOAs · IMD 2025. R² is evaluated on the transformed held-out target.</p></section></aside></div>
  </div>
}
