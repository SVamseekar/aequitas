import type { LucideIcon } from "lucide-react"
import {
  Bus,
  Database,
  FileSearch,
  FileText,
  Leaf,
  MapPin,
  Network,
  PoundSterling,
  Scale,
  Sliders,
  SlidersHorizontal,
} from "lucide-react"

export const HEADLINE_STATS = [
  { label: "Gini coefficient", value: "0.5741", sub: "Bus service inequality" },
  { label: "Palma ratio", value: "5.702×", sub: "Top 10% vs bottom 40%" },
  { label: "Evening isolated", value: "15.4%", sub: "of LSOAs" },
  { label: "Sunday deserts", value: "20.0%", sub: "of LSOAs" },
] as const

export const AUDIENCES = [
  {
    title: "Local Transport Authorities",
    description:
      "Prioritise interventions, model scenarios, and build franchising evidence under the Bus Services Act 2025.",
  },
  {
    title: "Central government & DfT",
    description:
      "Compare regional equity gaps, service quality deserts, and investment returns using national open data.",
  },
  {
    title: "Researchers & analysts",
    description:
      "Explore pre-computed metrics across 33,755 LSOAs with traceable formulas and exportable findings.",
  },
] as const

export const DATA_SOURCES = [
  "NaPTAN",
  "BODS GTFS",
  "ONS Census 2021",
  "IMD 2025",
  "NOMIS BRES",
  "NHS ODS",
  "DfT TAG",
  "DESNZ 2025",
] as const

export interface DimensionCard {
  icon: LucideIcon
  title: string
  question: string
  grounded: string
  route: string
}

export const DIMENSIONS: DimensionCard[] = [
  {
    icon: Scale,
    title: "Equity & Deprivation",
    question: "Which areas get the least bus service relative to need?",
    grounded: "Gini, Lorenz, Palma ratio across 33,755 LSOAs",
    route: "/equity",
  },
  {
    icon: MapPin,
    title: "Accessibility",
    question: "Can residents reach jobs, healthcare, and schools by bus?",
    grounded: "2SFCA 400m catchment analysis",
    route: "/accessibility",
  },
  {
    icon: Bus,
    title: "Service Quality",
    question: "Where do evening and weekend services disappear?",
    grounded: "Headway, isolation, and peak ratio metrics",
    route: "/service-quality",
  },
  {
    icon: Network,
    title: "Route Network",
    question: "Is the network fragmented across operators and boundaries?",
    grounded: "13,099 routes, operator concentration analysis",
    route: "/route-network",
  },
  {
    icon: Leaf,
    title: "Modal Shift & Carbon",
    question: "What is the emissions impact of shifting car trips to buses?",
    grounded: "DfT elasticities, DESNZ 2025 carbon factors",
    route: "/modal-shift",
  },
  {
    icon: PoundSterling,
    title: "Economic Appraisal",
    question: "Does this investment pass a benefit-cost test?",
    grounded: "BCR via Green Book / TAG methodology",
    route: "/economic",
  },
  {
    icon: FileText,
    title: "Bus Services Act 2025",
    question: "Is your authority ready for franchising under the new Act?",
    grounded: "Franchising readiness and operator concentration tiers",
    route: "/bus-services-act",
  },
  {
    icon: Sliders,
    title: "Policy Scenarios",
    question: "What happens if we restore evening frequency or add on-demand transport?",
    grounded: "Parameterised scenario modelling",
    route: "/scenarios",
  },
]

export const HOW_IT_WORKS = [
  {
    icon: Database,
    step: "Select your region",
    description:
      "Filter by region and area type to see analytics for the place you are responsible for.",
  },
  {
    icon: FileSearch,
    step: "Review evidence-graded findings",
    description:
      "Every chart and number comes with a plain-English explanation of what it means and why it matters.",
  },
  {
    icon: SlidersHorizontal,
    step: "Model scenarios and export",
    description:
      "Test interventions, see the cost and impact, and export findings ready for your business case.",
  },
] as const