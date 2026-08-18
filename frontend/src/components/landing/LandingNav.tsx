import { useEffect, useState } from "react"
import { Link } from "react-router"
import { useAuth } from "@/contexts/AuthContext"
import { AequitasLogo } from "@/components/shared/AequitasLogo"

const LINKS = [
  { to: "/briefings", label: "Briefings" },
  { to: "/methodology", label: "Method" },
  { to: "/about", label: "About" },
] as const

export function LandingNav() {
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
          <AequitasLogo className="w-5 h-5 text-[var(--l-ink)]" aria-hidden />
          <span className="text-[17px] font-semibold tracking-tight text-[var(--l-ink)]">
            aequitas
          </span>
        </Link>

        <div className="flex items-center gap-5 lg:gap-7">
          <div className="hidden md:flex items-center gap-6 lg:gap-7">
            {LINKS.map((l) => (
              <Link key={l.to} to={l.to} className="landing-nav-link">
                {l.label}
              </Link>
            ))}
            <Link to={user ? "/app/england" : "/auth"} className="landing-nav-link hidden md:inline">
              {user ? "Open" : "Log in"}
            </Link>
          </div>
          <Link to={user ? "/app/england" : "/auth"} className="landing-nav-link md:hidden">
            {user ? "Open" : "Log in"}
          </Link>
          <Link to="/contact" className="landing-btn-outline">
            Contact
          </Link>
        </div>
      </nav>
    </header>
  )
}
