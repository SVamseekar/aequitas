import { Link, useParams, useSearchParams } from "react-router"
import { Seo } from "@/components/shared/Seo"
import { breadcrumbJsonLd } from "@/lib/structuredData"
import { COUNTRY_BRIEFS, topicBySlug } from "@/lib/briefingCatalog"
import { PublicTopicEvidence } from "@/components/briefing/PublicTopicEvidence"
import { DIMENSION_API_IDS } from "@/lib/constants"
import { BriefingLayout } from "./BriefingLayout"

export default function TopicBriefingPage({ slug: slugProp }: { slug?: string }) {
  const params = useParams()
  const [search] = useSearchParams()
  const country = COUNTRY_BRIEFS.find(item => item.code === search.get("country")) ?? COUNTRY_BRIEFS[0]
  const topic = topicBySlug(slugProp ?? params.slug)
  if (!topic) {
    return (
      <BriefingLayout>
        <h1 className="text-2xl font-semibold">Topic not found</h1>
        <Link to="/briefings" className="text-[var(--l-rust)] text-sm">
          All briefings
        </Link>
      </BriefingLayout>
    )
  }

  return (
    <BriefingLayout>
      <Seo
        title={`${topic.title} — Aequitas (${topic.keywords.slice(0, 5).join(", ")})`}
        description={`${topic.question} ${topic.body[0]}`}
        path={topic.path}
        jsonLd={breadcrumbJsonLd([
          { name: "Briefings", path: "/briefings" },
          { name: topic.title, path: topic.path },
        ])}
      />
      <p className="text-xs font-medium uppercase tracking-wide text-[var(--l-rust)]">
        Briefings / {topic.title}
      </p>
      <h1 className="font-display text-3xl sm:text-4xl text-[var(--l-ink)] mt-2 mb-2 text-balance">
        {topic.question}
      </h1>
      <p className="public-briefing-lede">{topic.body[0]}</p>

      <nav className="public-country-tabs" aria-label="Country evidence">{COUNTRY_BRIEFS.map(item => {
        const next = new URLSearchParams(search); next.set('country', item.code); next.delete('exhibit')
        return <Link key={item.code} to={{ search: `?${next}` }} aria-current={country.code === item.code ? 'page' : undefined}>{item.name}</Link>
      })}</nav>
      <p className="text-sm text-muted-foreground mb-6">{topic.perCountry[country.code]}</p>
      {DIMENSION_API_IDS[topic.slug] ? <PublicTopicEvidence key={`${topic.slug}-${country.code}`} slug={topic.slug} country={country.code} /> : <section className="public-topic-evidence"><h2>{country.name}: {topic.title}</h2><p>{topic.perCountry[country.code]}</p><p>Open the selected analytical page to inspect current availability and calculation scope.</p></section>}
      <div className="public-topic-actions"><Link className="landing-btn-primary" to={`/app/${country.code}/${topic.slug === 'appraisal' ? 'economy' : topic.slug === 'destinations' ? 'access?view=destinations' : topic.slug === 'realtime' ? 'ops' : topic.slug === 'chat' ? '' : topic.slug}`}>Open selected evidence</Link><Link className="landing-btn-secondary" to={country.path}>Read {country.name} briefing</Link></div>

      <Link to="/briefings" className="text-sm underline text-[var(--l-ink)]">
        All briefings
      </Link>
    </BriefingLayout>
  )
}
