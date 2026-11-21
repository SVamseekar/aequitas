import { Seo } from "@/components/shared/Seo"
import { LandingCapabilities } from "@/components/landing/LandingCapabilities"
import { LandingCoverage } from "@/components/landing/LandingCoverage"
import { LandingCta } from "@/components/landing/LandingCta"
import { LandingDataSources } from "@/components/landing/LandingDataSources"
import { LandingEngage } from "@/components/landing/LandingEngage"
import { LandingFooter } from "@/components/landing/LandingFooter"
import { LandingHero } from "@/components/landing/LandingHero"
import { LandingNav } from "@/components/landing/LandingNav"
import { landingPageJsonLd } from "@/lib/structuredData"
import { DEFAULT_DESCRIPTION } from "@/lib/site"
import { CountryBriefCards } from '@/components/landing/CountryBriefCards'

export default function LandingPage() {
  return (
    <div className="landing-root public-redesign min-h-screen">
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
        <section className='landing-shell public-process'><h2>From data to fairer, more useful bus networks.</h2><p>Aequitas combines official timetables with official measures of need to identify who is missing out and help you plan and communicate change.</p><ol>{[['Choose a scope', 'Select a country, region or area, and the network date to analyse.'], ['Review evidence', 'See where coverage and service quality fall short of local need.'], ['Compare options', 'Explore policy interventions and network changes.'], ['Prepare a briefing', 'Build a clear, reproducible briefing for your audience.']].map(([title, body]) => <li key={title}><h3>{title}</h3><p>{body}</p></li>)}</ol></section>
        <section className='landing-shell public-country-section'><h2>Official data. Local insight.</h2><p>Four country packs, each grounded in official transport and deprivation data.</p><CountryBriefCards /></section>
        <LandingDataSources />
        <LandingCapabilities />
        <LandingCoverage />
        <LandingEngage />
        <LandingCta />
      </main>

      <LandingFooter />
    </div>
  )
}
