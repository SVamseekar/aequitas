import { Link, useNavigate } from "react-router"
import { ArrowRight } from "lucide-react"
import { useAuth } from "@/contexts/AuthContext"
import { AequitasLogo } from "@/components/shared/AequitasLogo"
import { SITE_TAGLINE } from "@/lib/site"

export function LandingNav() {
  const navigate = useNavigate()
  const { user } = useAuth()
  const ctaPath = user ? "/dashboard" : "/auth"
  const ctaLabel = user ? "Open platform" : "Get started"

  return (
    <header className="border-b border-border bg-card/40 backdrop-blur-md relative z-10">
      <nav
        aria-label="Primary"
        className="max-w-7xl mx-auto px-6 flex items-center justify-between min-h-16 py-3"
      >
        <Link to="/" className="flex items-center gap-2.5 shrink-0" aria-label="Aequitas home">
          <AequitasLogo className="w-5 h-5 text-indigo-400 shrink-0" aria-hidden />
          <span className="text-sm font-mono font-bold tracking-[0.3em] uppercase text-foreground whitespace-nowrap">
            AEQUITAS
          </span>
          <span className="hidden md:inline text-sm font-mono text-muted-foreground font-normal whitespace-nowrap">
            · {SITE_TAGLINE}
          </span>
        </Link>
        <div className="flex items-center gap-6">
          <Link
            to="/about"
            className="text-xs text-muted-foreground hover:text-foreground transition-colors font-mono tracking-widest"
          >
            About
          </Link>
          <button
            onClick={() => navigate(ctaPath)}
            className="flex items-center gap-2 px-4 py-1.5 text-xs font-semibold bg-indigo-600 hover:bg-indigo-500 text-white rounded transition-all focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-indigo-400 focus-visible:ring-offset-2 focus-visible:ring-offset-background"
          >
            {ctaLabel} <ArrowRight className="w-3.5 h-3.5" aria-hidden />
          </button>
        </div>
      </nav>
    </header>
  )
}