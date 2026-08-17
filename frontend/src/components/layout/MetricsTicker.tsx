import { useQuery } from "@tanstack/react-query"
import { tickerFallbackMetrics } from "@/lib/metricsCanon"
import { tickerForUnknownPack, type TickerChip } from "@/lib/tickerCountry"
import { useFilters, useOps } from "@/api/hooks"

const ENGLAND_FALLBACK: TickerChip[] = [...tickerFallbackMetrics()]

const LIVE_TICKER = new Set(["england", "ireland", "netherlands", "france"])

function useTickerMetrics() {
  const { country, region, urbanRural, pack, mode } = useFilters()
  return useQuery<TickerChip[]>({
    queryKey: ["metrics", "ticker", country, region, urbanRural, pack, mode],
    queryFn: async () => {
      if (!LIVE_TICKER.has(country)) return tickerForUnknownPack(country)
      const qs = new URLSearchParams({ region, urban_rural: urbanRural, country })
      if (pack) qs.set("pack", pack)
      if (country === "netherlands" || country === "france") qs.set("mode", mode)
      const res = await fetch(`/api/metrics/ticker?${qs}`)
      if (res.status === 404 && pack) return tickerForUnknownPack(country)
      if (!res.ok) throw new Error(`ticker ${res.status}`)
      return res.json() as Promise<TickerChip[]>
    },
    staleTime: 30_000,
  })
}

export function MetricsTicker() {
  const { country, pack } = useFilters()
  const { data: metrics, isError } = useTickerMetrics()
  const ops = useOps(country, pack)
  const unknownPack = Boolean(pack) && isError
  const base: TickerChip[] =
    !LIVE_TICKER.has(country)
      ? tickerForUnknownPack(country)
      : unknownPack
        ? tickerForUnknownPack(country)
        : Array.isArray(metrics) && metrics.length > 0
          ? metrics
          : country === "ireland" || country === "netherlands" || country === "france"
            ? [{
                key: "pack",
                label:
                  country === "ireland" ? "Ireland" : country === "netherlands" ? "Netherlands" : "France",
                value: "…",
                sub: "loading filter",
              }]
            : ENGLAND_FALLBACK
  const opsChip: TickerChip | null =
    unknownPack || !ops.data
      ? null
      : ops.data.empty
        ? {
            key: "ops",
            label: "Ops",
            value: "empty",
            sub:
              country === "ireland"
                ? "NTA RT not in rollup"
                : country === "netherlands"
                  ? "OVapi RT empty"
                  : country === "france"
                    ? "NAP RT incomplete"
                    : "BODS RT empty",
          }
        : {
            key: "ops",
            label: "Ops",
            value: ops.data.pct_late == null ? `${ops.data.n_updates}` : `${ops.data.pct_late.toFixed(0)}% late`,
            sub: "rollup snapshot",
          }
  const list = opsChip ? [...base, opsChip] : base
  const doubled = [...list, ...list]

  return (
    <div className="border-b border-white/50 bg-white/20 backdrop-blur-2xl overflow-hidden h-9 flex items-center">
      <div className="flex items-center gap-0 ticker-track" aria-hidden="true">
        {doubled.map((m, i) => (
          <div key={`${m.key}-${i}`} className="flex items-center gap-3 px-5 shrink-0">
            <span className="text-xs text-muted-foreground">{m.label}</span>
            <span className="text-xs font-semibold tabular-nums text-primary">{m.value}</span>
            <span className="text-xs text-muted-foreground/90">{m.sub}</span>
            <span className="text-border text-xs ml-1">·</span>
          </div>
        ))}
      </div>
    </div>
  )
}
