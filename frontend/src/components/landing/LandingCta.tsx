import { LandingActions } from "./LandingActions"

export function LandingCta() {
  return (
    <section aria-labelledby="landing-cta-heading" className="bg-[var(--l-paper)] border-t border-[var(--l-rule)]">
      <div className="landing-shell py-16 sm:py-20 text-center">
        <h2
          id="landing-cta-heading"
          className="font-display text-3xl sm:text-4xl text-[var(--l-ink)] leading-[1.12] max-w-xl mx-auto text-balance"
        >
          Commission a pack
        </h2>
        <p className="mt-4 text-[var(--l-slate)] max-w-md mx-auto leading-relaxed text-pretty">
          Authorities, agencies, and ministries. Same method. Your country.
        </p>
        <div className="mt-8 flex justify-center">
          <LandingActions />
        </div>
      </div>
    </section>
  )
}
