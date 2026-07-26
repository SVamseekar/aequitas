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

const DATASETS = [
  {
    name: "NaPTAN",
    detail: `${m.stops.toLocaleString("en-GB")} active bus stops (BCT/BCS/BCE, England ATCO prefix).`,
  },
  {
    name: "BODS GTFS",
    detail: `${m.routes.toLocaleString("en-GB")} unique routes, ${m.trips.toLocaleString("en-GB")} trips across operator feeds.`,
  },
  {
    name: "ONS Census 2021",
    detail: `${m.lsoas.toLocaleString("en-GB")} LSOAs, ${m.population.toLocaleString("en-GB")} population (TS001).`,
  },
  {
    name: "MHCLG IMD 2025",
    detail: `Indices of Multiple Deprivation — all ${m.lsoas.toLocaleString("en-GB")} LSOAs, zero code mismatch at join.`,
  },
  {
    name: "NOMIS BRES 2023",
    detail: "Employment counts for accessibility-to-jobs analysis.",
  },
  {
    name: "NHS ODS / GIAS",
    detail: "Hospitals, GP practices, and secondary schools for facility access metrics.",
  },
  {
    name: "DfT TAG v2.03fc",
    detail: "Transport Appraisal Guidance — values of time, BCR framing, appraisal parameters.",
  },
  {
    name: "DESNZ 2025",
    detail: "Greenhouse gas conversion factors for bus and car CO₂ intensities (carbon section j3).",
  },
] as const

