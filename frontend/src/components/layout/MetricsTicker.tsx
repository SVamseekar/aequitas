import { useQuery } from "@tanstack/react-query"
import { tickerFallbackMetrics } from "@/lib/metricsCanon"

interface TickerMetric {
  key: string
  label: string
  value: string
  sub: string
}

const FALLBACK: TickerMetric[] = [...tickerFallbackMetrics()]

function useTickerMetrics() {
  return useQuery<TickerMetric[]>({
    queryKey: ["metrics", "ticker"],
    queryFn: async () => {
      const res = await fetch("/api/metrics/ticker")
      if (!res.ok) return FALLBACK
      return res.json() as Promise<TickerMetric[]>
    },
    staleTime: 60_000,
    initialData: FALLBACK,
  })
}

export function MetricsTicker() {
  const { data: metrics } = useTickerMetrics()
  const doubled = [...metrics, ...metrics]

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
