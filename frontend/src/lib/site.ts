export const SITE_NAME = "Aequitas"
export const SITE_TAGLINE = "Where the bus fails people — one method, in-country ranks"
export const SITE_URL =
  (import.meta.env.VITE_SITE_URL as string | undefined)?.trim() ??
  "https://aequitas.souravamseekar.com"

export const DEFAULT_DESCRIPTION =
  "See where the bus fails people in England, Ireland, and the Netherlands. Open timetables joined to official deprivation. Same method. Ranks stay inside each country."

export const DEFAULT_OG_IMAGE = `${SITE_URL}/og-image.png`
/** og-image.png is 1024×1024 (JPEG data in a .png path). */
export const OG_IMAGE_WIDTH = 1024
export const OG_IMAGE_HEIGHT = 1024

export const SUPPORT_EMAIL = "aequitas@souravamseekar.com"
export const PORTFOLIO_URL = "https://souravamseekar.com"
export const GITHUB_URL = "https://github.com/SVamseekar/aequitas"
export const AUTHOR_NAME = "Marti Soura Vamseekar"

/** True when GA measurement ID is configured (prod loads gtag only if set). */
export function isAnalyticsConfigured(): boolean {
  return Boolean(import.meta.env.NEXT_PUBLIC_GA_MEASUREMENT_ID?.trim())
}
