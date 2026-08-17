import { Link } from "react-router"
import { ArrowUpRight } from "lucide-react"
import { COUNTRY_COVERAGE } from "./data"

export function LandingCoverage() {
  return (
    <section id="coverage" aria-labelledby="landing-coverage-heading" className="bg-[var(--l-paper)]">
      <div className="landing-shell py-12 sm:py-14 lg:py-16">
        <div className="flex flex-col lg:flex-row lg:items-end lg:justify-between gap-4 mb-8">
          <div className="max-w-xl">
            <p className="text-xs font-semibold uppercase tracking-[0.14em] text-[var(--l-rust)] mb-3">
              Coverage
            </p>
            <h2
              id="landing-coverage-heading"
              className="font-display text-3xl sm:text-4xl leading-[1.12] text-[var(--l-ink)]"
            >
              Same doors. Local evidence. In-country ranks.
            </h2>
          </div>
          <p className="text-base text-[var(--l-slate)] leading-relaxed max-w-sm lg:text-right">
            IMD, Pobal HP, SES-WOA, and F-EDI are never plotted on one axis. France briefing and
            chat are live; 15/30/45 stay honest-empty.
          </p>
        </div>

        <ul className="grid sm:grid-cols-2 gap-3">
          {COUNTRY_COVERAGE.map((c) => {
            const live = c.status === "live"
            return (
              <li key={c.code}>
                <Link
                  to={c.href}
                  className="landing-card group flex h-full flex-col p-5 sm:p-6 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--l-rust)]"
                >
                  <div className="flex items-start justify-between gap-3">
                    <h3 className="font-display text-2xl text-[var(--l-ink)] group-hover:text-[var(--l-rust)] transition-colors">
                      {c.name}
                    </h3>
                    <span
                      className={
                        live
                          ? "rounded-full bg-[var(--l-rust)]/10 px-2.5 py-0.5 text-[11px] font-semibold uppercase tracking-wide text-[var(--l-rust)]"
                          : "rounded-full border border-[var(--l-rule)] px-2.5 py-0.5 text-[11px] font-semibold uppercase tracking-wide text-[var(--l-slate)]"
                      }
                    >
                      {live ? "Live" : "Pack not built"}
                    </span>
                  </div>
                  <dl className="mt-4 grid gap-2 text-sm">
                    <div className="flex justify-between gap-4">
                      <dt className="text-[var(--l-slate)]">Network</dt>
                      <dd className="text-right text-[var(--l-ink)]">{c.network}</dd>
                    </div>
                    <div className="flex justify-between gap-4">
                      <dt className="text-[var(--l-slate)]">Deprivation</dt>
                      <dd className="text-right text-[var(--l-ink)]">{c.deprivation}</dd>
                    </div>
                    <div className="flex justify-between gap-4">
                      <dt className="text-[var(--l-slate)]">Geography</dt>
                      <dd className="text-right text-[var(--l-ink)]">{c.geography}</dd>
                    </div>
                  </dl>
                  <p className="mt-4 flex items-center justify-between gap-2 border-t border-[var(--l-rule)] pt-3 text-sm text-[var(--l-slate)]">
                    <span>{c.note}</span>
                    <ArrowUpRight className="h-4 w-4 shrink-0 opacity-40 group-hover:opacity-100" aria-hidden />
                  </p>
                </Link>
              </li>
            )
          })}
        </ul>
      </div>
    </section>
  )
}
