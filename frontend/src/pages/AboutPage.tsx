import { useNavigate } from "react-router"
import { ArrowLeft } from "lucide-react"

const DIMENSIONS = [
  { name: "Equity & Deprivation", metrics: "Gini coefficient (0.574), Lorenz curve, Palma ratio (5.70×), Concentration Index (+0.1358 pro-rich), triple-deprived LSOAs (612, 1.8%)." },
  { name: "Accessibility", metrics: "2SFCA with 400m Euclidean catchment — gaps to jobs (BRES 2023), NHS hospitals/GPs, and secondary schools. 6,776 LSOAs with zero access." },
  { name: "Service Quality", metrics: "Headway analysis, evening isolation (5,189 LSOAs, 15.4%), Sunday deserts (6,745, 20.0%), mean SQI 65.4/100." },
  { name: "Route Network", metrics: "13,099 deduplicated BODS routes, 7,241 with geometry (53.1%), mean length 23.0 km, operator HHI concentration, 37.7% cross-LA." },
  { name: "Modal Shift & Carbon", metrics: "DfT elasticity-based modal shift estimates. DESNZ 2025: bus 0.10385 kg CO₂/pax-km, car 0.17304 kg/veh-km." },
  { name: "Economic Appraisal", metrics: "BCR via TAG v2.03fc, Green Book NPV, GDP multipliers. Investment gap per LSOA below minimum service threshold." },
  { name: "Bus Services Act 2025", metrics: "LTA franchising readiness tiers, operator concentration per region, compliance gap assessment." },
  { name: "Policy Scenarios", metrics: "Parameterised modelling: frequency restoration (+10-50%), last bus extension (to 22:00-23:00), DRT rural coverage, franchise scope." },
]

const DATA_SOURCES = [
  { name: "NaPTAN", desc: "274,719 active bus stops (BCT/BCS/BCE, England ATCO prefix)" },
  { name: "BODS GTFS", desc: "13,099 unique routes, 1,752,443 trips across 9 operator feeds" },
  { name: "ONS Census 2021", desc: "33,755 LSOAs, 56,490,056 population (TS001)" },
  { name: "MHCLG IMD 2025", desc: "Indices of Multiple Deprivation — all 33,755 LSOAs, zero mismatch" },
  { name: "NOMIS BRES 2023", desc: "Employment data — 6,791 MSOAs, 27,343,200 England employees" },
  { name: "NHS ODS", desc: "3,714 hospitals and 12,059 GP practices (geocoded)" },
  { name: "GIAS", desc: "3,336 secondary and all-through schools (England bounding box)" },
  { name: "DfT TAG v2.03fc", desc: "Transport Appraisal Guidance — VoT, BCR bands, appraisal methodology" },
  { name: "DESNZ 2025", desc: "Greenhouse gas conversion factors — bus and car CO₂ emission intensities" },
  { name: "Code-Point Open", desc: "1,492,016 England postcodes for spatial joins" },
]

export default function AboutPage() {
  const navigate = useNavigate()

  return (
    <div className="min-h-screen bg-background">
      <div className="border-b border-border bg-card/50">
        <div className="max-w-4xl mx-auto px-4 flex items-center h-8">
          <span className="text-[9px] font-mono text-muted-foreground uppercase tracking-widest">About</span>
        </div>
      </div>

      <div className="max-w-4xl mx-auto px-4 py-12">
        <button
          onClick={() => navigate(-1)}
          className="flex items-center gap-2 text-xs text-muted-foreground hover:text-foreground mb-8 font-mono transition-colors"
        >
          <ArrowLeft className="w-3.5 h-3.5" /> BACK
        </button>

        <div className="h-px bg-indigo-500/40 mb-8 max-w-xs" />
        <span className="text-[10px] font-mono uppercase tracking-[0.2em] text-indigo-400 font-medium">About Aequitas</span>
        <h1 className="text-2xl font-bold tracking-tight mt-3 mb-4 text-foreground">
          UK Bus Transport Policy Intelligence
        </h1>
        <p className="text-sm text-muted-foreground leading-relaxed mb-10 max-w-2xl">
          Aequitas is a policy intelligence platform for UK government, Local Transport Authorities (LTAs),
          and transport researchers. It pre-computes evidence-graded analytics across 8 policy dimensions,
          covering all 33,755 LSOAs in England, and provides a Gemini-powered natural language interface
          for policy Q&A grounded in the pre-computed data.
        </p>

        <section className="mb-12">
          <h2 className="text-[10px] uppercase tracking-[0.15em] text-muted-foreground font-mono mb-6">
            8 Policy Dimensions
          </h2>
          <div className="space-y-4">
            {DIMENSIONS.map((d) => (
              <div key={d.name} className="border border-border rounded bg-card p-4">
                <p className="text-xs font-semibold text-indigo-400 mb-1">{d.name}</p>
                <p className="text-xs text-muted-foreground leading-relaxed">{d.metrics}</p>
              </div>
            ))}
          </div>
        </section>

        <section className="mb-12">
          <h2 className="text-[10px] uppercase tracking-[0.15em] text-muted-foreground font-mono mb-6">
            Data Sources
          </h2>
          <div className="grid sm:grid-cols-2 gap-3">
            {DATA_SOURCES.map((s) => (
              <div key={s.name} className="border border-border rounded bg-card p-3">
                <p className="text-[10px] font-mono text-indigo-400 uppercase tracking-wider mb-1">{s.name}</p>
                <p className="text-xs text-muted-foreground">{s.desc}</p>
              </div>
            ))}
          </div>
        </section>

        <section>
          <h2 className="text-[10px] uppercase tracking-[0.15em] text-muted-foreground font-mono mb-4">
            Methodology
          </h2>
          <div className="border border-border rounded bg-card p-4 text-xs text-muted-foreground leading-relaxed space-y-2">
            <p>All analytics are pre-computed at build time via a Python pipeline. The DuckDB warehouse
              is a read-only lookup store — zero runtime analytics. Every metric on screen traces to
              a specific column in a specific Parquet file, derived from the Phase 0 EDA notebooks
              (19 notebooks, 103 checks, 0 failures).</p>
            <p>Machine learning: Random Forest coverage prediction (R²=0.472), HDBSCAN+GMM LSOA clustering,
              Isolation Forest + LOF anomaly detection. All models trained on Phase 0 audit outputs.</p>
            <p>The RAG chatbot retrieves from ~1,365 pre-computed narratives using FAISS +
              all-MiniLM-L6-v2 embeddings, then grounds Gemini Flash responses in retrieved context.
              Citations are required; hallucination patterns are detected and suppressed.</p>
          </div>
        </section>
      </div>
    </div>
  )
}
