import { Link } from "react-router"

export function LandingHero() {
  return (
    <section aria-labelledby="landing-hero-heading" className="landing-hero-product">
      <img
        src="/landing/hero-street.jpg"
        alt=""
        className="landing-hero-bg"
        width={1920}
        height={1080}
        fetchPriority="high"
      />
      <div className="landing-hero-bg-veil" aria-hidden />

      <div className="landing-shell landing-hero-product-inner">
        <h1 id="landing-hero-heading" className="sr-only">
          Aequitas — official timetables joined to official deprivation
        </h1>

        <figure className="landing-product-window">
          <div className="landing-product-chrome" aria-hidden>
            <span />
            <span />
            <span />
            <p>England briefing</p>
          </div>
          <img
            src="/landing/product-home.jpg"
            alt="Aequitas England briefing: in-country score and map of the bus network against official deprivation"
            width={1440}
            height={900}
            className="landing-product-shot"
          />
        </figure>

        <p className="landing-hero-caption">
          <Link to="/briefings" className="landing-btn-ghost">
            Read the briefings →
          </Link>
          <span aria-hidden className="opacity-40">
            ·
          </span>
          <Link to="/methodology" className="landing-btn-ghost">
            How it is computed →
          </Link>
        </p>
      </div>
    </section>
  )
}
