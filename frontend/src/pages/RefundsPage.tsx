import { useNavigate } from "react-router"
import { ArrowLeft } from "lucide-react"
import { Seo } from "@/components/shared/Seo"
import { SUPPORT_EMAIL } from "@/lib/site"

const SECTIONS = [
  {
    title: "Free Tier",
    body: "Aequitas offers a free tier with core access to policy dimensions and platform features. No payment is required to sign up or use the free tier.",
  },
  {
    title: "Subscription Plans",
    body: "Paid subscriptions are billed monthly or annually and renew automatically until cancelled. You can cancel anytime from your account settings or by emailing us — cancelling stops future renewals, and you keep access until the end of the period you've already paid for. We do not refund partial months or unused days within a billing period, except where required by law.",
  },
  {
    title: "Annual Plans",
    body: "Cancelling an annual plan partway through the term does not trigger an automatic refund of the unused portion. If there are exceptional circumstances — extended service outage, a billing error, a mischarge — contact us and we'll review the request.",
  },
  {
    title: "Billing Errors",
    body: "If you're charged incorrectly — duplicate charge, wrong amount, or charged after cancellation — email us with your account email and the charge details. We aim to resolve billing errors within five business days.",
  },
  {
    title: "Service Issues",
    body: "If the platform is unavailable for a material period due to a fault on our side, we will work with you on service credits or term extensions proportional to the impact.",
  },
  {
    title: "How to Request a Review",
    body: "Email us with your account email, the charge in question, and the reason for your request. We aim to respond within five business days.",
  },
]

export default function RefundsPage() {
  const navigate = useNavigate()

  return (
    <div className="min-h-screen app-atmosphere text-foreground">
      <Seo
        title="Refunds Policy — Aequitas"
        description="Refund and cancellation terms for Aequitas subscriptions."
        path="/refunds"
      />
      <div className="border-b border-white/50 bg-white/20 backdrop-blur-2xl">
        <div className="max-w-3xl mx-auto px-6 flex items-center min-h-11">
          <span className="text-sm text-muted-foreground">Refunds Policy</span>
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
        <p className="marketing-eyebrow text-primary">Refunds Policy</p>
        <h1 className="text-3xl sm:text-4xl font-bold tracking-tight mt-3 mb-2 text-foreground">
          Cancellation & Refunds
        </h1>
        <p className="marketing-meta mb-6">Last updated: 2 July 2026</p>
        <p className="marketing-lede mb-12">
          Aequitas offers a free tier and paid subscription plans. This policy sets out how
          cancellations, renewals, and refunds work.
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
          Questions about billing:{" "}
          <a href={`mailto:${SUPPORT_EMAIL}`} className="text-primary hover:underline font-medium">
            {SUPPORT_EMAIL}
          </a>
        </p>
      </div>
    </div>
  )
}
