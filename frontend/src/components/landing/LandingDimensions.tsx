import { Link } from "react-router"
import { ArrowUpRight } from "lucide-react"
import { DIMENSIONS, type DimensionCard } from "./data"

const GROUPS: ReadonlyArray<{
  id: string
  label: string
  hint: string
  match: (d: DimensionCard) => boolean
}> = [
  {
    id: "measure",
    label: "Measure",
    hint: "Need, coverage, service, operators",
    match: (d) =>
      ["/equity", "/access", "/service", "/network"].includes(d.route),
  },
  {
    id: "interpret",
    label: "Interpret",
    hint: "Correlations, cost, statute, scenarios",
    match: (d) =>
      ["/correlations", "/economy", "/policy", "/scenarios"].includes(d.route),
  },
  {
    id: "observe",
    label: "Observe",
    hint: "Dated packs, reach, last official RT",
    match: (d) => ["/time", "/reach", "/ops"].includes(d.route),
  },
]

export function LandingDimensions({ embed = false }: { embed?: boolean }) {
  return (
    <section
      id={embed ? undefined : "dimensions"}
      aria-labelledby="landing-dimensions-heading"
      className={embed ? undefined : "bg-[var(--l-paper)]"}
    >
      <div className={embed ? "py-4" : "landing-shell py-12 sm:py-14 lg:py-16"}>
        <header className={embed ? "sr-only" : "mb-8 max-w-2xl"}>
          <p className="text-xs font-semibold uppercase tracking-[0.14em] text-[var(--l-rust)] mb-3">
            The briefing
          </p>
          <h2
            id="landing-dimensions-heading"
            className="font-display text-3xl sm:text-4xl leading-[1.12] text-[var(--l-ink)] text-balance"
          >
            Same questions in every country
          </h2>
          <p className="mt-3 text-sm text-[var(--l-slate)] text-pretty max-w-xl">
            Statute titles change. The doors do not.
          </p>
        </header>

        <div className="briefing-board">
          <div className="briefing-cols">
            {GROUPS.map((group) => {
              const items = DIMENSIONS.filter(group.match)
              return (
                <section
                  key={group.id}
                  className="briefing-col"
                  aria-labelledby={`briefing-${group.id}`}
                >
                  <header className="briefing-col-head">
                    <h3 id={`briefing-${group.id}`} className="briefing-col-kicker">
                      {group.label}
                    </h3>
                    <p className="briefing-col-hint">{group.hint}</p>
                  </header>
                  <ul>
                    {items.map((dimension) => {
                      const Icon = dimension.icon
                      return (
                        <li key={dimension.route}>
                          <Link
                            to={dimension.route}
                            className="briefing-row"
                          >
                            <span className="briefing-ico" aria-hidden>
                              <Icon className="w-3.5 h-3.5" strokeWidth={1.75} />
                            </span>
                            <span>
                              <span className="briefing-row-title">{dimension.title}</span>
                              <p className="briefing-row-q">{dimension.question}</p>
                              <p className="briefing-row-meta">{dimension.grounded}</p>
                            </span>
                            <ArrowUpRight
                              className="briefing-chevron w-4 h-4 shrink-0"
                              aria-hidden
                            />
                          </Link>
                        </li>
                      )
                    })}
                  </ul>
                </section>
              )
            })}
          </div>
        </div>
      </div>
    </section>
  )
}
