import { useEffect, useRef } from "react"
import maplibregl, { type StyleSpecification } from "maplibre-gl"
import "maplibre-gl/dist/maplibre-gl.css"
import type { StudioOp } from "@/pages/StudioPage"

interface AreaRow {
  area: string
  name?: string
  lat?: number
  lon?: number
  pop: number
  imd_decile: number | null
  covered_before: boolean
  covered_after: boolean
  delta_people: number
}

interface Result {
  areas: AreaRow[]
}

interface Props {
  result: Result
  mode: "baseline" | "after" | "difference"
  ops: StudioOp[]
}

const BASEMAP = 'https://tile.openstreetmap.org/{z}/{x}/{y}.png'

export default function StudioResultMap({ result, mode, ops }: Props) {
  const ref = useRef<HTMLDivElement>(null)
  const mapRef = useRef<maplibregl.Map | null>(null)

  useEffect(() => {
    if (!ref.current) return
    if (!mapRef.current) {
      mapRef.current = new maplibregl.Map({
        container: ref.current,
        style: {
          version: 8,
          sources: {
            carto: {
              type: "raster",
              tiles: [BASEMAP],
              tileSize: 256,
              attribution: '© <a href="https://www.openstreetmap.org/copyright">OpenStreetMap contributors</a>',
            },
          },
          layers: [
            { id: "background", type: "background", paint: { "background-color": "#e8e4dc" } },
            { id: "carto-tiles", type: "raster", source: "carto" },
          ],
        } as StyleSpecification,
        center: (() => {
          const point = result.areas.find(area => area.lat != null && area.lon != null) ?? ops.find(op => op.lat != null && op.lon != null)
          return [point?.lon ?? 0, point?.lat ?? 0] as [number, number]
        })(),
        zoom: 5.6,
      })
      mapRef.current.addControl(new maplibregl.NavigationControl(), 'top-left')
    }
    const map = mapRef.current
    const areaFeatures: GeoJSON.Feature[] = result.areas
      .filter((a) => a.lat != null && a.lon != null)
      .map((a) => {
        const colour =
          mode === "difference"
            ? a.delta_people > 0
              ? "#2f6f4e"
              : a.delta_people < 0
                ? "#8b3a2a"
                : "#c5b8a5"
            : mode === "after"
              ? a.covered_after
                ? "#2f6f4e"
                : "#c5b8a5"
              : a.covered_before
                ? "#2f6f4e"
                : "#c5b8a5"
        return {
          type: "Feature",
          properties: {
            kind: "area",
            name: a.name || a.area,
            people: a.pop,
            decile: a.imd_decile ?? "—",
            delta: a.delta_people,
            colour,
          },
          geometry: { type: "Point", coordinates: [a.lon as number, a.lat as number] },
        }
      })
    const stopFeatures: GeoJSON.Feature[] = ops
      .filter((o) => o.lat != null && o.lon != null)
      .map((o) => ({
        type: "Feature",
        properties: {
          kind: "stop",
          name: o.op === "add_stop" ? "Added stop" : o.op,
          people: "",
          decile: "",
          delta: "",
          colour: "#1d4ed8",
        },
        geometry: { type: "Point", coordinates: [o.lon as number, o.lat as number] },
      }))
    const features = [...areaFeatures, ...stopFeatures]

    const apply = () => {
      const src = map.getSource("studio-pts") as maplibregl.GeoJSONSource | undefined
      const data: GeoJSON.FeatureCollection = { type: "FeatureCollection", features }
      if (src) src.setData(data)
      else {
        map.addSource("studio-pts", { type: "geojson", data })
        map.addLayer({
          id: "studio-pts-circle",
          type: "circle",
          source: "studio-pts",
          paint: {
            "circle-radius": ["case", ["==", ["get", "kind"], "stop"], 7, 5],
            "circle-color": ["get", "colour"],
            "circle-opacity": 0.85,
            "circle-stroke-width": 1,
            "circle-stroke-color": "#fff",
          },
        })
        map.on("mousemove", "studio-pts-circle", (e) => {
          const f = e.features?.[0]
          if (!f) return
          const p = f.properties ?? {}
          map.getCanvas().style.cursor = "pointer"
          const text =
            p.kind === "stop"
              ? String(p.name)
              : `${p.name} — ${Number(p.people).toLocaleString("en-GB")} people, in-country decile ${p.decile}, change ${p.delta}`
          const popup = new maplibregl.Popup({ closeButton: false })
            .setLngLat(e.lngLat)
            .setText(text)
            .addTo(map)
          map.once("mouseleave", "studio-pts-circle", () => popup.remove())
        })
      }
      const withCoords = result.areas.filter((a) => a.lat != null && a.lon != null)
      if (withCoords.length) {
        const lons = withCoords.map((a) => a.lon as number)
        const lats = withCoords.map((a) => a.lat as number)
        map.fitBounds(
          [
            [Math.min(...lons), Math.min(...lats)],
            [Math.max(...lons), Math.max(...lats)],
          ],
          { padding: 32, animate: false, maxZoom: 10 },
        )
      }
    }
    if (map.isStyleLoaded()) apply()
    else map.once("load", apply)

    return () => { map.off('load', apply) }
  }, [result, mode, ops])

  useEffect(() => () => {
    mapRef.current?.remove()
    mapRef.current = null
  }, [])

  if (!result.areas.some(area => area.lat != null && area.lon != null) && !ops.some(op => op.lat != null && op.lon != null)) {
    return (
      <p className="text-sm text-muted-foreground py-4">
        No before/after map for this run — mapped coordinates are unavailable.
      </p>
    )
  }

  return <div ref={ref} className="studio-result-map" data-testid="studio-result-map" />
}
