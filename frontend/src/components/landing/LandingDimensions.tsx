import { useNavigate } from "react-router"
import { useAuth } from "@/contexts/AuthContext"
import { DIMENSIONS } from "./data"

export function LandingDimensions() {
  const navigate = useNavigate()
  const { user } = useAuth()

  return (
    <section aria-labelledby="landing-dimensions-heading" className="max-w-7xl mx-auto px-6 py-24">
      <p className="text-[11px] font-mono uppercase tracking-[0.3em] text-indigo-400 font-bold">
        8 policy dimensions
      </p>
      <h2
        id="landing-dimensions-heading"
        className="text-2xl font-bold text-foreground tracking-tight mt-3 mb-10"
      >
        Analytics across the full policy lifecycle
      </h2>
      <ul className="grid sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {DIMENSIONS.map((dimension) => (
          <li key={dimension.title}>
            <button
              type="button"
              onClick={() => navigate(user ? `/dashboard${dimension.route}` : "/auth")}
              className="w-full h-full text-left p-5 rounded-lg border border-border bg-card/40 hover:border-indigo-400/30 hover:bg-card/60 transition-colors duration-300 group focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-indigo-400"
            >
              <dimension.icon
                className="w-5 h-5 text-indigo-400 mb-4 group-hover:text-indigo-300 transition-colors duration-300"
                aria-hidden
              />
              <h3 className="text-xs font-bold text-foreground uppercase tracking-wider mb-1 font-mono">
                {dimension.title}
              </h3>
              <p className="text-[13px] text-muted-foreground leading-relaxed mb-4 min-h-[48px]">
                {dimension.question}
              </p>
              <p className="border-t border-border pt-3 text-[11px] font-mono text-muted-foreground tracking-wider uppercase">
                {dimension.grounded}
              </p>
            </button>
          </li>
        ))}
      </ul>
    </section>
  )
}