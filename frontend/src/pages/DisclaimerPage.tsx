import { Seo } from "@/components/shared/Seo"
import { BriefingLayout } from "./briefing/BriefingLayout"

export default function DisclaimerPage() {
  return (
    <BriefingLayout>
      <Seo
        title="Disclaimer — Aequitas"
        description="Aequitas is an independent briefing, not official government guidance."
        path="/disclaimer"
      />
      <p className="text-xs font-medium uppercase tracking-wide text-[var(--l-rust)]">Disclaimer</p>
      <h1 className="font-display text-3xl sm:text-4xl text-[var(--l-ink)] mt-2 mb-4">
        Not official government guidance
      </h1>
      <p className="text-[var(--l-slate)] max-w-2xl mb-10 text-pretty">
        Independent briefing. Not affiliated with DfT, NTA, CBS, or a French ministry.
      </p>

      <div className="space-y-6 max-w-2xl">
        {[
          {
            title: "Data accuracy",
            body: "Analytics come from official public datasets. No warranty of completeness or fitness for a funding decision.",
          },
          {
            title: "Appraisal is local",
            body: "England TAG / Green Book figures are not DfT-accredited scheme appraisal. Ireland CAF/PAG, Netherlands MKBA, France French method — never an EU-wide BCR.",
          },
          {
            title: "Chat",
            body: "Country-indexed assistant. Cite the briefing. Verify before a policy document.",
          },
          {
            title: "Dated packs",
            body: "Each country pack is a dated harvest. Do not treat outputs as live operations data.",
          },
          {
            title: "Liability",
            body: "Authors accept no liability for decisions made on these pages.",
          },
        ].map((s) => (
          <section key={s.title} className="border-b border-[var(--l-rule)] pb-6">
            <h2 className="font-semibold text-[var(--l-ink)] mb-2">{s.title}</h2>
            <p className="text-sm text-[var(--l-slate)] leading-relaxed">{s.body}</p>
          </section>
        ))}
      </div>
    </BriefingLayout>
  )
}
