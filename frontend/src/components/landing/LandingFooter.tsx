import { Link } from "react-router"
import {
  AUTHOR_NAME,
  GITHUB_URL,
  PORTFOLIO_URL,
  SUPPORT_EMAIL,
  isAnalyticsConfigured,
} from "@/lib/site"
import { useAuth } from "@/contexts/AuthContext"
import { AequitasLogo } from "@/components/shared/AequitasLogo"

const year = new Date().getFullYear()
const linkClass = "text-sm text-[var(--l-slate)] hover:text-[var(--l-ink)] transition-colors"

export function LandingFooter() {
  const { user } = useAuth()

  return (
    <footer className="relative border-t border-white/40 bg-white/20 backdrop-blur-xl">
      <div className="landing-shell py-10 sm:py-12">
        <div className="flex flex-col lg:flex-row lg:justify-between gap-8 mb-8">
          <div className="max-w-sm">
            <div className="flex items-center gap-2.5 mb-3">
              <AequitasLogo className="w-5 h-5 text-[var(--l-rust)]" aria-hidden />
              <span className="font-semibold text-[var(--l-ink)]">Aequitas</span>
            </div>
            <p className="text-sm text-[var(--l-slate)] leading-relaxed mb-4">
              Bus × deprivation briefing. England, Ireland, and the Netherlands are live. France
              uses the same doors; the pack is not built.
            </p>
            <p className="inline-flex items-center gap-2 text-xs text-amber-900 bg-amber-50 border border-amber-200 rounded-full px-3 py-1.5">
              <span className="w-1.5 h-1.5 rounded-full bg-amber-600" aria-hidden />
              Not official government guidance
            </p>
          </div>

          <div className="grid grid-cols-2 sm:grid-cols-4 gap-8 flex-1 lg:max-w-2xl">
            <nav aria-label="Product">
              <h2 className="text-xs font-semibold uppercase tracking-wide text-[var(--l-ink)] mb-3">
                Product
              </h2>
              <ul className="space-y-2">
                <li>
                  <Link to="/app/england" className={linkClass}>
                    Explore
                  </Link>
                </li>
                <li>
                  <a href="/#dimensions" className={linkClass}>
                    Dimensions
                  </a>
                </li>
                <li>
                  <Link to={user ? "/app/england" : "/auth"} className={linkClass}>
                    Sign in
                  </Link>
                </li>
              </ul>
            </nav>
            <nav aria-label="Resources">
              <h2 className="text-xs font-semibold uppercase tracking-wide text-[var(--l-ink)] mb-3">
                Resources
              </h2>
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
              <h2 className="text-xs font-semibold uppercase tracking-wide text-[var(--l-ink)] mb-3">
                Legal
              </h2>
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
              <h2 className="text-xs font-semibold uppercase tracking-wide text-[var(--l-ink)] mb-3">
                Contact
              </h2>
              <ul className="space-y-2">
                <li>
                  <Link to="/contact" className={linkClass}>
                    Contact form
                  </Link>
                </li>
                <li>
                  <a href={`mailto:${SUPPORT_EMAIL}`} className={linkClass}>
                    Email
                  </a>
                </li>
                <li>
                  <a href={PORTFOLIO_URL} target="_blank" rel="noopener noreferrer" className={linkClass}>
                    Portfolio
                  </a>
                </li>
                <li>
                  <a href={GITHUB_URL} target="_blank" rel="noopener noreferrer" className={linkClass}>
                    GitHub
                  </a>
                </li>
              </ul>
            </nav>
          </div>
        </div>

        <div className="border-t border-[var(--l-rule)] pt-5 flex flex-col sm:flex-row sm:justify-between gap-2">
          <p className="text-sm text-[var(--l-slate)]">
            © {year} Aequitas · {AUTHOR_NAME}
          </p>
          {isAnalyticsConfigured() && (
            <p className="text-sm text-[var(--l-slate)]">
              Privacy-respecting analytics when configured.{" "}
              <Link to="/privacy" className="text-[var(--l-rust)] hover:underline">
                Privacy
              </Link>
            </p>
          )}
        </div>
      </div>
    </footer>
  )
}
