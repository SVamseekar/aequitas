/** Product frame: three live packs, one method. Numbers are last measured warehouse scores. */
const PACKS = [
  { name: "England", score: "80.0", unit: "IMD × BODS", href: "LSOA" },
  { name: "Ireland", score: "55.5", unit: "HP × TFI", href: "Small Areas" },
  { name: "Netherlands", score: "69.6", unit: "SES × OVapi bus", href: "Buurten" },
  { name: "France", score: "47.7", unit: "F-EDI 2021 × NAP", href: "IRIS" },
] as const

export function LandingHeroVisual() {
  return (
    <div className="landing-glass-strong overflow-hidden">
      <div className="flex items-center justify-between gap-3 px-3.5 py-2.5 border-b border-white/40 bg-white/25">
        <div className="flex items-center gap-1.5" aria-hidden>
          <span className="h-2 w-2 rounded-full bg-[#e8b4a0] shadow-sm" />
          <span className="h-2 w-2 rounded-full bg-[#edd9a3] shadow-sm" />
          <span className="h-2 w-2 rounded-full bg-[#c5d4b8] shadow-sm" />
        </div>
        <p className="text-[11px] font-medium text-[var(--l-slate)] truncate">In-country score · live packs</p>
        <span className="landing-chip rounded-full px-2 py-0.5 text-[10px] text-[var(--l-slate)] shrink-0">
          0–100
        </span>
      </div>

      <div className="p-3 sm:p-4 flex flex-col gap-2.5">
        {PACKS.map((p) => (
          <div key={p.name} className="landing-glass rounded-xl px-3.5 py-3 flex items-end justify-between gap-3">
            <div>
              <p className="text-[10px] font-semibold uppercase tracking-wide text-[var(--l-slate)]">{p.name}</p>
              <p className="text-[11px] text-[var(--l-slate)] mt-0.5">{p.unit}</p>
            </div>
            <div className="text-right">
              <p className="font-display text-3xl text-[var(--l-ink)] tabular-nums leading-none">{p.score}</p>
              <p className="text-[10px] text-[var(--l-slate)] mt-1">{p.href}</p>
            </div>
          </div>
        ))}
      </div>

      <div className="border-t border-white/35 bg-white/20 px-3.5 py-2.5 text-[11px] text-[var(--l-slate)]">
        France briefing live. Chat and 15/30/45 stay honest-empty.
      </div>
    </div>
  )
}
