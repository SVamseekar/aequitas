import { Link } from "react-router"
import { Seo } from "@/components/shared/Seo"
import { breadcrumbJsonLd } from "@/lib/structuredData"
import { TOPIC_BRIEFS } from "@/lib/briefingCatalog"
import { BriefingLayout } from "./BriefingLayout"
import { CountryBriefCards } from '@/components/landing/CountryBriefCards'
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

      <h1 className="font-display text-3xl sm:text-4xl text-[var(--l-ink)] mt-2 mb-3 text-balance">
        Explore the briefings.
      </h1>
      <p className="text-[var(--l-slate)] max-w-2xl leading-relaxed text-pretty mb-10">
        Same questions. Local evidence. Ranks stay within each country.
      </p>

      <nav className='evidence-tabs' aria-label='Briefing index'><a href='#country-briefings'>Countries</a><a href='#topic-briefings'>Topics</a></nav>
      <section id='country-briefings' className='mb-10 scroll-mt-24'><h2 className='sr-only'>Countries</h2><CountryBriefCards /></section>
      <section id='topic-briefings' className='border-t border-border pt-7 scroll-mt-24'><h2 className='text-3xl mb-2'>Explore by topic</h2><p className='text-sm text-muted-foreground mb-5'>Find briefings on the questions that matter.</p><div className='public-topic-groups'>{[['Measure', ['equity','access','service','network']], ['Interpret', ['correlations','economy','policy','scenarios']], ['Observe', ['time','reach','ops']]].map(([name, slugs]) => <div className='public-topic-group' key={String(name)}><h3>{name}</h3>{TOPIC_BRIEFS.filter(topic => Array.isArray(slugs) && slugs.includes(topic.slug)).map(topic => <Link key={topic.slug} to={topic.path}>{topic.title}<span>{topic.question}</span></Link>)}</div>)}</div></section>

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
