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
        <p className="text-sm text-muted-foreground mb-6">
          Four countries, one method: GTFS × official small areas × in-country deprivation ranks.
          Never plot IMD, Pobal HP, SES-WOA, and F-EDI as one number. Router: R5/r5py + Geofabrik OSM
          (Wave 2). Ireland (Wave 5) uses TFI GTFS, CSO Small Areas 2022, and Pobal HP 2022
          (never IMD) inside the Republic only. Studio (Wave 3) applies a drawn or uploaded patch: walk-to-stop 400 m and the
          Wave 2 score without Java; 15/30/45 who-gains only when r5py actually runs — never a made-up
          frequency multiplier. France deprivation falls back to a documented Filosofi proxy if F-EDI is not free.
        </p>
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
          <h2 className="text-lg font-semibold text-foreground mb-5">Monthly network dates (Wave 6)</h2>
          <div className="app-glass-strong rounded-2xl border border-white/60 p-5 marketing-body space-y-3">
            <p>
              <code>/app/:country/time</code> plots the same in-country score (and 400 m share)
              across dated warehouse packs. Only the <strong className="text-foreground">network</strong>{" "}
              (England BODS / Ireland TFI) is allowed to time-travel.
            </p>
            <p>
              Frozen in every pack: <strong className="text-foreground">Census 2021</strong> LSOAs
              and population, <strong className="text-foreground">IMD 2025</strong> ranks,
              Ireland <strong className="text-foreground">CSO Small Areas 2022</strong> and{" "}
              <strong className="text-foreground">Pobal HP 2022</strong>. Those vintages are not
              rewritten as if they moved each month.
            </p>
            <p>
              Packs live under <code>data/packs/{"{country}"}/{"{YYYY-MM-DD}"}/</code> with a tiny
              manifest. <code>uv run aequitas refresh</code> writes a new date then swaps current
              if sanity passes. One date in the checkout is still a valid page — not a blank.
            </p>
          </div>
        </section>

        <section className="mb-12">
          <h2 className="text-lg font-semibold text-foreground mb-5">Ireland pack (Wave 5)</h2>
          <div className="app-glass-strong rounded-2xl border border-white/60 p-5 marketing-body space-y-3">
            <p>
              The Republic pack joins <strong className="text-foreground">TFI GTFS_All.zip</strong>{" "}
              stops and stop_times to <strong className="text-foreground">CSO Small Areas 2022</strong>{" "}
              and the <strong className="text-foreground">Pobal HP Deprivation Index 2022</strong>{" "}
              relative index and in-country decile. That is not IMD and is never plotted against IMD.
            </p>
            <p>
              Evening isolation is no TFI departure at or after 19:00 on a weekday calendar date.
              Urban/rural is a documented density rule (people per km² ≥ 150), not England RUC codes.
              Northern Ireland is out of scope (different deprivation measure).
            </p>
            <p>
              TAG/BCR and the Bus Services Act 2025 are England-only. 15/30/45 is not invented if
              r5py has not been run. Warehouse: <code>data/aequitas_ireland.duckdb</code> — the API
              never falls back to England when <code>country=ireland</code>.
            </p>
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
          <h2 className="text-lg font-semibold text-foreground mb-5">In-country score and r5py reach</h2>
          <div className="app-glass-strong rounded-2xl border border-white/60 p-5 marketing-body space-y-3">
            <p>
              The quoteable England score is{" "}
              <strong className="text-foreground">0–100 for the active filter</strong>, not a
              Europe-wide index. Formula:{" "}
              <code className="text-xs">
                100 × (0.40 × people within 400 m + 0.25 × evening served + 0.20 × weekday
                quality/100 + 0.15 × (1 − |coverage–deprivation r|))
              </code>
              . Each term is clipped to 0–1. If a term is missing for a cut, it is dropped, weights
              are renormalised, and the UI says so. National evening 15.4% is never reused on a
              filtered view.
            </p>
            <p>
              15 / 30 / 45 minute job, GP, and school counts are precomputed with{" "}
              <strong className="text-foreground">R5 + r5py</strong> (Java 17), Geofabrik OSM PBF,
              and BODS GTFS. Unit: destinations reachable from the LSOA centroid — not Hansen, not
              PTAL (Wave 4). Full England can take many hours; this pack only shows geographies that
              exist in <code className="text-xs">processed/reach/lsoa_access_times.parquet</code>.
              Missing ITL1s are named on the Access and Reach pages, not filled with invented bars.
              This checkout has <strong className="text-foreground">no ITL1 with r5py times</strong>
              until you place a Geofabrik PBF, BODS GTFS, destination Parquets, and run{" "}
              <code className="text-xs">uv run aequitas reach --region E12000005</code>.
            </p>
            <p>
              <strong className="text-foreground">Aequitas service / access bands</strong> are not
              TfL PTAL and are never labelled official PTAL. Without travel times, every LSOA gets a
              service band: 1 = no stop within 400 m or no weekday service; 2 = stop nearby but
              evening and Sunday isolated; otherwise weekday SQI thresholds 30 / 50 / 70 for bands
              3–6. When r5py job counts exist, that LSOA uses a travel-time band from nested
              destination counts (not Hansen). Hansen would be{" "}
              <code className="text-xs">sum dest × exp(−0.05 t)</code> and needs minutes, which this
              parquet does not store.
            </p>
            <p>
              The downloadable briefing pack (<code className="text-xs">/api/export/pack.csv</code>{" "}
              and printable HTML) is a <strong className="text-foreground">research pack</strong>,
              not a statutory BSIP submission.
            </p>
            <p>
              Maps use MapLibre with free CARTO/OSM raster tiles. Attribution: OpenStreetMap
              contributors and CARTO. No Mapbox token.
            </p>
            <p>
              Studio walk-to-stop uses ONS Open Geography{" "}
              <strong className="text-foreground">
                LSOA (December 2021) England and Wales population-weighted centroids
              </strong>{" "}
              (item 32729e42d05e4e23bc7e43a36aa4ae8b; British National Grid converted to WGS84),
              joined to Census 2021 LSOA codes in this pack. Adding or removing a stop measures
              people newly inside or outside 400 m of a stop for the active filter, then the same
              in-country score function. That is not 15/30/45-minute job access. Frequency and new
              corridors still need r5py.
            </p>
          </div>
        </section>

        <section className="mb-12">
          <h2 className="text-lg font-semibold text-foreground mb-5">Limitations</h2>
          <div className="app-glass-strong rounded-2xl border border-white/60 p-5 marketing-body">
            <ul className="list-disc pl-5 space-y-2.5">
              <li>
                Point-in-time snapshots (timetables, Census, IMD, BRES). Ops is a collector
                rollup of official GTFS-RT / SIRI where a feed exists — not live-to-the-second,
                not a national punctuality index.
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
