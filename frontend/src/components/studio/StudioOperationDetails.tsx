import { useState } from 'react'
import { operationLabel, type StudioOp } from '@/lib/studio'

interface Props { ops: StudioOp[]; disabled: boolean; onChange: (ops: StudioOp[]) => void }
export default function StudioOperationDetails({ ops, disabled, onChange }: Props) {
  const [index, setIndex] = useState(0)
  const selected = Math.min(index, Math.max(0, ops.length - 1))
  const op = ops[selected]
  const update = (values: Partial<StudioOp>) => onChange(ops.map((item, i) => i === selected ? { ...item, ...values } : item))
  return <section className='app-panel studio-details'>
    <h2>Selected operation</h2>
    <label>Operation<select value={selected} disabled={disabled || !op} onChange={event => setIndex(Number(event.target.value))}>{ops.length ? ops.map((item, i) => <option value={i} key={i}>{i + 1}. {operationLabel(item)}</option>) : <option value={0}>No operation selected</option>}</select></label>
    {op && (op.op === 'add_stop' || op.op === 'remove_stop') ? <>
      <label>Latitude<input type='number' step='any' value={op.lat ?? ''} disabled={disabled} onChange={event => update({ lat: event.target.value ? Number(event.target.value) : undefined })} /></label>
      <label>Longitude<input type='number' step='any' value={op.lon ?? ''} disabled={disabled} onChange={event => update({ lon: event.target.value ? Number(event.target.value) : undefined })} /></label>
      <label>Operation name<input value={op.name ?? ''} disabled={disabled} onChange={event => update({ name: event.target.value })} /></label>
    </> : <p>{op ? 'Corridor and frequency parameters appear in the operations list.' : 'Add or upload an operation to review its details.'}</p>}
  </section>
}
