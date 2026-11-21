import { useEffect, useRef, useState } from 'react'
import { fetchJson } from '@/api/client'
import { operationLabel, type StudioOp, type StudioPatch } from '@/lib/studio'

interface Props { patch: StudioPatch; disabled: boolean; onAdd: (ops: StudioOp[]) => void }
export default function StudioUpload({ patch, disabled, onAdd }: Props) {
  const [review, setReview] = useState<{ name: string; ops: StudioOp[] } | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [reading, setReading] = useState(false)
  const request = useRef<AbortController | null>(null)
  useEffect(() => () => request.current?.abort(), [])
  const read = async (file: File) => {
    request.current?.abort()
    const controller = new AbortController()
    request.current = controller
    setReview(null); setError(null); setReading(true)
    try {
      if (file.size > 10 * 1024 * 1024) throw new Error('Choose a file up to 10 MB.')
      const body: Record<string, string> = { filename: file.name, country: patch.country, region: patch.region, urban_rural: patch.urban_rural }
      if (file.name.toLowerCase().endsWith('.zip')) {
        const data = new Uint8Array(await file.arrayBuffer())
        let binary = ''
        for (let offset = 0; offset < data.length; offset += 8192) binary += String.fromCharCode(...data.subarray(offset, offset + 8192))
        body.archive_base64 = btoa(binary)
      } else body.text = await file.text()
      if (controller.signal.aborted) return
      const parsed = await fetchJson<{ ok: boolean; error: string | null; ops: StudioOp[] }>('/studio/parse', undefined, {
        method: 'POST', body: JSON.stringify(body), signal: controller.signal,
      })
      if (controller.signal.aborted) return
      if (!parsed.ok) throw new Error(parsed.error ?? 'That file could not be read.')
      setReview({ name: file.name, ops: parsed.ops })
    } catch (err) {
      if (!controller.signal.aborted) setError(err instanceof Error ? err.message : 'That file could not be read.')
    } finally { if (!controller.signal.aborted) setReading(false) }
  }
  return <div className='studio-two-columns'>
    <section className='app-panel'>
      <h2>Upload a network patch</h2>
      <p className='mt-2'>Review the file before adding its operations to your draft.</p>
      <label className='studio-dropzone'>
        <strong>Choose CSV, GeoJSON or GTFS ZIP</strong>
        <span>Up to 10 MB · latitude / longitude in WGS84</span>
        <input aria-label='Upload network patch' type='file' disabled={disabled || reading} accept='.csv,.txt,.geojson,.json,.zip' onChange={event => {
          const file = event.target.files?.[0]
          if (file) void read(file)
          event.target.value = ''
        }} />
      </label>
      <p>CSV accepts lat / lon or stop_lat / stop_lon. GeoJSON accepts points and lines. GTFS ZIP imports stops.txt; it does not import a routing timetable.</p>
      <p className='mt-3'>Country bounds are checked. Review the selected region and area before applying.</p>
    </section>
    <section className='app-panel' aria-busy={reading}>
      <h2>Validation preview</h2>
      {reading ? <p role='status' className='mt-4'>Reading and validating the file…</p> : null}
      {error ? <p role='alert' className='studio-notice mt-4'>{error}</p> : null}
      {!review && !reading && !error ? <p className='studio-empty'>Choose a file to review its operations. Impacts are not calculated.</p> : null}
      {review ? <>
        <p className='mt-4'>{review.name} · {review.ops.length} parsed operations</p>
        <dl className='studio-review'><div><dt>Country</dt><dd>{patch.country}</dd></div><div><dt>Region</dt><dd>{patch.region}</dd></div><div><dt>Area</dt><dd>{patch.urban_rural}</dd></div></dl>
        <div className='studio-table-scroll'><table className='studio-table'><thead><tr><th>Operation</th><th>Coordinates / parameters</th></tr></thead><tbody>{review.ops.map((op, index) => <tr key={index}><td>{index + 1}</td><td>{operationLabel(op)}</td></tr>)}</tbody></table></div>
        <button type='button' className='app-primary-button mt-4' disabled={disabled} onClick={() => {
          onAdd(review.ops.map(op => ({ ...op, source: 'upload' }))); setReview(null)
        }}>Add reviewed operations</button>
      </> : null}
    </section>
  </div>
}
