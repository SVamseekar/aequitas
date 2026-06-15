export const SITE_NAME = "Aequitas"
export const SITE_TAGLINE = "Public Sector Transport Intelligence"
export const SITE_URL =
  (import.meta.env.VITE_SITE_URL as string | undefined) ?? "https://aequitas.example.com"

export const DEFAULT_DESCRIPTION =
  "Aequitas helps transport authorities identify underserved communities, model funding scenarios, and build evidence-based business cases for bus network investment."

export const DEFAULT_OG_IMAGE = `${SITE_URL}/og-image.png`