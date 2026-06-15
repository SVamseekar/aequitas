import { HEADLINE_STATS } from "./data"

export function LandingStats() {
  return (
    <section aria-labelledby="landing-stats-heading" className="border-y border-border bg-card/20">
      <div className="max-w-7xl mx-auto px-6 py-12">
        <h2
          id="landing-stats-heading"
          className="text-[11px] font-mono uppercase tracking-[0.25em] text-indigo-400 font-bold mb-6"
        >
          What the data already shows
        </h2>
        <dl className="grid grid-cols-2 lg:grid-cols-4 gap-px bg-border overflow-hidden rounded-lg border border-border">
          {HEADLINE_STATS.map((stat) => (
            <div
              key={stat.label}
              className="bg-background p-6 hover:bg-card/40 transition-colors duration-300"
            >
              <dt className="text-[11px] font-mono uppercase tracking-[0.2em] text-muted-foreground mb-1">
                {stat.label}
              </dt>
              <dd className="text-3xl font-extrabold font-mono tracking-tight text-indigo-400">
                {stat.value}
              </dd>
              <dd className="text-xs text-muted-foreground mt-1">{stat.sub}</dd>
            </div>
          ))}
        </dl>
        <p className="text-[11px] font-mono text-muted-foreground mt-4">
          Built on national open data — stop locations, timetables, census deprivation indices,
          and route geometry across 33,755 LSOAs.
        </p>
      </div>
    </section>
  )
}