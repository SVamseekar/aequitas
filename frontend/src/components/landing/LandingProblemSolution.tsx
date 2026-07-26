export function LandingProblemSolution() {
  return (
    <section
      aria-labelledby="landing-challenge-heading"
      className="relative border-y border-white/40 bg-white/15 backdrop-blur-md"
    >
      <div className="landing-shell py-12 sm:py-14 lg:py-16">
        <div className="grid lg:grid-cols-2 gap-8 lg:gap-12">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.14em] text-[var(--l-rust)] mb-3">
              Why this exists
            </p>
            <h2
              id="landing-challenge-heading"
              className="font-display text-3xl sm:text-4xl leading-[1.12] text-[var(--l-ink)] max-w-md"
            >
              Funding still follows the loudest case — not the greatest need.
            </h2>
          </div>

          <div className="space-y-8">
            <div>
              <p className="text-sm font-semibold text-[var(--l-ink)] mb-2">The challenge</p>
              <p className="text-base sm:text-lg text-[var(--l-slate)] leading-relaxed">
                Stops, timetables, census deprivation, and route geometry live in disconnected
                formats. Authorities cannot quickly answer: which communities pay the price for poor
                service, and what would it cost to fix?
              </p>
            </div>
            <div>
              <p className="text-sm font-semibold text-[var(--l-ink)] mb-2">The product</p>
              <p className="text-base sm:text-lg text-[var(--l-slate)] leading-relaxed">
                Aequitas ingests national open data and pre-computes who is underserved, by how much,
                and why — with plain-English findings a non-analyst can take into a board meeting.
              </p>
            </div>
            <blockquote className="landing-glass rounded-2xl p-6 sm:p-8">
              <p className="font-display text-xl sm:text-2xl leading-snug text-[var(--l-ink)]">
                Evidence ready for business cases and franchising assessments — not another
                spreadsheet that needs an analyst to interpret.
              </p>
            </blockquote>
          </div>
        </div>
      </div>
    </section>
  )
}
