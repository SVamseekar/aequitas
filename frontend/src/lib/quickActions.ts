import { TrendingDown, MapPin, FileText } from "lucide-react"

export const ENGLAND_QUICK_ACTIONS = [
  {
    icon: TrendingDown,
    label: "Explore Inequity",
    prompt: "Show me the key inequity findings — Gini coefficient, Palma ratio, and which areas are most deprived of bus services.",
  },
  {
    icon: MapPin,
    label: "Compare Regions",
    prompt: "Compare bus service levels across English regions. Which regions perform best and worst on service quality and accessibility?",
  },
  {
    icon: FileText,
    label: "Ask About Policy",
    prompt: "What are the main policy recommendations from the Aequitas analysis? Which interventions would have the greatest impact?",
  },
]

export const NETHERLANDS_QUICK_ACTIONS = [
  {
    icon: TrendingDown,
    label: "SES × OVapi",
    prompt: "How does SES-WOA line up with OVapi weekday service in this filter?",
  },
  {
    icon: MapPin,
    label: "NH vs Groningen",
    prompt: "Who lives beyond 400 m in Noord-Holland versus Groningen?",
  },
  {
    icon: FileText,
    label: "OV-wet",
    prompt: "What do concession / OV-wet programmes cover in this filter?",
  },
]

export const FRANCE_QUICK_ACTIONS = [
  {
    icon: TrendingDown,
    label: "F-EDI × NAP",
    prompt: "How does F-EDI 2021 line up with NAP weekday service in this filter?",
  },
  {
    icon: MapPin,
    label: "IDF vs Occitanie",
    prompt: "How does Île-de-France compare with Occitanie on Sunday deserts and Gini?",
  },
  {
    icon: FileText,
    label: "AOM / SPC",
    prompt: "What do AOM and SPC programmes cover against NAP coverage in this filter?",
  },
]

export const IRELAND_QUICK_ACTIONS = [
  {
    icon: TrendingDown,
    label: "HP × TFI",
    prompt: "How does Pobal HP 2022 line up with TFI weekday service in this filter?",
  },
  {
    icon: MapPin,
    label: "Dublin vs Cork",
    prompt: "Who lives beyond 400 m in Dublin versus Cork?",
  },
  {
    icon: FileText,
    label: "NTA programmes",
    prompt: "What do Connecting Ireland, BusConnects and Local Link cover in this filter?",
  },
]

/** Irish chips on Ireland. Never BSA/IMD on the Republic drawer. */
