import { Link } from "react-router"
import {
  AUTHOR_NAME,
  GITHUB_URL,
  PORTFOLIO_URL,
  SUPPORT_EMAIL,
  isAnalyticsConfigured,
} from "@/lib/site"

const year = new Date().getFullYear()

export function Footer() {
  return (
    <footer className="border-t border-border mt-auto">
      <div className="max-w-7xl mx-auto px-4 py-6">
        <p className="text-[11px] text-amber-400 font-mono font-semibold tracking-wide mb-5">
          POLICY ANALYSIS TOOL — NOT OFFICIAL DfT GUIDANCE
        </p>

        <div className="grid grid-cols-2 md:grid-cols-4 gap-6 mb-5">
          <nav aria-label="Product">
            <h2 className="text-[10px] font-mono uppercase tracking-widest text-foreground font-bold mb-2">
              Product
            </h2>
            <ul className="space-y-1.5">
              <li>
                <Link
                  to="/dashboard"
                  className="text-[11px] text-muted-foreground hover:text-foreground font-mono uppercase tracking-wide transition-colors"
                >
                  Explore
                </Link>
              </li>
              <li>
                <Link
                  to="/dashboard"
                  className="text-[11px] text-muted-foreground hover:text-foreground font-mono uppercase tracking-wide transition-colors"
                >
                  Dimensions
                </Link>
              </li>
              <li>
                <Link
                  to="/profile"
                  className="text-[11px] text-muted-foreground hover:text-foreground font-mono uppercase tracking-wide transition-colors"
                >
                  Profile
                </Link>
              </li>
            </ul>
          </nav>

          <nav aria-label="Resources">
            <h2 className="text-[10px] font-mono uppercase tracking-widest text-foreground font-bold mb-2">
              Resources
            </h2>
            <ul className="space-y-1.5">
              <li>
                <Link
                  to="/methodology"
                  className="text-[11px] text-muted-foreground hover:text-foreground font-mono uppercase tracking-wide transition-colors"
                >
                  Methodology
                </Link>
              </li>
              <li>
                <Link
                  to="/about"
                  className="text-[11px] text-muted-foreground hover:text-foreground font-mono uppercase tracking-wide transition-colors"
                >
                  About
                </Link>
              </li>
              <li>
                <Link
                  to="/accessibility"
                  className="text-[11px] text-muted-foreground hover:text-foreground font-mono uppercase tracking-wide transition-colors"
                >
                  Accessibility
                </Link>
              </li>
            </ul>
          </nav>

          <nav aria-label="Legal">
            <h2 className="text-[10px] font-mono uppercase tracking-widest text-foreground font-bold mb-2">
              Legal
            </h2>
            <ul className="space-y-1.5">
              <li>
                <Link
                  to="/privacy"
                  className="text-[11px] text-muted-foreground hover:text-foreground font-mono uppercase tracking-wide transition-colors"
                >
                  Privacy
                </Link>
              </li>
              <li>
                <Link
                  to="/terms"
                  className="text-[11px] text-muted-foreground hover:text-foreground font-mono uppercase tracking-wide transition-colors"
                >
                  Terms
                </Link>
              </li>
              <li>
                <Link
                  to="/disclaimer"
                  className="text-[11px] text-muted-foreground hover:text-foreground font-mono uppercase tracking-wide transition-colors"
                >
                  Disclaimer
                </Link>
              </li>
              <li>
                <Link
                  to="/refunds"
                  className="text-[11px] text-muted-foreground hover:text-foreground font-mono uppercase tracking-wide transition-colors"
                >
                  Refunds
                </Link>
              </li>
            </ul>
          </nav>

          <nav aria-label="Contact">
            <h2 className="text-[10px] font-mono uppercase tracking-widest text-foreground font-bold mb-2">
              Contact
            </h2>
            <ul className="space-y-1.5">
              <li>
                <a
                  href={`mailto:${SUPPORT_EMAIL}`}
                  className="text-[11px] text-muted-foreground hover:text-foreground font-mono tracking-wide transition-colors break-all"
                >
                  Email
                </a>
              </li>
              <li>
                <Link
                  to="/contact"
                  className="text-[11px] text-muted-foreground hover:text-foreground font-mono uppercase tracking-wide transition-colors"
                >
                  Contact form
                </Link>
              </li>
              <li>
                <a
                  href={PORTFOLIO_URL}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-[11px] text-muted-foreground hover:text-foreground font-mono uppercase tracking-wide transition-colors"
                >
                  Portfolio
                </a>
              </li>
              <li>
                <a
                  href={GITHUB_URL}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-[11px] text-muted-foreground hover:text-foreground font-mono uppercase tracking-wide transition-colors"
                >
                  GitHub
                </a>
              </li>
            </ul>
          </nav>
        </div>

        <div className="border-t border-border pt-4 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2">
          <p className="text-[11px] font-mono text-muted-foreground">
            © {year} Aequitas · {AUTHOR_NAME}
          </p>
          {isAnalyticsConfigured() && (
            <p className="text-[11px] font-mono text-muted-foreground/80">
              Privacy-respecting analytics when configured.{" "}
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
