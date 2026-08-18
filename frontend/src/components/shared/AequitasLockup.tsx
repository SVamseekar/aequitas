import { AequitasLogo } from "./AequitasLogo"

type Size = "nav" | "footer" | "auth"

const SIZES: Record<Size, { mark: string; name: string; line: string }> = {
  nav: { mark: "w-7 h-7", name: "text-[1.35rem] leading-none", line: "text-[0.62rem]" },
  footer: { mark: "w-8 h-8", name: "text-[1.5rem] leading-none", line: "text-[0.65rem]" },
  auth: { mark: "w-8 h-8", name: "text-[1.5rem] leading-none", line: "text-[0.65rem]" },
}

export function AequitasLockup({
  size = "nav",
  showLine = true,
  className = "",
}: {
  size?: Size
  showLine?: boolean
  className?: string
}) {
  const s = SIZES[size]
  return (
    <span className={`aequitas-lockup ${className}`}>
      <AequitasLogo className={`${s.mark} aequitas-lockup-mark`} />
      <span className="aequitas-lockup-type">
        <span className={`aequitas-lockup-name ${s.name}`}>aequitas</span>
        {showLine && <span className={`aequitas-lockup-line ${s.line}`}>In-country briefings</span>}
      </span>
    </span>
  )
}
