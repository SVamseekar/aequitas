import { Link } from "react-router"
import { Seo } from "@/components/shared/Seo"
import { breadcrumbJsonLd } from "@/lib/structuredData"
import { COUNTRY_BRIEFS } from "@/lib/briefingCatalog"
import { AUTHOR_NAME } from "@/lib/site"
import {
  METRICS_CANON,
  formatGini,
  formatPalma,
  formatConcentrationIndex,
} from "@/lib/metricsCanon"
import { BriefingLayout } from "./briefing/BriefingLayout"

const m = METRICS_CANON

const RULES = [
  {
    title: "One method, four countries",
    body: "Official GTFS × official small areas × that country’s deprivation index. Ranks never leave the country.",
  },
  {
    title: "No Europe-wide index",
    body: "IMD, Pobal HP, SES-WOA, and F-EDI are never plotted on one axis.",
  },
  {
    title: "Dated packs",
    body: "Only the network timetable time-travels. Census and deprivation stay frozen.",
  },
  {
    title: "Empty stays empty",
    body: "15 / 30 / 45 minutes appear only after r5py. Missing GTFS-RT delay is not filled in.",
  },
  {
    title: "Local appraisal",
    body: "England TAG / Green Book. Ireland CAF / PAG. Netherlands MKBA. France French socio-economic method. No EU-wide BCR.",
  },
]

export default function MethodologyPage() {
  return (
    <BriefingLayout>
      <Seo
        title="How Aequitas is computed — four-country method"
        description="Official GTFS joined to official deprivation. Same score formula. Ranks stay in-country. England Gini 0.5741. No Europe-wide index."
        path="/methodology"
        jsonLd={breadcrumbJsonLd([{ name: "Methodology", path: "/methodology" }])}
      />

      <p className="text-xs font-medium uppercase tracking-wide text-[var(--l-rust)]">
        Method · {AUTHOR_NAME}
      </p>
      <h1 className="font-display text-3xl sm:text-4xl text-[var(--l-ink)] mt-2 mb-3">
        How it is computed
      </h1>
      <p className="text-[var(--l-slate)] max-w-2xl leading-relaxed mb-10">
        The warehouse is a dated lookup. These pages describe the method. The engine runs
        locally from official feeds.
      </p>

      <ol className="space-y-4 mb-12 max-w-2xl">
        {RULES.map((rule, i) => (
          <li key={rule.title} className="flex gap-4">
            <span className="font-display text-xl text-[var(--l-rust)]/50 tabular-nums w-7 shrink-0">
              {String(i + 1).padStart(2, "0")}
            </span>
            <div>
              <h2 className="font-semibold text-[var(--l-ink)]">{rule.title}</h2>
              <p className="text-sm text-[var(--l-slate)] mt-1 leading-relaxed">{rule.body}</p>
            </div>
          </li>
        ))}
      </ol>

      <h2 className="text-lg font-semibold text-[var(--l-ink)] mb-3">Stacks</h2>
      <div className="overflow-x-auto mb-12">
        <table className="w-full text-sm text-left border-collapse">
          <thead>
            <tr className="border-b border-[var(--l-rule)] text-[var(--l-slate)]">
              <th className="py-2 pr-4 font-medium">Country</th>
              <th className="py-2 pr-4 font-medium">Network</th>
              <th className="py-2 pr-4 font-medium">Deprivation</th>
              <th className="py-2 pr-4 font-medium">Geography</th>
              <th className="py-2 font-medium">Score</th>
            </tr>
          </thead>
          <tbody>
            {COUNTRY_BRIEFS.map((c) => (
              <tr key={c.code} className="border-b border-[var(--l-rule)]/70">
                <td className="py-2.5 pr-4">
                  <Link to={c.path} className="font-medium text-[var(--l-ink)] hover:text-[var(--l-rust)]">
                    {c.name}
                  </Link>
                </td>
                <td className="py-2.5 pr-4 text-[var(--l-slate)]">{c.network}</td>
                <td className="py-2.5 pr-4 text-[var(--l-slate)]">{c.deprivation}</td>
                <td className="py-2.5 pr-4 text-[var(--l-slate)]">{c.areaUnit}</td>
                <td className="py-2.5 tabular-nums text-[var(--l-ink)]">{c.score}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <h2 className="text-lg font-semibold text-[var(--l-ink)] mb-3">England reference pack</h2>
      <p className="text-sm text-[var(--l-slate)] mb-4 max-w-2xl">
        Warehouse {m.warehouseBuiltAt}, pack {m.asOf}. {m.qualityChecks} quality checks,{" "}
        {m.qualityFails} failures. Score = 100 × (0.40 × people within 400 m + 0.25 × evening
        served + 0.20 × weekday quality + 0.15 × (1 − |coverage–deprivation r|)).
      </p>
      <dl className="grid grid-cols-2 sm:grid-cols-4 gap-4 mb-12 text-sm">
        <div>
          <dt className="text-[var(--l-slate)]">Gini</dt>
          <dd className="font-display text-2xl tabular-nums">{formatGini(m.gini)}</dd>
        </div>
        <div>
          <dt className="text-[var(--l-slate)]">Palma</dt>
          <dd className="font-display text-2xl tabular-nums">{formatPalma(m.palma)}</dd>
        </div>
        <div>
          <dt className="text-[var(--l-slate)]">Concentration</dt>
          <dd className="font-display text-2xl tabular-nums">
            {formatConcentrationIndex(m.concentrationIndex)}
          </dd>
        </div>
        <div>
          <dt className="text-[var(--l-slate)]">Scale</dt>
          <dd className="font-medium text-[var(--l-ink)] mt-1">
            {m.tripsDisplay} trips · {m.lsoas.toLocaleString("en-GB")} LSOAs
          </dd>
        </div>
      </dl>

      <p className="text-sm text-[var(--l-slate)]">
        Not official government guidance.{" "}
        <Link to="/disclaimer" className="underline">
          Disclaimer
        </Link>
        {" · "}
        <Link to="/topics" className="underline">
          All topics
        </Link>
      </p>
    </BriefingLayout>
  )
}
