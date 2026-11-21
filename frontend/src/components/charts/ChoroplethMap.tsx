import { useRef, useEffect, useMemo, useState } from "react"
import maplibregl, { type StyleSpecification } from "maplibre-gl"
import "maplibre-gl/dist/maplibre-gl.css"

interface AreaDatum {
  area_code: string
  area_name: string
  value: number | null
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
  onStatus?: (status:'ready'|'unavailable')=>void
}

const OSM_RASTER = 'https://tile.openstreetmap.org/{z}/{x}/{y}.png'

function computeBounds(featureCollection: GeoJSON.FeatureCollection): [[number, number], [number, number]] | null {
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

function formatHoverValue(value: number | null | undefined, metricLabel: string): string {
  if (value == null || !Number.isFinite(value)) return "—"
  const compact = value.toLocaleString("en-GB", { maximumFractionDigits: value >= 100 ? 0 : 1 })
  if (metricLabel.includes("%")) return `${compact}%`
  return compact
}

export default function ChoroplethMap({ chartData, onAreaClick, className,onStatus }: Props) {
  const ref = useRef<HTMLDivElement>(null)
  const mapRef = useRef<maplibregl.Map | null>(null)
  const clickRef = useRef(onAreaClick)
  clickRef.current = onAreaClick
  const statusRef=useRef(onStatus)
  statusRef.current=onStatus
  const chartDataKey = useMemo(() => JSON.stringify(chartData), [chartData])
  const [mapUnavailable, setMapUnavailable] = useState(false)
  const [svgMarkup, setSvgMarkup] = useState<string | null>(null)

  useEffect(() => {
    if (!ref.current) return
    const data = (chartData.data ?? []) as AreaDatum[]
    if (!data.length) {
      setMapUnavailable(true)
      setSvgMarkup(null)
      statusRef.current?.('unavailable')
      return
    }
    setMapUnavailable(false)
    setSvgMarkup(null)
    const container = ref.current

    const values = new Map<string, number | null>()
    const names = new Map<string, string>()
    const hovers = new Map<string, string | undefined>()
    for (const d of data) {
      for (const key of choroplethLookupKeys(d.area_code, d.area_name)) {
        values.set(key, typeof d.value === 'number' && Number.isFinite(d.value) ? d.value : null)
        names.set(key, d.area_name)
        hovers.set(key, d.hover)
      }
    }
    const maxVal = Math.max(1, ...data.flatMap(d => typeof d.value === 'number' && Number.isFinite(d.value) ? [d.value] : []))
    const colorMode = (chartData.color_mode as string | undefined) ?? "continuous"

    const inferredIreland = looksLikeIrelandCounties(data)
    const inferredNl = looksLikeNetherlandsProvinces(data)
    const inferredFr = looksLikeFranceRegions(data)
    const geography =
      (chartData.geography as string | undefined) ??
      (inferredIreland
        ? "ireland_county"
        : inferredNl
          ? "netherlands_provincie"
          : inferredFr
            ? "france_region"
            : "region")
    const boundaryFile =
      geography === "ireland_county"
        ? "/boundaries/ireland_counties.geojson"
        : geography === "netherlands_provincie"
          ? "/boundaries/netherlands_provincies.geojson"
        : geography === "france_region"
          ? "/boundaries/france_regions.geojson"
        : geography === "lad"
          ? "/boundaries/lad.geojson"
          : "/boundaries/regions.geojson"
    const codeKeys =
      geography === "ireland_county"
        ? ["COUNTY_SLUG", "county_slug", "COUNTY", "county", "NAME", "name"]
        : geography === "netherlands_provincie"
          ? ["name", "NAME", "statcode", "statnaam", "prov_naam", "PV_NAAM"]
        : geography === "france_region"
          ? ["name", "NAME", "nom", "code", "CODE"]
        : geography === "lad"
          ? ["LAD22CD", "lad22cd"]
          : ["RGN22CD", "rgn22cd"]
    const nameKeys =
      geography === "ireland_county"
        ? ["COUNTY", "county", "NAME", "name"]
        : geography === "netherlands_provincie"
          ? ["statnaam", "name", "NAME", "PV_NAAM", "prov_naam"]
        : geography === "france_region"
          ? ["nom", "name", "NAME"]
        : geography === "lad"
          ? ["LAD22NM", "lad22nm"]
          : ["RGN22NM", "rgn22nm"]

    const request = new AbortController()
    let disposed = false
    fetch(boundaryFile, { signal: request.signal })
      .then((r) => {
        if (!r.ok) throw new Error(`Failed to load boundaries: HTTP ${r.status}`)
        return r.json()
      })
      .then((geojson: { features: GeoJsonFeature[] }) => {
        if (disposed) return
        const matched: GeoJsonFeature[] = []
        for (const f of geojson.features) {
          const code = firstProp(f.properties, codeKeys)
          const valueKey = lookupChoroplethValue(values, f.properties, codeKeys)
          if (valueKey !== undefined) {
            f.properties["value"] = values.get(valueKey) ?? null
            f.properties["area_name"] =
              names.get(valueKey) ?? firstProp(f.properties, nameKeys) ?? valueKey
            f.properties["area_code"] = valueKey
            if (hovers.get(valueKey)) f.properties["hover"] = hovers.get(valueKey)
            matched.push(f)
          } else if (geography === "france_region") {
            const insee = String(f.properties["code"] ?? "")
            const slug = FR_INSEE_TO_SLUG[insee] ?? frBoundarySlug(String(firstProp(f.properties, nameKeys) ?? ""))
            const vk = [...choroplethLookupKeys(slug)].find((k) => values.has(k))
            f.properties["value"] = vk !== undefined ? values.get(vk) : null
            f.properties["area_name"] = firstProp(f.properties, nameKeys) ?? slug
            f.properties["area_code"] = slug
            matched.push(f)
          } else if (
            geography !== "lad" &&
            geography !== "ireland_county" &&
            geography !== "netherlands_provincie" &&
            geography !== "france_region" &&
            regionAllowsOutline(chartData)
          ) {
            f.properties["value"] = null
            f.properties["area_name"] = firstProp(f.properties, nameKeys)
            f.properties["area_code"] = code
            matched.push(f)
          }
        }
        geojson.features = matched
        if (matched.length === 0) {
          setMapUnavailable(true)
          setSvgMarkup(null)
          statusRef.current?.('unavailable')
          return
        }
        const paintSvg = () => {
          setSvgMarkup(
            svgFromFeatures(matched as GeoJSON.Feature[], maxVal, colorMode, Boolean(clickRef.current)),
          )
          setMapUnavailable(false)
          statusRef.current?.('ready')
        }
        // Paint local polygons first so MapLibre abort / late tiles never leave
        // a blank CARTO frame. GL is an enhancement, not the only paint path.
        paintSvg()
        const bounds = computeBounds(geojson as GeoJSON.FeatureCollection)
        // The Irish county asset uses projected metres. Its real polygons can
        // render in the local SVG path, but cannot be sent to MapLibre as degrees.
        if(bounds?.some(([x,y])=>Math.abs(x)>180||Math.abs(y)>90))return
        if (
          geography === "ireland_county" ||
          geography === "netherlands_provincie" ||
          geography === "france_region" ||
          geography === "region" ||
          geography === "lad"
        ) {
          // SVG is the briefing exhibit. Skip GL — ERR_ABORTED left blank maps.
          if (colorMode !== 'coverage' && colorMode !== 'desert_rate') return
        }

        const style: StyleSpecification = {
          version: 8,
          sources: {
            carto: {
              type: "raster",
              tiles: [OSM_RASTER],
              tileSize: 256,
              attribution: '© <a href="https://www.openstreetmap.org/copyright">OpenStreetMap contributors</a>',
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
                  colorMode === 'coverage'
                    ? ['case', ['==', ['get', 'value'], null], '#d9d7d2', ['step', ['get', 'value'], '#c6602d', 60, '#e5ae69', 75, '#dfd7a2', 85, '#9eb17f', 95, '#64885d']]
                    : colorMode === 'desert_rate'
                    ? ['case', ['==', ['get', 'value'], null], '#d9d7d2', ['step', ['get', 'value'], '#64885d', 10, '#9eb17f', 20, '#dfd7a2', 40, '#e5ae69', 60, '#c6602d', 80, '#8f2d18']]
                    : colorMode === "band"
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
                "fill-opacity": colorMode === 'coverage' ? 1 : 0.78,
              },
            },
            {
              id: "regions-outline",
              type: "line",
              source: "regions",
              paint: { "line-color": colorMode === 'coverage' ? '#ffffff' : '#2a2118', "line-width": 1.2 },
            },
          ],
        }

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
          if (colorMode === 'coverage' || colorMode === 'desert_rate') {
            setSvgMarkup(null)
            if (typeof map.addControl === 'function') map.addControl(new maplibregl.NavigationControl({ showCompass: false }), 'top-left')
          }
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
        if (disposed) return
        setMapUnavailable(true)
        setSvgMarkup(null)
        statusRef.current?.('unavailable')
      })

    return () => {
      disposed = true
      request.abort()
      mapRef.current?.remove()
      mapRef.current = null
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps -- stabilized via JSON key
  }, [chartDataKey])

  return (
    <div data-map-state={mapUnavailable?'unavailable':svgMarkup||mapRef.current?'ready':'loading'} className={`relative min-h-[280px] h-[min(62vh,520px)] rounded-md overflow-hidden ${className ?? ""}`}>
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
          onClick={event => {
            const area = (event.target as Element).closest('[data-area-code]')?.getAttribute('data-area-code')
            if (area) clickRef.current?.(area)
          }}
          onKeyDown={event => {
            if (event.key !== 'Enter' && event.key !== ' ') return
            const area = (event.target as Element).closest('[data-area-code]')?.getAttribute('data-area-code')
            if (area) { event.preventDefault(); clickRef.current?.(area) }
          }}
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

const FR_INSEE_TO_SLUG: Record<string, string> = {
  "11": "ile-de-france",
  "24": "centre-val-de-loire",
  "27": "bourgogne-franche-comte",
  "28": "normandie",
  "32": "hauts-de-france",
  "44": "grand-est",
  "52": "pays-de-la-loire",
  "53": "bretagne",
  "75": "nouvelle-aquitaine",
  "76": "occitanie",
  "84": "auvergne-rhone-alpes",
  "93": "provence-alpes-cote-dazur",
  "94": "corse",
}

function compactGeoKey(value: string): string {
  return value
    .trim()
    .toLowerCase()
    .normalize("NFD")
    .replace(/\p{M}/gu, "")
    .replace(/[^a-z0-9]/g, "")
}

function frBoundarySlug(value: string): string {
  const folded = value
    .trim()
    .toLowerCase()
    .normalize("NFD")
    .replace(/\p{M}/gu, "")
    .replace(/['’]/g, "")
    .replace(/\s+/g, "-")
  const compact = compactGeoKey(value)
  return (
    FR_INSEE_TO_SLUG[folded] ??
    FR_INSEE_TO_SLUG[compact] ??
    (compact === "centrevaldeloire" ? "centre-val-de-loire" : folded)
  )
}

function choroplethLookupKeys(areaCode: string, areaName?: string): string[] {
  const keys = [
    areaCode,
    normalizeCountyKey(areaCode),
    nlBoundarySlug(areaCode),
    frBoundarySlug(areaCode),
    compactGeoKey(areaCode),
  ]
  if (areaName) {
    keys.push(
      areaName,
      normalizeCountyKey(areaName),
      nlBoundarySlug(areaName),
      frBoundarySlug(areaName),
      compactGeoKey(areaName),
    )
  }
  return [...new Set(keys.filter(Boolean))]
}

function lookupChoroplethValue(
  values: Map<string, number | null>,
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

const FR_REGION_SLUGS = new Set([
  "ile-de-france",
  "centre-val-de-loire",
  "bourgogne-franche-comte",
  "normandie",
  "hauts-de-france",
  "grand-est",
  "pays-de-la-loire",
  "bretagne",
  "nouvelle-aquitaine",
  "occitanie",
  "auvergne-rhone-alpes",
  "provence-alpes-cote-dazur",
  "corse",
])

function looksLikeFranceRegions(data: AreaDatum[]): boolean {
  if (!data.length) return false
  const hits = data.filter((d) => FR_REGION_SLUGS.has(frBoundarySlug(d.area_code)))
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
  interactive: boolean,
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
  const color = (value: number | null): string => {
    if (value === null) return '#d9d7d2'
    if (colorMode === 'desert_rate') {
      if (value < 10) return '#64885d'
      if (value < 20) return '#9eb17f'
      if (value < 40) return '#dfd7a2'
      if (value < 60) return '#e5ae69'
      if (value < 80) return '#c6602d'
      return '#8f2d18'
    }
    if (colorMode === 'coverage') {
      if (value < 60) return '#c6602d'
      if (value < 75) return '#e5ae69'
      if (value < 85) return '#dfd7a2'
      if (value < 95) return '#9eb17f'
      return '#64885d'
    }
    if (colorMode === "band") {
      const bands: Record<number, string> = {
        1: "#4a1c0c", 2: "#8b3a1a", 3: "#c45c26", 4: "#e8b86d", 5: "#c5d4a8", 6: "#6b8f71",
      }
      return bands[value] ?? "#d9d3c7"
    }
    if (colorMode === 'reach_rate') {
      if (value < 10) return '#4f8050'
      if (value < 20) return '#d6d38d'
      if (value < 30) return '#efc45e'
      if (value < 40) return '#e7923c'
      return '#d85220'
    }
    const t = maxVal > 0 ? value / maxVal : 0
    if (t < 0.25) return "#edd3a4"
    if (t < 0.5) return "#e8b86d"
    if (t < 0.75) return "#c45c26"
    if (t < 0.9) return "#8b3a1a"
    return "#4a1c0c"
  }
  const paths: string[] = []
  for (const f of features) {
    const rawValue = f.properties?.value
    const value = typeof rawValue === 'number' && Number.isFinite(rawValue) ? rawValue : null
    const name = String(f.properties?.area_name ?? "")
    const code = String(f.properties?.area_code ?? '')
    const description = `${name}: ${value == null ? 'Unavailable' : value.toLocaleString('en-GB', { maximumFractionDigits: 1 }) + (colorMode === 'coverage' || colorMode === 'reach_rate' || colorMode === 'desert_rate' ? '%' : '')}`
    const geom = f.geometry
    const polys: number[][][][] = []
    if (geom?.type === "Polygon") polys.push(geom.coordinates as number[][][])
    if (geom?.type === "MultiPolygon") polys.push(...(geom.coordinates as number[][][][]))
    const d = polys
      .flatMap((poly) => poly.map((ring) => ringToD(ring as number[][], project)))
      .join(" ")
    paths.push(
      `<path d="${d}" fill="${color(value)}" stroke="${colorMode === 'coverage' ? '#fff' : '#2a2118'}" stroke-width="${colorMode === 'coverage' ? '1.2' : '0.6'}" data-area-code="${escapeXml(code)}"${interactive && value != null ? ` role="button" tabindex="0" aria-label="${escapeXml(description)}"` : ''}><title>${escapeXml(description)}</title></path>`,
    )
  }
  return `<svg viewBox="0 0 ${w} ${h}" class="h-full w-full" role="${interactive ? 'group' : 'img'}" aria-label="Regional choropleth">${paths.join("")}</svg>`
}

function escapeXml(s: string): string {
  return s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, '&quot;').replace(/'/g, '&apos;')
}
