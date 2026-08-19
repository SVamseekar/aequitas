import { Link } from "react-router"

const WHO = [
  {
    title: "Transport authorities",
    body: "A quoteable score, a map, and the same doors for every filter you already use.",
  },
  {
    title: "Ministries and regulators",
    body: "Compare equity inside one country. Your deprivation index never shares an axis with another.",
  },
  {
    title: "Operators and consultants",
    body: "A scoped pack for a franchise, a concession, or a network redesign — not a generic dashboard.",
  },
  {
    title: "Researchers",
    body: "Dated packs, cited sources, empty cells that stay empty until the model has actually run.",
  },
] as const

export function LandingEngage() {
  return (
    <section aria-labelledby="landing-engage-heading" className="bg-[var(--l-paper)]">
      <div className="landing-shell py-14 sm:py-16 lg:py-20">
        <p className="text-xs font-semibold uppercase tracking-[0.14em] text-[var(--l-rust)] mb-3">
          Commission a pack
        </p>
        <h2
          id="landing-engage-heading"
          className="font-display text-3xl sm:text-4xl text-[var(--l-ink)] max-w-xl text-balance"
        >
          Tell us the country. We adapt the method.
        </h2>
        <p className="mt-4 text-[var(--l-slate)] max-w-xl text-pretty">
          New geography, new official index, new appraisal rule, new real-time feed. The doors stay
          the same. Ranks never leave the country.
        </p>

        <ul className="mt-10 grid sm:grid-cols-2 gap-6 max-w-3xl">
          {WHO.map((w) => (
            <li key={w.title}>
              <h3 className="font-semibold text-[var(--l-ink)]">{w.title}</h3>
              <p className="mt-1.5 text-sm text-[var(--l-slate)] leading-relaxed text-pretty">
                {w.body}
              </p>
            </li>
          ))}
        </ul>

        <div className="mt-10">
          <Link to="/contact" className="landing-btn-primary">
            Start a conversation
          </Link>
        </div>
      </div>
    </section>
  )
}
