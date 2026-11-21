import { COUNTRIES, AREA_TYPES, regionsForCountry } from '@/lib/constants'
import { useFilters, usePackDates } from '@/api/hooks'

const formatNetworkDate=(value:string)=>/^\d{4}-\d{2}-\d{2}$/.test(value)?new Date(`${value}T12:00:00Z`).toLocaleDateString('en-GB',{day:'2-digit',month:'short',year:'numeric',timeZone:'UTC'}):value

export function FilterDropdowns() {
  const { country, region, urbanRural, pack, mode, setCountry, setRegion, setUrbanRural, setPack, setMode } = useFilters()
  const packs = usePackDates()
  const entry = packs.data?.[country]
  const dates = entry && 'dates' in entry ? entry.dates ?? [] : []
  const packValue = pack || dates.find(d => d.current)?.pack_id || 'current'
  return (
    <div className='app-context-controls'>
      <label>Country<select aria-label='Country' value={country} onChange={e => setCountry(e.target.value)}>{COUNTRIES.map(c => <option key={c.code} value={c.code}>{c.name}</option>)}</select></label>
      <label>Region<select aria-label='Region' value={region} onChange={e => setRegion(e.target.value)}>{regionsForCountry(country).map(r => <option key={r.code} value={r.code}>{r.name}</option>)}</select></label>
      <label>Area<select aria-label='Area' value={urbanRural} onChange={e => setUrbanRural(e.target.value)}>{AREA_TYPES.map(a => <option key={a.code} value={a.code}>{a.name}</option>)}</select></label>
      {country === 'netherlands' && <label>Mode<select aria-label='Mode' value={mode} onChange={e => setMode(e.target.value)}><option value='bus'>Bus only</option><option value='all'>All public transport</option></select></label>}
      <label>Network<select aria-label='Network' value={packValue} onChange={e => setPack(e.target.value)} disabled={!dates.length}>
        {!dates.length && <option value={packValue}>{pack || (packs.isError ? 'Dates unavailable' : 'Current pack')}</option>}
        {dates.map(d => <option key={d.pack_id} value={d.pack_id}>{formatNetworkDate(d.as_of)}</option>)}
        {pack && !dates.some(d => d.pack_id === pack) && <option value={pack}>{pack}</option>}
      </select></label>
    </div>
  )
}
