import { Link } from "react-router"
import {
  AUTHOR_NAME,
  GITHUB_URL,
  PORTFOLIO_URL,
  SUPPORT_EMAIL,
  isAnalyticsConfigured,
} from "@/lib/site"

const year = new Date().getFullYear()

const linkClass =
  "text-sm text-muted-foreground hover:text-foreground transition-colors underline-offset-4 hover:underline"

export function Footer() {
  return (
    <footer className="border-t border-white/50 mt-auto bg-white/15 backdrop-blur-2xl">
      <div className="max-w-7xl mx-auto px-4 py-8">
        <p className="text-sm text-amber-900 bg-amber-50/90 border border-amber-200/80 rounded-full px-3 py-2 mb-6 inline-flex items-start gap-2 max-w-2xl leading-snug">
          <span className="w-1.5 h-1.5 rounded-full bg-amber-600 shrink-0 mt-1.5" aria-hidden />
          Policy analysis tool — not official DfT guidance
        </p>

        <div className="grid grid-cols-2 md:grid-cols-4 gap-8 mb-6">
          <nav aria-label="Product">
            <h2 className="text-sm font-semibold text-foreground mb-3">Product</h2>
            <ul className="space-y-2">
              <li>
                <Link to="/dashboard" className={linkClass}>
                  Explore
                </Link>
              </li>
              <li>
                <Link to="/dashboard" className={linkClass}>
                  Dimensions
                </Link>
              </li>
              <li>
                <Link to="/profile" className={linkClass}>
                  Profile
                </Link>
              </li>
            </ul>
          </nav>

          <nav aria-label="Resources">
            <h2 className="text-sm font-semibold text-foreground mb-3">Resources</h2>
            <ul className="space-y-2">
              <li>
                <Link to="/methodology" className={linkClass}>
                  Methodology
                </Link>
              </li>
              <li>
                <Link to="/about" className={linkClass}>
                  About
                </Link>
              </li>
              <li>
                <Link to="/accessibility" className={linkClass}>
                  Accessibility
                </Link>
              </li>
            </ul>
          </nav>

          <nav aria-label="Legal">
            <h2 className="text-sm font-semibold text-foreground mb-3">Legal</h2>
            <ul className="space-y-2">
              <li>
                <Link to="/privacy" className={linkClass}>
                  Privacy
                </Link>
              </li>
              <li>
                <Link to="/terms" className={linkClass}>
                  Terms
                </Link>
              </li>
              <li>
                <Link to="/disclaimer" className={linkClass}>
                  Disclaimer
                </Link>
              </li>
              <li>
                <Link to="/refunds" className={linkClass}>
                  Refunds
                </Link>
              </li>
            </ul>
          </nav>

          <nav aria-label="Contact">
            <h2 className="text-sm font-semibold text-foreground mb-3">Contact</h2>
            <ul className="space-y-2">
              <li>
                <a href={`mailto:${SUPPORT_EMAIL}`} className={`${linkClass} break-all`}>
                  Email
                </a>
              </li>
              <li>
                <Link to="/contact" className={linkClass}>
                  Contact form
                </Link>
              </li>
              <li>
                <a
                  href={PORTFOLIO_URL}
                  target="_blank"
                  rel="noopener noreferrer"
                  className={linkClass}
                >
                  Portfolio
                </a>
              </li>
              <li>
                <a
                  href={GITHUB_URL}
                  target="_blank"
                  rel="noopener noreferrer"
                  className={linkClass}
                >
                  GitHub
                </a>
              </li>
            </ul>
          </nav>
        </div>

        <div className="border-t border-border pt-4 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2">
          <p className="text-sm text-muted-foreground">
            © {year} Aequitas · {AUTHOR_NAME}
          </p>
          {isAnalyticsConfigured() && (
            <p className="text-sm text-muted-foreground">
              Privacy-respecting analytics when configured.{" "}
              <Link to="/privacy" className="text-primary hover:underline">
                Privacy
              </Link>
            </p>
          )}
        </div>
      </div>
    </footer>
  )
}
