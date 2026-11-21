import { useState } from 'react'
import { hasStudioImpact, type StudioPatch, type StudioResult } from '@/lib/studio'
import StudioResultMap from './StudioResultMap'
import StudioGainsChart, { type DecileRow } from './StudioGainsChart'

interface Props { result: StudioResult | null; patch: StudioPatch; gains?: boolean }
export default function StudioResults({ result, patch, gains = false }: Props) {
  const [mode, setMode] = useState<'baseline' | 'after' | 'difference'>('difference')
  const computed = hasStudioImpact(result)
  const rank = patch.country === 'ireland' ? 'HP' : patch.country === 'netherlands' ? 'SES-WOA' : patch.country === 'france' ? 'F-EDI' : 'IMD'
  const rows: DecileRow[] = Array.from({ length: 10 }, (_, i) => {
    const decile = i + 1
    const available = computed && result?.areas.some(area => area.imd_decile === decile)
    const row = result?.deciles.find(item => item.imd_decile === decile)
    return { decile, gained: available ? row?.people_gained ?? 0 : null, lost: available ? row?.people_lost ?? 0 : null }
  })
  const value = (number: number | null | undefined) => number == null ? '—' : number.toLocaleString('en-GB')
  const score = (number: number | null | undefined) => number == null ? '—' : `${number.toFixed(1)} / 100`
  return <div data-testid='studio-result'>
    {!computed ? <p className='studio-notice mb-4'>{result ? result.note : 'Result layout preview · actual figures appear after a completed run.'} No computed impact is displayed.</p> : <p className='studio-notice mb-4'>{result?.note} Travel-time changes are unavailable in this run.</p>}
    {gains ? <>
      <div className='studio-two-columns'>
        <section className='app-panel'><h2>Change in access by {rank} decile</h2><p>People within 400 m of a stop · in-country ranks</p><StudioGainsChart rows={rows} /></section>
        <section className='app-panel'><h2>Who gains and loses</h2>{computed && result ? <StudioResultMap result={result} mode='difference' ops={result.patch.ops} /> : <div className='studio-empty studio-chart-empty'>The area map appears after calculation.<br />No computed spatial change yet.</div>}<p>Area centroids show gains and losses. They do not represent travel time or a continuous accessibility surface.</p></section>
      </div>
      <section className='app-panel mt-4'><h2>{rank} decile results</h2><div className='studio-table-scroll'><table className='studio-table'><thead><tr><th>{rank} decile</th><th>People gained</th><th>People lost</th><th>Cell definition</th></tr></thead><tbody>{rows.map(row => <tr key={row.decile}><td>{row.decile}</td><td>{value(row.gained)}</td><td>{value(row.lost)}</td><td>Population in decile {row.decile} within the selected area</td></tr>)}</tbody></table></div><p>— means this decile has no computed observations. Zero means observed areas had no change.</p></section>
    </> : <>
      <div className='studio-map-tabs' role='group' aria-label='Result map mode'>{(['baseline', 'after', 'difference'] as const).map(item => <button type='button' key={item} aria-pressed={item === mode} onClick={() => setMode(item)}>{item.charAt(0).toUpperCase() + item.slice(1)}</button>)}</div>
      <div className='studio-results-layout'>
        <section className='app-panel'>{computed && result ? <StudioResultMap result={result} mode={mode} ops={result.patch.ops} /> : <div className='studio-empty studio-map-empty'>No completed impact calculation.<br />{mode.charAt(0).toUpperCase() + mode.slice(1)} coverage will appear here.</div>}</section>
        <aside className='studio-result-aside'>
          <section className='app-panel'><h2>{mode === 'difference' ? 'Change in stop coverage' : `${mode === 'baseline' ? 'Baseline' : 'After'} stop coverage`}</h2><div className='studio-legend'>{mode === 'difference' ? <span><i className='loss' />People lost</span> : null}<span><i className='neutral' />{mode === 'difference' ? 'No change' : 'Outside 400 m'}</span><span><i className='gain' />{mode === 'difference' ? 'People gained' : 'Within 400 m'}</span></div><p>Population at area centroids</p></section>
          <section className='app-panel'><h2>Score comparison</h2><dl className='studio-review'><div><dt>Score before</dt><dd>{score(computed ? result?.score_before : null)}</dd></div><div><dt>Score after</dt><dd>{score(computed ? result?.score_after : null)}</dd></div><div><dt>Change</dt><dd>{computed && result?.score_before != null && result.score_after != null ? (result.score_after - result.score_before).toFixed(1) : '—'}</dd></div></dl></section>
          <section className='app-panel'><h2>People affected</h2><dl className='studio-review'><div><dt>Gained access</dt><dd>{value(computed ? result?.people_gained : null)}</dd></div><div><dt>Lost access</dt><dd>{value(computed ? result?.people_lost : null)}</dd></div><div><dt>Areas analysed</dt><dd>{value(computed ? result?.n_areas : null)}</dd></div></dl></section>
        </aside>
      </div>
    </>}
    {computed && result?.narrative ? <p className='mt-4'>{result.narrative}</p> : null}
    {result?.default_region_note ? <p className='studio-notice mt-4'>{result.default_region_note}</p> : null}
  </div>
}
