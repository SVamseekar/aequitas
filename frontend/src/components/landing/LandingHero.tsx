import { Link } from "react-router"
import { ArrowRight } from "lucide-react"
import { LandingHeroVisual } from "./LandingHeroVisual"

export function LandingHero() {

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
              England · Ireland · Netherlands · France
            </p>

            <h1
              id="landing-hero-heading"
              className="font-display text-4xl sm:text-5xl lg:text-[3.35rem] leading-[1.08] text-[var(--l-ink)] text-balance"
            >
              See where the bus{" "}
              <span className="text-[var(--l-rust)]">fails people</span>
            </h1>

            <p className="mt-5 text-lg text-[var(--l-slate)] leading-relaxed max-w-md text-pretty">
              Official timetables × official deprivation. Same method. Ranks stay in-country.
            </p>

            <div className="mt-7 flex flex-wrap items-center gap-3">
              <Link to="/topics" className="landing-btn-primary">
                Read the briefings
                <ArrowRight className="w-4 h-4" aria-hidden />
              </Link>
              <Link
                to="/methodology"
                className="text-sm font-medium text-[var(--l-slate)] hover:text-[var(--l-ink)] px-2"
              >
                How it is computed
              </Link>
            </div>

            <dl className="mt-8 grid grid-cols-3 gap-4 max-w-lg border-t border-[var(--l-rule)] pt-5">
              <div>
                <dt className="text-[11px] uppercase tracking-wide text-[var(--l-slate)]">Live packs</dt>
                <dd className="font-display text-2xl sm:text-3xl text-[var(--l-ink)] tabular-nums mt-1">4</dd>
                <dd className="text-xs text-[var(--l-slate)] mt-0.5">EN · IE · NL · FR</dd>
              </div>
              <div>
                <dt className="text-[11px] uppercase tracking-wide text-[var(--l-slate)]">Score</dt>
                <dd className="font-display text-2xl sm:text-3xl text-[var(--l-ink)] mt-1">0–100</dd>
                <dd className="text-xs text-[var(--l-slate)] mt-0.5">One formula</dd>
              </div>
              <div>
                <dt className="text-[11px] uppercase tracking-wide text-[var(--l-slate)]">Doors</dt>
                <dd className="font-display text-2xl sm:text-3xl text-[var(--l-ink)] mt-1">10</dd>
                <dd className="text-xs text-[var(--l-slate)] mt-0.5">Same questions</dd>
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
