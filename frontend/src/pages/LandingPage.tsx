import { useNavigate } from "react-router"
import { useAuth } from "@/contexts/AuthContext"
import {
  ArrowRight, Scale, MapPin, Bus, Network,
  Leaf, PoundSterling, FileText, Sliders,
} from "lucide-react"

const HEADLINE_STATS = [
  { label: "Gini Coefficient", value: "0.574", sub: "Bus service inequality" },
  { label: "Palma Ratio", value: "5.70×", sub: "Top 10% vs bottom 40%" },
  { label: "Evening Isolated", value: "15.4%", sub: "of LSOAs" },
  { label: "Sunday Deserts", value: "20.0%", sub: "of LSOAs" },
]

const DIMENSIONS = [
  {
    icon: Scale,
    title: "Equity & Deprivation",
    desc: "Gini, Lorenz, Palma ratio — measuring service inequality across 33,755 LSOAs.",
    route: "/equity",
  },
  {
    icon: MapPin,
    title: "Accessibility",
    desc: "2SFCA 400m catchment — gaps to jobs, healthcare, and secondary schools.",
    route: "/accessibility",
  },
  {
    icon: Bus,
    title: "Service Quality",
    desc: "Headway, evening isolation, Sunday deserts, peak ratios — mean SQI 65.4/100.",
    route: "/service-quality",
  },
  {
    icon: Network,
    title: "Route Network",
    desc: "13,099 routes, 37.7% cross-LA, operator HHI concentration analysis.",
    route: "/route-network",
  },
  {
    icon: Leaf,
    title: "Modal Shift & Carbon",
    desc: "DfT elasticities, DESNZ 2025 factors — CO₂ savings from modal shift.",
    route: "/modal-shift",
  },
  {
    icon: PoundSterling,
    title: "Economic Appraisal",
    desc: "BCR via TAG v2.03fc, Green Book methodology, GDP multipliers.",
    route: "/economic",
  },
  {
    icon: FileText,
    title: "Bus Services Act 2025",
    desc: "LTA franchising readiness tiers, operator concentration, compliance gaps.",
    route: "/bus-services-act",
  },
  {
    icon: Sliders,
    title: "Policy Scenarios",
    desc: "Parameterised modelling — frequency restoration, last bus, DRT coverage.",
    route: "/scenarios",
  },
]

