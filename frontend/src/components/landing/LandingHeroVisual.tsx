const SLIDES = [
  {
    src: "/landing/hero-stop.jpg",
    alt: "People boarding a city bus at a European stop in late-afternoon light",
  },
  {
    src: "/landing/hero-studio.jpg",
    alt: "Planners gathered around a printed bus-network map",
  },
  {
    src: "/landing/hero-street.jpg",
    alt: "A tram street with pedestrians at blue hour",
  },
] as const

export function LandingHeroVisual() {
  return (
    <div className="landing-hero-stage" aria-hidden={false}>
      {SLIDES.map((slide, i) => (
        <img
          key={slide.src}
          src={slide.src}
          alt={i === 0 ? slide.alt : ""}
          className={`landing-hero-slide landing-hero-slide-${i + 1}`}
          width={1920}
          height={1080}
          decoding="async"
          fetchPriority={i === 0 ? "high" : "low"}
        />
      ))}
      <div className="landing-hero-veil" aria-hidden />
    </div>
  )
}
