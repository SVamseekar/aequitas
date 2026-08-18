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

const SECTIONS = [
  {
    id: "join",
    title: "Join",
    body: "Official GTFS is joined to official small areas and that country’s deprivation index. England BODS × IMD. Ireland TFI × Pobal HP. Netherlands OVapi × SES-WOA. France NAP × F-EDI.",
  },
  {
    id: "rank",
    title: "Rank",
    body: "The 0–100 score uses 400 m coverage, evening service, weekday quality, and inverted coverage–deprivation correlation. Missing terms drop out. IMD, HP, SES-WOA, and F-EDI never share an axis.",
  },
  {
    id: "time",
    title: "Time",
    body: "Only the timetable pack time-travels. Census and deprivation stay frozen. A second dated GTFS pack is a real harvest — not a cloned warehouse.",
  },
  {
    id: "destinations",
    title: "Destinations",
    body: "Jobs, GPs, and schools use in-country point files. 15 / 30 / 45 minute reach appears only after r5py. Otherwise Reach shows service bands and an empty travel-time line.",
  },
  {
    id: "appraisal",
    title: "Appraisal",
    body: "England TAG / Green Book. Ireland CAF / PAG. Netherlands MKBA. France French socio-economic method. No EU-wide BCR.",
  },
  {
    id: "open",
    title: "Open",
    body: "The routing family is r5 / r5py. Warehouses stay on disk. These pages are the public briefing. Sign in is unchanged.",
  },
] as const

export default function MethodologyPage() {
  return (
    <BriefingLayout>
      <Seo
        title="How Aequitas is computed — four-country method"
        description="Official GTFS joined to official deprivation. Same score formula. Ranks stay in-country. England Gini 0.5741. No Europe-wide index."
        path="/methodology"
        jsonLd={breadcrumbJsonLd([{ name: "Method", path: "/methodology" }])}
      />

      <p className="text-xs font-medium uppercase tracking-wide text-[var(--l-rust)]">
        Method · {AUTHOR_NAME}
      </p>
      <h1 className="font-display text-3xl sm:text-4xl text-[var(--l-ink)] mt-2 mb-3">
        How it is computed
      </h1>
      <p className="text-[var(--l-slate)] max-w-2xl leading-relaxed mb-8 text-pretty">
        The warehouse is a dated lookup. These pages describe the method. The engine runs
        locally from official feeds.
      </p>

      <nav aria-label="Method sections" className="learn-nav">
        {SECTIONS.map((s) => (
          <a key={s.id} href={`#${s.id}`}>
            {s.title}
          </a>
        ))}
      </nav>

      <div className="grid lg:grid-cols-2 gap-8 items-center mb-14">
        <img
          src="/landing/method.jpg"
          alt="Maps, a clock, and a network sketch on a desk"
          width={1600}
          height={1000}
          className="rounded-2xl w-full aspect-[16/10] object-cover"
        />
        <p className="text-[var(--l-slate)] leading-relaxed text-pretty">
          One claim per section. The stack table is the source of truth for names and scores.
        </p>
      </div>

      <ol className="space-y-10 mb-14 max-w-2xl">
        {SECTIONS.map((section) => (
          <li key={section.id} id={section.id} className="scroll-mt-24">
            <h2 className="font-display text-2xl text-[var(--l-ink)]">{section.title}</h2>
            <p className="text-[var(--l-slate)] mt-2 leading-relaxed text-pretty">{section.body}</p>
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
        {m.qualityFails} failures.
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
        <Link to="/briefings" className="underline">
          All briefings
        </Link>
      </p>
    </BriefingLayout>
  )
}
