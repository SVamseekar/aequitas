import { Seo } from "@/components/shared/Seo"
import { LandingCapabilities } from "@/components/landing/LandingCapabilities"
import { LandingCoverage } from "@/components/landing/LandingCoverage"
import { LandingCta } from "@/components/landing/LandingCta"
import { LandingDataSources } from "@/components/landing/LandingDataSources"
import { LandingDemo } from "@/components/landing/LandingDemo"
import { LandingEngage } from "@/components/landing/LandingEngage"
import { LandingFooter } from "@/components/landing/LandingFooter"
import { LandingHero } from "@/components/landing/LandingHero"
import { LandingNav } from "@/components/landing/LandingNav"
import { landingPageJsonLd } from "@/lib/structuredData"
import { DEFAULT_DESCRIPTION } from "@/lib/site"

export default function LandingPage() {
  return (
    <div className="landing-root min-h-screen">
      <Seo
        title={`Aequitas — in-country transport briefings`}
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
        <LandingDemo />
        <LandingCapabilities />
        <LandingCoverage />
        <LandingEngage />
        <LandingCta />
      </main>

      <LandingFooter />
    </div>
  )
}
