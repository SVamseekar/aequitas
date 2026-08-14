import { useEffect, useRef } from "react"
import maplibregl, { type StyleSpecification } from "maplibre-gl"
import "maplibre-gl/dist/maplibre-gl.css"
import type { StudioOp } from "@/pages/StudioPage"

export type DrawnOp = Pick<StudioOp, "op" | "lat" | "lon" | "name" | "line">

interface Props {
  ops: StudioOp[]
  region: string
  country?: string
  onAdd: (op: DrawnOp) => void
  onDelete: (index: number) => void
  onOutsideFilter?: (message: string) => void
}

const ENGLAND: [[number, number], [number, number]] = [
  [-6.5, 49.8],
  [2.0, 55.9],
]
const IRELAND: [[number, number], [number, number]] = [
  [-10.8, 51.25],
  [-5.88, 55.45],
]
const NETHERLANDS: [[number, number], [number, number]] = [
  [3.2, 50.75],
  [7.22, 53.7],
]

function inEngland(lat: number, lon: number): boolean {
  return lat >= 49.8 && lat <= 55.9 && lon >= -6.5 && lon <= 2.0
}

function inRepublic(lat: number, lon: number): boolean {
  if (lat >= 54.02 && lat <= 55.32 && lon >= -8.18 && lon <= -5.4) return false
  return lat >= 51.25 && lat <= 55.45 && lon >= -10.8 && lon <= -5.88
}

function inNetherlands(lat: number, lon: number): boolean {
  return lat >= 50.75 && lat <= 53.7 && lon >= 3.2 && lon <= 7.22
}

function pointInRing(lon: number, lat: number, ring: number[][]): boolean {
  let inside = false
  for (let i = 0, j = ring.length - 1; i < ring.length; j = i++) {
    const xi = ring[i][0], yi = ring[i][1]
    const xj = ring[j][0], yj = ring[j][1]
    const intersect = yi > lat !== yj > lat && lon < ((xj - xi) * (lat - yi)) / (yj - yi + 0.0) + xi
    if (intersect) inside = !inside
  }
  return inside
}

function pointInFeature(lon: number, lat: number, feature: GeoJSON.Feature): boolean {
  const geom = feature.geometry
  if (!geom) return false
  const check = (coords: number[][][]) =>
    coords.some((poly) => {
      if (!poly[0] || !pointInRing(lon, lat, poly[0] as number[][])) return false
      return poly.slice(1).every((hole) => !pointInRing(lon, lat, hole as number[][]))
    })
  if (geom.type === "Polygon") return check(geom.coordinates as number[][][])
  if (geom.type === "MultiPolygon") return (geom.coordinates as number[][][][]).some((p) => check(p))
  return false
}

function boundsOf(feature: GeoJSON.Feature): maplibregl.LngLatBoundsLike | null {
  let minLng = Infinity, minLat = Infinity, maxLng = -Infinity, maxLat = -Infinity
  const walk = (coords: unknown): void => {
    if (!Array.isArray(coords)) return
    if (typeof coords[0] === "number") {
      const [lng, lat] = coords as [number, number]
      minLng = Math.min(minLng, lng)
      minLat = Math.min(minLat, lat)
      maxLng = Math.max(maxLng, lng)
      maxLat = Math.max(maxLat, lat)
    } else coords.forEach(walk)
  }
  if (feature.geometry && "coordinates" in feature.geometry) walk(feature.geometry.coordinates)
  if (!Number.isFinite(minLng)) return null
  return [[minLng, minLat], [maxLng, maxLat]]
}

const CARTO = "https://basemaps.cartocdn.com/light_all/{z}/{x}/{y}@2x.png"

const STYLE: StyleSpecification = {
  version: 8,
  sources: {
    carto: {
      type: "raster",
      tiles: [CARTO],
      tileSize: 256,
      attribution: "© OpenStreetMap contributors © CARTO",
    },
  },
  layers: [
    { id: "background", type: "background", paint: { "background-color": "#e8e4dc" } },
    { id: "carto-tiles", type: "raster", source: "carto", paint: { "raster-opacity": 0.9 } },
  ],
}

