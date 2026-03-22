import { useNavigate } from "react-router"

export function Footer() {
  const navigate = useNavigate()

  return (
    <footer className="border-t border-border mt-auto">
      <div className="max-w-7xl mx-auto px-4 py-4 flex flex-col sm:flex-row items-center justify-between gap-3">
        <span className="text-[10px] text-muted-foreground/40 font-mono">
          POLICY ANALYSIS TOOL — NOT OFFICIAL DfT GUIDANCE
        </span>
        <div className="flex items-center gap-4">
          <button
            onClick={() => navigate("/about")}
            className="text-[10px] text-muted-foreground/50 hover:text-muted-foreground font-mono uppercase tracking-wider transition-colors"
          >
            About
          </button>
          <button
            onClick={() => navigate("/disclaimer")}
            className="text-[10px] text-muted-foreground/50 hover:text-muted-foreground font-mono uppercase tracking-wider transition-colors"
          >
            Disclaimer
          </button>
          <button
            onClick={() => navigate("/contact")}
            className="text-[10px] text-muted-foreground/50 hover:text-muted-foreground font-mono uppercase tracking-wider transition-colors"
          >
            Contact
          </button>
        </div>
      </div>
    </footer>
  )
}
