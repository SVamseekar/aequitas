import {
  METRICS_CANON,
  formatGini,
  formatPalma,
  formatConcentrationIndex,
} from "@/lib/metricsCanon"

/** Brand-matched glass product frame — real metrics, frosted UI. */
export function LandingHeroVisual() {
  const m = METRICS_CANON

  const cells = [
    0.15, 0.4, 0.55, 0.7, 0.85, 0.95, 0.3, 0.5, 0.65, 0.8, 0.2, 0.45, 0.6, 0.75, 0.9, 0.35, 0.55,
    0.7, 0.25, 0.5, 0.8, 0.4, 0.65, 0.9, 0.2, 0.45, 0.7, 0.55, 0.85, 0.3, 0.6, 0.75, 0.5, 0.95,
    0.35, 0.65,
  ]

  const cellColor = (t: number) => {
    if (t < 0.25) return "#efe8dc"
    if (t < 0.4) return "#e4c4a8"
    if (t < 0.55) return "#d49a6a"
    if (t < 0.7) return "#c45c26"
    if (t < 0.85) return "#9a4318"
    return "#5c2a12"
  }

  const kpis = [
    { label: "Gini", value: formatGini(m.gini), hint: "Service inequality" },
    { label: "Palma", value: formatPalma(m.palma), hint: "Top 10% / bottom 40%" },
    {
      label: "Evening",
      value: `${m.eveningIsolatedPct.toFixed(1)}%`,
      hint: "LSOAs isolated",
    },
  ]

  return (
    <div className="landing-glass-strong overflow-hidden">
      {/* Window chrome */}
      <div className="flex items-center justify-between gap-3 px-3.5 py-2.5 border-b border-white/40 bg-white/25">
        <div className="flex items-center gap-1.5">
          <span className="h-2 w-2 rounded-full bg-[#e8b4a0] shadow-sm" aria-hidden />
          <span className="h-2 w-2 rounded-full bg-[#edd9a3] shadow-sm" aria-hidden />
          <span className="h-2 w-2 rounded-full bg-[#c5d4b8] shadow-sm" aria-hidden />
        </div>
        <p className="text-[11px] font-medium text-[var(--l-slate)] truncate">
          Equity &amp; Deprivation · All England
        </p>
        <span className="landing-chip rounded-full px-2 py-0.5 text-[10px] text-[var(--l-slate)] tabular-nums shrink-0">
          {m.sections} sections
        </span>
      </div>

      <div className="p-3 sm:p-4 grid sm:grid-cols-[1.15fr_0.85fr] gap-3">
        <div className="landing-glass rounded-xl p-3 min-h-[200px] flex flex-col">
          <div className="flex items-center justify-between mb-2.5">
            <p className="text-[10px] font-semibold uppercase tracking-wide text-[var(--l-slate)]">
              Bus service intensity
            </p>
            <p className="text-[10px] text-[var(--l-slate)]">LSOA choropleth</p>
          </div>
          <div className="grid grid-cols-6 gap-1 flex-1 content-center" aria-hidden>
            {cells.map((t, i) => (
              <div
                key={i}
                className="aspect-square rounded-[3px] shadow-[inset_0_0_0_1px_rgb(20_19_17_/_0.04)]"
                style={{ backgroundColor: cellColor(t) }}
              />
            ))}
          </div>
          <div className="mt-2.5 flex items-center justify-between text-[10px] text-[var(--l-slate)]">
            <span>Low service</span>
            <span className="flex-1 mx-2 h-px bg-gradient-to-r from-[#efe8dc] via-[#c45c26] to-[#5c2a12] opacity-80" />
            <span>High service</span>
          </div>
        </div>

        <div className="flex flex-col gap-2.5">
          {kpis.map((k) => (
            <div key={k.label} className="landing-glass rounded-xl px-3.5 py-3">
              <p className="text-[10px] font-semibold uppercase tracking-wide text-[var(--l-slate)]">
                {k.label}
              </p>
              <p className="font-display text-2xl text-[var(--l-ink)] tabular-nums mt-0.5 leading-none">
                {k.value}
              </p>
              <p className="text-[11px] text-[var(--l-slate)] mt-1">{k.hint}</p>
            </div>
          ))}
        </div>
      </div>

      <div className="border-t border-white/35 bg-white/20 px-3.5 py-2.5 flex flex-wrap gap-x-4 gap-y-1 text-[11px] text-[var(--l-slate)] backdrop-blur-md">
        <span>
          <strong className="text-[var(--l-ink)] font-semibold tabular-nums">
            {formatConcentrationIndex(m.concentrationIndex)}
          </strong>{" "}
          concentration
        </span>
        <span>
          <strong className="text-[var(--l-ink)] font-semibold tabular-nums">
            {m.sundayDesertPct.toFixed(1)}%
          </strong>{" "}
          Sunday deserts
        </span>
        <span>
          <strong className="text-[var(--l-ink)] font-semibold tabular-nums">
            {m.lsoas.toLocaleString("en-GB")}
          </strong>{" "}
          LSOAs
        </span>
      </div>
    </div>
  )
}
