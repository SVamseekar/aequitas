import { useQuery } from "@tanstack/react-query"
import { tickerFallbackMetrics } from "@/lib/metricsCanon"
import { tickerForUnknownPack, type TickerChip } from "@/lib/tickerCountry"
import { useFilters } from "@/api/hooks"

const ENGLAND_FALLBACK: TickerChip[] = [...tickerFallbackMetrics()]

const LIVE_TICKER = new Set(["england", "ireland", "netherlands"])

function useTickerMetrics() {
  const { country, region, urbanRural, pack, mode } = useFilters()
  return useQuery<TickerChip[]>({
    queryKey: ["metrics", "ticker", country, region, urbanRural, pack, mode],
    queryFn: async () => {
      if (!LIVE_TICKER.has(country)) return tickerForUnknownPack(country)
      const qs = new URLSearchParams({ region, urban_rural: urbanRural, country })
      if (pack) qs.set("pack", pack)
      if (country === "netherlands") qs.set("mode", mode)
      const res = await fetch(`/api/metrics/ticker?${qs}`)
      if (!res.ok) return tickerForUnknownPack(country)
      return res.json() as Promise<TickerChip[]>
    },
    staleTime: 30_000,
  })
}

export function MetricsTicker() {
  const { country, pack } = useFilters()
  const { data: metrics, isError } = useTickerMetrics()
  const unknownPack = Boolean(pack) && (isError || !metrics)
  const list: TickerChip[] =
    !LIVE_TICKER.has(country)
      ? tickerForUnknownPack(country)
      : unknownPack
        ? tickerForUnknownPack(country)
        : Array.isArray(metrics) && metrics.length > 0
          ? metrics
          : country === "ireland" || country === "netherlands"
            ? [{ key: "pack", label: country === "ireland" ? "Ireland" : "Netherlands", value: "…", sub: "loading filter" }]
            : ENGLAND_FALLBACK
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
