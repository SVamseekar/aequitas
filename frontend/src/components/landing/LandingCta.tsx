import { Link } from "react-router"
import { ArrowRight } from "lucide-react"

export function LandingCta() {
  return (
    <section aria-labelledby="landing-cta-heading" className="bg-[var(--l-paper)]">
      <div className="landing-shell py-12 sm:py-14">
        <div
          className="landing-glass-dark relative overflow-hidden rounded-3xl px-6 py-10 sm:px-12 sm:py-12 text-center"
          style={{
            background:
              "radial-gradient(ellipse 80% 70% at 50% -20%, rgb(184 78 31 / 0.35), transparent 55%), linear-gradient(160deg, rgb(40 32 26 / 0.75), rgb(18 16 14 / 0.88))",
          }}
        >
          <h2
            id="landing-cta-heading"
            className="font-display text-3xl sm:text-4xl text-[#f7f4ef] leading-[1.1] max-w-lg mx-auto"
          >
            Four countries. One method. Ranks stay in-country.
          </h2>
          <p className="mt-4 text-base sm:text-lg text-white/60 max-w-md mx-auto leading-relaxed">
            Dated packs from official timetables and official deprivation. No invented 45-minute
            jobs.
          </p>
          <div className="mt-8 flex flex-wrap items-center justify-center gap-3">
            <Link to="/topics" className="landing-btn-primary">
              Read the briefings
              <ArrowRight className="w-4 h-4" aria-hidden />
            </Link>
            <Link
              to="/methodology"
              className="inline-flex items-center gap-2 rounded-full border border-white/20 bg-white/10 px-6 py-3 text-sm font-semibold text-[#f7f4ef] hover:bg-white/15 transition-colors backdrop-blur-md"
            >
              How it is computed
            </Link>
          </div>
        </div>
      </div>
    </section>
  )
}
