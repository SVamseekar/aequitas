import { Link } from "react-router"
import { Seo } from "@/components/shared/Seo"
import { breadcrumbJsonLd } from "@/lib/structuredData"
import { AUTHOR_NAME } from "@/lib/site"
import { COUNTRY_BRIEFS } from "@/lib/briefingCatalog"
import { BriefingLayout } from "./briefing/BriefingLayout"

export default function AboutPage() {
  return (
    <BriefingLayout>
      <Seo
        title="About Aequitas — Marti Soura Vamseekar"
        description="Aequitas joins official GTFS to official deprivation in England, Ireland, the Netherlands, and France. Ranks stay in-country."
        path="/about"
        jsonLd={breadcrumbJsonLd([{ name: "About", path: "/about" }])}
      />
      <p className="text-xs font-medium uppercase tracking-wide text-[var(--l-rust)]">
        About · {AUTHOR_NAME}
      </p>
      <h1 className="font-display text-3xl sm:text-4xl text-[var(--l-ink)] mt-2 mb-4 text-balance">
        A briefing method, not a hosted warehouse
      </h1>
      <p className="text-[var(--l-slate)] max-w-xl text-pretty mb-8">
        Same doors in four countries. Official timetables × official deprivation. The engine
        runs locally; these pages name the field.
      </p>
      <img
        src="/landing/hero-studio.jpg"
        alt="Planners around a printed bus-network map"
        className="w-full rounded-2xl aspect-[21/8] object-cover mb-10"
        width={1920}
        height={730}
      />
      <ul className="grid sm:grid-cols-2 gap-2 mb-10 text-sm">
        {COUNTRY_BRIEFS.map((c) => (
          <li key={c.code}>
            <Link to={c.path} className="text-[var(--l-ink)] font-medium hover:text-[var(--l-rust)]">
              {c.name}
            </Link>
            <span className="text-[var(--l-slate)]"> — {c.deprivation}</span>
          </li>
        ))}
      </ul>
      <p className="text-sm">
        <Link to="/briefings" className="underline">
          Briefings
        </Link>
        {" · "}
        <Link to="/methodology" className="underline">
          Method
        </Link>
        {" · "}
        <Link to="/contact" className="underline">
          Contact
        </Link>
      </p>
    </BriefingLayout>
  )
}
