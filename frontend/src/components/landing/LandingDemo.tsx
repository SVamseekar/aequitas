export function LandingDemo() {
  return (
    <section
      id="demo"
      aria-labelledby="landing-demo-heading"
      className="bg-[var(--l-surface)] border-b border-[var(--l-rule)]"
    >
      <div className="landing-shell py-14 sm:py-16 lg:py-20">
        <div className="max-w-2xl mb-8">
          <p className="text-xs font-semibold uppercase tracking-[0.14em] text-[var(--l-rust)] mb-3">
            The briefing
          </p>
          <h2
            id="landing-demo-heading"
            className="font-display text-3xl sm:text-4xl text-[var(--l-ink)] text-balance"
          >
            Same doors. Local evidence.
          </h2>
          <p className="mt-3 text-[var(--l-slate)] text-pretty">
            A recorded walkthrough of a live country pack — score, map, equity, access, service,
            network, correlations, and scenarios. The engine runs locally. This is what a
            commissioned pack looks like.
          </p>
        </div>

        <figure className="landing-product-window landing-product-window-plain">
          <div className="landing-product-chrome" aria-hidden>
            <span />
            <span />
            <span />
            <p>Country pack</p>
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
      </div>
    </section>
  )
}
