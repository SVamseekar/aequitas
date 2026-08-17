import { AUDIENCES } from "./data"

export function LandingAudience() {
  return (
    <section aria-labelledby="landing-audience-heading" className="bg-[var(--l-paper)]">
      <div className="landing-shell py-12 sm:py-14 lg:py-16">
        <p className="text-xs font-semibold uppercase tracking-[0.14em] text-[var(--l-rust)] mb-3">
          Built for decision-makers
        </p>
        <h2
          id="landing-audience-heading"
          className="font-display text-3xl sm:text-4xl leading-[1.12] text-[var(--l-ink)] max-w-lg mb-8"
        >
          Who opens it when a funding paper is due.
        </h2>

        <ul className="grid md:grid-cols-3 gap-3 sm:gap-4">
          {AUDIENCES.map((audience, i) => (
            <li key={audience.title} className="landing-card p-5 sm:p-6 flex flex-col min-h-[180px]">
              <span className="font-display text-3xl text-[var(--l-rust)]/35 mb-4">
                {String(i + 1).padStart(2, "0")}
              </span>
              <h3 className="text-lg font-semibold text-[var(--l-ink)] mb-2">{audience.title}</h3>
              <p className="text-sm sm:text-base text-[var(--l-slate)] leading-relaxed mt-auto">
                {audience.description}
              </p>
            </li>
          ))}
        </ul>
      </div>
    </section>
  )
}
