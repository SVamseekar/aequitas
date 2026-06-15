import { Link, useNavigate } from "react-router"
import { ArrowRight } from "lucide-react"
import { useAuth } from "@/contexts/AuthContext"

export function LandingCta() {
  const navigate = useNavigate()
  const { user } = useAuth()
  const ctaPath = user ? "/dashboard" : "/auth"

  return (
    <section aria-labelledby="landing-cta-heading" className="border-y border-border bg-card/20 backdrop-blur-sm">
      <div className="max-w-7xl mx-auto px-6 py-24 text-center">
        <h2
          id="landing-cta-heading"
          className="text-3xl font-bold text-foreground tracking-tight mb-4 leading-tight"
        >
          Ready to see your region&apos;s data?
        </h2>
        <p className="text-sm text-muted-foreground max-w-md mx-auto mb-8 leading-relaxed">
          Explore evidence-graded analytics across 8 policy dimensions, or request access for your
          team.
        </p>
        <div className="flex flex-wrap items-center justify-center gap-4">
          <button
            onClick={() => navigate(ctaPath)}
            className="flex items-center gap-2.5 px-6 py-3.5 bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-bold uppercase tracking-wider rounded transition-all focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-indigo-400 focus-visible:ring-offset-2 focus-visible:ring-offset-background"
          >
            Explore the platform <ArrowRight className="w-4 h-4" aria-hidden />
          </button>
          <Link
            to="/contact"
            className="flex items-center gap-2.5 px-6 py-3.5 border border-border hover:border-indigo-500/40 text-muted-foreground hover:text-foreground hover:bg-card/50 text-xs font-bold uppercase tracking-wider rounded transition-all"
          >
            Request access
          </Link>
        </div>
      </div>
    </section>
  )
}