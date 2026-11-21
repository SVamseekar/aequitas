import type { SectionItem } from '@/api/types'
import { useFilters } from '@/api/hooks'
import { COUNTRIES, sectionTitle } from '@/lib/constants'
import { Markdown } from '@/components/shared/Markdown'

export function PackContext({sections,policy=false}:{sections:SectionItem[];policy?:boolean}) {
  const {country,pack}=useFilters()
  const name=COUNTRIES.find(row=>row.code===country)?.name??country
  return <div className='network-page'><section className='app-panel'><h2>{policy?'Country policy context':'Economic model assumptions'} — {name}</h2><p>Stored source pack: {pack||'current registered network'}. Network date is separate from policy, population, deprivation and appraisal-factor vintages.</p><p>{policy?'Readiness outputs and the source narrative below describe this analytical pack. They do not establish current statutory eligibility or approval.':'Source values retain their native units. Currency values, people gaps, annual estimates and present values are separate measures; no missing country factor is substituted.'}</p></section>{sections.map(section=><details className='app-panel mt-4' key={section.section_id}><summary>{sectionTitle(section.section_id,country)??section.section_id}</summary><div className='access-table-scroll'><table aria-label={`${section.section_id} stored inputs`}><thead><tr><th>Source field</th><th>Native source value</th></tr></thead><tbody>{Object.entries(section.stats).filter(([,v])=>v===null||typeof v==='number'||typeof v==='string'||typeof v==='boolean').map(([key,value])=><tr key={key}><th scope='row'>{key}</th><td>{value===null?'Unavailable':String(value)}</td></tr>)}</tbody></table></div>{policy&&section.narrative&&<><h3 className='mt-4'>Stored pack narrative</h3><Markdown content={section.narrative} /></>}</details>)}</div>
}
