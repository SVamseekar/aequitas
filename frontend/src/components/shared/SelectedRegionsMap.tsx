import { useEffect, useState } from 'react'
import { geoPath } from 'd3'
import {boundaryProjection} from '@/lib/boundaryProjection'

const files: Record<string, string> = { england: 'regions', ireland: 'ireland_counties', netherlands: 'netherlands_provincies', france: 'france_regions' }
const normalize = (value: string) => value.normalize('NFKD').replace(/[\u0300-\u036f]/g, '').toLowerCase().replace(/[^a-z0-9]+/g, '-')
interface Props { country: string; regionA: string; regionB: string; nameA: string; nameB: string; highlight?: 'a' | 'b' }
export default function SelectedRegionsMap({ country, regionA, regionB, nameA, nameB, highlight }: Props) {
  const [result, setResult] = useState<{country:string;data:GeoJSON.FeatureCollection}|null>(null)
  const [errorCountry, setErrorCountry] = useState<string|null>(null)
  const data=result?.country===country?result.data:null,error=errorCountry===country
  useEffect(() => {
    const controller = new AbortController()
    fetch(`/boundaries/${files[country]}.geojson`, { signal: controller.signal })
      .then(response => { if (!response.ok) throw new Error('Boundary unavailable'); return response.json() as Promise<GeoJSON.FeatureCollection> })
      .then(data=>{if(!controller.signal.aborted)setResult({country,data})}).catch(() => { if (!controller.signal.aborted) setErrorCountry(country) })
    return () => controller.abort()
  }, [country])
  if (error) return <p role='status'>Selected-region boundaries are unavailable.</p>
  if (!data) return <p role='status'>Loading country boundaries…</p>
  const {data:projected,projection}=boundaryProjection(data,[[10,10],[250,405]])
  const path = geoPath(projection)
  const keys = (feature: GeoJSON.Feature) => Object.entries(feature.properties ?? {}).filter(([key]) => ['RGN22CD', 'RGN22NM', 'COUNTY_SLUG', 'county_slug', 'COUNTY', 'county', 'NAME', 'name', 'nom', 'statnaam', 'PV_NAAM'].includes(key)).map(([, value]) => normalize(String(value)))
  const shape = (feature: GeoJSON.Feature) => {
    const names = keys(feature)
    if (highlight !== 'b' && names.some(name => [regionA, nameA].map(normalize).includes(name))) return '#c6582b'
    if (highlight !== 'a' && names.some(name => [regionB, nameB].map(normalize).includes(name))) return '#759765'
    return '#dddcd6'
  }
  return <><svg className='compare-region-map' viewBox='0 0 260 420' role='img' aria-label={`${nameA} and ${nameB} within ${country}`}>{projected.features.map((feature, index) => <path key={index} d={path(feature) ?? ''} fill={shape(feature)} stroke='white' strokeWidth='.8'><title>{String(feature.properties?.RGN22NM ?? feature.properties?.COUNTY ?? feature.properties?.nom ?? feature.properties?.name ?? '')}</title></path>)}</svg><p>Selected geography only. Colours identify the regions.</p></>
}
