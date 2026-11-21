import { Link, useSearchParams } from 'react-router'
import { useFilters, useScenarioSettings } from '@/api/hooks'
import { appPath, withSearch } from '@/lib/appRoutes'

export function ScenarioBuilder() {
  const { country, urbanRural } = useFilters()
  const [params] = useSearchParams()
  const { freqPct, lastBusHour, drtCoverage, franchise, setSettings } = useScenarioSettings()
  const studioParams = new URLSearchParams(params); studioParams.delete('view'); studioParams.delete('exhibit')
  const settings = [['Frequency uplift', `${freqPct}%`], ['Last bus time', `${lastBusHour}:00`], ['Rural DRT coverage', `${drtCoverage}%`], ['Franchise model', franchise]]
  const outputs = [['Target population affected', 'People'], ['Annual cost', `${country === 'england' ? '£' : '€'}m / year`], ['CO₂ change', 'Tonnes / year']]
  return <div className='scenario-sandbox'>
    <section className='app-panel'><h2>Scenario builder</h2><p>Explore service options. These controls are separate from the network Studio.</p>
      <div className='scenario-controls'>
        <div><label htmlFor='scenario-frequency'>Frequency uplift</label><output htmlFor='scenario-frequency'>{freqPct}%</output><input id='scenario-frequency' type='range' min={0} max={50} step={5} value={freqPct} onChange={event => setSettings({ freqPct: Number(event.target.value) })} /><small>0% – 50%</small></div>
        <div><label htmlFor='scenario-last-bus'>Last bus time</label><output htmlFor='scenario-last-bus'>{lastBusHour}:00</output><input id='scenario-last-bus' type='range' min={19} max={23} step={1} value={lastBusHour} onChange={event => setSettings({ lastBusHour: Number(event.target.value) })} /><small>19:00 – 23:00</small></div>
        <div><label htmlFor='scenario-drt'>Rural DRT coverage</label><output htmlFor='scenario-drt'>{drtCoverage}%</output><input id='scenario-drt' type='range' min={0} max={100} step={5} disabled={urbanRural === 'urban'} value={drtCoverage} onChange={event => setSettings({ drtCoverage: Number(event.target.value) })} /><small>{urbanRural === 'urban' ? 'Not applicable to an urban-only filter' : '0% – 100%'}</small></div>
        <div><label htmlFor='scenario-franchise'>Franchise model</label><select id='scenario-franchise' value={franchise} onChange={event => setSettings({ franchise: event.target.value as 'none' | 'partial' | 'full' })}><option value='none'>None</option><option value='partial'>Partial</option><option value='full'>Full</option></select></div>
      </div>
    </section>
    <section className='app-panel mt-4'><h2>Indicative scenario outputs</h2><p>Illustrative control state; model outputs require selected assumptions.</p><div className='scenario-output-cards'>{outputs.map(([label, unit]) => <article key={label}><h3>{label}</h3><strong>—</strong><small>{unit}</small></article>)}</div>
      <div className='scenario-summary'><div><h3>Service option summary</h3><table aria-label='Selected service options'><thead><tr><th>Option</th><th>Selected value</th></tr></thead><tbody>{settings.map(([label,value]) => <tr key={label}><td>{label}</td><td>{value}</td></tr>)}</tbody></table></div><aside><h3>About these results</h3><p>No benefit-cost ratio or calculated access impact is available for these controls. Stored scenario target populations do not describe newly gained access.</p><Link className='app-text-link' to={withSearch(appPath(country,'studio'),studioParams.toString())}>Open network Studio</Link></aside></div>
    </section>
  </div>
}
