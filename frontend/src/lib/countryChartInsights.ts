import type {SectionItem} from '@/api/types'
import {finiteObservation as finite,serviceNumber as number} from './serviceData'
import {modelFeatureLabel} from './modelLabels'
const record=(v:unknown):Record<string,unknown>=>v&&typeof v==='object'&&!Array.isArray(v)?v as Record<string,unknown>:{}
const text=(v:unknown)=>typeof v==='string'?v:''
const b=(v:unknown,d=0)=>`**${number(v,d)}**`

/** Foreign packs have different contracts; never relabel them as England's measures. */
export function countryChartInsights(section:SectionItem):string[]{
 const s=section.stats,id=section.section_id,out:string[]=[]
 if(id==='a7_investment_gap'&&finite(s.people_gap))return [`The stored people-gap is ${b(s.people_gap)} residents${finite(s.local_pct_covered)?`; local population coverage is ${number(s.local_pct_covered,1)}%`:''}.`,...(finite(s.national_pct_covered)?[`The national coverage benchmark is ${b(s.national_pct_covered,1)}%.`]:[]),'This is a people-gap measure; no currency cost is inferred.']
 if(id==='b2_operating_hours'&&finite(s.n_evening_isolated))return [`${b(s.n_evening_isolated)} areas${finite(s.pct_evening_isolated)?` (${number(s.pct_evening_isolated,1)}%)`:''} have no scheduled service after 19:00.`, 'This is an evening-service observation, not a supplied first/last-service time range.']
 if(id==='g2_anomalies'&&finite(s.n_flagged))return [`The source flags ${b(s.n_flagged)} areas using its stored rule.`,...(text(s.rule)?[`Rule: **${text(s.rule)}**.`]:[]),'Rule-based flags are not England ensemble-model anomaly counts or causal findings.']
 if(['a6_urban_rural_gap','f5_rural_penalty'].includes(id)){
  for(const [key,label]of [['urban','Urban'],['rural','Rural']]){const g=record(s[key]);if(finite(g.pct_covered))out.push(`${label} population coverage within 400 m is ${b(g.pct_covered,1)}%.`)}
  const gap=s.gap_pp??s.penalty_pp;if(finite(gap))out.push(`The stored difference is ${b(gap,1)} percentage points, not a relative percentage.`)
  if(out.length)return out
 }
 if(id==='c4_urban_rural_routes'&&(finite(s.urban_stops)||finite(s.rural_stops)))return [...(finite(s.urban_stops)?[`${b(s.urban_stops)} stops are in the stored urban grouping.`]:[]),...(finite(s.rural_stops)?[`${b(s.rural_stops)} stops are in the stored rural grouping.`]:[]),'These are stop counts, not route shares or service frequency.']
 if(id==='b4_route_frequency'&&Array.isArray(s.agencies)){
  const agencies=s.agencies.map(record).filter(row=>finite(row.n_routes)).sort((a,b)=>Number(b.n_routes)-Number(a.n_routes)),top=agencies[0]
  if(top)return [`The largest supplied agency is **${text(top.name)}**, with ${b(top.n_routes)} routes${finite(top.share)?` (${number(top.share*100,1)}%)`:''}.`,'This source counts routes by agency; route inventory is distinct from scheduled trips per day.']
 }
 if(id==='d6_transport_poverty'&&typeof s.method==='string')return [`Stored selection: **${s.method}**.`,...(finite(s.n_sas)?[`${b(s.n_sas)} source areas meet this criterion.`]:[]),...(finite(s.population)?[`These areas contain ${b(s.population)} residents; this is not an individual poverty classification.`]:[])]
 if(Array.isArray(s.features)&&!finite(s.r2)){
  for(const row of s.features.map(record))if(finite(row.r))out.push(`**${modelFeatureLabel(text(row.name))}**: stored correlation r = ${b(row.r,4)}.`)
  out.push('This pack supplies feature associations or rules, not numerical SHAP importance. Missing correlations remain unavailable.')
  return out
 }
 if(finite(s.r2))return [`Stored model R²: ${b(s.r2,4)}.`,...(text(s.target)?[`Source target: **${text(s.target)}**.`]:['No England target definition or fitted model is substituted for this country.']),'Model fit and feature associations do not establish causal effects.']
 if(id==='g1_route_clusters'&&finite(s.n_clusters)&&!Array.isArray(s.clusters))return [`The source specifies ${b(s.n_clusters)} groups${Array.isArray(s.labels)?`: ${s.labels.filter(v=>typeof v==='string').join(', ')}`:''}.`,'Point positions or counts are shown only where supplied; they are not inferred from group labels.']
 if(id==='g5_scenario_model'&&Array.isArray(s.points_at))return [`This view references **${s.points_at.length} stored interventions**. It does not supply a separate live model result.`,'Inspect the individual scenarios for their supplied target populations and available estimates.']
 if(id==='f2_disparity_ratio'&&Array.isArray(s.by_decile)){
  const rows=s.by_decile.map(record).filter(row=>finite(row.pct_covered)),first=rows[0],last=rows.at(-1)
  if(first)out.push(`Source decile **${String(first.decile)}** has ${b(first.pct_covered,1)}% population coverage within 400 m.`)
  if(last&&last!==first)out.push(`Source decile **${String(last.decile)}** has ${b(last.pct_covered,1)}% coverage. Deciles remain within **${text(s.index)||'this country'}**.`)
  if(finite(s.ratio))out.push(`Stored disparity ratio: ${b(s.ratio,3)}.`)
  return out
 }
 if(id==='j4_investment_priority'&&Array.isArray(s.ranking)){
  const rows=s.ranking.map(record).filter(row=>finite(row.pop_desert)).sort((a,b)=>Number(b.pop_desert)-Number(a.pop_desert)),top=rows[0]
  if(top)return [`**${text(top.name)}** has the largest stored population beyond the proximity threshold: ${b(top.pop_desert)} residents.`,'The ranking uses people and proximity; no missing currency appraisal is supplied.']
 }
 if(id==='bsa3_tier_distribution'&&s.tiers&&typeof s.tiers==='object')return Object.entries(record(s.tiers)).filter(([,v])=>finite(v)).map(([label,value])=>`**${label}**: ${b(value)} source areas. These are source programme categories, not England district-readiness tiers.`)
 if(finite(s.national_avg)&&text(s.unit))return [`The stored benchmark is ${b(s.national_avg,2)} ${text(s.unit)}.`,...(finite(s.value)&&s.value!==s.national_avg?[`The selected value is ${b(s.value,2)} in the same units.`]:[]),...(text(s.programme)?['This is the source coverage proxy, not a legal-eligibility result.']:[])]
 return out
}
