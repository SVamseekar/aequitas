/**
 * Public briefing catalogue — crawlable copy for the whole Aequitas topic map.
 * Scores and England warehouse figures are frozen from dated packs / METRICS_CANON.
 * Open GitHub issues (#12–#22) are treated as in-scope method (destinations,
 * r5py 15/30/45, in-country appraisal, GTFS-RT, FAISS[netherlands], second Time pack).
 */

export type CountryCode = "england" | "ireland" | "netherlands" | "france"

export type CountryBrief = {
  code: CountryCode
  name: string
  path: string
  score: number
  packAsOf: string
  network: string
  deprivation: string
  geography: string
  nAreas: string
  areaUnit: string
  policyTitle: string
  destinations: string
  appraisal: string
  realtime: string
  chat: string
  description: string
}

export const COUNTRY_BRIEFS: CountryBrief[] = [
  {
    code: "england",
    name: "England",
    path: "/briefings/england",
    score: 80.0,
    packAsOf: "2026-08-01",
    network: "BODS GTFS + NaPTAN",
    deprivation: "MHCLG IMD 2025",
    geography: "ONS LSOA 2021 (33,755 areas, 56.5M people)",
    nAreas: "33,755",
    areaUnit: "LSOAs",
    policyTitle: "Bus Services Act 2025 · LTA franchising",
    destinations: "NOMIS BRES jobs, NHS ODS hospitals/GPs, GIAS schools",
    appraisal: "DfT TAG v2.03fc · Green Book NPV / BCR",
    realtime: "BODS AVL / GTFS-RT TripUpdates (delay when the feed carries it)",
    chat: "FAISS[england] over dated England narratives",
    description:
      "England bus equity briefing: BODS GTFS and NaPTAN joined to IMD 2025 and Census 2021 LSOAs. Gini, Palma, 400 m coverage, Sunday deserts, TAG appraisal, BSA 2025.",
  },
  {
    code: "ireland",
    name: "Ireland",
    path: "/briefings/ireland",
    score: 55.5,
    packAsOf: "2026-08-13",
    network: "TFI GTFS_All.zip",
    deprivation: "Pobal HP 2022",
    geography: "CSO Small Areas 2022 · Republic only (18,919 areas)",
    nAreas: "18,919",
    areaUnit: "Small Areas",
    policyTitle: "NTA · Connecting Ireland · BusConnects · Local Link · PSO",
    destinations: "Official Republic jobs, GP, and school points (in-country files)",
    appraisal: "CAF / PAG — no England TAG and no EU-wide BCR",
    realtime: "NTA GTFS-RT TripUpdates (Dublin Bus, Bus Éireann, Go-Ahead)",
    chat: "FAISS[ireland] over TFI × Pobal HP narratives",
    description:
      "Republic of Ireland bus equity briefing: TFI GTFS joined to Pobal HP 2022 and CSO Small Areas. Ranks stay in the Republic. CAF/PAG appraisal, NTA programmes, NTA GTFS-RT.",
  },
  {
    code: "netherlands",
    name: "Netherlands",
    path: "/briefings/netherlands",
    score: 70.6,
    packAsOf: "2026-08-13",
    network: "OVapi GTFS (bus default; all-PT labelled)",
    deprivation: "CBS SES-WOA 2023",
    geography: "CBS buurten 2024 (13,827 neighbourhoods)",
    nAreas: "13,827",
    areaUnit: "buurten",
    policyTitle: "Concession / OV-wet — not a UK statute",
    destinations: "Official Dutch jobs, huisarts, and school destinations",
    appraisal: "MKBA — no TAG and no invented PBL euro",
    realtime: "OVapi GTFS-RT rollup when a dated file exists",
    chat: "FAISS[netherlands] from OVapi × SES-WOA narratives only",
    description:
      "Netherlands public-transport equity briefing: OVapi GTFS joined to CBS SES-WOA 2023 and buurten 2024. Bus vs all-PT modes. MKBA, concessions, FAISS[netherlands].",
  },
  {
    code: "france",
    name: "France",
    path: "/briefings/france",
    score: 47.7,
    packAsOf: "2026-08-17",
    network: "NAP / transport.data.gouv.fr GTFS harvest (metropolitan)",
    deprivation: "F-EDI 2021 (EDI IRIS)",
    geography: "IGN Contours IRIS · metropolitan (DOM out)",
    nAreas: "48,522",
    areaUnit: "IRIS",
    policyTitle: "AOM / SPC — organising authorities",
    destinations: "Official metropolitan jobs, médecins, and school destinations",
    appraisal: "French socio-economic appraisal — no EU BCR",
    realtime: "NAP GTFS-RT harvest (expanded feed set)",
    chat: "FAISS[france] over NAP × F-EDI narratives",
    description:
      "Metropolitan France bus equity briefing: NAP GTFS joined to F-EDI 2021 and IGN IRIS. Ranks stay in metropolitan France. AOM/SPC, French appraisal, NAP GTFS-RT.",
  },
]

