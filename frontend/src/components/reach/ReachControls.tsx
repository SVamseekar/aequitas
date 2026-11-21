import { useSearchParams } from 'react-router'
import { REACH_CUTOFFS, REACH_DESTINATIONS, reachSelection } from '@/lib/reach'

export function ReachControls({ segmentedCutoff = false }: { segmentedCutoff?: boolean }) {
  const [params, setParams] = useSearchParams()
  const { dest, cutoff } = reachSelection(params)
  const set = (key: string, value: string) => { const next = new URLSearchParams(params); next.set(key, value); setParams(next) }
  return <div className='reach-controls'>
    <div><span>Destination type</span><div className='reach-segmented'>{REACH_DESTINATIONS.map(item => <button type='button' key={item.id} aria-pressed={dest.id === item.id} onClick={() => set('dest', item.id)}>{item.label}</button>)}</div></div>
    {segmentedCutoff ? <div><span>Travel time cutoff</span><div className='reach-segmented'>{REACH_CUTOFFS.map(value => <button type='button' key={value} aria-pressed={cutoff === value} onClick={() => set('cutoff', String(value))}>{value} min</button>)}</div></div> : <label>Travel time cutoff<select aria-label='Travel time cutoff' value={cutoff} onChange={event => set('cutoff', event.target.value)}>{REACH_CUTOFFS.map(value => <option key={value} value={value}>{value} min</option>)}</select></label>}
  </div>
}
