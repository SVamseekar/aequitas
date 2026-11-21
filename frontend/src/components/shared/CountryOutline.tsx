import { useEffect, useState } from 'react'
import { geoPath } from 'd3'
import {boundaryProjection} from '@/lib/boundaryProjection'

const boundaries: Record<string, string> = { england: 'regions', ireland: 'ireland_counties', netherlands: 'netherlands_provincies', france: 'france_regions' }
const colors: Record<string, string> = { england: '#ce754f', ireland: '#93a97d', netherlands: '#78a0b6', france: '#ae959f' }

export function CountryOutline({ country, name }: { country: string; name: string }) {
  const [result, setResult] = useState<{country:string;shapes:string[]}|null>(null)
  const shapes=result?.country===country?result.shapes:[]
  useEffect(() => {
    const controller = new AbortController()
    fetch(`/boundaries/${boundaries[country] ?? 'regions'}.geojson`, { signal: controller.signal })
      .then(response => { if (!response.ok) throw new Error('Boundaries unavailable'); return response.json() as Promise<GeoJSON.FeatureCollection> })
      .then(source => { const {data,projection}=boundaryProjection(source,[[5,5],[95,100]]); const path = geoPath(projection); if(!controller.signal.aborted)setResult({country,shapes:data.features.map(feature => path(feature) ?? '')}) })
      .catch(() => { /* The country label remains available when the decorative outline cannot load. */ })
    return () => controller.abort()
  }, [country])
  return <svg width='100' height='105' viewBox='0 0 100 105' role='img' aria-label={`${name} boundary`} className='country-outline'>{shapes.map((shape, index) => <path key={index} d={shape} fill={colors[country] ?? colors.england} />)}</svg>
}
