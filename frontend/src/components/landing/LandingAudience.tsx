import { AUDIENCES } from "./data"

export function LandingAudience() {
  return (
    <section aria-labelledby="landing-audience-heading" className="max-w-7xl mx-auto px-6 py-20">
      <div className="h-px bg-indigo-400/40 mb-6 max-w-[48px]" aria-hidden />
      <p className="text-[11px] font-mono uppercase tracking-[0.3em] text-indigo-400 font-bold">
        Built for public sector decision-makers
      </p>
      <h2
        id="landing-audience-heading"
        className="text-2xl font-bold text-foreground tracking-tight mt-3 mb-10"
      >
        Who uses Aequitas
      </h2>
      <ul className="grid md:grid-cols-3 gap-4">
        {AUDIENCES.map((audience) => (
          <li
            key={audience.title}
            className="p-6 rounded-lg border border-border bg-card/40 hover:border-indigo-400/20 transition-colors"
          >
            <h3 className="text-sm font-semibold text-foreground mb-2">{audience.title}</h3>
            <p className="text-sm text-muted-foreground leading-relaxed">{audience.description}</p>
          </li>
        ))}
      </ul>
    </section>
  )
}