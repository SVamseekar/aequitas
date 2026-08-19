import type { CountryCode } from "@/lib/briefingCatalog"

/** One file per surface. Hero stills are never reused below the fold. */
export const PHOTOS = {
  heroStop: { src: "/landing/hero-stop.jpg", alt: "People boarding a city bus at dusk" },
  heroStudio: { src: "/landing/hero-studio.jpg", alt: "Planners around a printed network map" },
  heroStreet: { src: "/landing/hero-street.jpg", alt: "A tram street at blue hour" },
  capJoin: { src: "/landing/cap-join.jpg", alt: "Buses being prepared at a municipal depot" },
  capCompare: { src: "/landing/cap-compare.jpg", alt: "Two printed city maps compared on a table" },
  capBrief: { src: "/landing/cap-brief.jpg", alt: "A printed briefing dossier being read" },
  england: { src: "/landing/england.jpg", alt: "A red double-decker on a wet English street" },
  ireland: { src: "/landing/ireland.jpg", alt: "A city bus on a Georgian street in Ireland" },
  netherlands: { src: "/landing/netherlands.jpg", alt: "A Dutch tram, cyclists, and canal houses" },
  france: { src: "/landing/france.jpg", alt: "A city bus on a Haussmann boulevard" },
  method: { src: "/landing/method.jpg", alt: "Maps, a clock, and a network sketch on a desk" },
  briefings: { src: "/landing/briefings.jpg", alt: "A map archive drawer being opened" },
  about: { src: "/landing/about.jpg", alt: "An independent studio facing the city" },
} as const

export type PublicPhoto = { src: string; alt: string }

export const COUNTRY_PHOTO: Record<CountryCode, PublicPhoto> = {
  england: PHOTOS.england,
  ireland: PHOTOS.ireland,
  netherlands: PHOTOS.netherlands,
  france: PHOTOS.france,
}
