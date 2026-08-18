import { Link, useParams } from "react-router"
import { Seo } from "@/components/shared/Seo"
import { breadcrumbJsonLd } from "@/lib/structuredData"
import { AUTHOR_NAME } from "@/lib/site"
import { COUNTRY_BRIEFS, topicBySlug } from "@/lib/briefingCatalog"
import { BriefingLayout } from "./BriefingLayout"

export default function TopicBriefingPage({ slug: slugProp }: { slug?: string }) {
  const params = useParams()
  const topic = topicBySlug(slugProp ?? params.slug)
  if (!topic) {
    return (
      <BriefingLayout>
        <h1 className="text-2xl font-semibold">Topic not found</h1>
        <Link to="/topics" className="text-[var(--l-rust)] text-sm">
          All topics
        </Link>
      </BriefingLayout>
    )
  }

  return (
    <BriefingLayout>
      <Seo
        title={`${topic.title} — Aequitas (${topic.keywords.slice(0, 5).join(", ")})`}
        description={`${topic.question} ${topic.body[0]} England, Ireland, Netherlands, France.`}
        path={topic.path}
        jsonLd={breadcrumbJsonLd([
          { name: "Topics", path: "/topics" },
          { name: topic.title, path: topic.path },
        ])}
      />
      <p className="text-xs font-medium uppercase tracking-wide text-[var(--l-rust)]">
        Four countries · {AUTHOR_NAME}
      </p>
      <h1 className="font-display text-3xl sm:text-4xl text-[var(--l-ink)] mt-2 mb-3">
        {topic.title}
      </h1>
      <p className="text-lg text-[var(--l-slate)] mb-6">{topic.question}</p>
      {topic.body.map((p) => (
        <p key={p.slice(0, 40)} className="text-[var(--l-slate)] leading-relaxed mb-4 max-w-2xl">
          {p}
        </p>
      ))}

      <h2 className="text-lg font-semibold mt-8 mb-3">In each country</h2>
      <ul className="space-y-3 mb-8">
        {COUNTRY_BRIEFS.map((c) => (
          <li key={c.code} className="rounded-xl border border-[var(--l-rule)] p-4">
            <Link to={c.path} className="font-semibold text-[var(--l-ink)]">
              {c.name}
            </Link>
            <p className="text-sm text-[var(--l-slate)] mt-1">{topic.perCountry[c.code]}</p>
          </li>
        ))}
      </ul>

      <p className="text-xs text-[var(--l-slate)] mb-6">
        Search terms on this page: {topic.keywords.join(" · ")}
      </p>
      <Link to="/topics" className="text-sm underline text-[var(--l-ink)]">
        All topics
      </Link>
    </BriefingLayout>
  )
}
