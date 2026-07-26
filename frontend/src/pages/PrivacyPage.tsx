import { useNavigate } from "react-router"
import { ArrowLeft } from "lucide-react"
import { Seo } from "@/components/shared/Seo"
import { SUPPORT_EMAIL } from "@/lib/site"

const SECTIONS = [
  {
    title: "Data We Collect",
    body: "Account details (email address and display name) when you sign in with Google OAuth. Saved views, notes, conversations, and comparisons you create while using the platform, scoped to your organisation (tenant) workspace. Aggregated usage analytics via Google Analytics (GA4) on public pages. We do not collect payroll, financial, or personal data about third parties — Aequitas analyses publicly available government transport and demographic datasets, not data you upload about individuals.",
  },
  {
    title: "How We Use Data",
    body: "Your account details let you sign in and persist saved views, notes, and comparisons across sessions within your workspace. Usage analytics help us understand which dimensions and regions are most used, so we can prioritise development. We do not sell personal data, and we do not use your account activity to profile individuals outside the platform.",
  },
  {
    title: "Data Retention",
    body: "Account data is retained for as long as your account is active. You can request deletion of your account and associated saved data at any time by emailing us. Analytics data is retained per Google Analytics' standard retention settings.",
  },
  {
    title: "Third-Party Services",
    body: "Aequitas uses Google OAuth for authentication, a self-hosted PostgreSQL database for account and workspace data, Google Analytics (usage analytics), and Google Gemini (chatbot responses — your questions to the chatbot are sent to Google's API to generate answers grounded in pre-computed narratives). Invite emails may be sent via Brevo. No underlying government source data we analyse contains personal information about individuals.",
  },
  {
    title: "Your Rights (UK GDPR)",
    body: "Under UK GDPR you have the right to access, correct, or request deletion of personal data we hold about you, and to object to or restrict certain processing. To exercise these rights, contact us using the details below. We aim to respond within one month.",
  },
  {
    title: "Cookies",
    body: "We use an essential HttpOnly session cookie for authentication (signed, SameSite=Lax) and analytics cookies (Google Analytics) to understand site usage. You can control cookies through your browser settings; disabling essential cookies will prevent sign-in.",
  },
]

export default function PrivacyPage() {
  const navigate = useNavigate()

  return (
    <div className="min-h-screen app-atmosphere text-foreground">
      <Seo
        title="Privacy Policy — Aequitas"
        description="How Aequitas collects, uses, and protects personal data for accounts, saved views, and platform analytics."
        path="/privacy"
      />
      <div className="border-b border-white/50 bg-white/20 backdrop-blur-2xl">
        <div className="max-w-3xl mx-auto px-6 flex items-center min-h-11">
          <span className="text-sm text-muted-foreground">Privacy Policy</span>
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
        <p className="marketing-eyebrow text-primary">Privacy Policy</p>
        <h1 className="text-3xl sm:text-4xl font-bold tracking-tight mt-3 mb-2 text-foreground">
          How We Handle Your Data
        </h1>
        <p className="marketing-meta mb-6">Last updated: 2 July 2026</p>
        <p className="marketing-lede mb-12">
          Aequitas (&quot;we&quot;, &quot;us&quot;) operates aequitas.souravamseekar.com, a UK
          transport policy intelligence platform for Local Transport Authorities, government bodies,
          and researchers. This policy explains what data we collect and how we use it.
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
          Questions about this policy:{" "}
          <a href={`mailto:${SUPPORT_EMAIL}`} className="text-primary hover:underline font-medium">
            {SUPPORT_EMAIL}
          </a>
        </p>
      </div>
    </div>
  )
}
