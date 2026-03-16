import { SEVERITY } from "@/lib/colours"

interface Props {
  severity: "high" | "medium" | "low"
  children: React.ReactNode
}

export function Severity({ severity, children }: Props) {
  return (
    <span style={{ color: SEVERITY[severity] }} className="font-bold text-3xl">
      {children}
    </span>
  )
}
