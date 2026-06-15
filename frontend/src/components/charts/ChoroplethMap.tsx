import { useRef, useEffect, useMemo, useState } from "react"
import maplibregl, { type StyleSpecification } from "maplibre-gl"
import "maplibre-gl/dist/maplibre-gl.css"

interface AreaDatum {
  area_code: string
  area_name: string
  value: number
}

interface GeoJsonFeature {
  properties: Record<string, unknown>
  geometry: GeoJSON.Geometry
}

interface Props {
  chartData: Record<string, unknown>
}

/** Compute the bounding box of all matched features, walking nested coordinate arrays. */
function computeBounds(featureCollection: GeoJSON.FeatureCollection): maplibregl.LngLatBoundsLike | null {
  let minLng = Infinity
  let minLat = Infinity
  let maxLng = -Infinity
  let maxLat = -Infinity

  const walk = (coords: unknown[]): void => {
    if (typeof coords[0] === "number") {
      const [lng, lat] = coords as [number, number]
      minLng = Math.min(minLng, lng)
      minLat = Math.min(minLat, lat)
      maxLng = Math.max(maxLng, lng)
      maxLat = Math.max(maxLat, lat)
    } else {
      for (const c of coords) walk(c as unknown[])
    }
  }

  for (const feature of featureCollection.features) {
    if ("coordinates" in feature.geometry) {
      walk(feature.geometry.coordinates)
    }
  }

  if (!Number.isFinite(minLng)) return null
  return [[minLng, minLat], [maxLng, maxLat]]
}

export default function ChoroplethMap({ chartData }: Props) {
  const ref = useRef<HTMLDivElement>(null)
  const mapRef = useRef<maplibregl.Map | null>(null)
  const chartDataKey = useMemo(() => JSON.stringify(chartData), [chartData])
  const [mapUnavailable, setMapUnavailable] = useState(false)

  useEffect(() => {
    if (!ref.current) return
    setMapUnavailable(false)
    const data = (chartData.data ?? []) as AreaDatum[]
    const container = ref.current

    const values = new Map(data.map((d) => [d.area_code, d.value]))
    const maxVal = data.length > 0 ? Math.max(...data.map((d) => d.value)) : 1

    const geography = (chartData.geography as string | undefined) ?? "region"
    const boundaryFile = geography === "lad" ? "/boundaries/lad.geojson" : "/boundaries/regions.geojson"
    const codeKeys = geography === "lad" ? ["LAD22CD", "lad22cd"] : ["RGN22CD", "rgn22cd"]
    const nameKeys = geography === "lad" ? ["LAD22NM", "lad22nm"] : ["RGN22NM", "rgn22nm"]

    fetch(boundaryFile)
      .then((r) => {
        if (!r.ok) throw new Error(`Failed to load boundaries: HTTP ${r.status}`)
        return r.json()
      })
      .then((geojson: { features: GeoJsonFeature[] }) => {
        const matched: GeoJsonFeature[] = []
        for (const f of geojson.features) {
          const code = (f.properties[codeKeys[0]] ?? f.properties[codeKeys[1]]) as string | undefined
          if (code !== undefined && values.has(code)) {
            f.properties["value"] = values.get(code) ?? 0
            f.properties["area_name"] = f.properties[nameKeys[0]] ?? f.properties[nameKeys[1]]
            matched.push(f)
          } else if (geography !== "lad") {
            // Region-level maps show the full national outline even when a value is missing.
            f.properties["value"] = code !== undefined ? (values.get(code) ?? 0) : 0
            f.properties["area_name"] = f.properties[nameKeys[0]] ?? f.properties[nameKeys[1]]
            matched.push(f)
          }
        }
        geojson.features = matched

        const style: StyleSpecification = {
          version: 8,
          sources: {
            regions: {
              type: "geojson",
              data: geojson as GeoJSON.FeatureCollection,
            },
          },
          layers: [
            {
              id: "background",
              type: "background",
              paint: { "background-color": "#0f1117" },
            },
            {
              id: "regions-fill",
              type: "fill",
              source: "regions",
              paint: {
                "fill-color": [
                  "interpolate", ["linear"],
                  ["coalesce", ["get", "value"], 0],
                  0, "#440154",
                  maxVal * 0.25, "#31688e",
                  maxVal * 0.5, "#35b779",
                  maxVal * 0.75, "#90d743",
                  maxVal, "#fde725",
                ],
                "fill-opacity": 0.8,
              },
            },
            {
              id: "regions-outline",
              type: "line",
              source: "regions",
              paint: { "line-color": "#666", "line-width": 1 },
            },
          ],
        }

        const bounds = computeBounds(geojson as GeoJSON.FeatureCollection)

        const map = new maplibregl.Map({
          container,
          style,
          center: [-1.5, 52.8],
          zoom: 5.5,
          dragPan: true,
          doubleClickZoom: true,
          attributionControl: false,
          cooperativeGestures: true,
        })

        if (bounds) {
          map.fitBounds(bounds, { padding: 24, animate: false })
        }

        const metric = (chartData.metric as string | undefined) ?? "Value"
        const popup = new maplibregl.Popup({
          closeButton: false,
          closeOnClick: false,
          className: "maplibre-hover-popup",
        })

        map.on("load", () => {
          map.on("mousemove", "regions-fill", (e) => {
            if (!e.features || e.features.length === 0) return
            const props = e.features[0].properties as Record<string, unknown>
            const name = String(props["area_name"] ?? props["RGN22NM"] ?? "Unknown")
            const value = props["value"] as number | undefined
            const el = document.createElement("div")
            const strong = document.createElement("strong")
            strong.textContent = name
            el.appendChild(strong)
            el.appendChild(document.createElement("br"))
            el.appendChild(document.createTextNode(`${metric}: ${value !== undefined ? Number(value).toLocaleString(undefined, { maximumFractionDigits: 2 }) : "—"}`))
            popup.setLngLat(e.lngLat).setDOMContent(el).addTo(map)
            map.getCanvas().style.cursor = "pointer"
          })

          map.on("mouseleave", "regions-fill", () => {
            popup.remove()
            map.getCanvas().style.cursor = ""
          })
        })

        mapRef.current = map
      })
      .catch(() => {
        // Region boundary GeoJSON not available — show a visible fallback
        // instead of an empty map area.
        setMapUnavailable(true)
      })

    return () => {
      mapRef.current?.remove()
      mapRef.current = null
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps -- stabilized via JSON key
  }, [chartDataKey])

  return (
    <div className="relative h-[500px] rounded-md overflow-hidden">
      <div
        ref={ref}
        className="h-full w-full"
        aria-label={(chartData.title as string | undefined) ?? "Choropleth map"}
        role="img"
      />
      {mapUnavailable && (
        <div className="absolute inset-0 flex items-center justify-center bg-muted/50 text-center px-4">
          <p className="text-sm text-muted-foreground">
            Map data unavailable — region boundary file could not be loaded.
            Refer to the table or narrative below for this section&apos;s figures.
          </p>
        </div>
      )}
    </div>
  )
}
