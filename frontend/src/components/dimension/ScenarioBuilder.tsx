import { useFilters, useScenarioCalculation } from "@/api/hooks"
import { Sliders } from "lucide-react"

function clamp(v: number, min: number, max: number) {
  return Math.min(max, Math.max(min, v))
}

export function ScenarioBuilder() {
  const { region, urbanRural } = useFilters()
  const {
    freqPct,
    lastBusHour,
    drtCoverage,
    franchise,
    populationAffected,
    co2Saving,
    bcr,
    setSettings,
  } = useScenarioCalculation(region, urbanRural)

  const formattedBcr = typeof bcr === "number" ? bcr.toFixed(2) : String(bcr)

  const isRegulatoryOnly = franchise !== "none" && freqPct === 0 && lastBusHour === 19 && drtCoverage === 0

  const metrics = [
    {
      label: "Population affected",
      value: populationAffected.toLocaleString(),
      sub: "estimated people affected",
      isMuted: false,
    },
    {
      label: "CO₂ saving",
      value: isRegulatoryOnly ? "—" : `${co2Saving} kt`,
      sub: isRegulatoryOnly ? "N/A (Regulatory only)" : "annual estimate",
      isMuted: isRegulatoryOnly,
    },
    {
      label: "BCR",
      value: isRegulatoryOnly ? "—" : formattedBcr,
      sub: isRegulatoryOnly ? "N/A (Zero central capital cost)" : "benefit-cost ratio",
      isMuted: isRegulatoryOnly,
    },
  ]


  return (
    <div className="border border-indigo-500/30 rounded bg-card mb-6 overflow-hidden">
      <div className="px-5 py-3 border-b border-border flex items-center gap-2">
        <Sliders className="w-4 h-4 text-indigo-400" />
        <h3 className="text-xs font-mono font-bold uppercase tracking-widest text-foreground">Scenario Builder</h3>
        <span className="text-[11px] text-muted-foreground font-mono ml-2">
          Indicative estimates · not DfT-validated
        </span>
      </div>

      <div className="p-5 grid sm:grid-cols-2 gap-6">
        {/* Sliders */}
        <div className="space-y-5">
          <div>
            <div className="flex justify-between mb-1.5">
              <label className="text-[11px] font-mono uppercase tracking-wide text-muted-foreground">
                Frequency increase
              </label>
              <span className="text-[11px] font-mono text-indigo-400 font-semibold">+{freqPct}%</span>
            </div>
            <input
              type="range"
              min={0} max={50} step={5}
              value={freqPct}
              onChange={(e) => setSettings({ freqPct: clamp(Number(e.target.value), 0, 50) })}
              className="w-full accent-indigo-500"
            />
            <div className="flex justify-between text-[11px] text-muted-foreground/40 font-mono mt-0.5">
              <span>0%</span><span>50%</span>
            </div>
          </div>

          <div>
            <div className="flex justify-between mb-1.5">
              <label className="text-[11px] font-mono uppercase tracking-wide text-muted-foreground">
                Last bus extension
              </label>
              <span className="text-[11px] font-mono text-indigo-400 font-semibold">to {lastBusHour}:00</span>
            </div>
            <input
              type="range"
              min={19} max={23} step={1}
              value={lastBusHour}
              onChange={(e) => setSettings({ lastBusHour: clamp(Number(e.target.value), 19, 23) })}
              className="w-full accent-indigo-500"
            />
            <div className="flex justify-between text-[11px] text-muted-foreground/40 font-mono mt-0.5">
              <span>19:00</span><span>23:00</span>
            </div>
          </div>

          <div>
            <div className="flex justify-between mb-1.5">
              <label className="text-[11px] font-mono uppercase tracking-wide text-muted-foreground">
                DRT rural coverage
              </label>
              <span className="text-[11px] font-mono text-indigo-400 font-semibold">{drtCoverage}%</span>
            </div>
            <input
              type="range"
              min={0} max={100} step={5}
              value={drtCoverage}
              onChange={(e) => setSettings({ drtCoverage: clamp(Number(e.target.value), 0, 100) })}
              className="w-full accent-indigo-500"
            />
            <div className="flex justify-between text-[11px] text-muted-foreground/40 font-mono mt-0.5">
              <span>0%</span><span>100%</span>
            </div>
          </div>

          <div>
            <label className="text-[11px] font-mono uppercase tracking-wide text-muted-foreground block mb-1.5">
              Franchise scope
            </label>
            <div className="flex gap-2">
              {(["none", "partial", "full"] as const).map((opt) => (
                <button
                  key={opt}
                  type="button"
                  onClick={() => setSettings({ franchise: opt })}
                  className={`px-3 py-1.5 text-[11px] font-mono uppercase rounded border transition-colors ${
                    franchise === opt
                      ? "bg-indigo-600 border-indigo-600 text-white"
                      : "border-border text-muted-foreground hover:border-indigo-500/40 hover:text-foreground"
                  }`}
                >
                  {opt}
                </button>
              ))}
            </div>
          </div>
        </div>

        {/* Impact estimates */}
        <div className="space-y-3">
          <p className="text-[11px] font-mono uppercase tracking-wide text-muted-foreground mb-3">
            Estimated impact
          </p>
          {metrics.map((m) => (
            <div
              key={m.label}
              className={`border border-border rounded p-3 transition-opacity ${
                m.isMuted ? "bg-muted/10 opacity-60 select-none" : "bg-background"
              }`}
            >
              <p className="text-[11px] font-mono uppercase tracking-wide text-muted-foreground/60">{m.label}</p>
              <p className={`text-lg font-mono font-bold mt-0.5 ${m.isMuted ? "text-muted-foreground/40" : "text-indigo-400"}`}>
                {m.value}
              </p>
              <p className="text-[11px] text-muted-foreground/40 leading-snug">{m.sub}</p>
            </div>
          ))}
          <p className="text-[11px] text-muted-foreground/40 leading-relaxed mt-2">
            Coefficients derived from DfT elasticity-based scenario analysis (Phase 0). BCR uses
            TAG v2.03fc methodology. These are indicative estimates only.
          </p>
        </div>
      </div>
    </div>
  )
}
