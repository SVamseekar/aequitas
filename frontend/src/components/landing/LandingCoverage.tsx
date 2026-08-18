import { Link } from "react-router"
import { COUNTRY_COVERAGE } from "./data"

export function LandingCoverage() {
  return (
    <section
      id="coverage"
      aria-labelledby="landing-coverage-heading"
      className="border-y border-[var(--l-rule)] bg-[var(--l-surface)]"
    >
      <div className="landing-shell py-14 sm:py-16">
        <div className="flex flex-col sm:flex-row sm:items-end sm:justify-between gap-3 mb-8">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.14em] text-[var(--l-rust)] mb-2">
              Coverage
            </p>
            <h2
              id="landing-coverage-heading"
              className="font-display text-2xl sm:text-3xl text-[var(--l-ink)]"
            >
              Four official stacks
            </h2>
          </div>
          <Link
            to="/briefings"
            className="text-sm font-semibold text-[var(--l-rust)] hover:text-[var(--l-rust-deep)]"
          >
            Read more →
          </Link>
        </div>

        <ul className="grid grid-cols-2 lg:grid-cols-4 gap-3">
          {COUNTRY_COVERAGE.map((c) => (
            <li key={c.code}>
              <Link
                to={c.href}
                className="landing-card block h-full p-4 sm:p-5 hover:border-[var(--l-rust)]/35"
              >
                <h3 className="font-display text-xl text-[var(--l-ink)]">{c.name}</h3>
                <p className="mt-2 text-xs text-[var(--l-slate)] leading-snug">
                  {c.deprivation}
                </p>
                <p className="mt-1 text-xs text-[var(--l-slate)] leading-snug">{c.network}</p>
              </Link>
            </li>
          ))}
        </ul>
      </div>
    </section>
  )
}
