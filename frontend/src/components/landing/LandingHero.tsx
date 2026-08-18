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
        <p className="text-xs font-semibold uppercase tracking-[0.14em] text-white/75 mb-4">
          For authorities, agencies, and ministries
        </p>
        <h1
          id="landing-hero-heading"
          className="font-display text-4xl sm:text-5xl lg:text-[3.4rem] leading-[1.06] text-white text-balance max-w-3xl"
        >
          A briefing method you can commission for your country
        </h1>
        <p className="mt-5 text-lg text-white/80 leading-relaxed max-w-xl text-pretty">
          Official timetables joined to official need. Same doors everywhere. Ranks stay
          in-country. We build the pack for your geography, your index, your statute.
        </p>
        <div className="mt-8 flex flex-wrap items-center gap-3">
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
