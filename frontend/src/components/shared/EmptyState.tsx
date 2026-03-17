import type { ReactNode } from "react"

interface Props {
  icon: ReactNode
  title: string
  description?: string
}

export function EmptyState({ icon, title, description }: Props) {
  return (
    <div className="flex flex-col items-center justify-center py-16 text-center animate-fade-in">
      <div className="text-muted-foreground/20 mb-4">{icon}</div>
      <p className="text-xs uppercase tracking-widest text-muted-foreground font-mono">{title}</p>
      {description && (
        <p className="text-xs text-muted-foreground/60 mt-2 max-w-xs leading-relaxed">{description}</p>
      )}
    </div>
  )
}