export default function LandingPage() {
  const navigate = useNavigate()
  const { user } = useAuth()

  return (
    <div className="min-h-screen bg-background">
      {/* Status bar */}
      <div className="border-b border-border bg-card/50">
        <div className="max-w-7xl mx-auto px-4 flex items-center justify-between h-8">
          <div className="flex items-center gap-3">
            <div className="w-1.5 h-1.5 rounded-full bg-green-400 animate-pulse" />
            <span className="text-[10px] font-mono text-muted-foreground uppercase tracking-widest">
              Aequitas Intelligence — Systems Online
            </span>
          </div>
          <span className="text-[10px] font-mono text-muted-foreground/40">
            NaPTAN · BODS · ONS · IMD · DfT TAG
          </span>
        </div>
      </div>

      {/* Nav */}
      <nav className="border-b border-border">
        <div className="max-w-7xl mx-auto px-4 flex items-center justify-between h-14">
          <span className="text-sm font-mono font-bold tracking-widest uppercase text-foreground">
            AEQUITAS
          </span>
          <div className="flex items-center gap-3">
            <button
              onClick={() => navigate("/about")}
              className="text-[11px] text-muted-foreground hover:text-foreground transition-colors font-mono"
            >
              ABOUT
            </button>
            {user ? (
              <button
                onClick={() => navigate("/")}
                className="flex items-center gap-2 px-4 py-1.5 text-xs font-medium bg-indigo-600 text-white rounded hover:bg-indigo-500 transition-colors"
              >
                Open Terminal <ArrowRight className="w-3.5 h-3.5" />
              </button>
            ) : (
              <button
                onClick={() => navigate("/auth")}
                className="flex items-center gap-2 px-4 py-1.5 text-xs font-medium bg-indigo-600 text-white rounded hover:bg-indigo-500 transition-colors"
              >
                Get Started <ArrowRight className="w-3.5 h-3.5" />
              </button>
            )}
          </div>
        </div>
      </nav>

      {/* Hero */}
      <section className="max-w-7xl mx-auto px-4 pt-20 pb-16">
        <div className="max-w-2xl">
          <div className="h-px bg-indigo-500/40 mb-8 max-w-xs" />
          <span className="text-[10px] font-mono uppercase tracking-[0.2em] text-indigo-400 font-medium">
            Policy Intelligence Platform
          </span>
          <h1 className="text-4xl sm:text-5xl font-bold leading-[1.05] tracking-tight mt-3 mb-5 text-foreground">
            Evidence-Based Policy<br />
            <span className="text-indigo-400">for UK Bus Transport</span>
          </h1>
          <p className="text-sm text-muted-foreground max-w-lg leading-relaxed mb-8">
            Pre-computed analytics across 8 policy dimensions, 33,755 LSOAs, and 13,099 routes.
            Ask questions in plain English — grounded in NaPTAN, BODS, ONS, IMD, and DfT data.
          </p>
          <button
            onClick={() => navigate(user ? "/" : "/auth")}
            className="flex items-center gap-2 px-6 py-3 bg-indigo-600 text-white text-sm font-semibold rounded hover:bg-indigo-500 transition-colors"
          >
            Start Exploring <ArrowRight className="w-4 h-4" />
          </button>
        </div>
      </section>

      {/* Headline stats strip */}
      <section className="border-y border-border bg-card/30">
        <div className="max-w-7xl mx-auto px-4 py-6">
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-px bg-border">
            {HEADLINE_STATS.map((m) => (
              <div key={m.label} className="bg-background p-5">
                <p className="text-[9px] font-mono uppercase tracking-widest text-muted-foreground/60 mb-1">
                  {m.label}
                </p>
                <p className="text-2xl font-bold font-mono text-indigo-400">{m.value}</p>
                <p className="text-[10px] text-muted-foreground/50 mt-0.5">{m.sub}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* 8 Dimension cards */}
      <section className="max-w-7xl mx-auto px-4 py-16">
        <span className="text-[10px] font-mono uppercase tracking-[0.2em] text-muted-foreground font-medium block mb-8">
          8 Policy Dimensions
        </span>
        <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-3">
          {DIMENSIONS.map((d) => (
            <button
              key={d.title}
              onClick={() => navigate(user ? d.route : "/auth")}
              className="text-left p-4 rounded border border-border bg-card hover:border-indigo-500/40 hover:bg-card/80 transition-all group"
            >
              <d.icon className="w-5 h-5 text-indigo-400 mb-3 group-hover:scale-110 transition-transform" />
              <p className="text-xs font-semibold text-foreground mb-1">{d.title}</p>
              <p className="text-[11px] text-muted-foreground leading-relaxed">{d.desc}</p>
            </button>
          ))}
        </div>
      </section>

      {/* Footer */}
      <footer className="border-t border-border py-6">
        <div className="max-w-7xl mx-auto px-4 flex flex-col sm:flex-row items-center justify-between gap-3">
          <span className="text-[10px] text-muted-foreground/40 font-mono">
            POLICY ANALYSIS TOOL — NOT OFFICIAL DfT GUIDANCE
          </span>
          <div className="flex items-center gap-4">
            <button onClick={() => navigate("/about")} className="text-[10px] text-muted-foreground/50 hover:text-muted-foreground font-mono uppercase tracking-wider transition-colors">About</button>
            <button onClick={() => navigate("/disclaimer")} className="text-[10px] text-muted-foreground/50 hover:text-muted-foreground font-mono uppercase tracking-wider transition-colors">Disclaimer</button>
            <button onClick={() => navigate("/contact")} className="text-[10px] text-muted-foreground/50 hover:text-muted-foreground font-mono uppercase tracking-wider transition-colors">Contact</button>
          </div>
        </div>
      </footer>
    </div>
  )
}
