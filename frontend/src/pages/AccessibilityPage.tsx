import { Link, useNavigate } from "react-router"
import { ArrowLeft } from "lucide-react"
import { Seo } from "@/components/shared/Seo"
import { SUPPORT_EMAIL } from "@/lib/site"
import { breadcrumbJsonLd } from "@/lib/structuredData"

export default function AccessibilityPage() {
  const navigate = useNavigate()
  const description =
    "Aequitas accessibility statement: WCAG 2.2 AA target, known gaps, and how to report issues."

  return (
    <div className="min-h-screen bg-background">
      <Seo
        title="Accessibility Statement — Aequitas"
        description={description}
        path="/accessibility"
        jsonLd={breadcrumbJsonLd([{ name: "Accessibility", path: "/accessibility" }])}
      />
      <div className="border-b border-border bg-card/50">
        <div className="max-w-4xl mx-auto px-4 flex items-center h-8">
          <span className="text-[11px] font-mono text-muted-foreground uppercase tracking-widest">
            Accessibility
          </span>
        </div>
      </div>

      <div className="max-w-4xl mx-auto px-4 py-12">
        <button
          type="button"
          onClick={() => navigate(-1)}
          className="flex items-center gap-2 text-xs text-muted-foreground hover:text-foreground mb-8 font-mono transition-colors"
        >
          <ArrowLeft className="w-3.5 h-3.5" /> BACK
        </button>

        <div className="h-px bg-indigo-500/40 mb-8 max-w-xs" />
        <span className="text-[11px] font-mono uppercase tracking-[0.2em] text-indigo-400 font-medium">
          Inclusive design
        </span>
        <h1 className="text-2xl font-bold tracking-tight mt-3 mb-4 text-foreground">
          Accessibility statement
        </h1>
        <p className="text-sm text-muted-foreground leading-relaxed mb-10 max-w-2xl">
          Aequitas aims to be usable by as many people as possible, including disabled users and
          those using assistive technologies. This statement describes our target standard, what we
          have implemented, known gaps, and how to contact us about barriers.
        </p>

        <section className="mb-10">
          <h2 className="text-[11px] uppercase tracking-[0.15em] text-muted-foreground font-mono mb-4">
            Standard
          </h2>
          <div className="border border-border rounded bg-card p-4 text-xs text-muted-foreground leading-relaxed">
            <p>
              We target{" "}
              <strong className="text-foreground">WCAG 2.2 Level AA</strong> for public marketing
              pages and the authenticated analytics shell. This is a continuous improvement target,
              not a formal third-party certification.
            </p>
          </div>
        </section>

        <section className="mb-10">
          <h2 className="text-[11px] uppercase tracking-[0.15em] text-muted-foreground font-mono mb-4">
            Measures in place
          </h2>
          <div className="border border-border rounded bg-card p-4 text-xs text-muted-foreground leading-relaxed">
            <ul className="list-disc pl-4 space-y-2">
              <li>Semantic headings, landmarks, and skip-to-main-content on the landing page.</li>
              <li>Visible focus styles on primary navigation and CTAs.</li>
              <li>Text alternatives for key imagery (e.g. hero dashboard preview).</li>
              <li>
                Colour is not the sole means of conveying severity in many chart and KPI surfaces
                (labels and mono values accompany colour).
              </li>
              <li>
                Keyboard-operable filters and routes in the main app shell (browser-native and
                component focus management).
              </li>
            </ul>
          </div>
        </section>

        <section className="mb-10">
          <h2 className="text-[11px] uppercase tracking-[0.15em] text-muted-foreground font-mono mb-4">
            Known gaps
          </h2>
          <div className="border border-border rounded bg-card p-4 text-xs text-muted-foreground leading-relaxed">
            <ul className="list-disc pl-4 space-y-2">
              <li>
                Complex visualisations (maps, multi-series charts) may have limited screen-reader
                density compared with tabular exports; PDF export is available for dimension packs
                where configured.
              </li>
              <li>
                Map interactions (pan/zoom/tooltips) are mouse-primary; keyboard and SR experience
                for Mapbox layers is partial.
              </li>
              <li>
                Chat drawer streaming text may announce incompletely in some assistive technology
                combinations.
              </li>
              <li>
                Full automated + manual audit against every WCAG 2.2 AA criterion is not yet
                published as a formal conformance report.
              </li>
            </ul>
          </div>
        </section>

        <section className="mb-10">
          <h2 className="text-[11px] uppercase tracking-[0.15em] text-muted-foreground font-mono mb-4">
            Feedback
          </h2>
          <div className="border border-border rounded bg-card p-4 text-xs text-muted-foreground leading-relaxed space-y-2">
            <p>
              If you encounter an accessibility barrier, please email{" "}
              <a
                href={`mailto:${SUPPORT_EMAIL}?subject=Accessibility%20feedback`}
                className="text-indigo-400 hover:underline"
              >
                {SUPPORT_EMAIL}
              </a>{" "}
              or use the{" "}
              <Link to="/contact" className="text-indigo-400 hover:underline">
                contact form
              </Link>
              . Include the page URL, what you were trying to do, and the assistive technology you
              use if relevant. We aim to respond within a reasonable time and prioritise blocking
              issues.
            </p>
          </div>
        </section>

        <p className="text-xs text-muted-foreground">
          Related:{" "}
          <Link to="/methodology" className="text-indigo-400 hover:underline">
            Methodology
          </Link>
          {" · "}
          <Link to="/privacy" className="text-indigo-400 hover:underline">
            Privacy
          </Link>
          {" · "}
          <Link to="/" className="text-indigo-400 hover:underline">
            Home
          </Link>
        </p>
      </div>
    </div>
  )
}
