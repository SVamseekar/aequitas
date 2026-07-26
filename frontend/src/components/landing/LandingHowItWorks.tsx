import { HOW_IT_WORKS } from "./data"

export function LandingHowItWorks() {
  return (
    <section
      id="how"
      aria-labelledby="landing-how-heading"
      className="relative text-[var(--l-paper)] overflow-hidden"
      style={{
        background:
          "radial-gradient(ellipse 70% 80% at 50% 0%, rgb(184 78 31 / 0.22), transparent 55%), #161411",
      }}
    >
      <div className="landing-shell py-12 sm:py-14 lg:py-16">
        <p className="text-xs font-semibold uppercase tracking-[0.14em] text-[#d4784a] mb-3">
          How it works
        </p>
        <h2
          id="landing-how-heading"
          className="font-display text-3xl sm:text-4xl leading-[1.12] max-w-lg"
        >
          Region filter → evidence → scenario → export.
        </h2>

        <ol className="mt-8 sm:mt-10 grid md:grid-cols-3 gap-4 md:gap-5">
          {HOW_IT_WORKS.map((step, index) => (
            <li key={step.step} className="landing-glass-dark rounded-2xl p-5 sm:p-6">
              <div className="flex h-11 w-11 items-center justify-center rounded-xl border border-white/15 bg-white/10 font-display text-xl mb-3 backdrop-blur-md">
                {index + 1}
              </div>
              <h3 className="text-base sm:text-lg font-semibold mb-1.5">{step.step}</h3>
              <p className="text-sm sm:text-base text-white/65 leading-relaxed">{step.description}</p>
            </li>
          ))}
        </ol>
      </div>
    </section>
  )
}
