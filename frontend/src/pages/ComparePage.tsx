import { useMemo } from "react"
import { useSearchParams } from "react-router"
import { useQuery } from "@tanstack/react-query"
import { fetchJson } from "@/api/client"
import type { ReachResponse, ScoreResponse, SectionsResponse } from "@/api/types"
import { AREA_TYPES, regionsForCountry } from "@/lib/constants"
import { useFilters } from "@/api/hooks"
import { EmptyState } from "@/components/shared/EmptyState"
import { ArrowLeftRight } from "lucide-react"
import { COMPARE_METRICS, compareMetricLabel } from "@/lib/compareLabels"
import { isLondonRural } from "@/lib/uniqueExhibits"

function useSide(region: string, urbanRural: string, country: string) {
  return useQuery({
    queryKey: ["compare-side", country, region, urbanRural],
    queryFn: async () => {
      const access = await fetchJson<SectionsResponse>("/sections", {
        dimension: "accessibility",
        region,
        urban_rural: urbanRural,
        country,
      })
      const service = await fetchJson<SectionsResponse>("/sections", {
        dimension: "service_quality",
        region,
        urban_rural: urbanRural,
        country,
      })
      const score = await fetchJson<ScoreResponse>("/score", { region, urban_rural: urbanRural, country })
      const reach = await fetchJson<ReachResponse>("/reach", {
        region,
        urban_rural: urbanRural,
        dest_type: "jobs",
        cutoff: "45",
        country,
      })
      return { access, service, score, reach }
    },
    staleTime: Infinity,
    enabled: !!region,
  })
}

function pickNumber(sections: SectionsResponse | undefined, sectionId: string, key: string): number | null {
  const sec = sections?.sections.find((s) => s.section_id === sectionId)
  const v = sec?.stats?.[key]
  return typeof v === "number" ? v : null
}

function sideValues(bundle: ReturnType<typeof useSide>["data"]) {
  return {
    pct_within_400m: pickNumber(bundle?.access, "a3_walking_distance", "pct_covered"),
    evening_isolated: pickNumber(bundle?.service, "b2_operating_hours", "pct_evening_isolated"),
    in_country_score: bundle?.score.score ?? null,
    jobs_45: bundle?.reach.available ? bundle.reach.median : null,
  }
}

function formatMetric(id: string, v: number | null): string {
  if (v === null || Number.isNaN(v)) return "—"
  if (id === "in_country_score") return v.toFixed(1)
  if (id === "jobs_45") return Math.round(v).toLocaleString("en-GB")
  return `${v.toFixed(1)}%`
}

function slopeY(value: number, lo: number, hi: number): number {
  if (hi <= lo) return 28
  const t = (value - lo) / (hi - lo)
  return 52 - t * 40
}

function SlopeRow({
  id,
  left,
  right,
  nameA,
  nameB,
}: {
  id: string
  left: number | null
  right: number | null
  nameA: string
  nameB: string
}) {
  const both = left !== null && right !== null
  const pad = id === "in_country_score" ? 5 : Math.max(Math.abs((left ?? 0) - (right ?? 0)) * 0.4, 2)
  const nums = [left, right].filter((n): n is number => n !== null)
  const lo = nums.length ? Math.min(...nums) - pad : 0
  const hi = nums.length ? Math.max(...nums) + pad : 1
  const y1 = left === null ? 28 : slopeY(left, lo, hi)
  const y2 = right === null ? 28 : slopeY(right, lo, hi)

  return (
    <div>
      <p className="text-xs font-semibold text-foreground mb-2">{compareMetricLabel(id)}</p>
      <div className="grid grid-cols-[minmax(0,1fr)_140px_minmax(0,1fr)] gap-2 items-center text-sm">
        <div className="text-right min-w-0">
          <span className="text-muted-foreground">{nameA}</span>
          <span className="ml-2 font-semibold tabular-nums">{formatMetric(id, left)}</span>
        </div>
        <svg viewBox="0 0 140 56" className="w-full h-14" aria-hidden>
          <line x1="16" y1="8" x2="16" y2="48" stroke="currentColor" className="text-border" strokeWidth="1" />
          <line x1="124" y1="8" x2="124" y2="48" stroke="currentColor" className="text-border" strokeWidth="1" />
          {both && (
            <line
              x1="16"
              y1={y1}
              x2="124"
              y2={y2}
              stroke="currentColor"
              className="text-primary/70"
              strokeWidth="2"
            />
          )}
          <circle cx="16" cy={y1} r="4.5" className={left === null ? "fill-muted-foreground/30" : "fill-primary"} />
          <circle cx="124" cy={y2} r="4.5" className={right === null ? "fill-muted-foreground/30" : "fill-foreground"} />
        </svg>
        <div className="min-w-0">
          <span className="font-semibold tabular-nums">{formatMetric(id, right)}</span>
          <span className="ml-2 text-muted-foreground">{nameB}</span>
        </div>
      </div>
      {id === "jobs_45" && left === null && right === null && (
        <p className="text-xs text-muted-foreground mt-1">
          45-minute jobs are not precomputed for these regions in this pack.
        </p>
      )}
    </div>
  )
}

