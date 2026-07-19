import { Link, useNavigate } from "react-router"
import { ArrowRight } from "lucide-react"
import heroImage from "@/assets/hero.png"
import { SITE_TAGLINE } from "@/lib/site"
import { METRICS_CANON, formatGini } from "@/lib/metricsCanon"

export function LandingHero() {
  const navigate = useNavigate()
  // Analytics are public; auth only required for chat/save/profile
  const ctaPath = "/dashboard"

  return (
    <section
      aria-labelledby="landing-hero-heading"
      className="max-w-7xl mx-auto px-6 pt-20 pb-16 lg:pt-24 lg:pb-20 grid lg:grid-cols-2 gap-12 lg:gap-16 items-center"
    >
      <div className="max-w-2xl motion-safe:animate-fade-in">
        <div className="h-px bg-indigo-400/40 mb-6 max-w-[64px]" aria-hidden />
        <p className="text-[11px] font-mono uppercase tracking-[0.3em] text-indigo-400 font-bold">
          {SITE_TAGLINE}
        </p>
        <h1
          id="landing-hero-heading"
          className="text-4xl sm:text-5xl lg:text-[54px] font-black leading-[1.02] tracking-tight mt-3 mb-6 text-foreground"
        >
          See where your bus network
          <span className="text-indigo-400"> is failing people.</span>
        </h1>
        <p className="text-base text-muted-foreground max-w-lg leading-relaxed mb-9">
          Aequitas maps bus service levels against local deprivation, identifies underserved
          communities, and models the cost and impact of fixing it — so funding decisions are
          backed by evidence, not guesswork.
        </p>
        <div className="flex flex-wrap items-center gap-4">
          <button
            type="button"
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

      <figure className="relative flex flex-col items-center lg:items-end gap-3">
        <div className="relative border border-border rounded-xl p-2 bg-card/60 w-full max-w-lg shadow-2xl shadow-indigo-950/20">
          <img
            src={heroImage}
            alt="Aequitas dashboard showing bus equity analytics across England"
            width={640}
            height={400}
            loading="eager"
            fetchPriority="high"
            className="w-full h-auto rounded-lg"
          />
          <div className="absolute bottom-4 left-4 right-4 sm:right-auto sm:max-w-[min(100%,280px)] rounded-md border border-indigo-500/30 bg-background/90 backdrop-blur-sm px-3 py-2 shadow-lg">
            <p className="text-[10px] font-mono uppercase tracking-wider text-indigo-400 font-bold">
              National equity
            </p>
            <p className="text-sm font-mono font-bold text-foreground mt-0.5">
              Gini {formatGini(METRICS_CANON.gini)}
              <span className="text-muted-foreground font-normal text-xs ml-2">
                · {METRICS_CANON.sections} sections
              </span>
            </p>
          </div>
        </div>
        <figcaption className="text-[11px] font-mono text-muted-foreground text-center lg:text-right max-w-lg">
          National bus service inequality Gini {formatGini(METRICS_CANON.gini)} across{" "}
          {METRICS_CANON.lsoas.toLocaleString("en-GB")} LSOAs — pre-computed warehouse, not live ops data.
        </figcaption>
      </figure>
    </section>
  )
}
