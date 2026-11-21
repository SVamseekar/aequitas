import {readFileSync} from 'node:fs'
import {geoArea,geoPath} from 'd3'
import {describe,expect,it} from 'vitest'
import {boundaryProjection} from '../../src/lib/boundaryProjection'

describe('Actual country boundary coordinate systems',()=>{
 it('preserves projected Irish county coordinates rather than interpreting metres as degrees',()=>{
  const source=JSON.parse(readFileSync('public/boundaries/ireland_counties.geojson','utf8')) as GeoJSON.FeatureCollection
  const original=source.features[0].geometry
  const result=boundaryProjection(source,[[5,5],[95,100]])
  expect(result.planar).toBe(true)
  expect(result.data.features[0].geometry).toBe(original)
  const [[left,top],[right,bottom]]=geoPath(result.projection).bounds(result.data)
  expect(right-left).toBeGreaterThan(50)
  expect(bottom-top).toBeCloseTo(95,3)
  expect(left).toBeGreaterThanOrEqual(4.99)
  expect(bottom).toBeLessThanOrEqual(100.01)
 })
 it('normalizes Dutch spherical winding without mutating source polygons',()=>{
  const source=JSON.parse(readFileSync('public/boundaries/netherlands_provincies.geojson','utf8')) as GeoJSON.FeatureCollection
  const original=JSON.stringify(source)
  expect(geoArea(source)).toBeGreaterThan(2*Math.PI)
  const result=boundaryProjection(source,[[5,5],[95,100]])
  expect(result.planar).toBe(false)
  expect(geoArea(result.data)).toBeLessThan(0.1)
  expect(JSON.stringify(source)).toBe(original)
 })
 it('retains England and metropolitan France geographic shapes',()=>{
  for(const name of ['regions','france_regions']){
   const source=JSON.parse(readFileSync(`public/boundaries/${name}.geojson`,'utf8')) as GeoJSON.FeatureCollection
   const result=boundaryProjection(source,[[5,5],[95,100]])
   expect(result.planar).toBe(false)
   expect(geoArea(result.data)).toBeCloseTo(geoArea(source),8)
  }
 })
})
