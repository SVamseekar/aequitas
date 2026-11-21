import type { SectionItem } from '@/api/types'
import { coveragePresentation } from './coverage'

interface Presentation { title?: string; interpretation?: string; chartData: Record<string, unknown> }

/** Label stored exhibits by their actual measure; never replace observations. */
export function sectionPresentation(section: SectionItem, country: string): Presentation {
  let chartData = section.chart_data
  if (country !== 'england') {
    if (section.section_id === 'd7_deprivation_urban_rural' && chartData.type === 'heatmap') {
      chartData = { ...chartData, measure: 'population_400m_pct', height: 236 }
    }
    if (country === 'france' && section.section_id === 'f3_ethnic_access') {
      return { title: 'Immigrés share and stop density', interpretation: 'This INSEE measure describes origin (immigrés), rather than ethnicity. The association is at area level and does not establish causation.', chartData: { ...chartData, title: 'Immigrés share and stop density', x_label: 'Immigrés share (origin)' } }
    }
    if (country === 'netherlands' && section.section_id === 'f3_ethnic_access') {
      return { title: 'Herkomst buiten Europa and stop density', interpretation: 'CBS herkomst buiten Europa describes origin, rather than ethnicity. The association is at area level and does not establish causation.', chartData: { ...chartData, title: 'Herkomst buiten Europa and stop density', x_label: 'Herkomst buiten Europa share (origin)' } }
    }
    return { chartData }
  }
  if (['d8_feature_importance','g3_coverage_model','g4_shap'].includes(section.section_id)) return {
    title: section.section_id === 'g3_coverage_model' ? 'National model fit' : 'Predictive feature importance',
    interpretation: 'National Random Forest regression target: log1p(trips per capita). Held-out model fit and SHAP importance describe predictive associations, not causal effects. Region and area filters do not refit this model. Unexplained variance does not identify policy effects.',
    chartData: {...chartData,title:'Predictive feature importance'},
  }
  if (section.dimension === 'correlations' && chartData.type === 'scatter_regression') {
    const x = typeof chartData.x_label === 'string' ? chartData.x_label : 'Source predictor'
    const y = typeof chartData.y_label === 'string' ? chartData.y_label : 'Source service measure'
    const title = `${x} and ${y}`
    return {title,interpretation:`Area-level association within England. ${x} and ${y} retain the source units; scheduled trips and stop density are distinct from binary proximity. The plot is the supplied display sample, while the correlation and observation count describe the full selected filter. Correlation does not establish causation.`,chartData:{...chartData,title}}
  }
  const definitions: Record<string, [string, string, string?]> = {
    a3_walking_distance: [coveragePresentation(country).title, `${coveragePresentation(country).definition} The separately reported population with zero access is a population sum. This is distinct from travel-time accessibility.`],
    f1_gini: ['Distribution of service across the population', 'The Lorenz curve orders people by trips per capita, lowest first. The equality diagonal indicates equal service distribution. Gini, Palma and the deprivation concentration index describe different distributions and are not directly comparable.'],
    f2_disparity_ratio: ['Scheduled service by deprivation', 'Mean scheduled trips per capita by in-country IMD decile: 1 is most deprived and 10 least deprived. The disparity ratio is least-deprived divided by most-deprived. This area-level association does not imply causation.', 'Trips per capita'],
    f3_ethnic_access: ['Bus access by ethnicity', 'Each plotted point represents one area in the stored sample. The correlation describes the area-level association between Non-White population share and bus stops per 1,000 residents. It does not establish an individual-level or causal relationship.'],
    f5_rural_penalty: ['Rural service quality gap', 'Regional urban and rural service quality indices use SQI points. The relative gap compares rural SQI with urban SQI. London has no rural LSOAs under the official classification; its rural observation is unavailable.', 'Service Quality Index (points)'],
    f6_equitable_regions: ['Regional vulnerability', 'Additional warehouse exhibit; the metric is vulnerability index. A lower index indicates lower vulnerability. This measure is not Gini. The reference line is the selected warehouse average.', 'Vulnerability index'],
    a1_route_density: ['Route count by region', 'Additional warehouse exhibit. Values are route counts by region, rather than routes per square kilometre.', 'Routes'],
    a2_stop_density: ['Stop density by region', 'Stops per 1,000 residents. This inventory measure does not indicate service frequency or passenger demand.', 'Stops per 1,000 population'],
    a4_coverage_equity: ['Service distribution', 'This additional warehouse exhibit describes the distribution of trips per capita. It overlaps Equity and is not a binary stop-coverage measure. Open Equity for the primary distribution view.'],
    a6_urban_rural_gap: ['Urban/rural service gap', 'Mean trips per capita by region and settlement type. This measure differs from both 400 m stop coverage and the rural SQI gap. London rural is unavailable under the official classification.', 'Mean trips per capita'],
    a7_investment_gap: ['Gap to the national median', 'Indicative annual investment to reach the stated national-median service target. The source uses an unverified proxy cost of £500 per LSOA per unit of gap per year (COST-004); this is not an approved appraisal or benefit-cost ratio.', 'Indicative investment gap (£m / year)'],
    a8_coverage_prediction: ['Bus service from demographics', 'National Random Forest model of log1p(trips per capita), evaluated on a held-out test set. Region and area filters do not refit this model. SHAP importance describes predictive associations, not causal policy effects; unexplained variance cannot be attributed to policy choices.'],
    b5_frequency_deprivation: ['Service quality and deprivation', 'IMD score and scheduled Service Quality Index describe an area-level association within England. Higher IMD score indicates greater deprivation; higher SQI indicates better scheduled service quality. Correlation does not establish causation. The plot contains the supplied display sample; summary statistics describe the full selected filter.'],
    c5_length_vs_frequency: ['Route length and stop count', 'Each plotted observation represents a route, not a small area. Stop count is a geometric proxy and does not measure buses per hour, scheduled departures or passenger demand. Correlation does not establish causation. The plotted display sample is separate from the full route sample count.'],
    d7_deprivation_urban_rural: ['Urban minus rural service quality by deprivation decile', 'Stored Urban minus Rural Service Quality Index gap by in-country IMD decile. Positive values mean urban areas have higher SQI. Decile 1 is most deprived and 10 least deprived. This is an association, not a causal effect; the gap is in SQI points, not coverage percentage.'],
  }
  const definition = definitions[section.section_id]
  if (!definition) return { chartData }
  chartData = { ...chartData, title: definition[0], ...(definition[2] ? { x_label: definition[2] } : {}) }
  if (section.section_id === 'a1_route_density') chartData = { ...chartData, palette: ['#819d79'] }
  if (section.section_id === 'a2_stop_density') chartData = { ...chartData, palette: ['#6a98b6'] }
  if (section.section_id === 'f6_equitable_regions') chartData = { ...chartData, order: 'ascending' }
  if (section.section_id === 'c5_length_vs_frequency') chartData = {...chartData,x_label:'Route length (km)',y_label:'Stops per route (not measured frequency)'}
  if (section.section_id === 'd7_deprivation_urban_rural' && Array.isArray(chartData.data)) {
    const rows=[...chartData.data as {label:string;value:number}[]].sort((a,b)=>Number(a.label.replace(/\D/g,''))-Number(b.label.replace(/\D/g,'')))
    const maximum=Math.max(1,...rows.filter(row=>typeof row.value==='number'&&Number.isFinite(row.value)).map(row=>Math.abs(row.value)))
    chartData={...chartData,data:rows,order:'source',x_domain:[-maximum*1.1,maximum*1.1],reference_rules:[0],x_label:'Urban − rural SQI gap (points)',palette:['#6a98b6']}
  }
  if (section.section_id === 'f5_rural_penalty' || section.section_id === 'a6_urban_rural_gap') {
    chartData = { ...chartData, orientation: 'vertical', sqi_scale: section.section_id === 'f5_rural_penalty' }
    const categories = Array.isArray(chartData.categories) ? chartData.categories : []
    const london = categories.findIndex(label => label === 'London')
    if (london >= 0 && Array.isArray(chartData.series)) {
      chartData = { ...chartData, series: chartData.series.map(raw => {
        if (!raw || typeof raw !== 'object') return raw
        const series = raw as Record<string, unknown>
        if (series.name !== 'Rural') return series
        const field = Array.isArray(series.values) ? 'values' : 'data'
        const values = series[field]
        return Array.isArray(values) ? { ...series, [field]: values.map((value, index) => index === london ? null : value) } : series
      }) }
    }
  }
  return { title: definition[0], interpretation: definition[1], chartData }
}
