import { Link, useNavigate } from "react-router"
import { ArrowRight, ArrowUpRight } from "lucide-react"
import { METRICS_CANON, formatGini } from "@/lib/metricsCanon"
import { LandingHeroVisual } from "./LandingHeroVisual"

export function LandingHero() {
  const navigate = useNavigate()

  return (
    <section
      aria-labelledby="landing-hero-heading"
      className="relative border-b border-[var(--l-rule)]"
      style={{
        background:
          "radial-gradient(800px 420px at 90% 0%, rgb(184 78 31 / 0.08), transparent 55%), var(--l-paper)",
      }}
    >
      <div className="landing-shell py-12 sm:py-14 lg:py-16">
        <div className="grid lg:grid-cols-2 gap-8 lg:gap-10 items-center">
          <div className="min-w-0">
            <p className="landing-chip inline-flex items-center gap-2 rounded-full px-3 py-1.5 text-xs font-medium text-[var(--l-slate)] mb-5">
              <span className="h-1.5 w-1.5 rounded-full bg-[var(--l-rust)] shadow-[0_0_0_3px_rgb(184_78_31_/_0.15)]" aria-hidden />
              England · Ireland · Netherlands · France · £0 stack
            </p>

            <h1
              id="landing-hero-heading"
              className="font-display text-4xl sm:text-5xl lg:text-[3.35rem] leading-[1.08] text-[var(--l-ink)]"
            >
              See where the bus{" "}
              <span className="text-[var(--l-rust)]">fails people</span>
              <span className="text-[var(--l-slate)]"> — in England, Ireland, the Netherlands, and France.</span>
            </h1>

            <p className="mt-5 text-lg text-[var(--l-slate)] leading-relaxed max-w-xl">
              Open timetables joined to official deprivation at small-area level. Same method, four
              countries. No licence fee. Deprivation ranks stay inside each country.
            </p>

            <div className="mt-7 flex flex-wrap items-center gap-3">
              <button
                type="button"
                onClick={() => navigate("/app/england")}
                className="landing-btn-primary"
              >
                Explore England
                <ArrowRight className="w-4 h-4" aria-hidden />
              </button>
              <button
                type="button"
                onClick={() => navigate("/app/ireland")}
                className="landing-btn-secondary"
                data-testid="landing-ireland"
              >
                Explore Ireland
                <ArrowUpRight className="w-4 h-4 opacity-70" aria-hidden />
              </button>
              <Link to="/methodology" className="landing-btn-secondary">
                Methodology
                <ArrowUpRight className="w-4 h-4 opacity-70" aria-hidden />
              </Link>
            </div>

            <dl className="mt-8 grid grid-cols-3 gap-4 max-w-md border-t border-[var(--l-rule)] pt-5">
              <div>
                <dt className="text-[11px] uppercase tracking-wide text-[var(--l-slate)]">
                  Inequality
                </dt>
                <dd className="font-display text-2xl sm:text-3xl text-[var(--l-ink)] tabular-nums mt-1">
                  {formatGini(METRICS_CANON.gini)}
                </dd>
                <dd className="text-xs text-[var(--l-slate)] mt-0.5">National Gini</dd>
              </div>
              <div>
                <dt className="text-[11px] uppercase tracking-wide text-[var(--l-slate)]">
                  Sections
                </dt>
                <dd className="font-display text-2xl sm:text-3xl text-[var(--l-ink)] tabular-nums mt-1">
                  {METRICS_CANON.sections}
                </dd>
                <dd className="text-xs text-[var(--l-slate)] mt-0.5">Pre-computed</dd>
              </div>
              <div>
                <dt className="text-[11px] uppercase tracking-wide text-[var(--l-slate)]">Scope</dt>
                <dd className="font-display text-2xl sm:text-3xl text-[var(--l-ink)] mt-1">
                  {METRICS_CANON.dimensions}
                </dd>
                <dd className="text-xs text-[var(--l-slate)] mt-0.5">Policy dims</dd>
              </div>
            </dl>
          </div>

          <div className="min-w-0" aria-hidden={false}>
            <LandingHeroVisual />
          </div>
        </div>
      </div>
    </section>
  )
}
