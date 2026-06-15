import type { SVGProps } from "react"

export function AequitasLogo({ className = "w-5 h-5", ...props }: SVGProps<SVGSVGElement>) {
  return (
    <svg
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      className={className}
      {...props}
    >
      {/* Flat geometric 'A' monogram representing a transit network / route lines */}
      <path d="M4 20L12 4l8 16" />
      <path d="M8 13h8" />
      {/* Node connectors representing stops */}
      <circle cx="12" cy="4" r="1.5" fill="currentColor" stroke="none" />
      <circle cx="4" cy="20" r="1.5" fill="currentColor" stroke="none" />
      <circle cx="20" cy="20" r="1.5" fill="currentColor" stroke="none" />
    </svg>
  )
}
