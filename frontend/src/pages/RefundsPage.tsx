import { Link } from "react-router"
import { Seo } from "@/components/shared/Seo"
import { SUPPORT_EMAIL } from "@/lib/site"
import { BriefingLayout } from "./briefing/BriefingLayout"

const SECTIONS = [
  {
    title: "What you are paying for",
    body: "Aequitas work is scoped. A country pack, a method adaptation, or a briefing commission is agreed in writing before any invoice. Public pages on this site are free to read.",
  },
  {
    title: "Deposits",
    body: "A deposit may be required to reserve a slot and start a pack. The deposit is applied to the final invoice. It is refundable if we have not started work, or if we cannot deliver the agreed scope.",
  },
  {
    title: "If the scope changes",
    body: "If you change geography, data sources, or deliverables after work has started, we re-quote. Unused deposit after a mutually agreed stop is returned. Work already delivered is billed.",
  },
  {
    title: "If we cannot deliver",
    body: "If official data we depend on is missing, or we cannot complete the agreed pack, you are not charged for undelivered work. Deposits for that work are returned.",
  },
  {
    title: "Billing errors",
    body: "Duplicate charges, wrong amounts, or charges after a written cancellation: email us with the invoice and we aim to correct them within five business days.",
  },
  {
    title: "How to request a review",
    body: `Write to ${SUPPORT_EMAIL} with your organisation, the invoice, and the reason. We aim to reply within five business days.`,
  },
] as const

export default function RefundsPage() {
  return (
    <BriefingLayout>
      <Seo
        title="Fees and refunds — Aequitas"
        description="How deposits, scoped commissions, and refunds work when you commission an Aequitas country pack."
        path="/refunds"
      />
      <p className="text-xs font-medium uppercase tracking-wide text-[var(--l-rust)]">Fees</p>
      <h1 className="font-display text-3xl sm:text-4xl text-[var(--l-ink)] mt-2 mb-2">
        Fees and refunds
      </h1>
      <p className="text-sm text-[var(--l-slate)] mb-8">Last updated: 19 August 2026</p>
      <p className="text-[var(--l-slate)] max-w-2xl mb-10 text-pretty">
        Commissions are scoped. This page is the refund rule for that work — not a software
        subscription.
      </p>

      <div className="space-y-6 max-w-2xl">
        {SECTIONS.map((s) => (
          <section key={s.title} className="border-b border-[var(--l-rule)] pb-6">
            <h2 className="font-semibold text-[var(--l-ink)] mb-2">{s.title}</h2>
            <p className="text-sm text-[var(--l-slate)] leading-relaxed">{s.body}</p>
          </section>
        ))}
      </div>

      <p className="text-sm text-[var(--l-slate)] mt-10">
        <Link to="/contact" className="underline">
          Work with us
        </Link>
        {" · "}
        <Link to="/terms" className="underline">
          Terms
        </Link>
      </p>
    </BriefingLayout>
  )
}
