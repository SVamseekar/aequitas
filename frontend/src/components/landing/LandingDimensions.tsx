import { useNavigate } from "react-router"
import { ArrowUpRight } from "lucide-react"
import { DIMENSIONS } from "./data"

export function LandingDimensions() {
  const navigate = useNavigate()

  return (
    <section id="dimensions" aria-labelledby="landing-dimensions-heading" className="bg-[var(--l-paper)]">
      <div className="landing-shell py-12 sm:py-14 lg:py-16">
        <div className="flex flex-col lg:flex-row lg:items-end lg:justify-between gap-4 mb-8">
          <div className="max-w-xl">
            <p className="text-xs font-semibold uppercase tracking-[0.14em] text-[var(--l-rust)] mb-3">
              8 policy dimensions
            </p>
            <h2
              id="landing-dimensions-heading"
              className="font-display text-3xl sm:text-4xl leading-[1.12] text-[var(--l-ink)]"
            >
              The full policy lifecycle — equity to scenarios.
            </h2>
          </div>
          <p className="text-base text-[var(--l-slate)] leading-relaxed max-w-sm lg:text-right">
            Each dimension opens into pre-computed sections with charts, maps, and narrative.
          </p>
        </div>

        <ul className="grid sm:grid-cols-2 gap-3">
          {DIMENSIONS.map((dimension, index) => (
            <li key={dimension.title}>
              <button
                type="button"
                onClick={() => navigate(`/app/england${dimension.route}`)}
                className="landing-card group w-full text-left p-4 sm:p-5 flex gap-3.5 items-start focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--l-rust)]"
              >
                <span className="font-display text-2xl text-[var(--l-rust)]/45 tabular-nums w-8 shrink-0">
                  {String(index + 1).padStart(2, "0")}
                </span>
                <div className="min-w-0 flex-1">
                  <div className="flex items-start justify-between gap-2">
                    <h3 className="text-base font-semibold text-[var(--l-ink)] group-hover:text-[var(--l-rust)] transition-colors">
                      {dimension.title}
                    </h3>
                    <ArrowUpRight
                      className="w-4 h-4 text-[var(--l-slate)] opacity-40 group-hover:opacity-100 shrink-0 mt-0.5 transition-opacity"
                      aria-hidden
                    />
                  </div>
                  <p className="text-sm text-[var(--l-slate)] leading-relaxed mt-1.5">
                    {dimension.question}
                  </p>
                  <p className="text-xs text-[var(--l-slate)] mt-3 pt-3 border-t border-[var(--l-rule)]">
                    {dimension.grounded}
                  </p>
                </div>
              </button>
            </li>
          ))}
        </ul>
      </div>
    </section>
  )
}
