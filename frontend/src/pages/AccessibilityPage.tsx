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
    <div className="min-h-screen app-atmosphere text-foreground">
      <Seo
        title="Accessibility Statement — Aequitas"
        description={description}
        path="/accessibility"
        jsonLd={breadcrumbJsonLd([{ name: "Accessibility", path: "/accessibility" }])}
      />
      <div className="border-b border-white/50 bg-white/20 backdrop-blur-2xl">
        <div className="max-w-3xl mx-auto px-6 flex items-center min-h-11">
          <span className="text-sm text-muted-foreground">Accessibility</span>
        </div>
      </div>

      <div className="max-w-3xl mx-auto px-6 py-12 sm:py-14">
        <button
          type="button"
          onClick={() => navigate(-1)}
          className="flex items-center gap-2 text-sm text-muted-foreground hover:text-foreground mb-8 transition-colors"
        >
          <ArrowLeft className="w-4 h-4" /> Back
        </button>

        <div className="h-px bg-primary/40 mb-8 max-w-xs" />
        <p className="marketing-eyebrow text-primary">Inclusive design</p>
        <h1 className="text-3xl sm:text-4xl font-bold tracking-tight mt-3 mb-4 text-foreground">
          Accessibility statement
        </h1>
        <p className="marketing-lede mb-12">
          Aequitas aims to be usable by as many people as possible, including disabled users and
          those using assistive technologies. This statement describes our target standard, what we
          have implemented, known gaps, and how to contact us about barriers.
        </p>

        <section className="mb-10">
          <h2 className="text-lg font-semibold text-foreground mb-4">Standard</h2>
          <div className="app-glass-strong rounded-2xl border border-white/60 p-5 marketing-body">
            <p>
              We target{" "}
              <strong className="text-foreground">WCAG 2.2 Level AA</strong> for public marketing
              pages and the authenticated analytics shell. This is a continuous improvement target,
              not a formal third-party certification.
            </p>
          </div>
        </section>

        <section className="mb-10">
          <h2 className="text-lg font-semibold text-foreground mb-4">Measures in place</h2>
          <div className="app-glass-strong rounded-2xl border border-white/60 p-5 marketing-body">
            <ul className="list-disc pl-5 space-y-2.5">
              <li>Semantic headings, landmarks, and skip-to-main-content on the landing page.</li>
              <li>Visible focus styles on primary navigation and CTAs.</li>
              <li>Text alternatives for key imagery (e.g. hero dashboard preview).</li>
              <li>
                Colour is not the sole means of conveying severity in many chart and KPI surfaces
                (labels and values accompany colour).
              </li>
              <li>
                Keyboard-operable filters and routes in the main app shell (browser-native and
                component focus management).
              </li>
              <li>
                Marketing and legal pages use a minimum body size of 16px with improved secondary
                text contrast against the dark theme.
              </li>
            </ul>
          </div>
        </section>

        <section className="mb-10">
          <h2 className="text-lg font-semibold text-foreground mb-4">Known gaps</h2>
          <div className="app-glass-strong rounded-2xl border border-white/60 p-5 marketing-body">
            <ul className="list-disc pl-5 space-y-2.5">
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
          <h2 className="text-lg font-semibold text-foreground mb-4">Feedback</h2>
          <div className="app-glass-strong rounded-2xl border border-white/60 p-5 marketing-body space-y-2">
            <p>
              If you encounter an accessibility barrier, please email{" "}
              <a
                href={`mailto:${SUPPORT_EMAIL}?subject=Accessibility%20feedback`}
                className="text-primary hover:underline font-medium"
              >
                {SUPPORT_EMAIL}
              </a>{" "}
              or use the{" "}
              <Link to="/contact" className="text-primary hover:underline font-medium">
                contact form
              </Link>
              . Include the page URL, what you were trying to do, and the assistive technology you
              use if relevant. We aim to respond within a reasonable time and prioritise blocking
              issues.
            </p>
          </div>
        </section>

        <p className="text-sm text-muted-foreground">
          Related:{" "}
          <Link to="/methodology" className="text-primary hover:underline">
            Methodology
          </Link>
          {" · "}
          <Link to="/privacy" className="text-primary hover:underline">
            Privacy
          </Link>
          {" · "}
          <Link to="/" className="text-primary hover:underline">
            Home
          </Link>
        </p>
      </div>
    </div>
  )
}
