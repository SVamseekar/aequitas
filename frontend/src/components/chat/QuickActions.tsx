import { TrendingDown, MapPin, FileText } from "lucide-react"

interface Props {
  onSelect: (prompt: string) => void
}

const ACTIONS = [
  {
    icon: TrendingDown,
    label: "Explore Inequity",
    prompt: "Show me the key inequity findings — Gini coefficient, Palma ratio, and which areas are most deprived of bus services.",
  },
  {
    icon: MapPin,
    label: "Compare Regions",
    prompt: "Compare bus service levels across English regions. Which regions perform best and worst on service quality and accessibility?",
  },
  {
    icon: FileText,
    label: "Ask About Policy",
    prompt: "What are the main policy recommendations from the Aequitas analysis? Which interventions would have the greatest impact?",
  },
]

export function QuickActions({ onSelect }: Props) {
  return (
    <div className="space-y-2">
      <p className="text-[10px] font-mono uppercase tracking-wider text-muted-foreground/50 mb-3">
        Quick actions
      </p>
      <div className="grid grid-cols-3 gap-2">
        {ACTIONS.map((a) => (
          <button
            key={a.label}
            onClick={() => onSelect(a.prompt)}
            className="flex flex-col items-center gap-1.5 p-3 border border-border rounded bg-card hover:border-indigo-500/40 hover:bg-card/80 transition-all group text-center"
          >
            <a.icon className="w-4 h-4 text-indigo-400 group-hover:scale-110 transition-transform" />
            <span className="text-[10px] font-mono text-muted-foreground group-hover:text-foreground leading-tight transition-colors">
              {a.label}
            </span>
          </button>
        ))}
      </div>
    </div>
  )
}
