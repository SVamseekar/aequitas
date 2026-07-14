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
    body: "The service is provided \"as is\" to the extent permitted by law. Aequitas outputs (including AI-generated chatbot responses) should be independently verified before use in policy documents or funding decisions. We accept no liability for decisions made on the basis of Aequitas outputs.",
  },
]

export default function TermsPage() {
  const navigate = useNavigate()

  return (
    <div className="min-h-screen bg-background">
      <Seo
        title="Terms of Use — Aequitas"
        description="Terms governing access to the Aequitas platform, accounts, and transport policy analytics."
        path="/terms"
      />
      <div className="border-b border-border bg-card/50">
        <div className="max-w-4xl mx-auto px-4 flex items-center h-8">
          <span className="text-[11px] font-mono text-muted-foreground uppercase tracking-widest">Terms of Use</span>
        </div>
      </div>

      <div className="max-w-4xl mx-auto px-4 py-12">
        <button
          onClick={() => navigate(-1)}
          className="flex items-center gap-2 text-xs text-muted-foreground hover:text-foreground mb-8 font-mono transition-colors"
        >
          <ArrowLeft className="w-3.5 h-3.5" /> BACK
        </button>

        <div className="h-px bg-indigo-500/40 mb-8 max-w-xs" />
        <span className="text-[11px] font-mono uppercase tracking-[0.2em] text-indigo-400 font-medium">Terms of Use</span>
        <h1 className="text-2xl font-bold tracking-tight mt-3 mb-2 text-foreground">
          Terms Governing Use of Aequitas
        </h1>
        <p className="text-[11px] text-muted-foreground font-mono mb-6">Last updated: 2 July 2026</p>
        <p className="text-sm text-muted-foreground leading-relaxed mb-10 max-w-2xl">
          These Terms govern your use of the Aequitas website and platform. By creating an
          account or using the service, you agree to these Terms.
        </p>

        <div className="space-y-6">
          {SECTIONS.map((s) => (
            <div key={s.title} className="border border-border rounded bg-card p-4">
              <p className="text-xs font-semibold text-indigo-400 mb-2">{s.title}</p>
              <p className="text-xs text-muted-foreground leading-relaxed">{s.body}</p>
            </div>
          ))}
        </div>

        <p className="text-xs text-muted-foreground leading-relaxed mt-10">
          See also our <Link to="/disclaimer" className="text-indigo-400 hover:underline">Disclaimer</Link> and{" "}
          <Link to="/privacy" className="text-indigo-400 hover:underline">Privacy Policy</Link>.
          Questions about these Terms: <a href={`mailto:${SUPPORT_EMAIL}`} className="text-indigo-400 hover:underline">{SUPPORT_EMAIL}</a>
        </p>
      </div>
    </div>
  )
}