export type TopicBrief = {
  slug: string
  path: string
  title: string
  question: string
  keywords: string[]
  body: string[]
  perCountry: Record<CountryCode, string>
}

export const TOPIC_BRIEFS: TopicBrief[] = [
  {
    slug: "equity",
    path: "/briefings/equity",
    title: "Equity & deprivation",
    question: "Who gets the least service relative to need?",
    keywords: [
      "Gini",
      "Palma",
      "Lorenz",
      "concentration index",
      "IMD",
      "Pobal HP",
      "SES-WOA",
      "F-EDI",
    ],
    body: [
      "Inequality is measured inside one country. Lorenz curve, Gini, Palma, and a deprivation slope use that country’s official index only.",
      "England reference warehouse: Gini 0.5741, Palma 5.702×, concentration index +0.1358 (pro-rich), 612 triple-deprived LSOAs.",
      "IMD, Pobal HP, SES-WOA, and F-EDI never share an axis. There is no Europe-wide deprivation rank.",
    ],
    perCountry: {
      england: "IMD 2025 deciles on 33,755 LSOAs.",
      ireland: "Pobal HP 2022 on Republic Small Areas.",
      netherlands: "CBS SES-WOA 2023 on buurten.",
      france: "F-EDI 2021 quintiles/deciles on metropolitan IRIS.",
    },
  },
  {
    slug: "access",
    path: "/briefings/access",
    title: "Access & coverage",
    question: "How many people live beyond 400 m of a stop?",
    keywords: ["400 m", "2SFCA", "transport desert", "coverage", "r5py", "15 30 45"],
    body: [
      "Coverage is people within 400 m of a stop, plus desert and urban–rural gaps. 2SFCA is used where destinations exist.",
      "England pack (2026-08-01): 79.27% within 400 m. Ireland 55.05%. Netherlands 88.27%. France 56.3%.",
      "15 / 30 / 45 minute reach to jobs, GPs, and schools is computed with r5py isochrones when the pack includes them.",
    ],
    perCountry: {
      england: "NaPTAN stops × LSOA centroids; 2SFCA to BRES / NHS / GIAS.",
      ireland: "TFI stops × CSO Small Areas; official Republic destinations.",
      netherlands: "OVapi stops × buurten; huisarts and school points.",
      france: "NAP stops × IRIS; metropolitan destination files.",
    },
  },
  {
    slug: "service",
    path: "/briefings/service",
    title: "Service quality",
    question: "Where do evenings and Sundays disappear?",
    keywords: ["headway", "evening isolation", "Sunday desert", "SQI", "frequency"],
    body: [
      "Weekday frequency, evening isolation after 19:00, and Sunday deserts are computed from GTFS calendars (or calendar_dates when calendar.txt is missing).",
      "England: 5,189 evening-isolated LSOAs (15.4%), 6,745 Sunday deserts (20.0%), mean SQI 65.4/100.",
    ],
    perCountry: {
      england: "BODS GTFS headways on LSOAs.",
      ireland: "TFI weekday quality, evening, Sunday on Small Areas.",
      netherlands: "OVapi weekday / evening / Sunday on buurten.",
      france: "NAP weekday / evening / Sunday on IRIS.",
    },
  },
  {
    slug: "network",
    path: "/briefings/network",
    title: "Network & operators",
    question: "How concentrated are the operators?",
    keywords: ["HHI", "route length", "stops per route", "operator concentration", "cross-LA"],
    body: [
      "One Herfindahl–Hirschman index on a 0–10,000 scale. Route-length and stops-per-route distributions are persisted (c1 / c2).",
      "England: 13,099 BODS routes, 1.75M trips, 274,719 stops; 37.7% of routes cross a local-authority boundary.",
    ],
    perCountry: {
      england: "BODS agencies, HHI, cross-LA routes.",
      ireland: "TFI agencies, one HHI.",
      netherlands: "OVapi agencies; bus vs all-PT labelled.",
      france: "NAP operators after dataset_id prefixing.",
    },
  },
  {
    slug: "correlations",
    path: "/briefings/correlations",
    title: "Correlations & ML",
    question: "Does coverage track deprivation — or something else?",
    keywords: ["Pearson", "Random Forest", "SHAP", "HDBSCAN", "nocar_pct"],
    body: [
      "One correlation matrix and one scatter per country, using that country’s deprivation index.",
      "England ML: Random Forest coverage prediction R² = 0.472; top SHAP feature nocar_pct; HDBSCAN + GMM clusters; Isolation Forest anomalies.",
    ],
    perCountry: {
      england: "IMD and nocar / rural features on LSOAs.",
      ireland: "Pobal HP matrix on Small Areas.",
      netherlands: "SES-WOA matrix on buurten.",
      france: "F-EDI matrix on IRIS.",
    },
  },
  {
    slug: "economy",
    path: "/briefings/economy",
    title: "Economy & carbon",
    question: "Who is in the people-gap — and is there a published unit cost?",
    keywords: ["people-gap", "DESNZ", "CO2", "carbon", "modal shift"],
    body: [
      "People-gap first. Money only appears when an official unit cost is cited for that country.",
      "England carbon uses DESNZ 2025 factors (bus 0.10385 kg/pax-km, diesel car 0.17304 kg/veh-km).",
    ],
    perCountry: {
      england: "DESNZ 2025 + people-gap on LSOAs.",
      ireland: "Illustrative EPA Ireland carbon only if cited; people-gap otherwise.",
      netherlands: "People-gap; no invented PBL euro.",
      france: "People-gap; no invented ADEME euro.",
    },
  },
  {
    slug: "policy",
    path: "/briefings/policy",
    title: "Policy programmes",
    question: "Which programmes apply here?",
    keywords: [
      "Bus Services Act 2025",
      "NTA",
      "Connecting Ireland",
      "OV-wet",
      "AOM",
      "SPC",
    ],
    body: [
      "Policy titles are local. England BSA 2025 is not applied to Ireland, the Netherlands, or France.",
    ],
    perCountry: {
      england: "Bus Services Act 2025, LTA franchising readiness.",
      ireland: "NTA Connecting Ireland, BusConnects, Local Link, PSO.",
      netherlands: "Concession / OV-wet programmes.",
      france: "AOM organising authorities and SPC programmes.",
    },
  },
  {
    slug: "scenarios",
    path: "/briefings/scenarios",
    title: "Scenarios",
    question: "Who moves if frequency or evenings change?",
    keywords: ["frequency restoration", "DRT", "last bus", "franchise scope"],
    body: [
      "Listed interventions × people × in-country deprivation. Currency only if that country published a unit cost.",
    ],
    perCountry: {
      england: "Frequency, last bus, DRT rural, franchise scope on LSOAs.",
      ireland: "Irish interventions × HP decile.",
      netherlands: "OV / flex × SES-WOA.",
      france: "SPC / rural holes × F-EDI.",
    },
  },
  {
    slug: "time",
    path: "/briefings/time",
    title: "Time series",
    question: "Did the network move while the census stayed still?",
    keywords: ["dated pack", "GTFS vintage", "census frozen"],
    body: [
      "Network packs are dated. Census and deprivation stay frozen. A second real GTFS pack is compared to the first — the warehouse is not cloned to fake a time series.",
    ],
    perCountry: {
      england: "Pack 2026-08-01 plus a second dated BODS pack.",
      ireland: "Pack 2026-08-13 plus a second TFI vintage.",
      netherlands: "Pack 2026-08-13 plus a second OVapi vintage.",
      france: "Pack 2026-08-17 plus a second NAP harvest date.",
    },
  },
  {
    slug: "reach",
    path: "/briefings/reach",
    title: "Reach & Studio",
    question: "What does a walk-to-stop change do on this filter?",
    keywords: ["service bands", "Studio", "r5py", "isochrone"],
    body: [
      "Service bands 1–6 are pre-computed. Studio patches a filter. 15 / 30 / 45 minute isochrones come from r5py to official destinations.",
    ],
    perCountry: {
      england: "LSOA bands; r5py to jobs, GPs, schools.",
      ireland: "Small Area bands; r5py to Republic destinations.",
      netherlands: "Buurt bands; r5py to Dutch destinations.",
      france: "IRIS bands; r5py to metropolitan destinations.",
    },
  },
  {
    slug: "ops",
    path: "/briefings/ops",
    title: "Ops & real-time",
    question: "What did the last official real-time feed actually say?",
    keywords: ["GTFS-RT", "SIRI", "TripUpdates", "AVL", "punctuality"],
    body: [
      "Ops is the last official GTFS-RT or SIRI rollup. No invented national on-time percentage.",
      "England punctuality uses TripUpdates delay when the BODS AVL zip includes it. Ireland uses the NTA key for the three published operators. France expands the NAP GTFS-RT harvest.",
    ],
    perCountry: {
      england: "BODS AVL / GTFS-RT TripUpdates.",
      ireland: "NTA TripUpdates — Dublin Bus, Bus Éireann, Go-Ahead.",
      netherlands: "OVapi RT rollup when present.",
      france: "NAP GTFS-RT harvest (not a national AOM %).",
    },
  },
  {
    slug: "destinations",
    path: "/briefings/destinations",
    title: "Jobs, GPs, and schools",
    question: "Which official destinations sit inside the catchment?",
    keywords: ["BRES", "NHS ODS", "GIAS", "huisarts", "2SFCA"],
    body: [
      "Access to jobs, primary care, and schools uses official point files for that country. England already joins BRES, NHS ODS, and GIAS. Ireland, the Netherlands, and France use their own official destination extracts — never an England file.",
    ],
    perCountry: {
      england: "BRES 2023 employment, 3,714 hospitals, 12,059 GPs, 3,336 secondary schools.",
      ireland: "Official Republic jobs, GP, and school destinations.",
      netherlands: "Official jobs, huisarts, and school destinations.",
      france: "Official metropolitan jobs, médecins, and school destinations.",
    },
  },
  {
    slug: "appraisal",
    path: "/briefings/appraisal",
    title: "In-country appraisal",
    question: "Which official economic method applies?",
    keywords: ["TAG", "Green Book", "CAF", "PAG", "MKBA", "BCR"],
    body: [
      "There is no EU-wide BCR. England uses TAG / Green Book. Ireland uses CAF / PAG. The Netherlands uses MKBA. France uses French socio-economic appraisal.",
    ],
    perCountry: {
      england: "TAG v2.03fc, Green Book NPV, BCR bands.",
      ireland: "CAF / PAG — not TAG.",
      netherlands: "MKBA — not TAG.",
      france: "French socio-economic method — not an EU BCR.",
    },
  },
  {
    slug: "realtime",
    path: "/briefings/realtime",
    title: "GTFS-RT and SIRI",
    question: "What did the last official real-time file contain?",
    keywords: ["GTFS-RT", "SIRI", "TripUpdates", "NTA", "NAP", "OVapi", "BODS"],
    body: [
      "Real-time is a dated rollup of official feeds. Missing delay fields stay empty. Ireland without a stored NTA key does not invent Dublin-wide punctuality. France does not turn a sample of NAP feeds into a national AOM on-time rate.",
    ],
    perCountry: {
      england: "BODS AVL zip + TripUpdates delay when present.",
      ireland: "NTA GTFS-RT for three operators.",
      netherlands: "OVapi GTFS-RT rollup.",
      france: "Expanded NAP GTFS-RT harvest.",
    },
  },
  {
    slug: "chat",
    path: "/briefings/chat",
    title: "Country-indexed chat",
    question: "Which narratives can the assistant cite?",
    keywords: ["FAISS", "RAG", "Gemini", "country-indexed"],
    body: [
      "Chat is country-indexed. England, Ireland, and France use FAISS over that country’s narratives. The Netherlands index is FAISS[netherlands] from OVapi × SES-WOA only. Answers cite the briefing; they do not invent travel times.",
    ],
    perCountry: {
      england: "FAISS[england].",
      ireland: "FAISS[ireland].",
      netherlands: "FAISS[netherlands].",
      france: "FAISS[france].",
    },
  },
]

export function countryByCode(code: string | undefined): CountryBrief | undefined {
  return COUNTRY_BRIEFS.find((c) => c.code === code)
}

export function topicBySlug(slug: string | undefined): TopicBrief | undefined {
  return TOPIC_BRIEFS.find((t) => t.slug === slug)
}

export const BRIEFINGS_INDEX = "/briefings"

export const PUBLIC_BRIEFING_PATHS: string[] = [
  "/",
  BRIEFINGS_INDEX,
  ...COUNTRY_BRIEFS.map((c) => c.path),
  ...TOPIC_BRIEFS.map((t) => t.path),
  "/methodology",
  "/about",
  "/contact",
  "/accessibility",
]
