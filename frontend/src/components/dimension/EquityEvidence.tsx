import {useState} from 'react'
import {Info} from 'lucide-react'
import type {SectionItem} from '@/api/types'
import {ChartRenderer} from '@/components/charts/ChartRenderer'
import {useFilters} from '@/api/hooks'
import {sectionPresentation} from '@/lib/sectionPresentation'
import {finiteObservation as finite,serviceNumber as number} from '@/lib/serviceData'
import {chartInsights} from '@/lib/chartInsights'
import {ChartInsights} from './ChartInsights'
import {ProvenancePanel} from './ProvenancePanel'

export function EquityEvidence({section}:{section:SectionItem}) {
 const {country}=useFilters(),[metric,setMetric]=useState<string|null>(null)
 const s=section.stats,id=section.section_id,p=sectionPresentation(section,country)
 if(section.suppressed||s.omit||s.insufficient_data)return <section className='app-panel'><h2>Not available for this filter</h2><p>{typeof s.omit_reason==='string'?s.omit_reason:'This source does not supply publishable observations for the selected filter.'}</p></section>
 const distribution=['f1_gini','a4_coverage_equity'].includes(id),deprivation=id==='f2_disparity_ratio',social=id==='f3_ethnic_access',rural=id==='f5_rural_penalty',regional=id==='f6_equitable_regions'
 const chart={...p.chartData,...(social?{point_color:'#83a47e',line_color:'#d65b2d',show_summary:false}:{}),...(regional?{height:415,color_by:'rank',palette:['#7ba17b','#c4c58a','#eed89c','#eab078','#db6139'],color_reverse:true}:{}),...(deprivation?{color_by:'rank',palette:['#87a184','#b9c6b1','#ced8c8'],order:'source'}:{})}
 const stats=distribution?[
  ['Gini coefficient',number(s.gini,4),'Higher values indicate greater inequality in service distribution.','gini_national'],
  ['Palma ratio',`${number(s.palma,3)} ×`,"Ratio of the top 10% to bottom 40% of the population’s service.",'palma_ratio'],
  ['Concentration index',`${finite(s.concentration_index)&&s.concentration_index>0?'+':''}${number(s.concentration_index,4)}`,'Distribution ordered by deprivation; distinct from Gini.','concentration_index'],
  ['Small area count',number(s.n_lsoas??s.n),'Number of source areas included in this analysis.',''],
 ]:deprivation?[
  ['Most deprived areas',number(s.most_deprived_value,2),'Trips per capita',''],
  ['Least deprived areas',number(s.least_deprived_value,2),'Trips per capita',''],
  ['Disparity ratio',finite(s.ratio)?`${number(s.ratio,2)} ×`:'—','Least deprived / most deprived',''],
 ]:[]
 const scopeNote='England BODS schedules · Census 2021 LSOAs · IMD 2025. Network dates and population/deprivation vintages are distinct.'
 return <div className={`equity-evidence${distribution?' equity-distribution':''}${regional?' equity-regional':''}${rural?' equity-rural':''}`}>
  {regional&&<section className='app-panel equity-region-intro'><div><h2>Regional vulnerability</h2><p>Additional warehouse exhibit; metric is vulnerability index</p><ChartInsights items={chartInsights(section,country).slice(1,2)} title={null} /><p>A lower index indicates lower vulnerability. This is not a Gini coefficient.</p></div><div className='equity-benchmark'><h3>Selected-filter average</h3><strong>{number(s.national_avg,2)}</strong><p>Vulnerability index</p></div></section>}
  <div className='equity-exhibit app-panel'>
   <section className='equity-plot'><h2>{regional?'Regional vulnerability ranking':distribution?'Distribution of bus service across the population':social?'Bus access by ethnicity':p.title}</h2><p>{distribution?'Lorenz curve: population ordered by trips per capita (lowest first)':deprivation?'Average trips per capita by IMD decile: 1 most deprived, 10 least deprived':social?'Area-level relationship between ethnicity and bus stop density':rural?'Service quality index by region and settlement type':''}</p><ChartRenderer chartData={chart} /></section>
   {!regional&&!rural&&<aside className='equity-inspector'>
    {stats.length>0&&<><h3>{distribution?'Key distribution statistics':'Key values'}</h3>{stats.map(([label,value,note,provenance])=><section className='equity-stat' key={label}><h4>{label}{provenance&&<button type='button' aria-label={`Show ${label} provenance`} onClick={()=>setMetric(provenance)}><Info size={14} /></button>}</h4><strong>{value}</strong><p>{note}</p></section>)}</>}
    {social&&<><h3>Correlation (Pearson’s r)</h3><strong className='equity-correlation'>{number(s.r,4)}</strong><ChartInsights section={section} country={country} title={null} /><dl className='network-summary'><div><dt>Observations</dt><dd>{number(s.n)}</dd></div><div><dt>Significance (p)</dt><dd>{finite(s.p_value)&&s.p_value<0.0001?'< 0.0001':number(s.p_value,4)}</dd></div></dl><details><summary>Controls and methods</summary><p>{p.interpretation}</p></details></>}
    {rural&&<><h3>Key points</h3><ChartInsights section={section} country={country} title={null} /></>}
   </aside>}
  </div>
  {rural&&<section className='app-panel equity-settlement-summary'><div><h3>Summary (selected filter)</h3><dl>{[['Urban SQI',number(s.urban_value,2)],['Rural SQI',number(s.rural_value,2)],['Relative gap',`${number(s.gap_pct,1)}%`],['Observations',`Urban ${number(s.n_urban)} · Rural ${number(s.n_rural)}`]].map(([label,value])=><div key={label}><dt>{label}</dt><dd>{value}</dd></div>)}</dl></div><aside><ChartInsights section={section} country={country} /></aside></section>}
  {!regional&&<div className='equity-methods app-panel'><section><h3>{social||rural?'Controls and methods':'What this shows'}</h3><p>{distribution?'Population is ordered from lowest to highest trips per capita. A curve below the equality line indicates that a disproportionate share of scheduled service goes to people with higher service levels.':p.interpretation}</p></section><section>{distribution||deprivation?<ChartInsights section={section} country={country} items={distribution?[`Gini **${number(s.gini,4)}**, Palma **${number(s.palma,3)} ×** and deprivation concentration **${number(s.concentration_index,4)}** describe different aspects of service distribution.`]:undefined} />:<><h3>Data and scope</h3><p>{scopeNote}</p><p>Sample points and full-filter summary counts describe distinct scopes. Correlation does not establish causation.</p></>}</section></div>}
  {metric&&<ProvenancePanel metricId={metric} onClose={()=>setMetric(null)} />}
 </div>
}
