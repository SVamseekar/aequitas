import type { LucideIcon } from "lucide-react"
import {
  Bus,
  Clock,
  Database,
  FileSearch,
  FileText,
  Map,
  Network,
  Scale,
  Sliders,
  SlidersHorizontal,
  MapPin,
  GitCompare,
} from "lucide-react"

export const COUNTRY_COVERAGE = [
  {
    code: "england",
    name: "England",
    status: "live" as const,
    network: "BODS GTFS + NaPTAN",
    deprivation: "IMD 2025",
    geography: "LSOA 2021",
    note: "Score, map, Studio, Reach, Time",
    href: "/app/england",
  },
  {
    code: "ireland",
    name: "Ireland",
    status: "live" as const,
    network: "TFI GTFS_All.zip",
    deprivation: "Pobal HP 2022",
    geography: "CSO Small Areas 2022 · Republic",
    note: "Same doors. Ranks stay in the Republic.",
    href: "/app/ireland",
  },
  {
    code: "netherlands",
    name: "Netherlands",
    status: "live" as const,
    network: "OVapi GTFS",
    deprivation: "CBS SES-WOA 2023",
    geography: "Buurten 2024",
    note: "Bus is the default. All-PT is a labelled mode.",
    href: "/app/netherlands",
  },
  {
    code: "france",
    name: "France",
    status: "live" as const,
    network: "NAP GTFS harvest (441 merged / 111 skipped)",
    deprivation: "F-EDI 2021",
    geography: "IRIS (metropolitan)",
    note: "National score 47.7. Same doors. Chat on FAISS[france]. 15/30/45 still empty.",
    href: "/app/france",
  },
] as const

export const AUDIENCES = [
  {
    title: "Transport authorities",
    description:
      "Prioritise routes and funding with a quoteable score, a map, and exhibits that name the filter — without a proprietary access engine.",
  },
  {
    title: "Ministries and regulators",
    description:
      "Compare equity inside one country. IMD, HP, and SES-WOA never share an axis.",
  },
  {
    title: "Researchers",
    description:
      "Computed Gini, cited sources, dated network packs. Travel times stay empty until r5py has actually run.",
  },
] as const

export const DATA_SOURCES = [
  "BODS GTFS",
  "NaPTAN",
  "IMD 2025",
  "ONS Census 2021",
  "TFI GTFS",
  "Pobal HP 2022",
  "CSO Small Areas",
  "OVapi",
  "CBS SES-WOA",
  "CBS buurten",
  "NAP GTFS",
  "F-EDI 2021",
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
    title: "Equity",
    question: "Who gets the least service relative to need?",
    grounded: "Lorenz, Gini, Palma, in-country deprivation slope",
    route: "/equity",
  },
  {
    icon: MapPin,
    title: "Access",
    question: "How many people live beyond 400 m of a stop?",
    grounded: "Coverage, deserts, urban–rural gap — people in the title",
    route: "/access",
  },
  {
    icon: Bus,
    title: "Service",
    question: "Where do evenings and Sundays disappear?",
    grounded: "Weekday quality, evening isolation, Sunday deserts",
    route: "/service",
  },
  {
    icon: Network,
    title: "Network",
    question: "How concentrated are the operators?",
    grounded: "One HHI on a 0–10,000 scale",
    route: "/network",
  },
  {
    icon: GitCompare,
    title: "Correlations",
    question: "Does coverage track deprivation — or something else?",
    grounded: "One matrix + one scatter, not a wall of bars",
    route: "/correlations",
  },
  {
    icon: FileText,
    title: "Economy",
    question: "Who is in the people-gap — and is there a published unit cost?",
    grounded: "People-gap first. Official € / TAG only when cited.",
    route: "/economy",
  },
  {
    icon: Scale,
    title: "Policy",
    question: "Which programmes apply here?",
    grounded: "BSA 2025 · NTA · Concession / OV-wet — local titles",
    route: "/policy",
  },
  {
    icon: Sliders,
    title: "Scenarios",
    question: "Who moves if frequency or evenings change?",
    grounded: "Listed interventions × people × deprivation",
    route: "/scenarios",
  },
  {
    icon: Clock,
    title: "Time",
    question: "Did the network move while the census stayed still?",
    grounded: "Dated packs. Census and deprivation stay frozen.",
    route: "/time",
  },
  {
    icon: Map,
    title: "Reach & Studio",
    question: "What does a walk-to-stop change do on this filter?",
    grounded: "Service bands 1–6. 15/30/45 only after r5py.",
    route: "/reach",
  },
]

export const HOW_IT_WORKS = [
  {
    icon: Database,
    step: "Choose a country and filter",
    description:
      "England, Ireland, the Netherlands, or France. Region, urban/rural, and — in NL/FR — bus or all public transport.",
  },
  {
    icon: FileSearch,
    step: "Read the briefing",
    description:
      "Every exhibit has a key finding, so what, and a caveat that names this filter. Weak evidence is suppressed, not filled in.",
  },
  {
    icon: SlidersHorizontal,
    step: "Patch, compare, export",
    description:
      "Studio is walk-to-stop. Compare stays inside the country. The research pack uses that country’s nouns.",
  },
] as const
