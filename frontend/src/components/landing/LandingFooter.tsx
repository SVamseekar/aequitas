import { Link } from "react-router"
import {
  AUTHOR_NAME,
  GITHUB_URL,
  PORTFOLIO_URL,
  SUPPORT_EMAIL,
  isAnalyticsConfigured,
} from "@/lib/site"
import { useAuth } from "@/contexts/AuthContext"

const year = new Date().getFullYear()

export function LandingFooter() {
  const { user } = useAuth()
  const explorePath = user ? "/dashboard" : "/auth"
  const signInPath = user ? "/dashboard" : "/auth"

  return (
    <footer className="border-t border-border bg-background">
      <div className="max-w-7xl mx-auto px-6 py-12">
        <p className="flex items-center gap-2 text-[11px] text-amber-400 font-mono font-semibold tracking-[0.2em] uppercase mb-10">
          <span className="w-2 h-2 rounded-full bg-amber-400 shrink-0" aria-hidden />
          Policy analysis tool — not official government guidance
        </p>

        <div className="grid grid-cols-2 md:grid-cols-4 gap-8 mb-10">
          <nav aria-label="Product">
            <h2 className="text-[11px] font-mono uppercase tracking-widest text-foreground font-bold mb-4">
              Product
            </h2>
            <ul className="space-y-2.5">
              <li>
                <Link
                  to={explorePath}
                  className="text-[11px] text-muted-foreground hover:text-foreground font-mono uppercase tracking-wider transition-colors"
                >
                  Explore
                </Link>
              </li>
              <li>
                <a
                  href="/#dimensions"
                  className="text-[11px] text-muted-foreground hover:text-foreground font-mono uppercase tracking-wider transition-colors"
                >
                  Dimensions
                </a>
              </li>
              <li>
                <Link
                  to={signInPath}
                  className="text-[11px] text-muted-foreground hover:text-foreground font-mono uppercase tracking-wider transition-colors"
                >
                  Sign in
                </Link>
              </li>
            </ul>
          </nav>

          <nav aria-label="Resources">
            <h2 className="text-[11px] font-mono uppercase tracking-widest text-foreground font-bold mb-4">
              Resources
            </h2>
            <ul className="space-y-2.5">
              <li>
                <Link
                  to="/methodology"
                  className="text-[11px] text-muted-foreground hover:text-foreground font-mono uppercase tracking-wider transition-colors"
                >
                  Methodology
                </Link>
              </li>
              <li>
                <Link
                  to="/about"
                  className="text-[11px] text-muted-foreground hover:text-foreground font-mono uppercase tracking-wider transition-colors"
                >
                  About
                </Link>
              </li>
              <li>
                <Link
                  to="/accessibility"
                  className="text-[11px] text-muted-foreground hover:text-foreground font-mono uppercase tracking-wider transition-colors"
                >
                  Accessibility
                </Link>
              </li>
            </ul>
          </nav>

          <nav aria-label="Legal">
            <h2 className="text-[11px] font-mono uppercase tracking-widest text-foreground font-bold mb-4">
              Legal
            </h2>
            <ul className="space-y-2.5">
              <li>
                <Link
                  to="/privacy"
                  className="text-[11px] text-muted-foreground hover:text-foreground font-mono uppercase tracking-wider transition-colors"
                >
                  Privacy
                </Link>
              </li>
              <li>
                <Link
                  to="/terms"
                  className="text-[11px] text-muted-foreground hover:text-foreground font-mono uppercase tracking-wider transition-colors"
                >
                  Terms
                </Link>
              </li>
              <li>
                <Link
                  to="/disclaimer"
                  className="text-[11px] text-muted-foreground hover:text-foreground font-mono uppercase tracking-wider transition-colors"
                >
                  Disclaimer
                </Link>
              </li>
              <li>
                <Link
                  to="/refunds"
                  className="text-[11px] text-muted-foreground hover:text-foreground font-mono uppercase tracking-wider transition-colors"
                >
                  Refunds
                </Link>
              </li>
            </ul>
          </nav>

          <nav aria-label="Contact">
            <h2 className="text-[11px] font-mono uppercase tracking-widest text-foreground font-bold mb-4">
              Contact
            </h2>
            <ul className="space-y-2.5">
              <li>
                <a
                  href={`mailto:${SUPPORT_EMAIL}`}
                  className="text-[11px] text-muted-foreground hover:text-foreground font-mono tracking-wider transition-colors break-all"
                >
                  {SUPPORT_EMAIL}
                </a>
              </li>
              <li>
                <Link
                  to="/contact"
                  className="text-[11px] text-muted-foreground hover:text-foreground font-mono uppercase tracking-wider transition-colors"
                >
                  Contact form
                </Link>
              </li>
              <li>
                <a
                  href={PORTFOLIO_URL}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-[11px] text-muted-foreground hover:text-foreground font-mono uppercase tracking-wider transition-colors"
                >
                  Portfolio
                </a>
              </li>
              <li>
                <a
                  href={GITHUB_URL}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-[11px] text-muted-foreground hover:text-foreground font-mono uppercase tracking-wider transition-colors"
                >
                  GitHub
                </a>
              </li>
            </ul>
          </nav>
        </div>

        <div className="border-t border-border pt-6 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
          <p className="text-[11px] font-mono text-muted-foreground">
            © {year} Aequitas · {AUTHOR_NAME}
          </p>
          {isAnalyticsConfigured() && (
            <p className="text-[11px] font-mono text-muted-foreground/80">
              We use privacy-respecting analytics when configured.{" "}
              <Link to="/privacy" className="text-indigo-400/90 hover:underline">
                Privacy
              </Link>
            </p>
          )}
        </div>
      </div>
    </footer>
  )
}
