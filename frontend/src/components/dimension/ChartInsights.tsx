import type {SectionItem} from '@/api/types'
import {chartInsights} from '@/lib/chartInsights'
import {Markdown} from '@/components/shared/Markdown'

export function ChartInsights({section,country='england',items,title='Key points',className=''}:{section?:SectionItem;country?:string;items?:string[];title?:string|null;className?:string}) {
 const points=items??(section?chartInsights(section,country):[])
 if(!points.length)return null
 return <section className={`chart-insights ${className}`} aria-label={title??'Chart insight'}>{title&&<h3>{title}</h3>}<ul>{points.map((point,index)=><li key={`${index}-${point}`}><Markdown content={point} /></li>)}</ul></section>
}
