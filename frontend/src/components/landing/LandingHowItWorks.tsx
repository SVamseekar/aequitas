import { HOW_IT_WORKS } from "./data"

export function LandingHowItWorks() {
  return (
    <section
      aria-labelledby="landing-how-heading"
      className="border-y border-border bg-card/20 backdrop-blur-sm"
    >
      <div className="max-w-7xl mx-auto px-6 py-20">
        <p className="text-[11px] font-mono uppercase tracking-[0.3em] text-muted-foreground font-bold">
          How it works
        </p>
        <h2 id="landing-how-heading" className="sr-only">
          How Aequitas works
        </h2>
        <ol className="grid md:grid-cols-3 gap-8 mt-10">
          {HOW_IT_WORKS.map((step, index) => (
            <li
              key={step.step}
              className="p-6 rounded-lg border border-border bg-card/40 backdrop-blur-sm hover:border-border transition-colors"
            >
              <div
                className="w-8 h-8 rounded bg-indigo-400/10 flex items-center justify-center mb-4 border border-indigo-400/20"
                aria-hidden
              >
                <step.icon className="w-4 h-4 text-indigo-400" />
              </div>
              <h3 className="text-xs font-bold font-mono tracking-wider text-foreground uppercase mb-2">
                <span className="text-indigo-400 mr-2">{index + 1}.</span>
                {step.step}
              </h3>
              <p className="text-[13px] text-muted-foreground leading-relaxed">{step.description}</p>
            </li>
          ))}
        </ol>
      </div>
    </section>
  )
}