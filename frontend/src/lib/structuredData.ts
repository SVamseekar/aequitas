import {
  AUTHOR_NAME,
  DEFAULT_DESCRIPTION,
  GITHUB_URL,
  PORTFOLIO_URL,
  SITE_NAME,
  SITE_TAGLINE,
  SITE_URL,
} from "@/lib/site"
import { FAQ_ITEMS } from "@/components/landing/LandingFaq"

export function landingPageJsonLd() {
  return [
    {
      "@context": "https://schema.org",
      "@type": "Organization",
      name: SITE_NAME,
      url: SITE_URL,
      description: DEFAULT_DESCRIPTION,
      logo: `${SITE_URL}/favicon.svg`,
    },
    {
      "@context": "https://schema.org",
      "@type": "WebSite",
      name: SITE_NAME,
      url: SITE_URL,
      description: DEFAULT_DESCRIPTION,
      inLanguage: "en-GB",
      publisher: {
        "@type": "Person",
        name: AUTHOR_NAME,
        url: PORTFOLIO_URL,
        sameAs: [GITHUB_URL, PORTFOLIO_URL],
      },
    },
    {
      "@context": "https://schema.org",
      "@type": "WebApplication",
      name: SITE_NAME,
      alternateName: SITE_TAGLINE,
      url: SITE_URL,
      description: DEFAULT_DESCRIPTION,
      applicationCategory: "BusinessApplication",
      operatingSystem: "Web",
      browserRequirements: "Requires JavaScript",
      inLanguage: "en-GB",
      offers: {
        "@type": "Offer",
        price: "0",
        priceCurrency: "GBP",
      },
      audience: {
        "@type": "Audience",
        audienceType: "UK transport policy professionals, Local Transport Authorities, researchers",
      },
      featureList: [
        "Equity and deprivation analytics",
        "Accessibility gap analysis",
        "Service quality metrics",
        "Route network analysis",
        "Socio-economic and ML analytics",
        "Economic appraisal (BCR/Green Book)",
        "Bus Services Act 2025 readiness",
        "Policy scenario modelling",
      ],
    },
    faqPageJsonLd(),
  ]
}

export function faqPageJsonLd() {
  return {
    "@context": "https://schema.org",
    "@type": "FAQPage",
    mainEntity: FAQ_ITEMS.map((item) => ({
      "@type": "Question",
      name: item.question,
      acceptedAnswer: {
        "@type": "Answer",
        text: item.answer,
      },
    })),
  }
}

/** BreadcrumbList for public subpages (Home → page). */
export function breadcrumbJsonLd(
  items: ReadonlyArray<{ name: string; path: string }>,
) {
  return {
    "@context": "https://schema.org",
    "@type": "BreadcrumbList",
    itemListElement: [
      {
        "@type": "ListItem",
        position: 1,
        name: "Home",
        item: SITE_URL,
      },
      ...items.map((item, index) => ({
        "@type": "ListItem",
        position: index + 2,
        name: item.name,
        item: `${SITE_URL}${item.path}`,
      })),
    ],
  }
}
