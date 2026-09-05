import { Link } from "react-router"
import { Seo } from "@/components/shared/Seo"
import { breadcrumbJsonLd } from "@/lib/structuredData"
import { COUNTRY_BRIEFS, TOPIC_BRIEFS } from "@/lib/briefingCatalog"
import { AUTHOR_NAME } from "@/lib/site"
import { BriefingLayout } from "./BriefingLayout"
import { LandingDimensions } from "@/components/landing/LandingDimensions"

export default function TopicsIndexPage() {
  const extra = TOPIC_BRIEFS.filter((t) =>
    ["destinations", "appraisal", "realtime", "chat"].includes(t.slug),
  )

  return (
    <BriefingLayout>
      <Seo
        title="Aequitas briefing topics — GTFS × official deprivation, four countries"
        description="Public index of Aequitas: England IMD/LSOA, Ireland Pobal HP/CSO, Netherlands SES-WOA/buurten, France F-EDI/IRIS. Equity, access, service, network, appraisal, GTFS-RT, r5py, chat."
        path="/topics"
        jsonLd={breadcrumbJsonLd([{ name: "Topics", path: "/topics" }])}
      />
      <p className="text-xs font-medium uppercase tracking-wide text-[var(--l-rust)]">
        Field map · {AUTHOR_NAME}
      </p>
      <h1 className="font-display text-3xl sm:text-4xl text-[var(--l-ink)] mt-2 mb-3 text-balance">
        Everything the briefing covers
      </h1>
      <p className="text-[var(--l-slate)] max-w-2xl leading-relaxed text-pretty mb-8">
        Same method in England, Ireland, the Netherlands, and France. Official
        timetables joined to official deprivation. Ranks never leave the country.
      </p>

      <h2 className="text-lg font-semibold text-[var(--l-ink)] mb-3">Countries</h2>
      <ul className="grid sm:grid-cols-2 gap-3 mb-4">
        {COUNTRY_BRIEFS.map((c) => (
          <li key={c.code}>
            <Link
              to={c.path}
              className="landing-card block p-4 hover:border-[var(--l-rust)]/40 transition-colors"
            >
              <p className="font-semibold text-[var(--l-ink)]">{c.name}</p>
              <p className="text-sm text-[var(--l-slate)] mt-1 text-pretty">
                {c.network} · {c.deprivation} · score {c.score}
              </p>
            </Link>
          </li>
        ))}
      </ul>

      <LandingDimensions embed />

      <h2 className="text-lg font-semibold text-[var(--l-ink)] mb-3">Also in the method</h2>
      <ul className="grid sm:grid-cols-2 gap-3">
        {extra.map((t) => (
          <li key={t.slug}>
            <Link
              to={t.path}
              className="landing-card block p-4 hover:border-[var(--l-rust)]/40 transition-colors"
            >
              <p className="font-semibold text-[var(--l-ink)]">{t.title}</p>
              <p className="text-sm text-[var(--l-slate)] mt-1">{t.question}</p>
            </Link>
          </li>
        ))}
      </ul>
    </BriefingLayout>
  )
}
