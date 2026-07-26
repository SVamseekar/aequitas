import { METRICS_CANON, formatGini, formatPalma } from "@/lib/metricsCanon"

/** Lightweight Lorenz-style evidence graphic from metrics canon. */
export function LandingEquityViz() {
  const lorenz =
    "M 40 200 L 70 195 L 100 185 L 130 168 L 160 145 L 190 112 L 220 70 L 250 28 L 280 12 L 310 8"
  const equality = "M 40 200 L 310 8"

  return (
    <figure className="landing-glass-strong p-6 sm:p-8 h-full flex flex-col">
      <figcaption className="mb-5">
        <p className="text-xs font-semibold uppercase tracking-[0.12em] text-[var(--l-rust)]">
          Service inequality
        </p>
        <p className="font-display text-3xl sm:text-4xl text-[var(--l-ink)] mt-2 tabular-nums">
          Gini {formatGini(METRICS_CANON.gini)}
        </p>
        <p className="text-sm text-[var(--l-slate)] mt-2 leading-relaxed">
          Lorenz curve of bus service across England LSOAs · Palma {formatPalma(METRICS_CANON.palma)}
        </p>
      </figcaption>

      <div className="landing-glass rounded-xl overflow-hidden min-h-[200px] flex-1">
        <svg
          viewBox="0 0 340 220"
          className="w-full h-full min-h-[200px]"
          role="img"
          aria-label={`Lorenz-style curve for Gini ${formatGini(METRICS_CANON.gini)}`}
        >
          {[0, 1, 2, 3, 4].map((i) => (
            <line
              key={`h-${i}`}
              x1="40"
              y1={20 + i * 45}
              x2="310"
              y2={20 + i * 45}
              stroke="rgb(20 19 17 / 0.07)"
              strokeWidth="1"
            />
          ))}
          <path
            d={equality}
            fill="none"
            stroke="rgb(20 19 17 / 0.2)"
            strokeWidth="1.5"
            strokeDasharray="4 4"
          />
          <path d={`${lorenz} L 310 200 L 40 200 Z`} fill="rgb(184 78 31 / 0.12)" />
          <path
            d={lorenz}
            fill="none"
            stroke="#b84e1f"
            strokeWidth="2.5"
            strokeLinecap="round"
          />
          <text x="48" y="28" fill="rgb(90 85 76 / 0.75)" fontSize="10" fontFamily="system-ui,sans-serif">
            Cum. service
          </text>
          <text x="228" y="214" fill="rgb(90 85 76 / 0.75)" fontSize="10" fontFamily="system-ui,sans-serif">
            Cum. LSOAs →
          </text>
        </svg>
      </div>
    </figure>
  )
}
