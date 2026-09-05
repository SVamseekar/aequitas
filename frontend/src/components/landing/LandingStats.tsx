export function LandingStats() {
  return (
    <section id="proof" aria-labelledby="landing-stats-heading" className="relative">
      <div className="landing-shell py-12 sm:py-14 lg:py-16">
        <div className="grid lg:grid-cols-2 gap-6 lg:gap-10 mb-8">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.14em] text-[var(--l-rust)] mb-3">
              What we will not claim
            </p>
            <h2
              id="landing-stats-heading"
              className="font-display text-3xl sm:text-4xl leading-[1.12] text-[var(--l-ink)] max-w-md"
            >
              A briefing is only useful if the holes stay holes.
            </h2>
          </div>
          <p className="text-lg text-[var(--l-slate)] leading-relaxed max-w-xl lg:pt-8">
            Analytics are pre-computed into a DuckDB warehouse. The app is a lookup. Gini is
            computed on each build — not a locked demo number.
          </p>
        </div>

        <ul className="grid sm:grid-cols-2 gap-3">
          {[
            {
              title: "No Europe-wide IMD",
              body: "England uses IMD, Ireland Pobal HP, the Netherlands SES-WOA, France F-EDI. They never share an axis.",
            },
            {
              title: "No invented 15 / 30 / 45",
              body: "Job counts appear only after a local r5py run. Until then Reach is service bands, honestly empty on travel time.",
            },
            {
              title: "No euro BCR without a source",
              body: "People-gap first. TAG, CAF, or PBL money only when a free official unit cost exists.",
            },
            {
              title: "Network dates ≠ census dates",
              body: "Time moves BODS / TFI / OVapi / NAP. Census, IMD, HP, SES-WOA, and F-EDI stay frozen on the pack.",
            },
          ].map((item) => (
            <li key={item.title} className="landing-card p-5 sm:p-6">
              <h3 className="text-base font-semibold text-[var(--l-ink)]">{item.title}</h3>
              <p className="mt-2 text-sm text-[var(--l-slate)] leading-relaxed">{item.body}</p>
            </li>
          ))}
        </ul>
      </div>
    </section>
  )
}
