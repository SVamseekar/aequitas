import { ENGLAND_QUICK_ACTIONS, NETHERLANDS_QUICK_ACTIONS, FRANCE_QUICK_ACTIONS, IRELAND_QUICK_ACTIONS } from "@/lib/quickActions"

interface Props {
  onSelect: (prompt: string) => void
  country?: string
}

export function QuickActions({ onSelect, country }: Props) {
  const ACTIONS =
    country === "ireland"
      ? IRELAND_QUICK_ACTIONS
      : country === "netherlands"
        ? NETHERLANDS_QUICK_ACTIONS
        : country === "france"
          ? FRANCE_QUICK_ACTIONS
          : ENGLAND_QUICK_ACTIONS
  return (
    <div className="space-y-2">
      <p className="text-[11px] font-mono uppercase tracking-wide text-muted-foreground mb-3">
        Quick actions
      </p>
      <div className="grid grid-cols-3 gap-2">
        {ACTIONS.map((a) => (
          <button
            key={a.label}
            onClick={() => onSelect(a.prompt)}
            className="flex flex-col items-center gap-1.5 p-3 app-glass-strong rounded-2xl border border-white/60 hover:border-primary/35 hover:bg-white/40 transition-all group text-center"
          >
            <a.icon className="w-4 h-4 text-primary group-hover:scale-110 transition-transform" />
            <span className="text-[11px] font-mono text-muted-foreground group-hover:text-foreground leading-tight transition-colors">
              {a.label}
            </span>
          </button>
        ))}
      </div>
    </div>
  )
}
