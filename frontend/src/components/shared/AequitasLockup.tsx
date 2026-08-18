import { AequitasLogo } from "./AequitasLogo"

type Size = "nav" | "footer" | "auth"

const SIZES: Record<Size, { mark: string; name: string; line: string }> = {
  nav: { mark: "w-8 h-8", name: "text-[1.375rem] leading-none", line: "text-[0.6rem]" },
  footer: { mark: "w-9 h-9", name: "text-[1.55rem] leading-none", line: "text-[0.62rem]" },
  auth: { mark: "w-9 h-9", name: "text-[1.55rem] leading-none", line: "text-[0.62rem]" },
}

export function AequitasLockup({
  size = "nav",
  showLine,
  className = "",
}: {
  size?: Size
  showLine?: boolean
  className?: string
}) {
  const s = SIZES[size]
  const line = showLine ?? size !== "nav"
  return (
    <span className={`aequitas-lockup ${className}`}>
      <AequitasLogo className={`${s.mark} aequitas-lockup-mark`} />
      <span className="aequitas-lockup-type">
        <span className={`aequitas-lockup-name ${s.name}`}>Aequitas</span>
        {line && <span className={`aequitas-lockup-line ${s.line}`}>In-country briefings</span>}
      </span>
    </span>
  )
}