export default function StudioEditorMap({ ops, region, country = "england", onAdd, onDelete, onOutsideFilter }: Props) {
  const ref = useRef<HTMLDivElement>(null)
  const mapRef = useRef<maplibregl.Map | null>(null)
  const markers = useRef<maplibregl.Marker[]>([])
  const drawLine = useRef<boolean>(false)
  const lineAcc = useRef<[number, number][]>([])
  const onAddRef = useRef(onAdd)
  const regionRef = useRef(region)
  const countryRef = useRef(country)
  const warnRef = useRef(onOutsideFilter)
  const regionFeature = useRef<GeoJSON.Feature | null>(null)
  onAddRef.current = onAdd
  regionRef.current = region
  countryRef.current = country
  warnRef.current = onOutsideFilter

  useEffect(() => {
    if (!ref.current || mapRef.current) return
    const map = new maplibregl.Map({
      container: ref.current,
      style: STYLE,
      center: country === "ireland" ? [-8.0, 53.3] : country === "netherlands" ? [5.3, 52.2] : [-1.5, 52.8],
      zoom: country === "ireland" ? 6 : country === "netherlands" ? 6.2 : 5.4,
      attributionControl: true,
      maxBounds:
        country === "ireland"
          ? [
              [IRELAND[0][0] - 0.6, IRELAND[0][1] - 0.4],
              [IRELAND[1][0] + 0.6, IRELAND[1][1] + 0.4],
            ]
          : country === "netherlands"
            ? [
                [NETHERLANDS[0][0] - 0.4, NETHERLANDS[0][1] - 0.3],
                [NETHERLANDS[1][0] + 0.4, NETHERLANDS[1][1] + 0.3],
              ]
          : [
              [ENGLAND[0][0] - 1, ENGLAND[0][1] - 1],
              [ENGLAND[1][0] + 1, ENGLAND[1][1] + 1],
            ],
    })
    mapRef.current = map
    map.on("click", (e) => {
      const lat = e.lngLat.lat
      const lon = e.lngLat.lng
      if (countryRef.current === "ireland") {
        if (!inRepublic(lat, lon)) {
          warnRef.current?.(
            "That click is outside the Republic of Ireland. Studio does not apply England or Northern Ireland clicks.",
          )
          return
        }
      } else if (countryRef.current === "netherlands") {
        if (!inNetherlands(lat, lon)) {
          warnRef.current?.(
            "That click is outside the Netherlands. Studio does not apply England or Ireland clicks.",
          )
          return
        }
      } else if (!inEngland(lat, lon)) {
        warnRef.current?.("That click is outside England. Studio only patches the England pack.")
        return
      }
      const feat = regionFeature.current
      if (regionRef.current !== "all" && feat && !pointInFeature(lon, lat, feat)) {
        warnRef.current?.("That click is outside this filter.")
        return
      }
      warnRef.current?.("")
      if (drawLine.current) {
        lineAcc.current.push([lon, lat])
        if (lineAcc.current.length >= 2) {
          onAddRef.current({ op: "add_trips", line: [...lineAcc.current] })
          onAddRef.current({ op: "add_stop", lat, lon, name: "Drawn vertex" })
        }
        return
      }
      onAddRef.current({ op: "add_stop", lat, lon, name: "Drawn stop" })
    })
    return () => {
      map.remove()
      mapRef.current = null
    }
  }, [])

  useEffect(() => {
    const map = mapRef.current
    if (!map) return
    let cancelled = false
    const boundaryFile =
      country === "ireland"
        ? "/boundaries/ireland_counties.geojson"
        : country === "netherlands"
          ? "/boundaries/netherlands_provincies.geojson"
          : "/boundaries/regions.geojson"
    fetch(boundaryFile)
      .then((r) => r.json())
      .then((gj: GeoJSON.FeatureCollection) => {
        if (cancelled) return
        const feat =
          region === "all"
            ? null
            : (gj.features.find((f) => {
                const p = f.properties ?? {}
                return (
                  p.RGN22CD === region ||
                  p.rgn22cd === region ||
                  p.COUNTY_SLUG === region ||
                  p.prov_slug === region ||
                  String(p.statnaam ?? p.PROV_NAAM ?? p.COUNTY ?? p.county ?? "").toLowerCase() === region
                )
              }) ?? null)
        regionFeature.current = feat
        const bounds = feat
          ? boundsOf(feat)
          : country === "ireland"
            ? IRELAND
            : country === "netherlands"
              ? NETHERLANDS
              : ENGLAND
        if (bounds) map.fitBounds(bounds, { padding: 28, animate: false, maxZoom: 9 })
      })
      .catch(() => {
        if (region === "E12000005") {
          map.fitBounds(
            [
              [-3.3, 51.95],
              [-1.15, 53.3],
            ],
            { padding: 28, animate: false },
          )
        }
      })
    return () => {
      cancelled = true
    }
  }, [region, country])

  useEffect(() => {
    const map = mapRef.current
    if (!map) return
    markers.current.forEach((m) => m.remove())
    markers.current = []
    ops.forEach((op, i) => {
      if (op.lat == null || op.lon == null) return
      const el = document.createElement("button")
      el.type = "button"
      el.className = "h-3 w-3 rounded-full bg-primary border border-white"
      el.title = "Delete stop"
      el.addEventListener("click", (ev) => {
        ev.stopPropagation()
        onDelete(i)
      })
      markers.current.push(new maplibregl.Marker({ element: el }).setLngLat([op.lon, op.lat]).addTo(map))
    })
  }, [ops, onDelete])

  return (
    <div>
      <div className="flex gap-2 mb-2 text-xs">
        <button type="button" className="underline" onClick={() => { drawLine.current = false }}>
          Add / move stops (click)
        </button>
        <button
          type="button"
          className="underline"
          onClick={() => {
            drawLine.current = true
            lineAcc.current = []
          }}
        >
          Draw a line
        </button>
      </div>
      <div ref={ref} className="h-[min(52vh,440px)] rounded-2xl overflow-hidden" data-testid="studio-editor-map" />
    </div>
  )
}
