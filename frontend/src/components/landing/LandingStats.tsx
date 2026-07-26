import { HEADLINE_STATS, SCALE_STATS } from "./data"
import { METRICS_CANON } from "@/lib/metricsCanon"
import { LandingEquityViz } from "./LandingEquityViz"

export function LandingStats() {
  // Skip Gini (shown in viz); show the other three headline stats once
  const sideStats = HEADLINE_STATS.slice(1)

  return (
    <section id="proof" aria-labelledby="landing-stats-heading" className="relative">
      <div className="landing-shell py-12 sm:py-14 lg:py-16">
        <div className="grid lg:grid-cols-2 gap-6 lg:gap-10 mb-8 lg:mb-10">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.14em] text-[var(--l-rust)] mb-3">
              The evidence already exists
            </p>
            <h2
              id="landing-stats-heading"
              className="font-display text-3xl sm:text-4xl lg:text-[2.75rem] leading-[1.12] text-[var(--l-ink)] max-w-md"
            >
              A full England warehouse — not a demo spreadsheet.
            </h2>
          </div>
          <p className="text-lg text-[var(--l-slate)] leading-relaxed max-w-xl lg:pt-8">
            Stops, timetables, deprivation, and route geometry joined once offline. The product is a
            lookup layer over audited analytics across {METRICS_CANON.lsoas.toLocaleString("en-GB")}{" "}
            LSOAs.
          </p>
        </div>

        <div className="grid lg:grid-cols-12 gap-4 lg:gap-5">
          <div className="lg:col-span-7">
            <LandingEquityViz />
          </div>
          <div className="lg:col-span-5 grid gap-4">
            {sideStats.map((stat) => (
              <div key={stat.label} className="landing-card p-6 sm:p-7">
                <p className="text-sm text-[var(--l-slate)]">{stat.label}</p>
                <p className="font-display text-3xl sm:text-4xl text-[var(--l-ink)] mt-2 tabular-nums">
                  {stat.value}
                </p>
                <p className="text-sm text-[var(--l-slate)] mt-2">{stat.sub}</p>
              </div>
            ))}
          </div>
        </div>

        <ul className="mt-4 grid grid-cols-2 lg:grid-cols-4 gap-3">
          {SCALE_STATS.map((stat) => (
            <li
              key={stat.label}
              className="landing-glass rounded-2xl px-4 py-4 sm:px-5 sm:py-5"
            >
              <p className="text-[11px] uppercase tracking-wide text-[var(--l-slate)]">{stat.label}</p>
              <p className="font-display text-2xl text-[var(--l-ink)] mt-1 tabular-nums">{stat.value}</p>
              <p className="text-xs text-[var(--l-slate)] mt-1">{stat.sub}</p>
            </li>
          ))}
        </ul>
      </div>
    </section>
  )
}
