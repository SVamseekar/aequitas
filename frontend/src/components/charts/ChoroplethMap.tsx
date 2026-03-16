import { useRef, useEffect } from "react"
import maplibregl, { type StyleSpecification } from "maplibre-gl"
import "maplibre-gl/dist/maplibre-gl.css"

interface AreaDatum {
  area_code: string
  area_name: string
  value: number
}

interface GeoJsonFeature {
  properties: Record<string, unknown>
}

interface Props {
  chartData: Record<string, unknown>
}

export default function ChoroplethMap({ chartData }: Props) {
  const ref = useRef<HTMLDivElement>(null)
  const mapRef = useRef<maplibregl.Map | null>(null)

  useEffect(() => {
    if (!ref.current) return
    const data = (chartData.data ?? []) as AreaDatum[]
    const container = ref.current

    const values = new Map(data.map((d) => [d.area_code, d.value]))
    const maxVal = data.length > 0 ? Math.max(...data.map((d) => d.value)) : 1

    fetch("/boundaries/regions.geojson")
      .then((r) => r.json())
      .then((geojson: { features: GeoJsonFeature[] }) => {
        for (const f of geojson.features) {
          const code = (f.properties["RGN22CD"] ?? f.properties["rgn22cd"]) as string | undefined
          f.properties["value"] = code !== undefined ? (values.get(code) ?? 0) : 0
        }

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
              paint: { "background-color": "#f8f9fa" },
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

        const map = new maplibregl.Map({
          container,
          style,
          center: [-1.5, 52.8],
          zoom: 5.5,
          attributionControl: false,
        })

        mapRef.current = map
      })
      .catch(() => {
        // GeoJSON not available — map stays blank
      })

    return () => {
      mapRef.current?.remove()
      mapRef.current = null
    }
  }, [chartData])

  return (
    <div
      ref={ref}
      className="h-[500px] rounded-md overflow-hidden"
      aria-label={(chartData.title as string | undefined) ?? "Choropleth map"}
      role="img"
    />
  )
}
