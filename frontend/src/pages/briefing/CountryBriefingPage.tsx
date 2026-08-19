import { Link, useParams } from "react-router"
import { Seo } from "@/components/shared/Seo"
import { breadcrumbJsonLd } from "@/lib/structuredData"
import { AUTHOR_NAME } from "@/lib/site"
import { countryByCode, TOPIC_BRIEFS, type CountryCode } from "@/lib/briefingCatalog"
import { COUNTRY_PHOTO } from "@/lib/publicPhotos"
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
        {country.name} · {country.packAsOf} · score {country.score}
      </p>
      <h1 className="font-display text-3xl sm:text-4xl text-[var(--l-ink)] mt-2 mb-6 text-balance">
        {country.name}
      </h1>
      <img
        src={COUNTRY_PHOTO[country.code].src}
        alt={COUNTRY_PHOTO[country.code].alt}
        className="w-full rounded-2xl aspect-[21/8] object-cover object-center mb-8"
        width={1920}
        height={730}
      />

      <dl className="grid sm:grid-cols-2 gap-x-8 gap-y-3 mb-10 text-sm">
        {rows.map(([k, v]) => (
          <div key={k} className="border-b border-[var(--l-rule)] pb-2">
            <dt className="text-[11px] uppercase tracking-wide text-[var(--l-slate)]">{k}</dt>
            <dd className="mt-0.5 text-[var(--l-ink)]">{v}</dd>
          </div>
        ))}
      </dl>

      <h2 className="text-sm font-semibold uppercase tracking-wide text-[var(--l-slate)] mb-3">
        Doors
      </h2>
      <ul className="grid sm:grid-cols-2 gap-x-6 gap-y-2 mb-10 text-sm">
        {TOPIC_BRIEFS.filter((t) =>
          !["destinations", "appraisal", "realtime", "chat"].includes(t.slug),
        ).map((t) => (
          <li key={t.slug}>
            <Link to={t.path} className="font-medium text-[var(--l-ink)] hover:text-[var(--l-rust)]">
              {t.title}
            </Link>
          </li>
        ))}
      </ul>

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
