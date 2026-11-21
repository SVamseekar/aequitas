import { ChartInsights } from '@/components/dimension/ChartInsights'
import type { SectionItem } from '@/api/types'
import { ChartRenderer } from '@/components/charts/ChartRenderer'
import { sectionPresentation } from '@/lib/sectionPresentation'

export function CorrelationRural({section}:{section:SectionItem}) {
  const presentation=sectionPresentation(section,'england')
  return <div className='correlation-rural'>
    <div className='correlation-rural-main'><section className='app-panel'><h2>Deprivation × urban/rural — urban minus rural SQI gap by IMD decile</h2><p>England · service quality index points</p>{section.suppressed||section.stats.omit?<p>No observations are available for this filter.</p>:<ChartRenderer chartData={presentation.chartData} />}</section>
      <aside className='app-panel'><ChartInsights section={section} /><h2>What this shows</h2><p>Each bar is the urban-minus-rural SQI difference within an IMD decile, rather than a 400 m coverage percentage.</p><h3>Caveats</h3><p>Association at area level does not establish causation. Missing urban or rural observations remain unavailable.</p></aside></div>
    <div className='correlation-rural-notes'><section className='app-panel'><h2>About this measure</h2><p>{presentation.interpretation}</p></section><section className='app-panel'><h2>Data and notes</h2><p>England BODS schedules · Census 2021 LSOAs · IMD 2025.</p><p>Network dates and filters stay in the URL. Deprivation ranks are within England.</p></section></div>
  </div>
}
