export function LandingProblemSolution() {
  return (
    <section aria-labelledby="landing-challenge-heading" className="max-w-7xl mx-auto px-6 py-20 lg:py-24">
      <div className="h-px bg-indigo-400/40 mb-6 max-w-[48px]" aria-hidden />
      <p className="text-[11px] font-mono uppercase tracking-[0.3em] text-indigo-400 font-bold">
        Why Aequitas
      </p>
      <div className="grid lg:grid-cols-2 gap-16 mt-10">
        <article>
          <p className="text-[11px] font-mono text-muted-foreground uppercase tracking-widest mb-2 font-bold">
            The challenge
          </p>
          <h2
            id="landing-challenge-heading"
            className="text-2xl font-bold text-foreground tracking-tight mb-4 leading-snug"
          >
            Bus funding decisions are made with incomplete evidence
          </h2>
          <p className="text-sm text-muted-foreground leading-relaxed">
            Transport authorities sit on mountains of data — stop locations, timetables, census
            deprivation indices, route geometries — but it lives in disconnected formats. Nobody can
            quickly answer the question that matters:{" "}
            <strong className="text-foreground">
              which communities are paying the price for poor service, and what would it cost to fix?
            </strong>
          </p>
          <p className="text-sm text-muted-foreground leading-relaxed mt-4">
            Without that answer, funding goes to whoever has the loudest business case — not the
            area with the greatest need.
          </p>
        </article>
        <article>
          <p className="text-[11px] font-mono text-indigo-400 uppercase tracking-widest mb-2 font-bold">
            The solution
          </p>
          <h2 className="text-2xl font-bold text-foreground tracking-tight mb-4 leading-snug">
            Aequitas turns raw transport data into a funding case
          </h2>
          <p className="text-sm text-muted-foreground leading-relaxed">
            We ingest national open datasets and pre-compute the analysis: who is underserved, by
            how much, and why. Every number traces back to its source through a documented formula.
            Every finding comes with a plain-English explanation a non-analyst can present in a board
            meeting.
          </p>
          <p className="text-sm text-muted-foreground leading-relaxed mt-4">
            Run a scenario — restore evening frequency, extend the last bus, add demand-responsive
            transport — and see the population affected, the cost, and the CO₂ impact before you
            write the bid.
          </p>
        </article>
      </div>
      <blockquote className="border-l-2 border-indigo-400 pl-6 py-1.5 mt-16 max-w-3xl bg-indigo-400/5 rounded-r-md border-y border-r border-border">
        <p className="text-sm text-foreground font-medium leading-relaxed">
          The result: evidence ready for business cases, funding bids, and franchising assessments
          — not another spreadsheet that needs an analyst to interpret.
        </p>
      </blockquote>
    </section>
  )
}