export const FAQ_ITEMS = [
  {
    question: "Which countries?",
    answer: "England, Ireland (Republic), the Netherlands, France. Ranks stay in-country.",
  },
  {
    question: "What is the score?",
    answer:
      "0–100 from 400 m coverage, evening service, weekday quality, and inverted deprivation–service correlation. Missing terms drop out.",
  },
  {
    question: "15 / 30 / 45 minute jobs?",
    answer: "Only after a local r5py run. Otherwise Reach shows service bands and an empty travel-time line.",
  },
  {
    question: "Official guidance?",
    answer: "No. Independent briefing. Not DfT, NTA, CBS, or ministerial advice.",
  },
  {
    question: "Live punctuality?",
    answer: "Only the last official GTFS-RT / SIRI rollup. No invented national on-time rate.",
  },
  {
    question: "Can I run it locally?",
    answer: "Yes. Clone the repo and run ./scripts/dev.sh. Warehouses stay on disk, not on this host.",
  },
] as const

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
