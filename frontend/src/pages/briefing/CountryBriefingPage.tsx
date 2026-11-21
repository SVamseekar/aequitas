import { Link, useParams } from "react-router"
import { Seo } from "@/components/shared/Seo"
import { breadcrumbJsonLd } from "@/lib/structuredData"
import { AUTHOR_NAME } from "@/lib/site"
import { countryByCode, TOPIC_BRIEFS, type CountryCode } from "@/lib/briefingCatalog"
import { PublicCountryEvidence } from "@/components/briefing/PublicCountryEvidence"
import { BriefingLayout } from "./BriefingLayout"

export default function CountryBriefingPage({ code }: { code?: CountryCode }) {
  const params = useParams()
  const country = countryByCode(code ?? params.country)
  if (!country) {
    return (
      <BriefingLayout>
        <h1 className="text-2xl font-semibold">Country not found</h1>
        <Link to="/briefings" className="text-[var(--l-rust)] text-sm">
          All briefings
        </Link>
      </BriefingLayout>
    )
  }

  const rows = [
    ["Network", country.network],
    ["Deprivation", country.deprivation],
    ["Geography", country.geography],
    ["Policy", country.policyTitle],
    ["Appraisal", country.appraisal],
    ["Real-time", country.realtime],
  ] as const

  return (
    <BriefingLayout>
      <Seo
        title={`${country.name} bus equity — ${country.deprivation} × ${country.network.split(" ")[0]} | Aequitas`}
        description={country.description}
        path={country.path}
        jsonLd={breadcrumbJsonLd([
          { name: "Briefings", path: "/briefings" },
          { name: country.name, path: country.path },
        ])}
      />
      <p className="text-xs font-medium uppercase tracking-wide text-[var(--l-rust)]">
        Briefings / {country.name}
      </p>
      <h1 className="font-display text-3xl sm:text-4xl text-[var(--l-ink)] mt-2 mb-6 text-balance">
        {country.name} transport equity briefing
      </h1>
      <p className="public-briefing-lede">{country.description}</p>
      <PublicCountryEvidence key={country.code} code={country.code} name={country.name} />
      <div className="public-briefing-details">
      <aside className="public-briefing-about"><h2>About this briefing</h2>
      <dl className="grid sm:grid-cols-2 gap-x-8 gap-y-3 mb-10 text-sm">
        {rows.map(([k, v]) => (
          <div key={k} className="border-b border-[var(--l-rule)] pb-2">
            <dt className="text-[11px] uppercase tracking-wide text-[var(--l-slate)]">{k}</dt>
            <dd className="mt-0.5 text-[var(--l-ink)]">{v}</dd>
          </div>
        ))}
      </dl>

      <div className="public-briefing-actions"><Link to="/contact" className="landing-btn-primary">Discuss a briefing</Link><Link to={`/app/${country.code}`} className="landing-btn-secondary">Open local pack</Link></div>
      </aside>
      <section><h2 className="text-2xl mb-2">Explore the evidence</h2><p className="mb-4 text-sm text-muted-foreground">Dive into a topic or open the full analytical briefing.</p>
      <ul className="grid sm:grid-cols-2 gap-x-6 gap-y-2 mb-10 text-sm">
        {TOPIC_BRIEFS.filter((t) =>
          !["destinations", "appraisal", "realtime", "chat"].includes(t.slug),
        ).map((t) => (
          <li key={t.slug}>
            <Link to={`${t.path}?country=${country.code}`} aria-label={t.title} className="font-medium text-[var(--l-ink)] hover:text-[var(--l-rust)]">
              {t.title}
            </Link>
          </li>
        ))}
      </ul>

      </section>
      </div>
      <p className="text-xs text-[var(--l-slate)]">
        {AUTHOR_NAME}
        {" · "}
        <Link to="/briefings" className="underline">
          All briefings
        </Link>
        {" · "}
        <Link to="/methodology" className="underline">
          Method
        </Link>
      </p>
    </BriefingLayout>
  )
}
