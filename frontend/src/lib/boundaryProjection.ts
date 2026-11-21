import {geoArea,geoIdentity,geoMercator,geoPath} from 'd3'

/** D3's spherical polygon winding differs from RFC7946; leave source files untouched. */
function sphericalGeometry(geometry:GeoJSON.Geometry):GeoJSON.Geometry {
 const polygon=(coordinates:GeoJSON.Position[][])=>geoArea({type:'Polygon',coordinates})>2*Math.PI?coordinates.map(ring=>[...ring].reverse()):coordinates
 if(geometry.type==='Polygon')return {...geometry,coordinates:polygon(geometry.coordinates)}
 if(geometry.type==='MultiPolygon')return {...geometry,coordinates:geometry.coordinates.map(polygon)}
 if(geometry.type==='GeometryCollection')return {...geometry,geometries:geometry.geometries.map(sphericalGeometry)}
 return geometry
}

/** ITM coordinates stay planar; longitude/latitude use a spherical Mercator projection. */
export function boundaryProjection(source:GeoJSON.FeatureCollection,extent:[[number,number],[number,number]]){
 const bounds=geoPath(null).bounds(source)
 const planar=bounds.some(([x,y])=>Math.abs(x)>180||Math.abs(y)>90)
 const data=planar?source:{...source,features:source.features.map(feature=>feature.geometry?{...feature,geometry:sphericalGeometry(feature.geometry)}:feature)}
 const projection=planar?geoIdentity().reflectY(true).fitExtent(extent,data):geoMercator().fitExtent(extent,data)
 return {data,projection,planar}
}
