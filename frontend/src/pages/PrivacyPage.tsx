import { useNavigate } from "react-router"
import { ArrowLeft } from "lucide-react"
import { Seo } from "@/components/shared/Seo"
import { SUPPORT_EMAIL } from "@/lib/site"

const SECTIONS = [
  {
    title: "Data We Collect",
    body: "Account details (email address, password hash) via Supabase Auth when you sign up. Saved views, notes, and comparisons you create while using the platform. Aggregated usage analytics via Google Analytics (GA4) on public pages. We do not collect payroll, financial, or personal data about third parties — Aequitas analyses publicly available government transport and demographic datasets, not data you upload about individuals.",
  },
  {
    title: "How We Use Data",
    body: "Your account details let you sign in and persist saved views, notes, and comparisons across sessions. Usage analytics help us understand which dimensions and regions are most used, so we can prioritise development. We do not sell personal data, and we do not use your account activity to profile individuals outside the platform.",
  },
  {
    title: "Data Retention",
    body: "Account data is retained for as long as your account is active. You can request deletion of your account and associated saved data at any time by emailing us. Analytics data is retained per Google Analytics' standard retention settings.",
  },
  {
    title: "Third-Party Services",
    body: "Aequitas uses Supabase (authentication and database, EU-hosted), Google Analytics (usage analytics), and Google Gemini (chatbot responses — your questions to the chatbot are sent to Google's API to generate answers grounded in pre-computed narratives). No underlying government source data we analyse contains personal information about individuals.",
  },
  {
    title: "Your Rights (UK GDPR)",
    body: "Under UK GDPR you have the right to access, correct, or request deletion of personal data we hold about you, and to object to or restrict certain processing. To exercise these rights, contact us using the details below. We aim to respond within one month.",
  },
  {
    title: "Cookies",
    body: "We use essential cookies for authentication (via Supabase) and analytics cookies (Google Analytics) to understand site usage. You can control cookies through your browser settings; disabling them may affect sign-in functionality.",
  },
]

export default function PrivacyPage() {
  const navigate = useNavigate()

  return (
    <div className="min-h-screen bg-background">
      <Seo
        title="Privacy Policy — Aequitas"
        description="How Aequitas collects, uses, and protects personal data for accounts, saved views, and platform analytics."
        path="/privacy"
      />
      <div className="border-b border-border bg-card/50">
        <div className="max-w-4xl mx-auto px-4 flex items-center h-8">
          <span className="text-[11px] font-mono text-muted-foreground uppercase tracking-widest">Privacy Policy</span>
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
        <span className="text-[11px] font-mono uppercase tracking-[0.2em] text-indigo-400 font-medium">Privacy Policy</span>
        <h1 className="text-2xl font-bold tracking-tight mt-3 mb-2 text-foreground">
          How We Handle Your Data
        </h1>
        <p className="text-[11px] text-muted-foreground font-mono mb-6">Last updated: 2 July 2026</p>
        <p className="text-sm text-muted-foreground leading-relaxed mb-10 max-w-2xl">
          Aequitas ("we", "us") operates aequitas.souravamseekar.com, a UK transport policy
          intelligence platform for Local Transport Authorities, government bodies, and
          researchers. This policy explains what data we collect and how we use it.
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
          Questions about this policy: <a href={`mailto:${SUPPORT_EMAIL}`} className="text-indigo-400 hover:underline">{SUPPORT_EMAIL}</a>
        </p>
      </div>
    </div>
  )
}
