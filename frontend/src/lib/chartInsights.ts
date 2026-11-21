import type { SectionItem } from '@/api/types'
import { finiteObservation as finite, serviceNumber as number } from './serviceData'
import { modelFeatureLabel } from './modelLabels'
import { sectionPresentation } from './sectionPresentation'
import {countryChartInsights} from './countryChartInsights'

const record=(value:unknown):Record<string,unknown>=>value&&typeof value==='object'&&!Array.isArray(value)?value as Record<string,unknown>:{}
const bold=(value:unknown,digits=0)=>`**${number(value,digits)}**`
const text=(value:unknown)=>typeof value==='string'?value:''

/** Chart findings from this payload only. Legacy prose contains unsupported causal/legal claims. */
export function chartInsights(section:SectionItem,country='england'):string[] {
 const s=section.stats,id=section.section_id,items:string[]=[]
 if(section.suppressed||s.omit||s.insufficient_data)return []
 if(country!=='england'){const native=countryChartInsights(section);if(native.length)return native}
 const add=(condition:boolean,line:string)=>{if(condition)items.push(line)}
 if(finite(s.pct_covered)){
  const areas=country==='england'
  add(true,`${bold(s.pct_covered,1)}% of ${areas?'LSOAs have non-zero access':'the population is within 400 m of a stop'}.`)
  add(finite(s.n_zero_access),`${bold(s.n_zero_access)} ${areas?'LSOAs have zero access score':'areas are recorded with zero access'}${finite(s.pct_zero_access)?` (${number(s.pct_zero_access,1)}%)`:''}.`)
  add(finite(s.pop_zero_access),`Zero-access population: ${bold(s.pop_zero_access)} residents (separate count).`)
  items.push('Proximity is separate from service frequency and travel time.')
  return items
 }
 if(finite(s.r)){
  const x=text(section.chart_data.x_label)||text(s.x_label)||'The source predictor'
  const y=id==='c5_length_vs_frequency'?'stops per route':text(section.chart_data.y_label)||text(s.y_label)||'the source service measure'
  const association=[text(s.strength),text(s.direction)].filter(Boolean).join(' ')
  items.push(`${x} and ${y} have ${association?`a **${association}**`:'a stored'} association (r = ${bold(s.r,4)}).`)
  add(finite(s.n),`The relationship describes ${bold(s.n)} ${id==='c5_length_vs_frequency'?'routes':'observations'} in the selected filter; the plotted points are the supplied display sample.`)
  items.push(id==='c5_length_vs_frequency'?'Stop count is a geometric characteristic, not measured service frequency.':'This area-level association does not establish causation.')
  return items
 }
 if(finite(s.gini)){
  items.push(`The service-distribution Gini is ${bold(s.gini,4)}; zero represents equal distribution.`)
  add(finite(s.palma),`The Palma ratio is ${bold(s.palma,3)}. It measures a different part of the distribution from Gini.`)
  add(finite(s.concentration_index),`The deprivation concentration index is ${bold(s.concentration_index,4)}; it is distinct from the Gini measure.`)
  return items
 }
 if(finite(s.most_deprived_value)||finite(s.least_deprived_value)){
  add(finite(s.most_deprived_value),`The most-deprived group has ${bold(s.most_deprived_value,2)} ${text(s.unit)}.`)
  add(finite(s.least_deprived_value),`The least-deprived group has ${bold(s.least_deprived_value,2)} ${text(s.unit)}.`)
  add(finite(s.ratio)&&!s.ratio_undefined,`The least-deprived / most-deprived ratio is ${bold(s.ratio,2)}.`)
  return items
 }
 if(id==='c4_urban_rural_routes'){
  for(const [label,key,n]of [['Urban','urban_value','n_urban'],['Rural','rural_value','n_rural'],['Mixed','pct_mixed','n_mixed']])add(finite(s[key]),`${label} routes account for ${bold(s[key],1)}%${finite(s[n])?` (${number(s[n])} routes)`:''}.`)
  return items
 }
 if(id==='a6_urban_rural_gap'&&country!=='england'){
  for(const [key,label]of [['urban','Urban'],['rural','Rural']]){const group=record(s[key]);add(finite(group.pct_covered),`${label} population coverage within 400 m is ${bold(group.pct_covered,1)}%.`)}
  add(finite(s.gap_pp),`The stored urban–rural difference is ${bold(s.gap_pp,1)} percentage points, not a relative percentage.`)
  return items
 }
 if(finite(s.urban_value)||finite(s.rural_value)){
  add(finite(s.urban_value),`Urban mean: ${bold(s.urban_value,2)} ${text(s.unit)}.`)
  add(finite(s.rural_value),`Rural mean: ${bold(s.rural_value,2)} ${text(s.unit)}.`)
  add(finite(s.gap_pct),`The stored relative urban/rural gap is ${bold(s.gap_pct,1)}%.`)
  return items
 }
 if(id==='b2_operating_hours'){
  add(Boolean(text(s.median_first_service)&&text(s.median_last_service)),`Typical first and last service are **${text(s.median_first_service)}** and **${text(s.median_last_service)}** (stored medians).`)
  add(finite(s.n_evening_isolated),`${bold(s.n_evening_isolated)} areas${finite(s.pct_evening_isolated)?` (${number(s.pct_evening_isolated,1)}%)`:''} have no scheduled weekday service after 19:00.`)
  items.push('Regional endpoints describe typical service spans, not a timetable guarantee at every stop.')
  return items
 }
 if(id==='b3_weekend_penalty'){
  add(finite(s.sunday_pct_drop),`Sunday departures are ${bold(s.sunday_pct_drop,1)}% lower than weekday departures in this filter.`)
  add(finite(s.n_sunday_desert),`${bold(s.n_sunday_desert)} areas${finite(s.pct_sunday_desert)?` (${number(s.pct_sunday_desert,1)}%)`:''} have no scheduled Sunday service.`)
  items.push('Sunday-service deserts and areas with no bus stops are different subsets.')
  return items
 }
 if(id==='a5_service_deserts'){
  add(finite(s.n_desert_lsoas),`${bold(s.n_desert_lsoas)} areas have no stops within their boundaries.`)
  add(finite(s.pop_affected),`The zero-stop subset contains ${bold(s.pop_affected)} residents.`)
  items.push('A stop outside an area boundary may still be nearby; zero stops within a boundary does not establish zero journey access.')
  return items
 }
 if(id==='a7_investment_gap'){
  add(finite(s.n_below),`${bold(s.n_below)} areas${finite(s.pct_below)?` (${number(s.pct_below,1)}%)`:''} fall below the stored service target.`)
  add(finite(s.target),`The target is ${bold(s.target,2)} trips per capita${text(s.target_description)?` (${text(s.target_description)})`:''}.`)
  add(finite(s.mean_gap),`The mean service gap is ${bold(s.mean_gap,2)} trips per capita.`)
  add(finite(s.total_annual_cost_m),`Indicative annual cost: **£${number(s.total_annual_cost_m,1)}m**, using the unverified source cost proxy; not an approved appraisal.`)
  return items
 }
 if(finite(s.r2)){
  items.push(`Held-out model R² is ${bold(s.r2,4)} on **log1p(trips per capita)**.`)
  add(Boolean(text(s.top_feature)),`The leading supplied feature is **${modelFeatureLabel(text(s.top_feature))}**${finite(s.top_importance)?` (mean absolute SHAP ${number(s.top_importance,4)})`:''}${finite(s.n_features)?` across ${number(s.n_features)} features`:''}.`)
  items.push('Predictive associations do not establish policy effects; unexplained variance cannot be assigned to policy choices.')
  return items
 }
 if(id==='c1_route_length'||id==='c2_stops_per_route'){
  const unit=id==='c1_route_length'?'km':'stops per route'
  add(finite(s.median),`Median: ${bold(s.median,2)} ${unit}${finite(s.mean)?`; mean: ${number(s.mean,2)} ${unit}`:''}.`)
  add(!finite(s.median)&&finite(s.mean),`The stored mean is ${bold(s.mean,2)} ${unit}.`)
  add(finite(s.p10)&&finite(s.p90),`The 10th–90th percentile range is **${number(s.p10,2)}–${number(s.p90,2)} ${unit}**.`)
  add(Boolean(text(s.skew_label)),`The source describes this distribution as **${text(s.skew_label)}**.`)
  return items
 }
 if(finite(s.hhi)){
  items.push(`${text(s.region_name)||'Selected-filter'} operator HHI is ${bold(s.hhi,1)} / 10,000.`)
  add(Boolean(text(s.top_operator)),`The largest supplied operator is **${text(s.top_operator)}**${finite(s.top_operator_share)?` with ${number(s.top_operator_share,1)}% of scheduled service`:''}.`)
  items.push('National and regional concentration use different geographic aggregations; HHI is not service quality or legal eligibility.')
  return items
 }
 if(Array.isArray(s.clusters)){
  const groups=s.clusters.map(record).filter(group=>finite(group.n))
  add(finite(s.n_clusters),`The stored model contains ${bold(s.n_clusters)} ${id==='d6_transport_poverty'?'area groups, including noise':'route clusters'}.`)
  const largest=[...groups].sort((a,b)=>Number(b.n)-Number(a.n))[0]
  if(largest)items.push(`The largest stored group is **${String(largest.id)}** with ${bold(largest.n)} ${id==='d6_transport_poverty'?'areas':'routes'}${finite(largest.pct)?` (${number(largest.pct,1)}%)`:''}.`)
  return items
 }
 if(id==='g2_anomalies'){
  add(finite(s.n_anomalies),`The model flags ${bold(s.n_anomalies)} areas${finite(s.pct_anomalies)?` (${number(s.pct_anomalies,2)}%)`:''}.`)
  items.push('Model anomaly flags and descriptive categories use different definitions. Their totals must not be summed together.')
  return items
 }
 if(id==='d7_deprivation_urban_rural'){
  const chart=sectionPresentation(section,country).chartData
  const data=Array.isArray(chart.data)?chart.data.map(record):[]
  if(country==='england'){
   const rows=data.filter(row=>finite(row.value)),highest=[...rows].sort((a,b)=>Number(b.value)-Number(a.value))[0]
   if(highest)items.push(`The largest stored urban-minus-rural gap is **${number(highest.value,2)} SQI points** in **${text(highest.label)}**.`)
   items.push('Positive gaps mean higher urban SQI; decile 1 is most deprived within England.')
  }else{
   const cells=record(s.cells)
   for(const [key,label]of [['urban','Urban'],['rural','Rural']]){const cell=record(cells[key]);add(finite(cell.pct_covered),`${label} population coverage is ${bold(cell.pct_covered,1)}% in the stored grouping.`)}
   const values=Array.isArray(chart.values)?chart.values.flatMap(row=>Array.isArray(row)?row.filter(finite):[]):data.map(row=>row.value).filter(finite)
   if(!items.length&&values.length)items.push(`Observed population-coverage cells range from **${number(Math.min(...values),1)}%** to **${number(Math.max(...values),1)}%**. These are cell values, not a national average.`)
   items.push('Country-specific deciles; blank cells are unavailable, not zero.')
  }
  return items
 }
 if(finite(s.n_cross_la)){
  items.push(`${bold(s.n_cross_la)} routes${finite(s.pct_cross_la)?` (${number(s.pct_cross_la,1)}%)`:''} cross local-authority boundaries.`)
  add(Boolean(text(s.densest_corridor)),`The highest regional count is **${text(s.densest_corridor)}**${finite(s.densest_count)?` (${number(s.densest_count)} routes)`:''}; this is not a mapped corridor.`)
  return items
 }
 if(id==='b4_route_frequency'){
  const top=Array.isArray(s.top_routes)?record(s.top_routes[0]):{}
  add(finite(s.n_routes),`${bold(s.n_routes)} routes are included in the frequency analysis.`)
  add(Boolean(text(top.route_short_name))&&finite(top.n_trips_per_day),`The highest stored route sample is **${text(top.route_short_name)}**${text(top.agency_name)?` (${text(top.agency_name)})`:''}, with ${bold(top.n_trips_per_day)} scheduled trips per day.`)
  return items
 }
 const best=record(s.best),worst=record(s.worst)
 if(finite(s.national_avg)&&finite(best.value)&&finite(worst.value)){
  const unit=text(s.unit)
  items.push(`The source benchmark is ${bold(s.national_avg,2)} ${unit}.`)
  items.push(`**${text(best.name)}**: ${bold(best.value,2)} ${unit}; **${text(worst.name)}**: ${bold(worst.value,2)} ${unit}.`)
  if(s.higher_is_better===false)items.push('Lower values indicate lower vulnerability; a larger value does not mean better service.')
  return items
 }
 if(id==='j1_economic_value')add(finite(s.annual_benefit),`Annual modelled user benefits are **£${number(Number(s.annual_benefit)/1e6,1)} million**; this is not GDP.`)
 if(id==='j2_bcr')add(finite(s.bcr),`The stored BCR is ${bold(s.bcr,2)}${text(s.vfm_band)?` (${text(s.vfm_band)} model value-for-money band)`:''}; this is not appraisal approval.`)
 if(id==='j3_carbon'){
  add(finite(s.co2_saving_tonnes),`Modelled CO₂ saving: ${bold(s.co2_saving_tonnes,1)} tonnes per year.`)
  add(finite(s.co2_value_k),`Annual carbon value is **£${number(s.co2_value_k,2)} thousand**, not millions.`)
 }
 if(id==='bsa3_tier_distribution'){
  add(finite(s.n_total),`The source classifies ${bold(s.n_total)} local-authority districts.`)
  for(const [key,label]of [['n_tier1','Tier 1'],['n_tier2','Tier 2'],['n_tier3','Tier 3']])add(finite(s[key]),`${label}: ${bold(s[key])} districts. Model tiers are not statutory eligibility.`)
 }
 const scenario=record(s.scenario)
 if(Object.keys(scenario).length){
  add(Boolean(text(scenario.scope)||text(scenario.who)),`Target: **${text(scenario.scope)||text(scenario.who)}**.`)
  add(finite(scenario.population_affected),`${bold(scenario.population_affected)} people meet the stored targeting criterion; they are not newly gained access.`)
  items.push('Cost and carbon outputs are indicative where supplied. No approved benefit-cost ratio or live Studio result is inferred.')
 }
 if(Array.isArray(s.scenarios)||Array.isArray(s.rows)){
  const rows=(Array.isArray(s.scenarios)?s.scenarios:s.rows as unknown[]).map(record)
  if(rows.length)items.push(`Compare **${rows.length} stored scenarios**; their target populations are not newly gained access.`)
  items.push('Missing cost/carbon estimates remain unavailable. These results do not establish a BCR ranking or an approved intervention.')
 }
 if(!items.length&&Array.isArray(section.chart_data.data)&&section.chart_data.type==='horizontal_bar'){
  const rows=section.chart_data.data.map(record).filter(row=>finite(row.value)&&text(row.label))
  const ranked=[...rows].sort((a,b)=>Number(b.value)-Number(a.value))
  if(ranked.length){const high=ranked[0],low=ranked.at(-1)!;const unit=text(s.unit)||text(section.chart_data.x_label)
   items.push(`Highest stored value: **${text(high.label)}**, ${bold(high.value,2)} ${unit}.`)
   if(ranked.length>1)items.push(`Lowest stored value: **${text(low.label)}**, ${bold(low.value,2)} ${unit}.`)
  }
 }
 return items
}

export function chartMethod(section:SectionItem,country:string):string {
 const presentation=sectionPresentation(section,country)
 if(presentation.interpretation)return presentation.interpretation
 const type=section.chart_data.type
 if(type==='scatter_regression'||type==='scatter_clusters')return 'Axes retain their source units. Plotted points are the supplied display sample; summary statistics describe the source scope. Association does not establish causation.'
 if(type==='heatmap')return 'Cells use the stored measure and country-specific grouping. Blank cells are unavailable, rather than zero. Deprivation indices remain within each country.'
 return 'Values describe the selected country and source filter, with native units retained. Missing observations remain unavailable. Network dates and population/deprivation vintages are distinct.'
}
