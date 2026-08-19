import type { SVGProps } from "react"

/**
 * One-colour mark: a ring, an A, three nodes.
 * Reads as a network and as equity (a balanced A). Works at 16px.
 */
export function AequitasLogo({ className = "w-8 h-8", ...props }: SVGProps<SVGSVGElement>) {
  return (
    <svg
      viewBox="0 0 48 48"
      fill="none"
      className={className}
      aria-hidden
      {...props}
    >
      <circle cx="24" cy="24" r="20.25" stroke="currentColor" strokeWidth="1.75" />
      <path
        d="M24 12.5 14.2 35.25M24 12.5 33.8 35.25"
        stroke="currentColor"
        strokeWidth="1.75"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
      <path
        d="M17.4 25.75h13.2"
        stroke="currentColor"
        strokeWidth="1.75"
        strokeLinecap="round"
      />
      <circle cx="24" cy="12.5" r="2.15" fill="currentColor" />
      <circle cx="14.2" cy="35.25" r="2.15" fill="currentColor" />
      <circle cx="33.8" cy="35.25" r="2.15" fill="currentColor" />
    </svg>
  )
}
