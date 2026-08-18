import { Link } from "react-router"

export function LandingHero() {
  return (
    <section
      aria-labelledby="landing-hero-heading"
      className="border-b border-[var(--l-rule)] bg-[var(--l-paper)]"
    >
      <div className="landing-shell py-16 sm:py-20 lg:py-24">
        <p className="text-xs font-semibold uppercase tracking-[0.14em] text-[var(--l-rust)] mb-4">
          For authorities, agencies, and ministries
        </p>
        <h1
          id="landing-hero-heading"
          className="font-display text-4xl sm:text-5xl lg:text-[3.4rem] leading-[1.06] text-[var(--l-ink)] text-balance max-w-3xl"
        >
          A briefing method you can commission for your country
        </h1>
        <p className="mt-5 text-lg text-[var(--l-slate)] leading-relaxed max-w-xl text-pretty">
          Official timetables joined to official need. Same doors everywhere. Ranks stay
          in-country. We build the pack for your geography, your index, your statute.
        </p>
        <div className="mt-8 flex flex-wrap items-center gap-3">
          <Link to="/contact" className="landing-btn-primary">
            Work with us
          </Link>
          <Link to="/briefings" className="landing-btn-secondary">
            Read the briefings
          </Link>
        </div>
      </div>
    </section>
  )
}
