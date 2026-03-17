import { useState } from "react"
import { useQuery } from "@tanstack/react-query"
import { fetchJson } from "@/api/client"
import type { SectionsResponse } from "@/api/types"
import { DIMENSIONS, REGIONS } from "@/lib/constants"
import { EmptyState } from "@/components/shared/EmptyState"
import { ArrowLeftRight } from "lucide-react"

function useCompareSection(dimension: string, region: string) {
  return useQuery({
    queryKey: ["sections", dimension, region, "all"],
    queryFn: () => fetchJson<SectionsResponse>("/sections", { dimension, region, urban_rural: "all" }),
    staleTime: Infinity,
    enabled: !!dimension,
  })
}

function StatValue({ v }: { v: unknown }) {
  if (v === null || v === undefined) return <span className="text-muted-foreground/40">—</span>
  if (typeof v === "number") {
    return <span className="text-foreground font-mono">{parseFloat(v.toPrecision(4))}</span>
  }
  if (typeof v === "string") return <span className="text-foreground font-mono">{v}</span>
  return <span className="text-muted-foreground/40 text-[9px]">{JSON.stringify(v).slice(0, 40)}</span>
}

function RegionColumn({ dimension, region }: { dimension: string; region: string }) {
  const { data, isLoading } = useCompareSection(dimension, region)
  const regionName = REGIONS.find((r) => r.code === region)?.name ?? region

  if (isLoading) {
    return (
      <div className="space-y-2">
        {Array.from({ length: 4 }).map((_, i) => (
          <div key={i} className="h-12 bg-muted animate-pulse rounded" />
        ))}
      </div>
    )
  }

  const sections = data?.sections.filter((s) => Object.keys(s.stats ?? {}).length > 0) ?? []

  return (
    <div>
      <p className="text-[10px] font-mono uppercase tracking-wider text-indigo-400 mb-3">{regionName}</p>
      <div className="space-y-3">
        {sections.slice(0, 8).map((s) => {
          const stats = Object.entries(s.stats ?? {}).filter(([k, v]) =>
            typeof v === "number" || typeof v === "string" && k !== "unit" && k !== "entity_type"
          )
          return (
            <div key={s.section_id} className="border border-border rounded bg-card p-3">
              <p className="text-[9px] font-mono uppercase tracking-wider text-muted-foreground/60 mb-2">
                {s.section_id.replace(/_/g, " ")}
              </p>
              <div className="space-y-1">
                {stats.slice(0, 4).map(([k, v]) => (
                  <div key={k} className="flex justify-between gap-2">
                    <span className="text-[9px] text-muted-foreground/50 font-mono truncate">{k}</span>
                    <StatValue v={v} />
                  </div>
                ))}
              </div>
            </div>
          )
        })}
        {sections.length === 0 && (
          <p className="text-xs text-muted-foreground/40 font-mono">No data available</p>
        )}
      </div>
    </div>
  )
}

export default function ComparePage() {
  const [dimension, setDimension] = useState("equity")
  const [regionA, setRegionA] = useState("E12000002") // North West
  const [regionB, setRegionB] = useState("E12000007") // London

  return (
    <div className="min-h-screen bg-background">
      <div className="border-b border-border bg-card/50 h-8 flex items-center">
        <div className="max-w-7xl mx-auto px-4 w-full">
          <span className="text-[9px] font-mono text-muted-foreground uppercase tracking-widest">Compare regions</span>
        </div>
      </div>

      <div className="max-w-7xl mx-auto px-4 py-8">
        {/* Controls */}
        <div className="flex flex-wrap gap-3 mb-8">
          <div className="flex flex-col gap-1">
            <label className="text-[9px] font-mono uppercase tracking-wider text-muted-foreground/60">Dimension</label>
            <select
              value={dimension}
              onChange={(e) => setDimension(e.target.value)}
              className="text-xs font-mono bg-card border border-border rounded px-3 py-1.5 text-foreground focus:outline-none focus:ring-1 focus:ring-indigo-500"
            >
              {DIMENSIONS.map((d) => (
                <option key={d.id} value={d.id}>{d.name}</option>
              ))}
            </select>
          </div>

          <div className="flex flex-col gap-1">
            <label className="text-[9px] font-mono uppercase tracking-wider text-muted-foreground/60">Region A</label>
            <select
              value={regionA}
              onChange={(e) => setRegionA(e.target.value)}
              className="text-xs font-mono bg-card border border-border rounded px-3 py-1.5 text-foreground focus:outline-none focus:ring-1 focus:ring-indigo-500"
            >
              {REGIONS.filter((r) => r.code !== "all").map((r) => (
                <option key={r.code} value={r.code}>{r.name}</option>
              ))}
            </select>
          </div>

          <div className="flex items-end pb-0.5">
            <ArrowLeftRight className="w-4 h-4 text-muted-foreground/40" />
          </div>

          <div className="flex flex-col gap-1">
            <label className="text-[9px] font-mono uppercase tracking-wider text-muted-foreground/60">Region B</label>
            <select
              value={regionB}
              onChange={(e) => setRegionB(e.target.value)}
              className="text-xs font-mono bg-card border border-border rounded px-3 py-1.5 text-foreground focus:outline-none focus:ring-1 focus:ring-indigo-500"
            >
              {REGIONS.filter((r) => r.code !== "all").map((r) => (
                <option key={r.code} value={r.code}>{r.name}</option>
              ))}
            </select>
          </div>
        </div>

        {regionA === regionB ? (
          <EmptyState
            icon={<ArrowLeftRight className="w-10 h-10" />}
            title="Select two different regions"
            description="Choose distinct regions to compare their analytics side by side."
          />
        ) : (
          <div className="grid sm:grid-cols-2 gap-6">
            <RegionColumn dimension={dimension} region={regionA} />
            <RegionColumn dimension={dimension} region={regionB} />
          </div>
        )}
      </div>
    </div>
  )
}