export default function MethodologyPage() {
  const navigate = useNavigate()
  const description = `How Aequitas builds evidence-graded bus equity analytics: datasets, ${m.qualityChecks}/${m.qualityFails} quality checks, ${m.spatialJoinPct}% spatial join, TAG/Green Book appraisal, and known limitations.`

  return (
    <div className="min-h-screen app-atmosphere text-foreground">
      <Seo
        title="Methodology — Aequitas"
        description={description}
        path="/methodology"
        jsonLd={breadcrumbJsonLd([{ name: "Methodology", path: "/methodology" }])}
      />
      <div className="border-b border-white/50 bg-white/20 backdrop-blur-2xl">
        <div className="max-w-3xl mx-auto px-6 flex items-center min-h-11">
          <span className="text-sm text-muted-foreground">Methodology</span>
        </div>
      </div>

      <div className="max-w-3xl mx-auto px-6 py-12 sm:py-14">
        <button
          type="button"
          onClick={() => navigate(-1)}
          className="flex items-center gap-2 text-sm text-muted-foreground hover:text-foreground mb-8 transition-colors"
        >
          <ArrowLeft className="w-4 h-4" /> Back
        </button>

        <div className="h-px bg-primary/40 mb-8 max-w-xs" />
        <p className="marketing-eyebrow text-primary">Provenance</p>
        <h1 className="text-3xl sm:text-4xl font-bold tracking-tight mt-3 mb-4 text-foreground">
          Methodology &amp; data quality
        </h1>
        <p className="marketing-lede mb-12">
          Aequitas pre-computes all analytics offline into a read-only DuckDB warehouse. The web app
          is a lookup layer — not a live operational feed. Headline metrics below are locked to the
          metrics canon (warehouse built {m.warehouseBuiltAt}, pack {m.asOf}).
        </p>

        <section className="mb-12">
          <h2 className="text-lg font-semibold text-foreground mb-5">Datasets</h2>
          <div className="grid sm:grid-cols-2 gap-3">
            {DATASETS.map((s) => (
              <div key={s.name} className="app-glass-strong rounded-2xl border border-white/60 p-4">
                <p className="text-sm font-semibold text-primary mb-1.5">{s.name}</p>
                <p className="text-sm text-muted-foreground leading-relaxed">{s.detail}</p>
              </div>
            ))}
          </div>
        </section>

        <section className="mb-12">
          <h2 className="text-lg font-semibold text-foreground mb-5">Quality gates</h2>
          <div className="app-glass-strong rounded-2xl border border-white/60 p-5 marketing-body space-y-3">
            <p>
              Phase 0 EDA validation runs{" "}
              <strong className="text-foreground">
                {m.qualityChecks} automated checks
              </strong>{" "}
              with{" "}
              <strong className="text-foreground">{m.qualityFails} failures</strong>
              {m.qualityWarns > 0 ? (
                <>
                  {" "}
                  and {m.qualityWarns} warnings (documented, non-blocking)
                </>
              ) : null}
              . Pipeline stages do not promote a warehouse that fails hard gates.
            </p>
            <p>
              Spatial join of stops to LSOA geography achieves{" "}
              <strong className="text-foreground">
                {m.spatialJoinPct}% coverage
              </strong>{" "}
              on the England reference pack — residual unmapped points are tracked in audit outputs,
              not silently dropped from equity denominators without note.
            </p>
            <p>
              Scale of the reference warehouse: {m.tripsDisplay} GTFS trips ·{" "}
              {m.routes.toLocaleString("en-GB")} routes · {m.stops.toLocaleString("en-GB")} stops ·{" "}
              {m.lsoas.toLocaleString("en-GB")} LSOAs · {m.sections} analytical sections across{" "}
              {m.dimensions} policy dimensions.
            </p>
          </div>
        </section>

        <section className="mb-12">
          <h2 className="text-lg font-semibold text-foreground mb-5">
            Equity &amp; appraisal standards
          </h2>
          <div className="app-glass-strong rounded-2xl border border-white/60 p-5 marketing-body space-y-3">
            <p>
              National bus service inequality (headline pack): Gini{" "}
              <strong className="text-foreground tabular-nums">{formatGini(m.gini)}</strong>, Palma{" "}
              <strong className="text-foreground tabular-nums">{formatPalma(m.palma)}</strong>,
              concentration index{" "}
              <strong className="text-foreground tabular-nums">
                {formatConcentrationIndex(m.concentrationIndex)}
              </strong>
              . Evening isolation {m.eveningIsolatedPct.toFixed(1)}% of LSOAs; Sunday deserts{" "}
              {m.sundayDesertPct.toFixed(1)}%.
            </p>
            <p>
              Economic appraisal sections follow <strong className="text-foreground">DfT TAG</strong>{" "}
              parameterisation (v2.03fc) and <strong className="text-foreground">Green Book</strong>{" "}
              framing for BCR/NPV-style indicators. Figures are indicative policy-exploration
              estimates — not DfT-accredited scheme appraisals.
            </p>
            <p>
              Machine learning: Random Forest coverage prediction (R²={m.rfR2}), clustering and
              anomaly models trained on Phase 0 audit features. SHAP explanations support feature
              importance narratives.
            </p>
          </div>
        </section>

        <section className="mb-12">
          <h2 className="text-lg font-semibold text-foreground mb-5">Limitations</h2>
          <div className="app-glass-strong rounded-2xl border border-white/60 p-5 marketing-body">
            <ul className="list-disc pl-5 space-y-2.5">
              <li>
                Point-in-time snapshots (timetables, Census, IMD, BRES) — not a live operational
                network monitor.
              </li>
              <li>
                England-only LSOA coverage; Scotland, Wales, and Northern Ireland are out of scope.
              </li>
              <li>
                Some region × urban/rural filters yield empty or thin results (e.g. London × rural
                under RUC) — the UI surfaces this as geography, not a data outage.
              </li>
              <li>
                Chatbot answers are grounded in pre-computed narratives via RAG; they can still err
                and must be verified against primary sources before formal use.
              </li>
              <li>
                Not official government guidance — see the{" "}
                <Link to="/disclaimer" className="text-primary hover:underline font-medium">
                  disclaimer
                </Link>
                .
              </li>
            </ul>
          </div>
        </section>

        <p className="text-sm text-muted-foreground">
          Related:{" "}
          <Link to="/about" className="text-primary hover:underline">
            About
          </Link>
          {" · "}
          <Link to="/accessibility" className="text-primary hover:underline">
            Accessibility statement
          </Link>
          {" · "}
          <Link to="/contact" className="text-primary hover:underline">
            Contact
          </Link>
        </p>
      </div>
    </div>
  )
}
