import { useState } from 'react'
import { downloadStudioPatch, hasStudioImpact, type StudioJob, type StudioPatch, type StudioResult } from '@/lib/studio'
import { AREA_TYPES, COUNTRIES, regionsForCountry } from '@/lib/constants'

interface Props { patch: StudioPatch; job: StudioJob | null; result: StudioResult | null; pack: string; currentNetwork: boolean }
export default function StudioExport({ patch, job, result, pack, currentNetwork }: Props) {
  const [selected, setSelected] = useState({ patch: true, winners: false, research: false })
  const [error, setError] = useState<string | null>(null)
  const [downloading, setDownloading] = useState(false)
  const impact = hasStudioImpact(result) && job?.status === 'done'
  const country = COUNTRIES.find(item => item.code === patch.country)?.name ?? patch.country
  const region = regionsForCountry(patch.country).find(item => item.code === patch.region)?.name ?? patch.region
  const area = AREA_TYPES.find(item => item.code === patch.urban_rural)?.name ?? patch.urban_rural
  const items = [
    { key: 'patch' as const, name: 'Patch JSON', description: 'Draft network operations in WGS84.', ready: patch.ops.length > 0 },
    { key: 'winners' as const, name: 'Winners / losers CSV', description: 'Area gains and losses from this run.', ready: impact },
    { key: 'research' as const, name: 'Research pack CSV', description: 'Warehouse evidence with this result.', ready: impact && ['england', 'ireland'].includes(patch.country) && currentNetwork },
  ]
  const chosen = items.filter(item => selected[item.key] && item.ready)
  const download = async () => {
    setError(null); setDownloading(true)
    try {
      for (const item of chosen) {
        if (item.key === 'patch') { downloadStudioPatch(patch); continue }
        if (!job) continue
        const url = item.key === 'winners' ? `/api/studio/jobs/${encodeURIComponent(job.id)}/winners.csv` : `/api/export/pack.csv?${new URLSearchParams({ country: patch.country, region: patch.region, urban_rural: patch.urban_rural, studio_job: job.id })}`
        const response = await fetch(url, { credentials: 'include' })
        if (!response.ok) throw new Error(`Could not download ${item.name} (${response.status}). Please retry.`)
        const href = URL.createObjectURL(await response.blob())
        const anchor = document.createElement('a')
        anchor.href = href; anchor.download = item.key === 'winners' ? 'studio-winners-losers.csv' : 'aequitas-research-pack.csv'; anchor.click()
        window.setTimeout(() => URL.revokeObjectURL(href), 1000)
      }
    } catch (err) { setError(err instanceof Error ? err.message : 'Download failed.') }
    finally { setDownloading(false) }
  }
  return <>
    <div className='studio-two-columns'>
      <section className='app-panel'><h2>1. Review your selection</h2><p className='mt-2'>These settings define the data included in the exported files.</p><dl className='studio-review'><div><dt>Country</dt><dd>{country}</dd></div><div><dt>Region</dt><dd>{region}</dd></div><div><dt>Area</dt><dd>{area}</dd></div><div><dt>Network</dt><dd>{pack || 'Current warehouse'}</dd></div><div><dt>Result method</dt><dd>Walk-to-stop · 400 m</dd></div><div><dt>Operations</dt><dd>{patch.ops.length}</dd></div></dl></section>
      <section className='app-panel'><h2>2. Export items</h2><p className='mt-2'>Select the files to download.</p><div className='studio-export-items'>{items.map(item => <label key={item.key} className={item.ready ? '' : 'unavailable'}><div><strong>{item.name}</strong><p>{item.description}</p><span>{item.ready ? item.key === 'patch' ? 'Draft available' : 'Result available' : item.key === 'patch' ? 'No draft yet' : 'No computed impact yet'}</span></div><input type='checkbox' checked={selected[item.key] && Boolean(item.ready)} disabled={!item.ready || downloading} onChange={event => setSelected(previous => ({ ...previous, [item.key]: event.target.checked }))} /></label>)}</div></section>
    </div>
    {!impact ? <p className='studio-notice mt-4'>Impact files are disabled until a completed calculation contains area results. You can export a draft Patch JSON when available.</p> : null}
    <div className='studio-two-columns mt-4'><section className='app-panel'><h2>3. Summary</h2><dl className='studio-review'><div><dt>Export items</dt><dd>{chosen.map(item => item.name).join(', ') || 'None selected'}</dd></div><div><dt>Method</dt><dd>Walk-to-stop · 400 m</dd></div></dl></section><section className='app-panel'><h2>4. Download</h2><button type='button' className='app-primary-button studio-download' disabled={!chosen.length || downloading} onClick={() => void download()}>{downloading ? 'Downloading…' : 'Download selected files'}</button>{error ? <p role='alert' className='studio-notice mt-3'>{error}</p> : null}</section></div>
  </>
}
