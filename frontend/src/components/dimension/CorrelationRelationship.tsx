import type { SectionItem } from '@/api/types'
import { ChartRenderer } from '@/components/charts/ChartRenderer'
import { finiteObservation as finite, serviceNumber as number } from '@/lib/serviceData'
import { sectionPresentation } from '@/lib/sectionPresentation'
import { ChartInsights } from './ChartInsights'

/** Native sample plot and full-filter statistics have deliberately distinct scopes. */
export function CorrelationRelationship({ section }: { section: SectionItem }) {
  const presentation=sectionPresentation(section,'england')
  const r=section.stats.r,p=section.stats.p_value
  if(section.suppressed||section.stats.omit)return <section className='app-panel'><h2>{presentation.title}</h2><p>{typeof section.stats.omit_reason==='string'?section.stats.omit_reason:'This relationship is unavailable for the selected filter. No point positions or statistics are inferred.'}</p></section>
  return <article className='correlation-relationship evidence-featured' data-section={section.section_id}>
    <section className='app-panel'><h2>{presentation.title}</h2><p>Stored area-level relationship · source units retained.</p><div className='evidence-chart'><ChartRenderer chartData={{...presentation.chartData,height:260,show_summary:false,point_color:'#8eac83',point_opacity:.45,point_radius:2,line_color:'#d65b2d'}} /></div></section>
    <aside className='app-panel evidence-statistics'><h2>Correlation (Pearson’s r)</h2><strong className='correlation-value'>{finite(r)?r.toFixed(4):'—'}</strong><ChartInsights title={null} items={finite(r)?[`A **${typeof section.stats.strength==='string'?section.stats.strength:'stored'} ${typeof section.stats.direction==='string'?section.stats.direction:'source'}** relationship between the plotted measures. This is an association, not a causal effect.`]:[]} />
      <dl>{[['Observations',number(section.stats.n)],['p-value',finite(p)?p<0.0001?'< 0.0001':p.toFixed(4):'—']].map(([label,value])=><div key={label}><dt>{label}</dt><dd>{value}</dd></div>)}</dl>
      <p className='correlation-method'>Statistics describe the full selected filter. The plot shows the supplied display sample. Association does not establish causation.</p>
      <details><summary>Interpretation and source units</summary><p>{presentation.interpretation}</p><p>England BODS schedules · Census 2021 LSOAs · IMD 2025.</p></details>
    </aside>
  </article>
}
