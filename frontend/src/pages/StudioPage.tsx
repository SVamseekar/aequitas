import { useEffect, useState } from 'react'
import { Link, useSearchParams } from 'react-router'
import { useFilters, usePackDates } from '@/api/hooks'
import { AREA_TYPES, COUNTRIES, regionsForCountry } from '@/lib/constants'
import { appPath, withSearch } from '@/lib/appRoutes'
import { isLondonRural } from '@/lib/uniqueExhibits'
import { downloadStudioPatch, operationLabel, studioViews, studioViewNames, type StudioOp, type StudioPatch, type StudioView } from '@/lib/studio'
import { useStudioRun } from '@/hooks/useStudioRun'
import { BriefingActions } from '@/components/shared/BriefingActions'
import StudioEditorMap from '@/components/studio/StudioEditorMap'
import StudioUpload from '@/components/studio/StudioUpload'
import StudioJobStages from '@/components/studio/StudioJobStages'
import StudioResults from '@/components/studio/StudioResults'
import StudioExport from '@/components/studio/StudioExport'
import StudioOperationDetails from '@/components/studio/StudioOperationDetails'

export type { StudioOp } from '@/lib/studio'

export default function StudioPage() {
  const { country, region, urbanRural, pack, mode } = useFilters()
  // Context changes cancel observation and restore only that context's draft.
  const contextKey = JSON.stringify([country, region, urbanRural, pack, mode])
  return <StudioWorkspace key={contextKey} country={country} region={region} urbanRural={urbanRural} pack={pack} contextKey={contextKey} />
}

