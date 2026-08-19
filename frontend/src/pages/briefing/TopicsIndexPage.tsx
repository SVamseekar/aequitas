import { Link } from "react-router"
import { Seo } from "@/components/shared/Seo"
import { breadcrumbJsonLd } from "@/lib/structuredData"
import { COUNTRY_BRIEFS, TOPIC_BRIEFS } from "@/lib/briefingCatalog"
import { AUTHOR_NAME } from "@/lib/site"
import { BriefingLayout } from "./BriefingLayout"
import { LandingDimensions } from "@/components/landing/LandingDimensions"
import { LandingActions } from "@/components/landing/LandingActions"

export default function TopicsIndexPage() {
  const extra = TOPIC_BRIEFS.filter((t) =>
    ["destinations", "appraisal", "realtime", "chat"].includes(t.slug),
  )

  return (
    <BriefingLayout>
      <Seo
        title="Aequitas briefing topics — GTFS × official deprivation, four countries"
        description="Public index of Aequitas: England IMD/LSOA, Ireland Pobal HP/CSO, Netherlands SES-WOA/buurten, France F-EDI/IRIS. Equity, access, service, network, appraisal, GTFS-RT, r5py, chat."
        path="/briefings"
        jsonLd={breadcrumbJsonLd([{ name: "Briefings", path: "/briefings" }])}
      />

      <p className="text-xs font-medium uppercase tracking-wide text-[var(--l-rust)]">
        Briefings · {AUTHOR_NAME}
      </p>
      <h1 className="font-display text-3xl sm:text-4xl text-[var(--l-ink)] mt-2 mb-3 text-balance">
        Four countries. Same doors.
      </h1>
      <p className="text-[var(--l-slate)] max-w-2xl leading-relaxed text-pretty mb-10">
        Official timetables joined to official deprivation. Ranks never leave the country.
      </p>

      <div className="overflow-hidden rounded-2xl mb-12 aspect-[21/8] bg-[#1a1612]">
        <img
          src="/landing/briefings.jpg"
          alt="A map archive drawer being opened"
          className="h-full w-full object-cover"
          width={1920}
          height={730}
        />
      </div>

      <h2 className="text-lg font-semibold text-[var(--l-ink)] mb-4">Countries</h2>
      <ul className="divide-y divide-[var(--l-rule)] border-y border-[var(--l-rule)] mb-12">
        {COUNTRY_BRIEFS.map((c) => (
          <li key={c.code}>
            <Link
              to={c.path}
              className="flex flex-col sm:flex-row sm:items-baseline sm:justify-between gap-1 py-4 group"
            >
              <span className="font-display text-xl text-[var(--l-ink)] group-hover:text-[var(--l-rust)]">
                {c.name}
              </span>
              <span className="text-sm text-[var(--l-slate)]">
                {c.deprivation} · score {c.score}
              </span>
            </Link>
          </li>
        ))}
      </ul>

      <LandingDimensions embed />

      <h2 className="text-lg font-semibold text-[var(--l-ink)] mt-10 mb-4">Also in the method</h2>
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

      <div className="mt-12 pt-10 border-t border-[var(--l-rule)]">
        <LandingActions />
      </div>
    </BriefingLayout>
  )
}
