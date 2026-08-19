import { Link } from "react-router"
import { Seo } from "@/components/shared/Seo"
import { BriefingLayout } from "./briefing/BriefingLayout"

const SECTIONS = [
  {
    title: "Service Scope",
    body: "Aequitas provides pre-computed transport equity analytics for UK bus networks, covering all 33,755 LSOAs in England. It is a policy intelligence and research tool — not official DfT guidance, not a substitute for DfT-accredited scheme appraisal, and not legal or financial advice. See our Disclaimer for full detail on data limitations and intended use.",
  },
  {
    title: "Accounts",
    body: "You need an account to save views, notes, and comparisons. You're responsible for keeping your credentials secure and for activity under your account. Provide accurate information when signing up.",
  },
  {
    title: "Acceptable Use",
    body: "Use Aequitas for lawful transport policy research and analysis. Don't attempt to scrape, bulk-extract, or redistribute the underlying pre-computed dataset outside normal platform use; don't attempt to bypass authentication or interfere with the service. Don't misrepresent Aequitas outputs as official government guidance.",
  },
  {
    title: "Intellectual Property",
    body: "Aequitas' methodology, composite indices, interface, and pre-computed narratives are our property. Underlying government source data (NaPTAN, BODS GTFS, ONS Census, MHCLG IMD, NOMIS BRES, NHS ODS, GIAS, DfT TAG, DESNZ) remains subject to its original open licences (OGL v3.0, ODbL, and others as specified per source) — Aequitas does not claim ownership of that source data and does not redistribute it in raw form.",
  },
  {
    title: "Subscriptions & Pricing",
    body: "Aequitas offers a free tier and paid subscription tiers for advanced features (extended saved views, comparison tools, and priority access to new dimensions). Subscriptions are billed monthly or annually and renew automatically until cancelled. Pricing is shown at signup or upgrade and won't change for existing subscribers without advance notice. See our Refunds Policy for cancellation and billing terms.",
  },
  {
    title: "Availability & Changes",
    body: "We may update features, data pipelines, or these Terms as the platform evolves. Material changes will be reflected on this page with an updated date. We aim to keep the service available but don't guarantee uninterrupted access.",
  },
  {
    title: "Limitation of Liability",
    body: 'The service is provided "as is" to the extent permitted by law. Aequitas outputs (including AI-generated chatbot responses) should be independently verified before use in policy documents or funding decisions. We accept no liability for decisions made on the basis of Aequitas outputs.',
  },
]

export default function TermsPage() {
  return (
    <BriefingLayout>
      <Seo
        title="Terms of Use — Aequitas"
        description="Terms governing access to the Aequitas website, accounts, and briefings."
        path="/terms"
      />
      <p className="text-xs font-medium uppercase tracking-wide text-[var(--l-rust)]">Terms</p>
      <h1 className="font-display text-3xl sm:text-4xl text-[var(--l-ink)] mt-2 mb-2">
        Terms of use
      </h1>
      <p className="text-sm text-[var(--l-slate)] mb-8">Last updated: 2 July 2026</p>

      <div className="space-y-6 max-w-2xl">
        {SECTIONS.map((s) => (
          <section key={s.title} className="border-b border-[var(--l-rule)] pb-6">
            <h2 className="font-semibold text-[var(--l-ink)] mb-2">{s.title}</h2>
            <p className="text-sm text-[var(--l-slate)] leading-relaxed">{s.body}</p>
          </section>
        ))}
      </div>

      <p className="text-sm text-[var(--l-slate)] mt-10">
        <Link to="/disclaimer" className="underline">
          Disclaimer
        </Link>
        {" · "}
        <Link to="/privacy" className="underline">
          Privacy
        </Link>
      </p>
    </BriefingLayout>
  )
}
