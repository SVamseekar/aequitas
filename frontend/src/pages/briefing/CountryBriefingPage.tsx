import { Link, useParams } from "react-router"
import { Seo } from "@/components/shared/Seo"
import { breadcrumbJsonLd } from "@/lib/structuredData"
import { AUTHOR_NAME } from "@/lib/site"
import { countryByCode, TOPIC_BRIEFS, type CountryCode } from "@/lib/briefingCatalog"
import { BriefingLayout } from "./BriefingLayout"

export default function CountryBriefingPage({ code }: { code?: CountryCode }) {
  const params = useParams()
  const country = countryByCode(code ?? params.country)
  if (!country) {
    return (
      <BriefingLayout>
        <h1 className="text-2xl font-semibold">Country not found</h1>
        <Link to="/topics" className="text-[var(--l-rust)] text-sm">
          All topics
        </Link>
      </BriefingLayout>
    )
  }

  return (
    <BriefingLayout>
      <Seo
        title={`${country.name} bus equity — ${country.deprivation} × ${country.network.split(" ")[0]} | Aequitas`}
        description={country.description}
        path={country.path}
        jsonLd={breadcrumbJsonLd([
          { name: "Topics", path: "/topics" },
          { name: country.name, path: country.path },
        ])}
      />
      <p className="text-xs font-medium uppercase tracking-wide text-[var(--l-rust)]">
        {country.name} · pack {country.packAsOf} · {AUTHOR_NAME}
      </p>
      <h1 className="font-display text-3xl sm:text-4xl text-[var(--l-ink)] mt-2 mb-3">
        {country.name}: official timetables × official deprivation
      </h1>
      <p className="text-[var(--l-slate)] max-w-2xl leading-relaxed mb-8">
        {country.description} In-country score {country.score} from the dated pack. Built by{" "}
        {AUTHOR_NAME}.
      </p>

      <dl className="grid sm:grid-cols-2 gap-4 mb-10 text-sm">
        <div>
          <dt className="text-[var(--l-slate)]">Network</dt>
          <dd className="font-medium text-[var(--l-ink)]">{country.network}</dd>
        </div>
        <div>
          <dt className="text-[var(--l-slate)]">Deprivation</dt>
          <dd className="font-medium text-[var(--l-ink)]">{country.deprivation}</dd>
        </div>
        <div>
          <dt className="text-[var(--l-slate)]">Geography</dt>
          <dd className="font-medium text-[var(--l-ink)]">{country.geography}</dd>
        </div>
        <div>
          <dt className="text-[var(--l-slate)]">Policy</dt>
          <dd className="font-medium text-[var(--l-ink)]">{country.policyTitle}</dd>
        </div>
        <div>
          <dt className="text-[var(--l-slate)]">Destinations</dt>
          <dd className="font-medium text-[var(--l-ink)]">{country.destinations}</dd>
        </div>
        <div>
          <dt className="text-[var(--l-slate)]">Appraisal</dt>
          <dd className="font-medium text-[var(--l-ink)]">{country.appraisal}</dd>
        </div>
        <div>
          <dt className="text-[var(--l-slate)]">Real-time</dt>
          <dd className="font-medium text-[var(--l-ink)]">{country.realtime}</dd>
        </div>
        <div>
          <dt className="text-[var(--l-slate)]">Chat</dt>
          <dd className="font-medium text-[var(--l-ink)]">{country.chat}</dd>
        </div>
      </dl>

      <h2 className="text-lg font-semibold mb-3">Doors in {country.name}</h2>
      <ul className="space-y-2 mb-8">
        {TOPIC_BRIEFS.map((t) => (
          <li key={t.slug}>
            <Link to={t.path} className="text-[var(--l-ink)] hover:text-[var(--l-rust)]">
              {t.title}
            </Link>
            <span className="text-sm text-[var(--l-slate)]"> — {t.perCountry[country.code]}</span>
          </li>
        ))}
      </ul>

      <p className="text-sm text-[var(--l-slate)]">
        <Link to="/topics" className="underline">
          All countries and topics
        </Link>
        {" · "}
        <Link to="/methodology" className="underline">
          How it is computed
        </Link>
      </p>
    </BriefingLayout>
  )
}
