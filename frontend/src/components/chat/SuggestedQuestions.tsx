interface Props {
  dimension: string
  country?: string
  onSelect: (question: string) => void
}

const SUGGESTIONS: Record<string, string[]> = {
  default: [
    "What are the most transport-deprived areas in England?",
    "How does bus service inequality compare to income inequality?",
    "Which regions should be prioritised for franchising under the Bus Services Act?",
    "What would happen if evening bus services were extended to 11pm?",
  ],
  equity: [
    "Explain the Gini coefficient for bus services",
    "Which regions have the highest Palma ratio?",
    "How does the Concentration Index show pro-rich bias?",
    "What are triple-deprived LSOAs?",
  ],
  accessibility: [
    "Which LSOAs have zero access to employment?",
    "How is the 2SFCA accessibility score calculated?",
    "Where are the biggest healthcare access gaps?",
    "How many LSOAs lack secondary school access?",
  ],
  service_quality: [
    "What is the mean Service Quality Index?",
    "How many LSOAs are evening-isolated?",
    "Which regions have the worst Sunday service?",
    "Explain the headway analysis methodology",
  ],
  route_network: [
    "How many routes cross local authority boundaries?",
    "Which operators have the highest HHI concentration?",
    "What proportion of routes have geometry data?",
    "How long is the average bus route?",
  ],
  correlations: [
    "What socio-economic factors most predict bus coverage?",
    "What does a SHAP value mean for policy?",
    "How much of coverage variance is policy-driven?",
    "Which areas are anomalies in coverage vs deprivation?",
  ],
  economic: [
    "How is the Benefit-Cost Ratio calculated?",
    "What is the GDP multiplier for bus investment?",
    "Which regions have the largest investment gap?",
    "Explain the Green Book NPV methodology",
  ],
  bus_services_act: [
    "Which LTAs are most ready for franchising?",
    "What does high operator concentration mean for policy?",
    "Explain the LTA readiness tiers",
    "How does the Bus Services Act change franchising rules?",
  ],
  scenarios: [
    "What happens if we restore evening services to 11pm?",
    "How much CO₂ would a 10% frequency increase save?",
    "Model DRT coverage for rural LSOAs",
    "What is the population impact of frequency restoration?",
  ],
}

export const NETHERLANDS_SUGGESTIONS = [
  "Which provincies sit farthest from an OVapi stop on the 400 m map?",
  "How does SES-WOA line up with OVapi weekday service in this filter?",
  "Who lives beyond 400 m in Noord-Holland versus Groningen?",
  "What does OVapi operator HHI say about concentration (bus vs all-PT)?",
]

export const FRANCE_SUGGESTIONS = [
  "What is the Gini of NAP weekday trips per IRIS?",
  "How does Île-de-France compare with Occitanie on Sunday deserts?",
  "What does F-EDI 2021 say about weekday service in this filter?",
  "How do AOM / SPC programmes sit against NAP coverage?",
]

export const IRELAND_SUGGESTIONS = [
  "Which Republic counties sit farthest from a TFI stop on the 400 m map?",
  "How does Pobal HP 2022 line up with TFI weekday service in this filter?",
  "Who lives beyond 400 m in Dublin versus Cork?",
  "What does TFI operator HHI say about concentration in the Republic?",
]

export function SuggestedQuestions({ dimension, country, onSelect }: Props) {
  const questions =
    country === "ireland"
      ? IRELAND_SUGGESTIONS
      : country === "netherlands"
        ? NETHERLANDS_SUGGESTIONS
        : country === "france"
          ? FRANCE_SUGGESTIONS
          : (SUGGESTIONS[dimension] ?? SUGGESTIONS.default)

  return (
    <div className="space-y-2">
      <p className="text-[11px] font-mono uppercase tracking-wide text-muted-foreground mb-3">
        Suggested questions
      </p>
      {questions.map((q) => (
        <button
          key={q}
          onClick={() => onSelect(q)}
          className="w-full text-left text-xs text-muted-foreground hover:text-foreground hover:app-glass-strong border border-white/60 hover:border-primary/35 rounded px-3 py-2 transition-all"
        >
          {q}
        </button>
      ))}
    </div>
  )
}
