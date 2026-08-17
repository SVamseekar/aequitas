import { DATA_SOURCES } from "./data"

export function LandingDataSources() {
  const loop = [...DATA_SOURCES, ...DATA_SOURCES]

  return (
    <section
      aria-label="Data sources"
      className="relative border-y border-white/40 py-5 overflow-hidden bg-white/20 backdrop-blur-xl"
    >
      <p className="text-center text-[11px] font-semibold uppercase tracking-[0.14em] text-[var(--l-slate)] mb-3 px-4">
        Official files only — BODS, TFI, OVapi, NAP, IMD, HP, SES-WOA, F-EDI
      </p>
      <div className="relative">
        <div
          className="pointer-events-none absolute inset-y-0 left-0 w-16 sm:w-28 z-10 bg-gradient-to-r from-[var(--l-paper)] to-transparent"
          aria-hidden
        />
        <div
          className="pointer-events-none absolute inset-y-0 right-0 w-16 sm:w-28 z-10 bg-gradient-to-l from-[var(--l-paper)] to-transparent"
          aria-hidden
        />
        <div className="landing-marquee-track gap-2.5 px-3">
          {loop.map((source, i) => (
            <span
              key={`${source}-${i}`}
              className="landing-chip inline-flex rounded-full px-3.5 py-1.5 text-sm text-[var(--l-ink)] whitespace-nowrap"
            >
              {source}
            </span>
          ))}
        </div>
      </div>
    </section>
  )
}
