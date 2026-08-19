import { Seo } from "@/components/shared/Seo"
import { SUPPORT_EMAIL } from "@/lib/site"
import { BriefingLayout } from "./briefing/BriefingLayout"

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
  return (
    <BriefingLayout>
      <Seo
        title="Privacy Policy — Aequitas"
        description="How Aequitas collects, uses, and protects personal data for accounts, saved views, and platform analytics."
        path="/privacy"
      />
      <p className="text-xs font-medium uppercase tracking-wide text-[var(--l-rust)]">Privacy</p>
      <h1 className="font-display text-3xl sm:text-4xl text-[var(--l-ink)] mt-2 mb-2">
        How we handle your data
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
        Questions:{" "}
        <a href={`mailto:${SUPPORT_EMAIL}`} className="underline">
          {SUPPORT_EMAIL}
        </a>
      </p>
    </BriefingLayout>
  )
}
