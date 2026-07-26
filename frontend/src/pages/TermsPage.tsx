import { Link, useNavigate } from "react-router"
import { ArrowLeft } from "lucide-react"
import { Seo } from "@/components/shared/Seo"
import { SUPPORT_EMAIL } from "@/lib/site"

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
  const navigate = useNavigate()

  return (
    <div className="min-h-screen app-atmosphere text-foreground">
      <Seo
        title="Terms of Use — Aequitas"
        description="Terms governing access to the Aequitas platform, accounts, and transport policy analytics."
        path="/terms"
      />
      <div className="border-b border-white/50 bg-white/20 backdrop-blur-2xl">
        <div className="max-w-3xl mx-auto px-6 flex items-center min-h-11">
          <span className="text-sm text-muted-foreground">Terms of Use</span>
        </div>
      </div>

      <div className="max-w-3xl mx-auto px-6 py-12 sm:py-14">
        <button
          onClick={() => navigate(-1)}
          className="flex items-center gap-2 text-sm text-muted-foreground hover:text-foreground mb-8 transition-colors"
        >
          <ArrowLeft className="w-4 h-4" /> Back
        </button>

        <div className="h-px bg-primary/40 mb-8 max-w-xs" />
        <p className="marketing-eyebrow text-primary">Terms of Use</p>
        <h1 className="text-3xl sm:text-4xl font-bold tracking-tight mt-3 mb-2 text-foreground">
          Terms Governing Use of Aequitas
        </h1>
        <p className="marketing-meta mb-6">Last updated: 2 July 2026</p>
        <p className="marketing-lede mb-12">
          These Terms govern your use of the Aequitas website and platform. By creating an account
          or using the service, you agree to these Terms.
        </p>

        <div className="space-y-4">
          {SECTIONS.map((s) => (
            <div key={s.title} className="app-glass-strong rounded-2xl border border-white/60 p-5">
              <p className="marketing-card-title mb-2">{s.title}</p>
              <p className="marketing-body">{s.body}</p>
            </div>
          ))}
        </div>

        <p className="text-base text-muted-foreground leading-relaxed mt-10">
          See also our{" "}
          <Link to="/disclaimer" className="text-primary hover:underline font-medium">
            Disclaimer
          </Link>{" "}
          and{" "}
          <Link to="/privacy" className="text-primary hover:underline font-medium">
            Privacy Policy
          </Link>
          . Questions about these Terms:{" "}
          <a href={`mailto:${SUPPORT_EMAIL}`} className="text-primary hover:underline font-medium">
            {SUPPORT_EMAIL}
          </a>
        </p>
      </div>
    </div>
  )
}
