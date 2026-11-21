import {Link} from 'react-router'
import {useFilters,usePackDates} from '@/api/hooks'
import {COUNTRY_BRIEFS} from '@/lib/briefingCatalog'

export function SourceFooter(){
 const {country,pack}=useFilters(),packs=usePackDates()
 const entry=packs.data?.[country],dates=entry&&'dates' in entry?entry.dates??[]:[]
 const selected=dates.find(row=>row.pack_id===pack)||(!pack?dates.find(row=>row.current):undefined)
 const brief=COUNTRY_BRIEFS.find(row=>row.code===country)
 const date=selected?.as_of
 const network=date&&/^\d{4}-\d{2}-\d{2}$/.test(date)?new Date(`${date}T12:00:00Z`).toLocaleDateString('en-GB',{day:'2-digit',month:'short',year:'numeric',timeZone:'UTC'}):pack||'Current registered network'
 return <footer className='app-source-footer'><span>Network: {brief?.network??country} · {network} <span aria-hidden='true'> · </span> Geography: {brief?.geography.replace(/\s*\(.*/, '')??'Source geography'} <span aria-hidden='true'> · </span> Deprivation: {brief?.deprivation??'National index'}</span><div><Link to='/methodology'>Methodology</Link><Link to='/privacy'>Privacy</Link><Link to='/contact'>Contact</Link></div></footer>
}
