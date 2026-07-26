import { useState } from "react"
import { Plus, Minus } from "lucide-react"
import { METRICS_CANON, formatGini, formatPalma } from "@/lib/metricsCanon"

const m = METRICS_CANON

export const FAQ_ITEMS = [
  {
    question: "What geography is covered?",
    answer: `England only — all ${m.lsoas.toLocaleString("en-GB")} Lower Super Output Areas (LSOAs), covering ${m.populationDisplay} population. Filters cover 9 English regions and urban/rural area types (${m.filterCombos} national/regional combos in the warehouse).`,
  },
  {
    question: "What data sources power Aequitas?",
    answer: `National open data: NaPTAN (${m.stops.toLocaleString("en-GB")} active bus stops), BODS GTFS (${m.routes.toLocaleString("en-GB")} routes, ${m.tripsDisplay} trips), ONS Census 2021, MHCLG IMD 2025, NOMIS BRES, NHS ODS, GIAS schools, DfT TAG, and DESNZ emission factors. Full detail is on the Methodology page.`,
  },
  {
    question: "Is this official Department for Transport guidance?",
    answer:
      "No. Aequitas is an independent policy analysis tool. It is not affiliated with, endorsed by, or produced by DfT, ONS, or any UK government body. Outputs are for exploration and evidence-building — not formal scheme appraisal.",
  },
  {
    question: "How is equity measured?",
    answer: `Service distribution inequality uses Gini (${formatGini(m.gini)}), Palma ratio (${formatPalma(m.palma)}), and concentration index on bus service levels across LSOAs, cross-referenced with IMD deprivation. National figures are locked to the warehouse audit pack (as of ${m.asOf}).`,
  },
  {
    question: "Can Local Transport Authorities filter to their region?",
    answer:
      "Yes. The platform filters by nine English regions and urban/rural classification so LTAs can focus on their geography. Some combos (for example London × rural) have no matching LSOAs under the rural-urban classification — the UI explains that explicitly.",
  },
  {
    question: "How do scenarios relate to the Bus Services Act 2025?",
    answer:
      "The Bus Services Act dimension scores franchising readiness and operator concentration. Policy Scenarios model interventions such as frequency restoration, evening extension, and DRT rural coverage so authorities can explore evidence ahead of franchising or enhanced partnership decisions.",
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
              Questions authorities ask first.
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
                        <span className="mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-full border border-[var(--l-rule)] bg-[var(--l-paper)]">
                          {isOpen ? (
                            <Minus className="w-3.5 h-3.5" aria-hidden />
                          ) : (
                            <Plus className="w-3.5 h-3.5" aria-hidden />
                          )}
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
