import type { SVGProps } from "react"

/** Contained Æ mark — Latin ligature for aequitas (equity). */
export function AequitasLogo({ className = "w-7 h-7", ...props }: SVGProps<SVGSVGElement>) {
  return (
    <svg viewBox="0 0 32 32" fill="none" className={className} aria-hidden {...props}>
      <rect width="32" height="32" rx="8" fill="currentColor" />
      <path
        fill="#fff8f0"
        d="M9.2 23.6 14.55 8.4h3.05l1.55 4.35h3.7V8.4h2.35v15.2h-2.35v-4.85h-3.55L20.6 23.6h-2.55l-1.15-3.55h-3.85l-1.2 3.55H9.2Zm5.15-5.55h3.05l-1.5-4.55-1.55 4.55Z"
      />
    </svg>
  )
}
