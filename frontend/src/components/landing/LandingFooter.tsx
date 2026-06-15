import { Link } from "react-router"

export function LandingFooter() {
  return (
    <footer className="py-10 border-t border-border bg-background">
      <div className="max-w-7xl mx-auto px-6 flex flex-col md:flex-row items-center justify-between gap-6">
        <p className="flex items-center gap-2 text-[11px] text-amber-400 font-mono font-semibold tracking-[0.2em] uppercase">
          <span className="w-2 h-2 rounded-full bg-amber-400" aria-hidden />
          Policy analysis tool — not official government guidance
        </p>
        <nav aria-label="Footer" className="flex items-center gap-6">
          <Link
            to="/about"
            className="text-[11px] text-muted-foreground hover:text-foreground font-mono uppercase tracking-widest transition-colors"
          >
            About
          </Link>
          <Link
            to="/disclaimer"
            className="text-[11px] text-muted-foreground hover:text-foreground font-mono uppercase tracking-widest transition-colors"
          >
            Disclaimer
          </Link>
          <Link
            to="/contact"
            className="text-[11px] text-muted-foreground hover:text-foreground font-mono uppercase tracking-widest transition-colors"
          >
            Contact
          </Link>
        </nav>
      </div>
    </footer>
  )
}