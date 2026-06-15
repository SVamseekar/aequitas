import { useQuery } from "@tanstack/react-query"

interface TickerMetric {
  key: string
  label: string
  value: string
  sub: string
}

const FALLBACK: TickerMetric[] = [
  { key: "gini", label: "Gini Coefficient", value: "0.5741", sub: "bus service inequality" },
  { key: "palma", label: "Palma Ratio", value: "5.702×", sub: "top 10% vs bottom 40%" },
  { key: "concentration_index", label: "Concentration Index", value: "+0.1358", sub: "pro-rich bias" },
  { key: "evening_isolated", label: "Evening Isolated", value: "15.4%", sub: "5,189 LSOAs" },
  { key: "sunday_deserts", label: "Sunday Deserts", value: "20.0%", sub: "6,745 LSOAs" },
  { key: "mean_sqi", label: "Mean SQI", value: "65.4", sub: "out of 100" },
]

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
  // Double the list so the CSS scroll loop is seamless
  const doubled = [...metrics, ...metrics]

  return (
    <div className="border-b border-border bg-card/20 overflow-hidden h-8 flex items-center">
      <div className="flex items-center gap-0 ticker-track" aria-hidden="true">
        {doubled.map((m, i) => (
          <div key={`${m.key}-${i}`} className="flex items-center gap-4 px-6 shrink-0">
            <span className="text-[11px] font-mono text-muted-foreground uppercase tracking-wide">{m.label}</span>
            <span className="text-[11px] font-mono font-semibold text-indigo-400">{m.value}</span>
            <span className="text-[11px] text-muted-foreground/40">{m.sub}</span>
            <span className="text-border text-[11px] ml-2">·</span>
          </div>
        ))}
      </div>
    </div>
  )
}
