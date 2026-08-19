import { Link } from "react-router"
import { Seo } from "@/components/shared/Seo"
import { SUPPORT_EMAIL } from "@/lib/site"
import { breadcrumbJsonLd } from "@/lib/structuredData"
import { BriefingLayout } from "./briefing/BriefingLayout"

export default function AccessibilityPage() {
  const description =
    "Aequitas accessibility statement: WCAG 2.2 AA target, known gaps, and how to report issues."

  return (
    <BriefingLayout>
      <Seo
        title="Accessibility Statement — Aequitas"
        description={description}
        path="/accessibility"
        jsonLd={breadcrumbJsonLd([{ name: "Accessibility", path: "/accessibility" }])}
      />
      <p className="text-xs font-medium uppercase tracking-wide text-[var(--l-rust)]">
        Inclusive design
      </p>
      <h1 className="font-display text-3xl sm:text-4xl text-[var(--l-ink)] mt-2 mb-4">
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

        <p className="text-sm text-[var(--l-slate)]">
          Related:{" "}
          <Link to="/methodology" className="underline">
            Method
          </Link>
          {" · "}
          <Link to="/privacy" className="underline">
            Privacy
          </Link>
        </p>
    </BriefingLayout>
  )
}
