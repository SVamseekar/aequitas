import { useEffect, useMemo, useRef, useState } from "react"
import { Link, useSearchParams } from "react-router"
import { useFilters } from "@/api/hooks"
import { apiPost, fetchJson } from "@/api/client"
import { AREA_TYPES, COUNTRIES, regionsForCountry } from "@/lib/constants"
import { appPath, withSearch } from "@/lib/appRoutes"
import { filterSentence } from "@/lib/scoreFormat"
import { isLondonRural } from "@/lib/uniqueExhibits"
import StudioEditorMap, { type DrawnOp } from "@/components/studio/StudioEditorMap"
import StudioResultMap from "@/components/studio/StudioResultMap"

export interface StudioOp {
  op: "add_stop" | "remove_stop" | "add_trips" | "frequency_uplift"
  lat?: number
  lon?: number
  name?: string
  factor?: number
  extra_trips?: number
  line?: number[][]
  source?: "drawn" | "upload"
}

interface JobSnapshot {
  id: string
  status: string
  error?: string | null
  result?: StudioResult | null
}

interface StudioResult {
  ok: boolean
  mode: string
  note: string
  patch: { country: string; region: string; urban_rural: string; ops: StudioOp[]; source: string }
  score_before: number | null
  score_after: number | null
  people_gained: number
  people_lost: number
  n_areas: number
  deciles: { imd_decile: number; people_gained: number; people_lost: number }[]
  areas: {
    area: string
    name?: string
    lat?: number
    lon?: number
    pop: number
    imd_decile: number | null
    covered_before: boolean
    covered_after: boolean
    delta_people: number
  }[]
  reach_available: boolean
  needs_r5py: boolean
  narrative: string
  default_region_note?: string | null
}

const LAST_PATCH_KEY = "aequitas.studio.lastPatch"

