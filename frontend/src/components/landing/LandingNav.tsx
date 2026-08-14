import { useEffect, useState } from "react"
import { Link, useNavigate } from "react-router"
import { ArrowRight } from "lucide-react"
import { useAuth } from "@/contexts/AuthContext"
import { AequitasLogo } from "@/components/shared/AequitasLogo"

export function LandingNav() {
  const navigate = useNavigate()
  const { user } = useAuth()
  const [scrolled, setScrolled] = useState(false)

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 12)
    onScroll()
    window.addEventListener("scroll", onScroll, { passive: true })
    return () => window.removeEventListener("scroll", onScroll)
  }, [])

  return (
    <header className={`landing-nav sticky top-0 z-40 ${scrolled ? "is-scrolled" : ""}`}>
      <nav
        aria-label="Primary"
        className="landing-shell flex items-center justify-between h-16 sm:h-[4.25rem]"
      >
        <Link to="/" className="flex items-center gap-2.5" aria-label="Aequitas home">
          <span className="landing-chip flex h-9 w-9 items-center justify-center rounded-xl">
            <AequitasLogo className="w-4 h-4 text-[var(--l-rust)]" aria-hidden />
          </span>
          <span className="text-[15px] font-semibold text-[var(--l-ink)]">Aequitas</span>
        </Link>

        <div className="hidden md:flex items-center gap-8 text-sm text-[var(--l-slate)]">
          <a href="#proof" className="hover:text-[var(--l-ink)] transition-colors">
            Evidence
          </a>
          <a href="#dimensions" className="hover:text-[var(--l-ink)] transition-colors">
            Dimensions
          </a>
          <a href="#how" className="hover:text-[var(--l-ink)] transition-colors">
            How it works
          </a>
          <Link to="/about" className="hover:text-[var(--l-ink)] transition-colors">
            About
          </Link>
        </div>

        <div className="flex items-center gap-2 sm:gap-3">
          <Link
            to="/contact"
            className="hidden sm:inline text-sm font-medium text-[var(--l-slate)] hover:text-[var(--l-ink)] px-2 py-2"
          >
            Contact
          </Link>
          <button
            type="button"
            onClick={() => navigate(user ? "/app/england" : "/auth")}
            className="landing-btn-primary !py-2 !px-4 text-sm"
          >
            {user ? "Open platform" : "Sign in"}
            <ArrowRight className="w-3.5 h-3.5" aria-hidden />
          </button>
        </div>
      </nav>
    </header>
  )
}
