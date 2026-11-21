import {AlertTriangle,FileQuestion,MapPin} from 'lucide-react'
import type {ReactNode} from 'react'

/** Keep empty geography, missing observations and request failure separate. */
export function EvidenceState({kind,title,description,retry,action}:{kind:'empty'|'unavailable'|'error';title:string;description:string;retry?:()=>void;action?:ReactNode}){
 const Icon=kind==='empty'?MapPin:kind==='unavailable'?FileQuestion:AlertTriangle
 return <section className={`app-panel evidence-state evidence-state-${kind}`} role={kind==='error'?'alert':undefined}>
  <Icon size={42} aria-hidden='true' /><h1>{title}</h1><p>{description}</p><div className='workspace-actions'>{retry&&<button type='button' className='app-btn-primary' onClick={retry}>Retry evidence</button>}{action}</div>
 </section>
}