export default function ComparePage() {
  const { country } = useFilters()
  const [params, setParams] = useSearchParams()
  const urbanRural = params.get("urban_rural") ?? "all"
  const regions = regionsForCountry(country).filter((r) => r.code !== "all")
  const regionA =
    params.get("a") ??
    (country === "ireland" ? "cork" : country === "netherlands" ? "groningen" : "E12000002")
  const regionB =
    params.get("b") ??
    (country === "ireland" ? "dublin" : country === "netherlands" ? "noord-holland" : "E12000007")

  const set = (key: string, value: string) => {
    const next = new URLSearchParams(params)
    next.set(key, value)
    setParams(next)
  }

  const aQ = useSide(regionA, urbanRural, country)
  const bQ = useSide(regionB, urbanRural, country)
  const aVals = useMemo(() => sideValues(aQ.data), [aQ.data])
  const bVals = useMemo(() => sideValues(bQ.data), [bQ.data])
  const nameA = regions.find((r) => r.code === regionA)?.name ?? regionA
  const nameB = regions.find((r) => r.code === regionB)?.name ?? regionB
  const emptyCombo = isLondonRural(regionA, urbanRural) || isLondonRural(regionB, urbanRural)

  return (
    <div>
      <div className="mb-6">
        <h1 className="text-xl font-semibold tracking-tight text-foreground">Compare two regions</h1>
        <p className="text-sm text-muted-foreground mt-1">
          Same metrics, English names. Slope encodes the gap — not a warehouse dump.
        </p>
      </div>

      <div className="flex flex-wrap gap-3 mb-8">
        <div className="flex flex-col gap-1">
          <label className="text-[11px] font-mono uppercase tracking-wide text-muted-foreground/60">Area type</label>
          <select
            value={urbanRural}
            onChange={(e) => set("urban_rural", e.target.value)}
            className="text-xs font-mono app-glass-strong border border-white/60 rounded-2xl px-3 py-1.5"
          >
            {AREA_TYPES.map((a) => (
              <option key={a.code} value={a.code}>{a.name}</option>
            ))}
          </select>
        </div>
        <div className="flex flex-col gap-1">
          <label className="text-[11px] font-mono uppercase tracking-wide text-muted-foreground/60">Region A</label>
          <select
            value={regionA}
            onChange={(e) => set("a", e.target.value)}
            className="text-xs font-mono app-glass-strong border border-white/60 rounded-2xl px-3 py-1.5"
          >
            {regions.map((r) => (
              <option key={r.code} value={r.code}>{r.name}</option>
            ))}
          </select>
        </div>
        <div className="flex items-end pb-0.5">
          <ArrowLeftRight className="w-4 h-4 text-muted-foreground/40" />
        </div>
        <div className="flex flex-col gap-1">
          <label className="text-[11px] font-mono uppercase tracking-wide text-muted-foreground/60">Region B</label>
          <select
            value={regionB}
            onChange={(e) => set("b", e.target.value)}
            className="text-xs font-mono app-glass-strong border border-white/60 rounded-2xl px-3 py-1.5"
          >
            {regions.map((r) => (
              <option key={r.code} value={r.code}>{r.name}</option>
            ))}
          </select>
        </div>
      </div>

      {regionA === regionB ? (
        <EmptyState
          icon={<ArrowLeftRight className="w-10 h-10" />}
          title="Select two different regions"
          description="Choose distinct regions to compare the same metrics."
        />
      ) : emptyCombo ? (
        <p className="text-sm text-muted-foreground py-8 max-w-xl">
          London has no rural LSOAs — this combination is empty.
        </p>
      ) : (
        <div className="space-y-7">
          {COMPARE_METRICS.map((m) => (
            <SlopeRow
              key={m.id}
              id={m.id}
              left={aVals[m.id]}
              right={bVals[m.id]}
              nameA={nameA}
              nameB={nameB}
            />
          ))}
        </div>
      )}
    </div>
  )
}
