import { Link } from "react-router"
import { LandingHeroVisual } from "./LandingHeroVisual"

export function LandingHero() {
  return (
    <section
      aria-labelledby="landing-hero-heading"
      className="landing-hero-photo relative overflow-hidden"
    >
      <LandingHeroVisual />

      <div className="landing-hero-copy landing-shell">
        <p className="landing-chip inline-flex items-center gap-2 rounded-full px-3 py-1.5 text-xs font-medium text-white/85 mb-4 border-white/25 bg-white/10">
          <span className="h-1.5 w-1.5 rounded-full bg-white" aria-hidden />
          England · Ireland · Netherlands · France
        </p>

        <h1
          id="landing-hero-heading"
          className="font-display text-4xl sm:text-5xl lg:text-[3.5rem] leading-[1.06] text-white text-balance max-w-2xl"
        >
          See where the bus fails people
        </h1>

        <p className="mt-4 text-base sm:text-lg text-white/80 leading-relaxed max-w-md text-pretty">
          Official timetables × official deprivation. Same method. Ranks stay in-country.
        </p>

        <div className="mt-7 flex flex-wrap items-center gap-x-6 gap-y-2">
          <Link to="/briefings" className="landing-btn-ghost">
            Read the briefings →
          </Link>
          <Link to="/methodology" className="landing-btn-ghost">
            How it is computed →
          </Link>
        </div>
      </div>
    </section>
  )
}
