import { useContext } from 'react'
import { MessageCircle } from 'lucide-react'
import { AssistantContext } from '@/lib/assistantContext'

export function BriefingActions() {
  const open = useContext(AssistantContext)
  return open ? <button type='button' className='app-panel-button assistant-entry' onClick={open}><MessageCircle size={17} aria-hidden='true' /> Ask Aequitas</button> : null
}
