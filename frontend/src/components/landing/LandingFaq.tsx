import { useState } from "react"

export const FAQ_ITEMS = [
  {
    question: "Which countries are live?",
    answer:
      "England, Ireland (Republic), and the Netherlands. France uses the same ten doors; the warehouse is not built, so the app says so. Deprivation ranks stay inside each country.",
  },
  {
    question: "What is the in-country score?",
    answer:
      "A 0–100 figure: people within 400 m, evening service, weekday quality, and an inverted deprivation–service correlation. Missing terms are dropped and the weights renormalised. London rural is empty under the official classification.",
  },
  {
    question: "Do you sell 15 / 30 / 45 minute job access?",
    answer:
      "Only after a local r5py run with a Geofabrik extract. Until then Reach shows Aequitas service bands and an honest empty sentence. We do not invent job counts.",
  },
  {
    question: "Is this official government guidance?",
    answer:
      "No. Aequitas is an independent briefing. It is not NTA, CBS, DfT, or ministerial guidance. Outputs are for exploration — not statutory appraisal.",
  },
  {
    question: "How do network dates relate to the census?",
    answer:
      "Time moves timetable-derived metrics (BODS, TFI, OVapi). Census geographies and IMD / HP / SES-WOA stay frozen. One pack date is one point, not a fabricated monthly series.",
  },
  {
    question: "Do you show live punctuality?",
    answer:
      "Only where a collector wrote a rollup from an official free GTFS-RT or SIRI feed. England uses BODS when the feed answers; Ireland names NTA’s three operators and stays empty without a key; the Netherlands uses OVapi RT if it exists; France’s NAP union is incomplete. No invented national on-time figure.",
  },
  {
    question: "Can I run it locally?",
    answer:
      "Yes. Clone the repo, copy .env.example, and run ./scripts/dev.sh. Warehouses are local DuckDB files and are not in git. Analytics work with DEV_AUTH_BYPASS in development.",
  },
] as const

export function LandingFaq() {
  const [open, setOpen] = useState<number | null>(0)

  return (
    <section
      id="faq"
      aria-labelledby="landing-faq-heading"
      className="relative border-y border-white/40 bg-white/15 backdrop-blur-md"
    >
      <div className="landing-shell py-12 sm:py-14 lg:py-16">
        <div className="grid lg:grid-cols-12 gap-8 lg:gap-12">
          <div className="lg:col-span-4">
            <p className="text-xs font-semibold uppercase tracking-[0.14em] text-[var(--l-rust)] mb-3">
              FAQ
            </p>
            <h2
              id="landing-faq-heading"
              className="font-display text-3xl sm:text-4xl leading-[1.12] text-[var(--l-ink)]"
            >
              What a serious buyer asks first.
            </h2>
          </div>

          <div className="lg:col-span-8">
            <dl className="divide-y divide-[var(--l-rule)] border-y border-[var(--l-rule)]">
              {FAQ_ITEMS.map((item, index) => {
                const isOpen = open === index
                return (
                  <div key={item.question}>
                    <dt>
                      <button
                        type="button"
                        aria-expanded={isOpen}
                        onClick={() => setOpen(isOpen ? null : index)}
                        className="w-full flex items-start justify-between gap-4 py-5 text-left"
                      >
                        <span className="text-base sm:text-lg font-semibold text-[var(--l-ink)] pr-2">
                          {item.question}
                        </span>
                        <span className="mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-full border border-[var(--l-rule)] bg-[var(--l-paper)] text-sm tabular-nums text-[var(--l-slate)]">
                          {isOpen ? "–" : "+"}
                        </span>
                      </button>
                    </dt>
                    {isOpen && (
                      <dd className="pb-5 pr-10">
                        <p className="text-base text-[var(--l-slate)] leading-relaxed max-w-2xl">
                          {item.answer}
                        </p>
                      </dd>
                    )}
                  </div>
                )
              })}
            </dl>
          </div>
        </div>
      </div>
    </section>
  )
}
