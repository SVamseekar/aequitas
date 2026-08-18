import { Seo } from "@/components/shared/Seo"
import { LandingAudience } from "@/components/landing/LandingAudience"
import { LandingCta } from "@/components/landing/LandingCta"
import { LandingCoverage } from "@/components/landing/LandingCoverage"
import { LandingDataSources } from "@/components/landing/LandingDataSources"
import { LandingDimensions } from "@/components/landing/LandingDimensions"
import { LandingFaq } from "@/components/landing/LandingFaq"
import { LandingFooter } from "@/components/landing/LandingFooter"
import { LandingHero } from "@/components/landing/LandingHero"
import { LandingHowItWorks } from "@/components/landing/LandingHowItWorks"
import { LandingNav } from "@/components/landing/LandingNav"
import { LandingProblemSolution } from "@/components/landing/LandingProblemSolution"
import { LandingStats } from "@/components/landing/LandingStats"
import { landingPageJsonLd } from "@/lib/structuredData"
import { DEFAULT_DESCRIPTION } from "@/lib/site"

export default function LandingPage() {
  return (
    <div className="landing-root min-h-screen">
      <Seo
        title={`Aequitas — GTFS × deprivation in England, Ireland, Netherlands, France`}
        description={DEFAULT_DESCRIPTION}
        path="/"
        jsonLd={landingPageJsonLd()}
      />

      <a
        href="#main-content"
        className="sr-only focus:not-sr-only focus:absolute focus:z-50 focus:top-4 focus:left-4 focus:px-4 focus:py-2 focus:bg-[var(--l-rust)] focus:text-white focus:rounded-full focus:text-sm"
      >
        Skip to main content
      </a>

      <LandingNav />

      <main id="main-content">
        <LandingHero />
        <LandingDataSources />
        <LandingCoverage />
        <LandingStats />
        <LandingProblemSolution />
        <LandingDimensions />
        <LandingHowItWorks />
        <LandingAudience />
        <LandingFaq />
        <LandingCta />
      </main>

      <LandingFooter />
    </div>
  )
}
