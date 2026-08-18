import { Link } from "react-router"

const CAPS = [
  {
    id: "join",
    title: "Join official networks to official need",
    body: "GTFS from BODS, TFI, OVapi, and the French NAP. Deprivation from IMD, Pobal HP, SES-WOA, and F-EDI. One join per country.",
    href: "/methodology#join",
    img: "/landing/cap-join.jpg",
    alt: "Buses being prepared at a municipal depot",
  },
  {
    id: "compare",
    title: "Compare impacts inside one country",
    body: "Same doors in England, Ireland, the Netherlands, and France. Ranks never leave the country. Empty travel times stay empty.",
    href: "/briefings",
    img: "/landing/cap-compare.jpg",
    alt: "Two printed city maps compared on a table",
  },
  {
    id: "brief",
    title: "Publish a briefing, not a hosted warehouse",
    body: "These pages name the field. The engine runs locally from dated packs. Sign in is unchanged.",
    href: "/about",
    img: "/landing/cap-brief.jpg",
    alt: "A printed briefing dossier being read",
  },
] as const

export function LandingCapabilities() {
  return (
    <section aria-labelledby="landing-caps-heading" className="bg-[var(--l-paper)]">
      <div className="landing-shell py-16 sm:py-20 lg:py-24">
        <p className="text-xs font-semibold uppercase tracking-[0.14em] text-[var(--l-rust)] mb-3">
          What it does
        </p>
        <h2
          id="landing-caps-heading"
          className="font-display text-3xl sm:text-4xl leading-[1.12] text-[var(--l-ink)] max-w-xl text-balance"
        >
          Measure who the bus reaches — and who it misses
        </h2>

        <ul className="mt-12 sm:mt-16 space-y-16 sm:space-y-20">
          {CAPS.map((cap, i) => (
            <li
              key={cap.id}
              className={`grid lg:grid-cols-2 gap-8 lg:gap-14 items-center ${
                i % 2 === 1 ? "lg:[&>div:first-child]:order-2" : ""
              }`}
            >
              <div className="overflow-hidden rounded-2xl bg-[#1a1612] aspect-[16/10]">
                <img
                  src={cap.img}
                  alt={cap.alt}
                  width={1600}
                  height={1000}
                  className="h-full w-full object-cover"
                  loading="lazy"
                  decoding="async"
                />
              </div>
              <div>
                <h3 className="font-display text-2xl sm:text-3xl text-[var(--l-ink)] text-balance">
                  {cap.title}
                </h3>
                <p className="mt-4 text-[var(--l-slate)] leading-relaxed text-pretty max-w-md">
                  {cap.body}
                </p>
                <Link to={cap.href} className="landing-btn-text mt-5">
                  Learn more →
                </Link>
              </div>
            </li>
          ))}
        </ul>
      </div>
    </section>
  )
}
