import { Link, useNavigate } from "react-router"
import { ArrowLeft } from "lucide-react"
import { Seo } from "@/components/shared/Seo"
import {
  METRICS_CANON,
  formatConcentrationIndex,
  formatGini,
  formatPalma,
} from "@/lib/metricsCanon"
import { breadcrumbJsonLd } from "@/lib/structuredData"

const m = METRICS_CANON

const DIMENSIONS = [
  {
    name: "Equity & Deprivation",
    metrics: `Gini coefficient (${formatGini(m.gini)}), Lorenz curve, Palma ratio (${formatPalma(m.palma)}), Concentration Index (${formatConcentrationIndex(m.concentrationIndex)} pro-rich), triple-deprived LSOAs (${m.tripleDeprivedLsoas.toLocaleString("en-GB")}, 1.8%).`,
  },
  {
    name: "Accessibility",
    metrics:
      "2SFCA with 400m Euclidean catchment — gaps to jobs (BRES 2023), NHS hospitals/GPs, and secondary schools. 6,776 LSOAs with zero access.",
  },
  {
    name: "Service Quality",
    metrics: `Headway analysis, evening isolation (${m.eveningIsolatedLsoas.toLocaleString("en-GB")} LSOAs, ${m.eveningIsolatedPct.toFixed(1)}%), Sunday deserts (${m.sundayDesertLsoas.toLocaleString("en-GB")}, ${m.sundayDesertPct.toFixed(1)}%), mean SQI 65.4/100.`,
  },
  {
    name: "Route Network",
    metrics: `${m.routes.toLocaleString("en-GB")} deduplicated BODS routes, 7,241 with geometry (53.1%), mean length 23.0 km, operator HHI concentration, 37.7% cross-LA.`,
  },
  {
    name: "Socio-Economic & ML",
    metrics: `Deprivation correlations, Random Forest coverage prediction (R²=${m.rfR2}), HDBSCAN clustering, Isolation Forest anomalies, SHAP feature importance.`,
  },
  {
    name: "Economic Appraisal",
    metrics:
      "BCR via TAG v2.03fc, Green Book NPV, GDP multipliers. Investment gap per LSOA below minimum service threshold. Carbon / modal shift under DESNZ 2025 factors (j3).",
  },
  {
    name: "Bus Services Act 2025",
    metrics:
      "LTA franchising readiness tiers, operator concentration per region, compliance gap assessment.",
  },
  {
    name: "Policy Scenarios",
    metrics:
      "Parameterised modelling: frequency restoration (+10-50%), last bus extension (to 22:00-23:00), DRT rural coverage, franchise scope.",
  },
]

const DATA_SOURCES = [
  {
    name: "NaPTAN",
    desc: `${m.stops.toLocaleString("en-GB")} active bus stops (BCT/BCS/BCE, England ATCO prefix)`,
  },
  {
    name: "BODS GTFS",
    desc: `${m.routes.toLocaleString("en-GB")} unique routes, ${m.trips.toLocaleString("en-GB")} trips across 9 operator feeds`,
  },
  {
    name: "ONS Census 2021",
    desc: `${m.lsoas.toLocaleString("en-GB")} LSOAs, ${m.population.toLocaleString("en-GB")} population (TS001)`,
  },
  {
    name: "MHCLG IMD 2025",
    desc: `Indices of Multiple Deprivation — all ${m.lsoas.toLocaleString("en-GB")} LSOAs, zero mismatch`,
  },
  { name: "NOMIS BRES 2023", desc: "Employment data — 6,791 MSOAs, 27,343,200 England employees" },
  { name: "NHS ODS", desc: "3,714 hospitals and 12,059 GP practices (geocoded)" },
  { name: "GIAS", desc: "3,336 secondary and all-through schools (England bounding box)" },
  {
    name: "DfT TAG v2.03fc",
    desc: "Transport Appraisal Guidance — VoT, BCR bands, appraisal methodology",
  },
  {
    name: "DESNZ 2025",
    desc: "Greenhouse gas conversion factors — bus and car CO₂ emission intensities",
  },
  { name: "Code-Point Open", desc: "1,492,016 England postcodes for spatial joins" },
]