interface Props { country: string; region: string; urbanRural: string; pack: string; contextKey: string }
function StudioWorkspace({ country, region, urbanRural, pack, contextKey }: Props) {
  const [params, setParams] = useSearchParams()
  const rawView = params.get('view')
  const view: StudioView = studioViews.includes(rawView as StudioView) ? rawView as StudioView : 'edit'
  const storageKey = `aequitas.studio.patch.v2:${contextKey}`
  const [ops, setOps] = useState<StudioOp[]>(() => {
    try {
      const parsed = JSON.parse(window.localStorage.getItem(storageKey) ?? 'null') as StudioPatch | null
      return parsed?.country === country && parsed.region === region && parsed.urban_rural === urbanRural && Array.isArray(parsed.ops) ? parsed.ops : []
    } catch { return [] }
  })
  const [warning, setWarning] = useState<string | null>(null)
  const [factor, setFactor] = useState('1.5')
  const [extraTrips, setExtraTrips] = useState('4')
  const run = useStudioRun()
  const packs = usePackDates()
  const countryPacks = packs.data?.[country as keyof NonNullable<typeof packs.data>]
  const currentDate = countryPacks && 'dates' in countryPacks ? countryPacks.dates?.find(item => item.current) : undefined
  const currentNetwork = !pack || ['current', 'latest'].includes(pack.toLowerCase()) || Boolean(currentDate && [currentDate.pack_id, currentDate.as_of].includes(pack))
  const patch: StudioPatch = { country, region, urban_rural: urbanRural, ops, source: ops.some(op => op.source === 'upload') ? 'upload' : 'drawn' }
  useEffect(() => {
    try { window.localStorage.setItem(storageKey, JSON.stringify({ country, region, urban_rural: urbanRural, ops })) } catch { /* Draft remains editable when storage is unavailable. */ }
  }, [storageKey, country, region, urbanRural, ops])
  const selectView = (next: StudioView) => {
    const search = new URLSearchParams(params)
    search.set('view', next)
    setParams(search)
  }
  const updateOps = (next: StudioOp[]) => {
    if (run.running) return
    run.reset(); setOps(next)
  }
  const apply = () => { selectView('job'); void run.start(patch, pack) }
  const countryName = COUNTRIES.find(item => item.code === country)?.name ?? country
  const regionName = regionsForCountry(country).find(item => item.code === region)?.name ?? region
  const areaName = AREA_TYPES.find(item => item.code === urbanRural)?.name ?? urbanRural
  const unavailable = !['england', 'ireland'].includes(country) ? `Studio calculations are not available for ${countryName} yet. You can edit and export a draft.` : !currentNetwork ? 'Studio calculates against the current warehouse only. Select the current network to run this patch.' : null
  if (isLondonRural(region, urbanRural)) return <p className='py-8 text-sm'>London has no rural LSOAs under the official urban/rural classification — this filter is empty.</p>
  const displayedPatch = run.submitted ?? patch
  return <div className='studio-page pb-10'>
    <div className='studio-heading'><div><h1>Studio — {view === 'edit' ? 'Edit network' : studioViewNames[view]}</h1><p>{countryName} · {regionName} · {areaName}</p></div><div className='flex gap-2'><BriefingActions /><button type='button' className='app-primary-button' onClick={() => selectView('export')}>Export briefing</button></div></div>
    <nav className='studio-view-tabs' aria-label='Studio views'>{studioViews.map(item => <Link key={item} aria-current={view === item ? 'page' : undefined} to={{ search: (() => { const search = new URLSearchParams(params); search.set('view', item); return `?${search}` })() }}>{studioViewNames[item]}</Link>)}</nav>
    {unavailable ? <p className='studio-notice mb-4'>{unavailable}</p> : null}
    {run.running ? <p role='status' className='studio-notice mb-4'>Calculation in progress. Submitted operations are frozen. Changing country or filters opens a separate draft.</p> : null}
    {view === 'edit' ? <>
      <div className='studio-editor-layout'>
        <aside className='app-panel' data-testid='studio-patch-list'><h2>Operations</h2><p className='mt-2'>Draft edits ({ops.length}) · impacts not calculated</p><ol className='studio-operation-list'>{ops.map((op, index) => <li key={index}><p>{operationLabel(op)}</p><button type='button' className='app-text-link' disabled={run.running} aria-label={`Remove operation ${index + 1}`} onClick={() => updateOps(ops.filter((_, i) => i !== index))}>Remove</button></li>)}</ol>{!ops.length ? <p className='mt-4'>No operations yet — draw a stop or upload a file.</p> : null}<button type='button' className='app-panel-button mt-4' onClick={() => selectView('upload')}>Upload a file</button></aside>
        <section className='app-panel studio-canvas-panel'><fieldset disabled={run.running}><legend className='sr-only'>Network editing tools</legend><StudioEditorMap country={country} region={region} ops={ops} onAdd={op => updateOps([...ops, { ...op, source: 'drawn' }])} onDelete={index => updateOps(ops.filter((_, i) => i !== index))} onOutsideFilter={message => setWarning(message || null)} onFrequency={() => document.getElementById("studio-frequency-factor")?.focus()} /></fieldset><p className='mt-3'>Draft stop and corridor edits · WGS84 coordinates. Stop proximity is not travel time.</p></section>
      </div>
      <div className='app-panel studio-frequency mt-4'><h2>Frequency uplift</h2><label>Factor<input type='number' id='studio-frequency-factor' min='0.01' step='0.1' value={factor} disabled={run.running} onChange={event => setFactor(event.target.value)} /></label><label>Extra trips<input type='number' min='0' step='1' value={extraTrips} disabled={run.running} onChange={event => setExtraTrips(event.target.value)} /></label><button type='button' className='app-panel-button' disabled={run.running || !factor || !extraTrips || !Number.isFinite(Number(factor)) || Number(factor) <= 0 || !Number.isInteger(Number(extraTrips)) || Number(extraTrips) < 0} onClick={() => updateOps([...ops, { op: 'frequency_uplift', factor: Number(factor), extra_trips: Number(extraTrips), source: 'drawn' }])}>Add frequency uplift (needs r5py)</button><p>Frequency and corridor travel-time impacts are unavailable until a routing calculation supports them.</p></div>
      <StudioOperationDetails ops={ops} disabled={run.running} onChange={updateOps} />
      {warning ? <p role='alert' className='studio-notice mt-3'>{warning}</p> : null}
    </> : null}
    {view === 'upload' ? <StudioUpload patch={patch} disabled={run.running} onAdd={added => { updateOps([...ops, ...added]); selectView('edit') }} /> : null}
    {view === 'job' ? <StudioJobStages job={run.job} submitted={run.submitted} starting={run.starting} error={run.error} onRetryStatus={run.retryStatus} onRetry={() => { if (run.submitted) void run.start(run.submitted, pack) }} /> : null}
    {view === 'results' || view === 'gains' ? <StudioResults result={run.result} patch={displayedPatch} gains={view === 'gains'} /> : null}
    {view === 'export' ? <StudioExport patch={displayedPatch} job={run.job} result={run.result} pack={pack || currentDate?.as_of || ''} currentNetwork={currentNetwork} /> : null}
    {view !== 'export' ? <div className='studio-actions mt-4'><button type='button' className='app-primary-button' disabled={!ops.length || run.running || Boolean(unavailable)} onClick={apply}>{run.running ? 'Calculating…' : 'Apply patch'}</button><button type='button' className='app-panel-button' disabled={!ops.length || run.running} onClick={() => updateOps([])}>Clear patch</button><button type='button' className='app-text-link' disabled={!ops.length} onClick={() => downloadStudioPatch(patch)}>Download patch JSON</button>{run.result ? <button type='button' className='app-panel-button' onClick={() => selectView('results')}>View completed run</button> : null}<Link className='app-text-link' to={withSearch(appPath(country, 'scenarios'), params.toString())}>Listed scenarios</Link></div> : null}
  </div>
}
