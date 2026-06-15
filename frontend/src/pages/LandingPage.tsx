import { Seo } from "@/components/shared/Seo"
import { LandingAudience } from "@/components/landing/LandingAudience"
import { LandingCta } from "@/components/landing/LandingCta"
import { LandingDataSources } from "@/components/landing/LandingDataSources"
import { LandingDimensions } from "@/components/landing/LandingDimensions"
import { LandingFooter } from "@/components/landing/LandingFooter"
import { LandingHero } from "@/components/landing/LandingHero"
import { LandingHowItWorks } from "@/components/landing/LandingHowItWorks"
import { LandingNav } from "@/components/landing/LandingNav"
import { LandingProblemSolution } from "@/components/landing/LandingProblemSolution"
import { LandingStats } from "@/components/landing/LandingStats"
import { landingPageJsonLd } from "@/lib/structuredData"
import { DEFAULT_DESCRIPTION, SITE_TAGLINE } from "@/lib/site"

export default function LandingPage() {
  return (
    <div className="min-h-screen bg-background text-foreground relative overflow-hidden">
      <Seo
        title={`Aequitas — ${SITE_TAGLINE}`}
        description={DEFAULT_DESCRIPTION}
        path="/"
        jsonLd={landingPageJsonLd()}
      />

      <a
        href="#main-content"
        className="sr-only focus:not-sr-only focus:absolute focus:z-50 focus:top-4 focus:left-4 focus:px-4 focus:py-2 focus:bg-indigo-600 focus:text-white focus:rounded focus:text-sm"
      >
        Skip to main content
      </a>

      <div
        className="absolute inset-0 opacity-40 bg-[linear-gradient(to_right,#80808012_1px,transparent_1px),linear-gradient(to_bottom,#80808012_1px,transparent_1px)] bg-[size:24px_24px] pointer-events-none"
        aria-hidden
      />

      <LandingNav />

      <main id="main-content" className="relative z-10">
        <LandingHero />
        <LandingStats />
        <LandingAudience />
        <LandingProblemSolution />
        <LandingHowItWorks />
        <LandingDimensions />
        <LandingDataSources />
        <LandingCta />
      </main>

      <LandingFooter />
    </div>
  )
}