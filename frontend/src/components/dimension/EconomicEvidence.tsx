import { ChartInsights } from '@/components/dimension/ChartInsights'
import type { SectionItem } from '@/api/types'
import { useSections } from '@/api/hooks'
import { ChartRenderer } from '@/components/charts/ChartRenderer'
import { economyMetrics } from '@/lib/economicPresentation'
import { finiteObservation as finite, serviceNumber as number } from '@/lib/serviceData'

function FactorRow({country,name,method}:{country:string;name:string;method:string}) {
  const query=useSections('economic','all','all',country,'','bus')
  const stats=query.data?.sections.find(row=>row.section_id==='j2_bcr')?.stats
  return <tr><th scope='row'>{name}</th><td>{method}</td><td>{query.isPending?'Loading…':query.error||!stats?'Unavailable':stats.omit_euro?'No currency appraisal applied':finite(stats.bcr)?'Stored BCR supplied':'Unavailable'}</td><td>{typeof stats?.reason==='string'?stats.reason:'No additional source reason supplied.'}</td></tr>
}

export function EconomicEvidence({section}:{section:SectionItem}) {
  const id=section.section_id,bcr=id==='j2_bcr',carbon=id==='j3_carbon',priority=id==='j4_investment_priority'
  const title=bcr?'Appraisal of coverage gaps':carbon?'Carbon reduction from modal shift':priority?'Regional investment prioritisation':'Annual modelled economic value'
  const metrics=economyMetrics(section)
  const chartData={...section.chart_data,title,...(bcr?{markers:finite(section.stats.bcr)?[{label:typeof section.stats.area_name==='string'?section.stats.area_name:'Selected filter',value:section.stats.bcr}]:[]}:priority?{x_label:'Investment gap (£ / year)',order:'source',color_by:'rank',palette:['#e9b999','#d77f52','#b7532a']}:carbon?{order:'source',palette:['#819d79']}:{order:'source',color_by:'rank',palette:['#7ba17b','#b5c38b','#e9dba2','#edbb7c','#d5794e']} )}

  return <div className='network-page economic-evidence'><div className='plan-metrics'>{metrics.map(row=><section className='app-panel' key={row.label}><h2>{row.label}</h2><strong>{row.value}</strong><p>{row.unit}</p></section>)}</div>
    <div className='network-main'><section className='app-panel'><h2>{title}</h2><p>{priority?'Additional warehouse exhibit. Actual pounds per year are not converted to millions.':bcr?'Modelled monetised benefits divided by present-value investment. The marker is the supplied selected-filter BCR.':carbon?'Indicative modal-shift estimate; regional observations use tonnes of CO₂ per year.':'Monetised model estimate, rather than GDP or total economic output.'}</p><ChartRenderer chartData={chartData} /></section>
      <aside className='app-panel'><ChartInsights section={section} /><h2>Inputs and interpretation</h2>{bcr?<><p>Appraisal period: {number(section.stats.appraisal_years)} years. Present-value investment: £{number(section.stats.investment_m,1)} million.</p><p>The stored value-for-money band describes this model and does not constitute statutory appraisal or approval.</p></>:carbon?<><p>Source carbon price: £{number(section.stats.carbon_price,2)} per tonne. Modelled modal-shift trips: {number(section.stats.modal_shift_trips,2)} per year.</p><p>Carbon value uses thousands of pounds per year, separate from annual-benefit figures in millions. Source factors describe the dated model; they are not new travel-demand observations.</p></>:priority?<p>Higher investment gaps indicate greater modelled need, rather than better service. The average is a benchmark, not a promised allocation.</p>:<><p>Source value of time: £{number(section.stats.vot,2)} per hour. Benefits use the stored additional-trip and time-value assumptions.</p><p>These are indicative user-benefit estimates; they are not a direct measure of productivity or GDP.</p></>}<p>Transport: England BODS schedules. Population geography: Census 2021. Deprivation context: IMD 2025.</p></aside></div>
    <details className='app-panel mt-4'><summary>Stored model assumptions and scalar inputs</summary><div className='access-table-scroll'><table aria-label='Stored economic inputs'><thead><tr><th>Source field</th><th>Source value (native unit)</th></tr></thead><tbody>{Object.entries(section.stats).filter(([,value])=>typeof value==='string'||typeof value==='number'||value===null).map(([key,value])=><tr key={key}><th scope='row'>{key}</th><td>{value===null?'—':String(value)}</td></tr>)}</tbody></table></div></details>
    {priority&&<section className='app-panel mt-4'><h2>Current national method availability</h2><p>Separate current national extracts, independent of this page's selected region and network date. Country appraisal methods and currency factors are not transferred between countries.</p><div className='access-table-scroll'><table aria-label='Country appraisal availability'><thead><tr><th>Country</th><th>Method context</th><th>Stored currency appraisal</th><th>Source reason</th></tr></thead><tbody><FactorRow country='ireland' name='Ireland' method='CAF / PAG' /><FactorRow country='netherlands' name='Netherlands' method='MKBA' /><FactorRow country='france' name='France' method='Quinet' /></tbody></table></div></section>}
  </div>
}
