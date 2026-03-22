import { useNavigate } from "react-router"
import { ArrowLeft, GitBranch, Mail } from "lucide-react"

export default function ContactPage() {
  const navigate = useNavigate()

  return (
    <div className="min-h-screen bg-background">
      <div className="border-b border-border bg-card/50">
        <div className="max-w-4xl mx-auto px-4 flex items-center h-8">
          <span className="text-[9px] font-mono text-muted-foreground uppercase tracking-widest">Contact</span>
        </div>
      </div>

      <div className="max-w-4xl mx-auto px-4 py-12">
        <button
          onClick={() => navigate(-1)}
          className="flex items-center gap-2 text-xs text-muted-foreground hover:text-foreground mb-8 font-mono transition-colors"
        >
          <ArrowLeft className="w-3.5 h-3.5" /> BACK
        </button>

        <div className="h-px bg-indigo-500/40 mb-8 max-w-xs" />
        <span className="text-[10px] font-mono uppercase tracking-[0.2em] text-indigo-400 font-medium">Contact & Feedback</span>
        <h1 className="text-2xl font-bold tracking-tight mt-3 mb-4 text-foreground">
          Get in Touch
        </h1>
        <p className="text-sm text-muted-foreground leading-relaxed mb-10 max-w-2xl">
          Aequitas is an open research project. Feedback from transport researchers, LTA planners,
          and policy analysts is welcome.
        </p>

        <div className="grid sm:grid-cols-2 gap-4 mb-10">
          <div className="border border-border rounded bg-card p-5">
            <div className="flex items-center gap-2 mb-3">
              <GitBranch className="w-4 h-4 text-indigo-400" />
              <p className="text-xs font-semibold text-foreground">GitHub Issues</p>
            </div>
            <p className="text-xs text-muted-foreground leading-relaxed mb-3">
              Bug reports, feature requests, and data accuracy issues. Please include the dimension,
              metric, and LSOA/region in question.
            </p>
            <p className="text-[10px] font-mono text-indigo-400/70 uppercase tracking-wider">Preferred channel</p>
          </div>

          <div className="border border-border rounded bg-card p-5">
            <div className="flex items-center gap-2 mb-3">
              <Mail className="w-4 h-4 text-indigo-400" />
              <p className="text-xs font-semibold text-foreground">Research Enquiries</p>
            </div>
            <p className="text-xs text-muted-foreground leading-relaxed mb-3">
              For research collaboration, data licensing questions, or institutional use cases,
              use GitHub Discussions on the project repository.
            </p>
            <p className="text-[10px] font-mono text-indigo-400/70 uppercase tracking-wider">Via GitHub Discussions</p>
          </div>
        </div>

        <section>
          <h2 className="text-[10px] uppercase tracking-[0.15em] text-muted-foreground font-mono mb-4">
            Known Limitations
          </h2>
          <div className="border border-border rounded bg-card p-4 text-xs text-muted-foreground leading-relaxed space-y-2">
            <p>The 400m Euclidean catchment for accessibility metrics underestimates true walking distances
              in areas with physical barriers (rivers, railways, motorways). Network-distance catchments
              are planned for Phase 3.</p>
            <p>BODS GTFS feeds cover 2024–25 timetables. Rural operators with fewer than 5 vehicles
              may be underrepresented. Demand-responsive transport (DRT) services are not captured.</p>
            <p>Modal shift estimates use DfT aggregate elasticities, not revealed-preference data.
              Local elasticity variation is not modelled.</p>
          </div>
        </section>
      </div>
    </div>
  )
}
