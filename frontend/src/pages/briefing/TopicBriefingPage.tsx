import { Link, useParams } from "react-router"
import { Seo } from "@/components/shared/Seo"
import { breadcrumbJsonLd } from "@/lib/structuredData"
import { COUNTRY_BRIEFS, topicBySlug } from "@/lib/briefingCatalog"
import { BriefingLayout } from "./BriefingLayout"

export default function TopicBriefingPage({ slug: slugProp }: { slug?: string }) {
  const params = useParams()
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
        Four countries
      </p>
      <h1 className="font-display text-3xl sm:text-4xl text-[var(--l-ink)] mt-2 mb-2 text-balance">
        {topic.title}
      </h1>
      <p className="text-[var(--l-slate)] mb-8 text-pretty">{topic.question}</p>

      <ul className="space-y-3 mb-10">
        {COUNTRY_BRIEFS.map((c) => (
          <li key={c.code} className="grid grid-cols-[7rem_minmax(0,1fr)] gap-3 text-sm border-b border-[var(--l-rule)] pb-3">
            <Link to={c.path} className="font-semibold text-[var(--l-ink)]">
              {c.name}
            </Link>
            <span className="text-[var(--l-slate)]">{topic.perCountry[c.code]}</span>
          </li>
        ))}
      </ul>

      <Link to="/briefings" className="text-sm underline text-[var(--l-ink)]">
        All briefings
      </Link>
    </BriefingLayout>
  )
}
