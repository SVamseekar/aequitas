import { DATA_SOURCES } from "./data"

export function LandingDataSources() {
  return (
    <section
      aria-labelledby="landing-sources-heading"
      className="border-y border-border bg-card/10"
    >
      <div className="max-w-7xl mx-auto px-6 py-10">
        <h2
          id="landing-sources-heading"
          className="text-[11px] font-mono uppercase tracking-[0.25em] text-muted-foreground font-bold mb-5 text-center"
        >
          Grounded in official UK open data
        </h2>
        <ul className="flex flex-wrap items-center justify-center gap-x-6 gap-y-3">
          {DATA_SOURCES.map((source) => (
            <li
              key={source}
              className="text-xs font-mono text-muted-foreground uppercase tracking-wider"
            >
              {source}
            </li>
          ))}
        </ul>
      </div>
    </section>
  )
}