export default function StudioPage() {
  const { country, region, urbanRural } = useFilters()
  const [params] = useSearchParams()
  const countryName = COUNTRIES.find((c) => c.code === country)?.name ?? country
  const regionName = regionsForCountry(country).find((r) => r.code === region)?.name ?? region
  const areaName = AREA_TYPES.find((a) => a.code === urbanRural)?.name ?? urbanRural
  const place = filterSentence(regionName, areaName)

  const [ops, setOps] = useState<StudioOp[]>([])
  const [uploadError, setUploadError] = useState<string | null>(null)
  const [job, setJob] = useState<JobSnapshot | null>(null)
  const [result, setResult] = useState<StudioResult | null>(null)
  const [applyError, setApplyError] = useState<string | null>(null)
  const [narrow, setNarrow] = useState(false)
  const [clickWarn, setClickWarn] = useState<string | null>(null)
  const [mapMode, setMapMode] = useState<"baseline" | "after" | "difference">("difference")
  const pollRef = useRef<number | null>(null)

  useEffect(() => {
    if (typeof window.matchMedia !== "function") return
    const mq = window.matchMedia("(max-width: 420px)")
    const apply = () => setNarrow(mq.matches)
    apply()
    mq.addEventListener("change", apply)
    return () => mq.removeEventListener("change", apply)
  }, [])

  useEffect(() => {
    try {
      const raw = localStorage.getItem(LAST_PATCH_KEY)
      if (!raw) return
      const parsed = JSON.parse(raw) as { ops?: StudioOp[] }
      if (Array.isArray(parsed.ops) && parsed.ops.length) setOps(parsed.ops)
    } catch {
      /* ignore */
    }
  }, [])

  useEffect(() => {
    try {
      localStorage.setItem(LAST_PATCH_KEY, JSON.stringify({ ops }))
    } catch {
      /* ignore */
    }
  }, [ops])

  useEffect(() => {
    return () => {
      if (pollRef.current) window.clearInterval(pollRef.current)
    }
  }, [])

  const packReady = COUNTRIES.find((c) => c.code === country)?.packReady ?? false
  if (!packReady) {
    return (
      <div className="py-8 max-w-xl">
        <h1 className="text-2xl font-semibold mb-2">Studio</h1>
        <p className="text-sm text-muted-foreground">
          The {countryName} pack is not built yet. Studio computes on England and Ireland.
        </p>
      </div>
    )
  }

  if (isLondonRural(region, urbanRural)) {
    return (
      <p className="text-sm text-muted-foreground py-8 max-w-xl">
        London has no rural LSOAs under the official urban/rural classification — this filter is empty.
      </p>
    )
  }

  const addDrawn = (drawn: DrawnOp) => {
    setOps((prev) => [...prev, { ...drawn, source: "drawn" }])
  }

  const onUpload = async (file: File) => {
    setUploadError(null)
    const text = await file.text()
    try {
      const parsed = await apiPost<{ ok: boolean; error: string | null; ops: StudioOp[] }>(
        "/studio/parse",
        { text, filename: file.name },
      )
      if (!parsed.ok) {
        setUploadError(parsed.error ?? "That file could not be read.")
        return
      }
      setOps((prev) => [...prev, ...parsed.ops.map((o) => ({ ...o, source: "upload" as const }))])
    } catch (err) {
      setUploadError(err instanceof Error ? err.message : "That file could not be read.")
    }
  }

  const apply = async () => {
    setApplyError(null)
    setResult(null)
    try {
      const created = await apiPost<JobSnapshot>("/studio/jobs", {
        country,
        region,
        urban_rural: urbanRural,
        ops,
        source: ops.some((o) => o.source === "upload") ? "upload" : "drawn",
      })
      setJob(created)
      if (created.status === "done" && created.result) {
        setResult(created.result)
        return
      }
      if (pollRef.current) window.clearInterval(pollRef.current)
      pollRef.current = window.setInterval(async () => {
        const st = await fetchJson<JobSnapshot>(`/studio/jobs/${created.id}`)
        setJob(st)
        if (st.status === "done") {
          const body = await fetchJson<StudioResult>(`/studio/jobs/${created.id}/result`)
          setResult(body)
          if (pollRef.current) window.clearInterval(pollRef.current)
        }
        if (st.status === "error") {
          setApplyError(st.error ?? "Studio job failed.")
          if (pollRef.current) window.clearInterval(pollRef.current)
        }
      }, 1200)
    } catch (err) {
      setApplyError(err instanceof Error ? err.message : "Could not start the studio job.")
    }
  }

  const downloadPatch = () => {
    const blob = new Blob(
      [JSON.stringify({ country, region, urban_rural: urbanRural, ops, source: "drawn" }, null, 2)],
      { type: "application/json" },
    )
    const a = document.createElement("a")
    a.href = URL.createObjectURL(blob)
    a.download = "studio-patch.json"
    a.click()
  }

  const downloadCsv = () => {
    if (!job?.id) return
    window.location.href = `/api/studio/jobs/${job.id}/winners.csv`
  }

  const patchSummary = useMemo(
    () =>
      ops.map((o, i) => {
        if (o.op === "add_stop") return `${i + 1}. Add stop ${o.name ?? ""} ${o.lat?.toFixed(3)}, ${o.lon?.toFixed(3)}`
        if (o.op === "remove_stop") return `${i + 1}. Remove stop ${o.lat?.toFixed(3)}, ${o.lon?.toFixed(3)}`
        if (o.op === "frequency_uplift") return `${i + 1}. Frequency ×${o.factor ?? "?"} / +${o.extra_trips ?? 0} trips`
        return `${i + 1}. New corridor (${o.line?.length ?? 0} vertices)`
      }),
    [ops],
  )

  return (
    <div className="pb-10">
      <h1 className="text-2xl sm:text-3xl font-semibold tracking-tight mb-1">Studio — {place}</h1>
      <p className="text-sm text-muted-foreground mb-4 max-w-2xl">
        Draw or upload a stop or corridor. Who gains is walk-to-stop (400 m) unless r5py and a PBF
        are on this machine. Frequency and new corridors are not multiplied by a made-up factor.
      </p>

      {narrow ? (
        <p className="text-sm text-muted-foreground mb-4">
          Use a wider screen to draw on the map. You can still upload a CSV or GeoJSON.
        </p>
      ) : null}

      {!narrow ? (
        <StudioEditorMap
          country={country}
          ops={ops}
          region={region}
          onAdd={addDrawn}
          onDelete={(index) => setOps((prev) => prev.filter((_, i) => i !== index))}
          onOutsideFilter={(msg) => setClickWarn(msg || null)}
        />
      ) : null}
      {clickWarn ? <p className="text-sm text-destructive mt-2">{clickWarn}</p> : null}

      <div className="mt-4 flex flex-wrap gap-3 items-center">
        <label className="text-sm border border-border rounded-lg px-3 py-2 cursor-pointer">
          Upload GTFS / GeoJSON / CSV
          <input
            type="file"
            accept=".csv,.txt,.geojson,.json,.zip,text/csv,application/geo+json"
            className="sr-only"
            onChange={(e) => {
              const f = e.target.files?.[0]
              if (f) void onUpload(f)
            }}
          />
        </label>
        <button
          type="button"
          className="text-sm border border-border rounded-lg px-3 py-2"
          onClick={() =>
            setOps((prev) => [...prev, { op: "frequency_uplift", factor: 1.5, extra_trips: 4 }])
          }
        >
          Add frequency uplift (needs r5py)
        </button>
        <button type="button" className="text-sm text-muted-foreground underline" onClick={() => setOps([])}>
          Clear patch
        </button>
      </div>
      {uploadError ? <p className="text-sm text-destructive mt-2">{uploadError}</p> : null}

      <div className="mt-4 app-glass rounded-2xl p-4" data-testid="studio-patch-list">
        <p className="text-[11px] font-mono uppercase tracking-wide text-muted-foreground mb-2">
          Patch ({ops.length})
        </p>
        {ops.length === 0 ? (
          <p className="text-sm text-muted-foreground">No operations yet — draw a stop or upload a file.</p>
        ) : (
          <ul className="text-sm space-y-1">
            {patchSummary.map((line) => (
              <li key={line}>{line}</li>
            ))}
          </ul>
        )}
      </div>

      <div className="mt-4 flex flex-wrap gap-3">
        <button
          type="button"
          disabled={ops.length === 0 || job?.status === "running"}
          onClick={() => void apply()}
          className="px-4 py-2 rounded-lg bg-primary text-primary-foreground text-sm font-medium disabled:opacity-50"
        >
          {job?.status === "running" ? "Applying… (poll, not a silent spinner)" : "Apply patch"}
        </button>
        <button type="button" className="text-sm underline" onClick={downloadPatch} disabled={ops.length === 0}>
          Download patch JSON
        </button>
        <button type="button" className="text-sm underline" onClick={downloadCsv} disabled={!result}>
          Download winners/losers CSV
        </button>
        {job?.id ? (
          <a
            className="text-sm underline"
            href={`/api/export/pack.csv?region=${encodeURIComponent(region)}&urban_rural=${encodeURIComponent(urbanRural)}&studio_job=${encodeURIComponent(job.id)}`}
          >
            Download briefing pack (CSV)
          </a>
        ) : null}
        <Link className="text-sm text-muted-foreground underline" to={withSearch(appPath(country, "scenarios"), params.toString())}>
          Listed scenarios still live here
        </Link>
      </div>
      {applyError ? <p className="text-sm text-destructive mt-2">{applyError}</p> : null}

      {result ? (
        <div className="mt-8" data-testid="studio-result">
          <p className="text-[11px] font-mono uppercase tracking-wide text-muted-foreground">
            Before / after score
          </p>
          <p className="text-4xl font-bold tabular-nums">
            {result.score_before == null ? "—" : result.score_before.toFixed(1)} →{" "}
            {result.score_after == null ? "—" : result.score_after.toFixed(1)}
          </p>
          <p className="text-sm text-muted-foreground mt-2 max-w-2xl">{result.note}</p>
          {result.default_region_note ? (
            <p className="text-sm text-muted-foreground mt-1">{result.default_region_note}</p>
          ) : null}
          {result.narrative ? <p className="text-sm mt-3 max-w-2xl">{result.narrative}</p> : null}
          <p className="text-sm mt-3">
            {result.people_gained.toLocaleString("en-GB")} people newly within 400 m;{" "}
            {result.people_lost.toLocaleString("en-GB")} lose that walk.
            {result.reach_available
              ? " Reach parquet exists — 15/30/45 is only shown when r5py actually recomputed it."
              : " No reach parquet — 15/30/45 job counts are not shown."}
          </p>

          {result.deciles.length > 0 ? (
            <table className="mt-4 text-sm w-full max-w-lg">
              <thead>
                <tr className="text-left text-muted-foreground">
                  <th className="py-1">IMD decile (England ranks)</th>
                  <th>People gained</th>
                  <th>People lost</th>
                </tr>
              </thead>
              <tbody>
                {result.deciles.map((d) => (
                  <tr key={d.imd_decile}>
                    <td className="py-1">{d.imd_decile}</td>
                    <td>{d.people_gained.toLocaleString("en-GB")}</td>
                    <td>{d.people_lost.toLocaleString("en-GB")}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          ) : (
            <p className="text-sm text-muted-foreground mt-3">No decile who-gains for this run.</p>
          )}

          <div className="mt-4 flex gap-2 text-sm">
            {(["baseline", "after", "difference"] as const).map((m) => (
              <button
                key={m}
                type="button"
                className={`px-3 py-1 rounded-full border ${mapMode === m ? "border-primary text-primary" : "border-border"}`}
                onClick={() => setMapMode(m)}
              >
                {m}
              </button>
            ))}
          </div>
          <StudioResultMap result={result} mode={mapMode} ops={ops} />
        </div>
      ) : null}
    </div>
  )
}
