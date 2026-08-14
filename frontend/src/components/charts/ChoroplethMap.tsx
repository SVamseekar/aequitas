import { useRef, useEffect, useMemo, useState } from "react"
import maplibregl, { type StyleSpecification } from "maplibre-gl"
import "maplibre-gl/dist/maplibre-gl.css"

interface AreaDatum {
  area_code: string
  area_name: string
  value: number
  hover?: string
}

interface GeoJsonFeature {
  properties: Record<string, unknown>
  geometry: GeoJSON.Geometry
}

interface Props {
  chartData: Record<string, unknown>
  onAreaClick?: (areaCode: string) => void
  className?: string
}

const CARTO_POSITRON =
  "https://basemaps.cartocdn.com/light_all/{z}/{x}/{y}@2x.png"

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

function formatHoverValue(value: number | undefined, metricLabel: string): string {
  if (value === undefined || Number.isNaN(value)) return "—"
  const compact = value.toLocaleString("en-GB", { maximumFractionDigits: value >= 100 ? 0 : 1 })
  if (metricLabel.includes("%")) return `${compact}%`
  return compact
}

export default function ChoroplethMap({ chartData, onAreaClick, className }: Props) {
  const ref = useRef<HTMLDivElement>(null)
  const mapRef = useRef<maplibregl.Map | null>(null)
  const clickRef = useRef(onAreaClick)
  clickRef.current = onAreaClick
  const chartDataKey = useMemo(() => JSON.stringify(chartData), [chartData])
  const [mapUnavailable, setMapUnavailable] = useState(false)
  const [svgMarkup, setSvgMarkup] = useState<string | null>(null)

  useEffect(() => {
    if (!ref.current) return
    const data = (chartData.data ?? []) as AreaDatum[]
    if (!data.length) {
      setMapUnavailable(true)
      setSvgMarkup(null)
      return
    }
    setMapUnavailable(false)
    setSvgMarkup(null)
    const container = ref.current

    const values = new Map<string, number>()
    const names = new Map<string, string>()
    const hovers = new Map<string, string | undefined>()
    for (const d of data) {
      for (const key of choroplethLookupKeys(d.area_code, d.area_name)) {
        values.set(key, d.value)
        names.set(key, d.area_name)
        hovers.set(key, d.hover)
      }
    }
    const maxVal = data.length > 0 ? Math.max(...data.map((d) => d.value), 1) : 1
    const colorMode = (chartData.color_mode as string | undefined) ?? "continuous"

    const inferredIreland = looksLikeIrelandCounties(data)
    const inferredNl = looksLikeNetherlandsProvinces(data)
    const geography =
      (chartData.geography as string | undefined) ??
      (inferredIreland ? "ireland_county" : inferredNl ? "netherlands_provincie" : "region")
    const boundaryFile =
      geography === "ireland_county"
        ? "/boundaries/ireland_counties.geojson"
        : geography === "netherlands_provincie"
          ? "/boundaries/netherlands_provincies.geojson"
        : geography === "lad"
          ? "/boundaries/lad.geojson"
          : "/boundaries/regions.geojson"
    const codeKeys =
      geography === "ireland_county"
        ? ["COUNTY_SLUG", "county_slug", "COUNTY", "county", "NAME", "name"]
        : geography === "netherlands_provincie"
          ? ["name", "NAME", "statcode", "statnaam", "prov_naam", "PV_NAAM"]
        : geography === "lad"
          ? ["LAD22CD", "lad22cd"]
          : ["RGN22CD", "rgn22cd"]
    const nameKeys =
      geography === "ireland_county"
        ? ["COUNTY", "county", "NAME", "name"]
        : geography === "netherlands_provincie"
          ? ["statnaam", "name", "NAME", "PV_NAAM", "prov_naam"]
        : geography === "lad"
          ? ["LAD22NM", "lad22nm"]
          : ["RGN22NM", "rgn22nm"]

    fetch(boundaryFile)
      .then((r) => {
        if (!r.ok) throw new Error(`Failed to load boundaries: HTTP ${r.status}`)
        return r.json()
      })
      .then((geojson: { features: GeoJsonFeature[] }) => {
        const matched: GeoJsonFeature[] = []
        for (const f of geojson.features) {
          const code = firstProp(f.properties, codeKeys)
          const valueKey = lookupChoroplethValue(values, f.properties, codeKeys)
          if (valueKey !== undefined) {
            f.properties["value"] = values.get(valueKey) ?? 0
            f.properties["area_name"] =
              names.get(valueKey) ?? firstProp(f.properties, nameKeys) ?? valueKey
            f.properties["area_code"] = valueKey
            if (hovers.get(valueKey)) f.properties["hover"] = hovers.get(valueKey)
            matched.push(f)
          } else if (
            geography !== "lad" &&
            geography !== "ireland_county" &&
            geography !== "netherlands_provincie" &&
            regionAllowsOutline(chartData)
          ) {
            f.properties["value"] = 0
            f.properties["area_name"] = firstProp(f.properties, nameKeys)
            f.properties["area_code"] = code
            matched.push(f)
          }
        }
        geojson.features = matched
        if (matched.length === 0) {
          setMapUnavailable(true)
          setSvgMarkup(null)
          return
        }
        const paintSvg = () => {
          setSvgMarkup(
            svgFromFeatures(matched as GeoJSON.Feature[], maxVal, colorMode),
          )
          setMapUnavailable(false)
        }
        // Paint local polygons first so MapLibre abort / late tiles never leave
        // a blank CARTO frame. GL is an enhancement, not the only paint path.
        paintSvg()
        if (
          geography === "ireland_county" ||
          geography === "netherlands_provincie" ||
          geography === "region" ||
          geography === "lad"
        ) {
          // SVG is the briefing exhibit. Skip GL — ERR_ABORTED left blank maps.
          return
        }

        const style: StyleSpecification = {
          version: 8,
          sources: {
            carto: {
              type: "raster",
              tiles: [CARTO_POSITRON],
              tileSize: 256,
              attribution: "© OpenStreetMap contributors © CARTO",
            },
            regions: {
              type: "geojson",
              data: geojson as GeoJSON.FeatureCollection,
            },
          },
          layers: [
            {
              id: "background",
              type: "background",
              paint: { "background-color": "#e8e4dc" },
            },
            {
              id: "carto-tiles",
              type: "raster",
              source: "carto",
              paint: { "raster-opacity": 0.85 },
            },
            {
              id: "regions-fill",
              type: "fill",
              source: "regions",
              paint: {
                "fill-color":
                  colorMode === "band"
                    ? [
                        "match",
                        ["coalesce", ["get", "value"], 0],
                        1, "#4a1c0c",
                        2, "#8b3a1a",
                        3, "#c45c26",
                        4, "#e8b86d",
                        5, "#c5d4a8",
                        6, "#6b8f71",
                        "#d9d3c7",
                      ]
                    : [
                        "interpolate", ["linear"],
                        ["coalesce", ["get", "value"], 0],
                        0, "#f7f1e8",
                        maxVal * 0.25, "#e8b86d",
                        maxVal * 0.5, "#c45c26",
                        maxVal * 0.75, "#8b3a1a",
                        maxVal, "#4a1c0c",
                      ],
                "fill-opacity": 0.78,
              },
            },
            {
              id: "regions-outline",
              type: "line",
              source: "regions",
              paint: { "line-color": "#2a2118", "line-width": 0.8 },
            },
          ],
        }

        const bounds = computeBounds(geojson as GeoJSON.FeatureCollection)

        let map: maplibregl.Map
        try {
          map = new maplibregl.Map({
            container,
            style,
            center:
              geography === "ireland_county"
                ? [-8.0, 53.4]
                : geography === "netherlands_provincie"
                  ? [5.3, 52.2]
                  : [-1.5, 52.8],
            zoom:
              geography === "ireland_county" ? 6.2 : geography === "netherlands_provincie" ? 6.3 : 5.5,
            dragPan: true,
            doubleClickZoom: true,
            attributionControl: { compact: true },
            cooperativeGestures: true,
          })
        } catch {
          paintSvg()
          return
        }

        map.on("error", () => {
          if (!mapRef.current) paintSvg()
        })

        if (bounds) {
          map.fitBounds(bounds, { padding: 24, animate: false })
        }

        const metric = (chartData.metric_label as string | undefined)
          ?? (chartData.metric as string | undefined)
          ?? "Value"
        const popup = new maplibregl.Popup({
          closeButton: false,
          closeOnClick: false,
          className: "maplibre-hover-popup",
        })

        map.on("load", () => {
          map.on("mousemove", "regions-fill", (e) => {
            if (!e.features || e.features.length === 0) return
            const props = e.features[0].properties as Record<string, unknown>
            const name = String(props["area_name"] ?? "Unknown")
            const value = props["value"] as number | undefined
            const el = document.createElement("div")
            const strong = document.createElement("strong")
            strong.textContent = name
            el.appendChild(strong)
            el.appendChild(document.createElement("br"))
            const hover = props["hover"] ? String(props["hover"]) : ""
            el.appendChild(
              document.createTextNode(hover || formatHoverValue(value, String(metric))),
            )
            popup.setLngLat(e.lngLat).setDOMContent(el).addTo(map)
            map.getCanvas().style.cursor = "pointer"
          })

          map.on("mouseleave", "regions-fill", () => {
            popup.remove()
            map.getCanvas().style.cursor = ""
          })

          map.on("click", "regions-fill", (e) => {
            const feat = e.features?.[0]
            const code = feat?.properties?.area_code
            if (typeof code === "string") clickRef.current?.(code)
          })
        })

        mapRef.current = map
      })
      .catch(() => {
        setMapUnavailable(true)
        setSvgMarkup(null)
      })

    return () => {
      mapRef.current?.remove()
      mapRef.current = null
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps -- stabilized via JSON key
  }, [chartDataKey])

  return (
    <div className={`relative min-h-[280px] h-[min(62vh,520px)] rounded-md overflow-hidden ${className ?? ""}`}>
      <div
        ref={ref}
        className="h-full w-full"
        aria-label={(chartData.title as string | undefined) ?? "Choropleth map"}
        role="img"
      />
      {svgMarkup && (
        <div
          className="absolute inset-0 bg-[#e8e4dc]"
          data-testid="choropleth-svg-fallback"
          dangerouslySetInnerHTML={{ __html: svgMarkup }}
        />
      )}
      {mapUnavailable && !svgMarkup && (
        <div
          className="absolute inset-0 flex items-center justify-center bg-muted/50 text-center px-4"
          data-testid="map-unavailable"
        >
          <p className="text-sm text-muted-foreground">
            Map boundaries could not be loaded. The score and figures above still apply.
          </p>
        </div>
      )}
    </div>
  )
}

function regionAllowsOutline(chartData: Record<string, unknown>): boolean {
  const data = (chartData.data ?? []) as AreaDatum[]
  return data.length === 0 || data.length >= 8
}

const IRELAND_COUNTY_SLUGS = new Set([
  "carlow", "cavan", "clare", "cork", "donegal", "dublin", "galway", "kerry",
  "kildare", "kilkenny", "laois", "leitrim", "limerick", "longford", "louth",
  "mayo", "meath", "monaghan", "offaly", "roscommon", "sligo", "tipperary",
  "waterford", "westmeath", "wexford", "wicklow",
])

function normalizeCountyKey(value: string): string {
  return value.trim().toLowerCase().replace(/\s+/g, "")
}

/** GeoJSON `name` is friesland; CBS `statnaam` is Fryslân. Match the slug. */
const NL_SLUG_ALIASES: Record<string, string> = {
  fryslan: "friesland",
  "fryslân": "friesland",
  friesland: "friesland",
}

function nlBoundarySlug(value: string): string {
  const folded = value
    .trim()
    .toLowerCase()
    .normalize("NFD")
    .replace(/\p{M}/gu, "")
    .replace(/\s+/g, "")
  return NL_SLUG_ALIASES[folded] ?? NL_SLUG_ALIASES[normalizeCountyKey(value)] ?? normalizeCountyKey(value)
}

function choroplethLookupKeys(areaCode: string, areaName?: string): string[] {
  const keys = [areaCode, normalizeCountyKey(areaCode), nlBoundarySlug(areaCode)]
  if (areaName) keys.push(areaName, normalizeCountyKey(areaName), nlBoundarySlug(areaName))
  return [...new Set(keys.filter(Boolean))]
}

function lookupChoroplethValue(
  values: Map<string, number>,
  props: Record<string, unknown>,
  codeKeys: string[],
): string | undefined {
  for (const key of codeKeys) {
    const raw = props[key]
    if (typeof raw !== "string" || !raw.trim()) continue
    for (const candidate of choroplethLookupKeys(raw)) {
      if (values.has(candidate)) return candidate
    }
  }
  return undefined
}

function firstProp(props: Record<string, unknown>, keys: string[]): string | undefined {
  for (const key of keys) {
    const raw = props[key]
    if (typeof raw === "string" && raw.trim()) return raw
  }
  return undefined
}

function looksLikeIrelandCounties(data: AreaDatum[]): boolean {
  if (!data.length) return false
  const hits = data.filter((d) => IRELAND_COUNTY_SLUGS.has(normalizeCountyKey(d.area_code)))
  return hits.length >= Math.min(3, data.length) && hits.length === data.length
}

const NL_PROV_SLUGS = new Set([
  "drenthe", "flevoland", "friesland", "fryslan", "gelderland", "groningen",
  "limburg", "noord-brabant", "noord-holland", "overijssel", "utrecht", "zeeland", "zuid-holland",
])

function looksLikeNetherlandsProvinces(data: AreaDatum[]): boolean {
  if (!data.length) return false
  const hits = data.filter((d) => NL_PROV_SLUGS.has(normalizeCountyKey(d.area_code)))
  return hits.length >= Math.min(3, data.length)
}

function ringToD(
  ring: number[][],
  project: (lng: number, lat: number) => [number, number],
): string {
  return ring
    .map((pt, i) => {
      const [x, y] = project(pt[0], pt[1])
      return `${i === 0 ? "M" : "L"}${x.toFixed(1)} ${y.toFixed(1)}`
    })
    .join(" ") + " Z"
}

function svgFromFeatures(
  features: GeoJSON.Feature[],
  maxVal: number,
  colorMode: string,
): string {
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
  for (const f of features) {
    if (f.geometry && "coordinates" in f.geometry) walk(f.geometry.coordinates)
  }
  const w = 640
  const h = 720
  const pad = 12
  const dx = Math.max(maxLng - minLng, 0.01)
  const dy = Math.max(maxLat - minLat, 0.01)
  const project = (lng: number, lat: number): [number, number] => {
    const x = pad + ((lng - minLng) / dx) * (w - pad * 2)
    const y = pad + ((maxLat - lat) / dy) * (h - pad * 2)
    return [x, y]
  }
  const color = (value: number): string => {
    if (colorMode === "band") {
      const bands: Record<number, string> = {
        1: "#4a1c0c", 2: "#8b3a1a", 3: "#c45c26", 4: "#e8b86d", 5: "#c5d4a8", 6: "#6b8f71",
      }
      return bands[value] ?? "#d9d3c7"
    }
    const t = maxVal > 0 ? value / maxVal : 0
    if (t < 0.25) return "#f7f1e8"
    if (t < 0.5) return "#e8b86d"
    if (t < 0.75) return "#c45c26"
    if (t < 0.9) return "#8b3a1a"
    return "#4a1c0c"
  }
  const paths: string[] = []
  for (const f of features) {
    const value = Number(f.properties?.value ?? 0)
    const name = String(f.properties?.area_name ?? "")
    const geom = f.geometry
    const polys: number[][][][] = []
    if (geom?.type === "Polygon") polys.push(geom.coordinates as number[][][])
    if (geom?.type === "MultiPolygon") polys.push(...(geom.coordinates as number[][][][]))
    const d = polys
      .flatMap((poly) => poly.map((ring) => ringToD(ring as number[][], project)))
      .join(" ")
    paths.push(
      `<path d="${d}" fill="${color(value)}" stroke="#2a2118" stroke-width="0.6"><title>${escapeXml(name)}: ${value.toLocaleString("en-GB")}</title></path>`,
    )
  }
  return `<svg viewBox="0 0 ${w} ${h}" class="h-full w-full" role="img" aria-label="County choropleth">${paths.join("")}</svg>`
}

function escapeXml(s: string): string {
  return s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;")
}
