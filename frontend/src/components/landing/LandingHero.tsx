import { Link } from "react-router"

export function LandingHero() {
  return (
    <section aria-labelledby="landing-hero-heading" className="landing-hero-photo">
      <img
        src="/landing/hero-street.jpg"
        alt="A city street at dusk — the kind of network a briefing is built for"
        className="landing-hero-bg"
        width={1920}
        height={1080}
        fetchPriority="high"
      />
      <div className="landing-hero-bg-veil" aria-hidden />

      <div className="landing-shell landing-hero-copy">
        <p className="text-xs font-semibold uppercase tracking-[0.14em] text-white mb-3">
          For authorities, agencies, and ministries
        </p>
        <h1
          id="landing-hero-heading"
          className="font-display text-4xl sm:text-5xl lg:text-[3.15rem] leading-[1.08] text-white text-balance"
        >
          Commission a briefing
          <br />
          for your country
        </h1>
        <p className="mt-4 text-base sm:text-[1.05rem] text-white leading-relaxed text-pretty">
          Official timetables × official need. Ranks stay in-country.
        </p>
        <div className="mt-6 flex flex-wrap items-center gap-3">
          <Link to="/contact" className="landing-btn-primary">
            Work with us
          </Link>
          <Link to="/briefings" className="landing-btn-on-photo">
            Read the briefings
          </Link>
        </div>
      </div>
    </section>
  )
}
