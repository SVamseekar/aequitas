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
          <video
            className="landing-product-shot"
            poster="/landing/product-home.jpg"
            autoPlay
            muted
            loop
            playsInline
            controls
            preload="metadata"
          >
            <source src="/landing/product-demo.mp4" type="video/mp4" />
            Your browser cannot play this walkthrough.
          </video>
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
