import { useState } from "react"
import { Sliders } from "lucide-react"

// Pre-computed impact coefficients from Phase 0 scenario analysis
// These are estimated marginal effects per unit change, not per-LSOA exact
const COEFFICIENTS = {
  freq_pct: { lsoas_affected: 0.42, co2_saving_kt: 0.18, bcr: 1.8 },
  last_bus_min: { lsoas_affected: 0.31, co2_saving_kt: 0.09, bcr: 1.4 },
  drt_coverage_pct: { lsoas_affected: 0.15, co2_saving_kt: 0.04, bcr: 1.1 },
}

const FRANCHISE_MULTIPLIERS: Record<string, number> = {
  none: 1.0,
  partial: 1.3,
  full: 1.7,
}

function clamp(v: number, min: number, max: number) {
  return Math.min(max, Math.max(min, v))
}

export function ScenarioBuilder() {
  const [freqPct, setFreqPct] = useState(10)
  const [lastBusHour, setLastBusHour] = useState(22)
  const [drtCoverage, setDrtCoverage] = useState(0)
  const [franchise, setFranchise] = useState<"none" | "partial" | "full">("none")

  const lastBusMin = (lastBusHour - 19) * 60
  const multiplier = FRANCHISE_MULTIPLIERS[franchise]

  const lsoasAffected = Math.round(
    (freqPct * COEFFICIENTS.freq_pct.lsoas_affected +
      lastBusMin * COEFFICIENTS.last_bus_min.lsoas_affected +
      drtCoverage * COEFFICIENTS.drt_coverage_pct.lsoas_affected) *
      multiplier *
      100
  )
  const co2Saving = (
    (freqPct * COEFFICIENTS.freq_pct.co2_saving_kt +
      lastBusMin * COEFFICIENTS.last_bus_min.co2_saving_kt +
      drtCoverage * COEFFICIENTS.drt_coverage_pct.co2_saving_kt) *
    multiplier
  ).toFixed(1)
  const bcr = (
    (COEFFICIENTS.freq_pct.bcr * (freqPct / 10) +
      COEFFICIENTS.last_bus_min.bcr * (lastBusMin / 60) +
      COEFFICIENTS.drt_coverage_pct.bcr * (drtCoverage / 20)) /
    3 *
    multiplier
  ).toFixed(2)

  return (
    <div className="border border-indigo-500/30 rounded bg-card mb-6 overflow-hidden">
      <div className="px-5 py-3 border-b border-border flex items-center gap-2">
        <Sliders className="w-4 h-4 text-indigo-400" />
        <h3 className="text-xs font-mono font-bold uppercase tracking-widest text-foreground">Scenario Builder</h3>
        <span className="text-[9px] text-muted-foreground/50 font-mono ml-2">
          Indicative estimates · not DfT-validated
        </span>
      </div>

      <div className="p-5 grid sm:grid-cols-2 gap-6">
        {/* Sliders */}
        <div className="space-y-5">
          <div>
            <div className="flex justify-between mb-1.5">
              <label className="text-[10px] font-mono uppercase tracking-wider text-muted-foreground">
                Frequency increase
              </label>
              <span className="text-[11px] font-mono text-indigo-400 font-semibold">+{freqPct}%</span>
            </div>
            <input
              type="range"
              min={0} max={50} step={5}
              value={freqPct}
              onChange={(e) => setFreqPct(clamp(Number(e.target.value), 0, 50))}
              className="w-full accent-indigo-500"
            />
            <div className="flex justify-between text-[9px] text-muted-foreground/40 font-mono mt-0.5">
              <span>0%</span><span>50%</span>
            </div>
          </div>

          <div>
            <div className="flex justify-between mb-1.5">
              <label className="text-[10px] font-mono uppercase tracking-wider text-muted-foreground">
                Last bus extension
              </label>
              <span className="text-[11px] font-mono text-indigo-400 font-semibold">to {lastBusHour}:00</span>
            </div>
            <input
              type="range"
              min={19} max={23} step={1}
              value={lastBusHour}
              onChange={(e) => setLastBusHour(clamp(Number(e.target.value), 19, 23))}
              className="w-full accent-indigo-500"
            />
            <div className="flex justify-between text-[9px] text-muted-foreground/40 font-mono mt-0.5">
              <span>19:00</span><span>23:00</span>
            </div>
          </div>

          <div>
            <div className="flex justify-between mb-1.5">
              <label className="text-[10px] font-mono uppercase tracking-wider text-muted-foreground">
                DRT rural coverage
              </label>
              <span className="text-[11px] font-mono text-indigo-400 font-semibold">{drtCoverage}%</span>
            </div>
            <input
              type="range"
              min={0} max={100} step={5}
              value={drtCoverage}
              onChange={(e) => setDrtCoverage(clamp(Number(e.target.value), 0, 100))}
              className="w-full accent-indigo-500"
            />
            <div className="flex justify-between text-[9px] text-muted-foreground/40 font-mono mt-0.5">
              <span>0%</span><span>100%</span>
            </div>
          </div>

          <div>
            <label className="text-[10px] font-mono uppercase tracking-wider text-muted-foreground block mb-1.5">
              Franchise scope
            </label>
            <div className="flex gap-2">
              {(["none", "partial", "full"] as const).map((opt) => (
                <button
                  key={opt}
                  type="button"
                  onClick={() => setFranchise(opt)}
                  className={`px-3 py-1.5 text-[10px] font-mono uppercase rounded border transition-colors ${
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
          <p className="text-[10px] font-mono uppercase tracking-wider text-muted-foreground mb-3">
            Estimated impact
          </p>
          {[
            { label: "LSOAs affected", value: lsoasAffected.toLocaleString(), sub: "out of 33,755" },
            { label: "CO₂ saving", value: `${co2Saving} kt`, sub: "annual estimate" },
            { label: "BCR", value: bcr, sub: "benefit-cost ratio" },
          ].map((m) => (
            <div key={m.label} className="border border-border rounded bg-background p-3">
              <p className="text-[9px] font-mono uppercase tracking-wider text-muted-foreground/60">{m.label}</p>
              <p className="text-lg font-mono font-bold text-indigo-400 mt-0.5">{m.value}</p>
              <p className="text-[9px] text-muted-foreground/40">{m.sub}</p>
            </div>
          ))}
          <p className="text-[9px] text-muted-foreground/30 leading-relaxed mt-2">
            Coefficients derived from DfT elasticity-based scenario analysis (Phase 0). BCR uses
            TAG v2.03fc methodology. These are indicative estimates only.
          </p>
        </div>
      </div>
    </div>
  )
}
