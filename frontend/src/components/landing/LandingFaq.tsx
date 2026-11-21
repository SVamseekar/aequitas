import { FAQ_ITEMS } from "@/lib/landingFaq"

export function LandingFaq() {
  return (
    <section
      id="faq"
      aria-labelledby="landing-faq-heading"
      className="relative border-y border-white/40 bg-white/15 backdrop-blur-md"
    >
      <div className="landing-shell py-12 sm:py-14">
        <h2
          id="landing-faq-heading"
          className="font-display text-3xl sm:text-4xl leading-[1.12] text-[var(--l-ink)] mb-8"
        >
          FAQ
        </h2>
        <div className="divide-y divide-[var(--l-rule)] border-y border-[var(--l-rule)]">
          {FAQ_ITEMS.map((item) => (
            <details key={item.question} className="group py-1">
              <summary className="cursor-pointer list-none flex items-start justify-between gap-4 py-4 text-left font-semibold text-[var(--l-ink)] [&::-webkit-details-marker]:hidden">
                {item.question}
                <span
                  className="mt-0.5 flex h-7 w-7 shrink-0 items-center justify-center rounded-full border border-[var(--l-rule)] text-sm text-[var(--l-slate)] group-open:hidden"
                  aria-hidden
                >
                  +
                </span>
                <span
                  className="mt-0.5 hidden h-7 w-7 shrink-0 items-center justify-center rounded-full border border-[var(--l-rule)] text-sm text-[var(--l-slate)] group-open:flex"
                  aria-hidden
                >
                  –
                </span>
              </summary>
              <p className="pb-4 pr-10 text-sm text-[var(--l-slate)] leading-relaxed max-w-2xl">
                {item.answer}
              </p>
            </details>
          ))}
        </div>
      </div>
    </section>
  )
}