export default function AboutPage() {
  const navigate = useNavigate()

  return (
    <div className="min-h-screen app-atmosphere text-foreground">
      <Seo
        title="About Aequitas — England, Ireland, Netherlands, France | Marti Soura Vamseekar"
        description={`Aequitas joins official GTFS to official deprivation in four countries (IMD, Pobal HP, SES-WOA, F-EDI). ${m.sections} sections. Built by Marti Soura Vamseekar.`}
        path="/about"
        jsonLd={breadcrumbJsonLd([{ name: "About", path: "/about" }])}
      />
      <div className="border-b border-white/50 bg-white/20 backdrop-blur-2xl">
        <div className="max-w-3xl mx-auto px-6 flex items-center min-h-11">
          <span className="text-sm text-muted-foreground">About</span>
        </div>
      </div>

      <div className="max-w-3xl mx-auto px-6 py-12 sm:py-14">
        <button
          onClick={() => navigate(-1)}
          className="flex items-center gap-2 text-sm text-muted-foreground hover:text-foreground mb-8 transition-colors"
        >
          <ArrowLeft className="w-4 h-4" /> Back
        </button>

        <div className="h-px bg-primary/40 mb-8 max-w-xs" />
        <p className="marketing-eyebrow text-primary">About Aequitas</p>
        <h1 className="text-3xl sm:text-4xl font-bold tracking-tight mt-3 mb-4 text-foreground">
          Official timetables × official deprivation, four countries
        </h1>
        <p className="marketing-lede mb-12">
          Aequitas is a briefing method by Marti Soura Vamseekar: the same doors in England
          (BODS, IMD, LSOA), Ireland (TFI, Pobal HP, CSO Small Areas), the Netherlands (OVapi,
          SES-WOA, buurten), and France (NAP, F-EDI, IRIS). Ranks never leave the country.{" "}
          {m.sections} analytical sections on the England reference warehouse; country packs
          carry the same doors. Chat is country-indexed (FAISS).
        </p>

        <section className="mb-12">
          <h2 className="text-lg font-semibold text-foreground mb-5">
            {m.dimensions} Policy Dimensions
          </h2>
          <div className="space-y-4">
            {DIMENSIONS.map((d) => (
              <div key={d.name} className="app-glass-strong rounded-2xl border border-white/60 p-5">
                <p className="marketing-card-title mb-2">{d.name}</p>
                <p className="marketing-body">{d.metrics}</p>
              </div>
            ))}
          </div>
        </section>

        <section className="mb-12">
          <h2 className="text-lg font-semibold text-foreground mb-5">Data Sources</h2>
          <div className="grid sm:grid-cols-2 gap-3">
            {DATA_SOURCES.map((s) => (
              <div key={s.name} className="app-glass-strong rounded-2xl border border-white/60 p-4">
                <p className="text-sm font-semibold text-primary mb-1.5">{s.name}</p>
                <p className="text-sm text-muted-foreground leading-relaxed">{s.desc}</p>
              </div>
            ))}
          </div>
        </section>

        <section>
          <h2 className="text-lg font-semibold text-foreground mb-5">Methodology</h2>
          <div className="app-glass-strong rounded-2xl border border-white/60 p-5 marketing-body space-y-3">
            <p>
              All analytics are pre-computed at build time via a Python pipeline. The DuckDB
              warehouse is a read-only lookup store — zero runtime analytics. Every metric on
              screen traces to a specific column in a specific Parquet file, derived from the Phase
              0 EDA notebooks ({m.qualityChecks} checks, {m.qualityFails} failures
              {m.qualityWarns > 0 ? `, ${m.qualityWarns} warnings` : ""}).
            </p>
            <p>
              Machine learning: Random Forest coverage prediction (R²={m.rfR2}), HDBSCAN+GMM LSOA
              clustering, Isolation Forest + LOF anomaly detection. All models trained on Phase 0
              audit outputs.
            </p>
            <p>
              The RAG chatbot retrieves from pre-computed narratives across {m.sections} analytical
              sections using FAISS + all-MiniLM-L6-v2 embeddings, then grounds Gemini Flash
              responses in retrieved context. Citations are required; hallucination patterns are
              detected and suppressed.
            </p>
            <p>
              Full public write-up:{" "}
              <Link to="/methodology" className="text-primary hover:underline font-medium">
                Methodology &amp; data quality
              </Link>
              .
            </p>
          </div>
        </section>
      </div>
    </div>
  )
}
