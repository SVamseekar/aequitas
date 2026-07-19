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
  return (
    <section
      id="faq"
      aria-labelledby="landing-faq-heading"
      className="max-w-7xl mx-auto px-6 py-24"
    >
      <p className="text-[11px] font-mono uppercase tracking-[0.3em] text-indigo-400 font-bold">
        FAQ
      </p>
      <h2
        id="landing-faq-heading"
        className="text-2xl font-bold text-foreground tracking-tight mt-3 mb-10"
      >
        Common questions from transport authorities
      </h2>
      <dl className="max-w-3xl space-y-4">
        {FAQ_ITEMS.map((item) => (
          <div
            key={item.question}
            className="border border-border rounded-lg bg-card/40 p-5 hover:border-indigo-500/20 transition-colors"
          >
            <dt className="text-sm font-semibold text-foreground mb-2">{item.question}</dt>
            <dd className="text-sm text-muted-foreground leading-relaxed">{item.answer}</dd>
          </div>
        ))}
      </dl>
    </section>
  )
}
