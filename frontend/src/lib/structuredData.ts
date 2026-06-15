import { DEFAULT_DESCRIPTION, SITE_NAME, SITE_TAGLINE, SITE_URL } from "@/lib/site"

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
        "@type": "Organization",
        name: SITE_NAME,
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
        "Modal shift and carbon modelling",
        "Economic appraisal (BCR/Green Book)",
        "Bus Services Act 2025 readiness",
        "Policy scenario modelling",
      ],
    },
  ]
}