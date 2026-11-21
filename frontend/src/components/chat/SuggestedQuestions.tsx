import { SUGGESTIONS, NETHERLANDS_SUGGESTIONS, FRANCE_SUGGESTIONS, IRELAND_SUGGESTIONS } from "@/lib/suggestedQuestions"

interface Props {
  dimension: string
  country?: string
  onSelect: (question: string) => void
}

export function SuggestedQuestions({ dimension, country, onSelect }: Props) {
  const questions =
    country === "ireland"
      ? IRELAND_SUGGESTIONS
      : country === "netherlands"
        ? NETHERLANDS_SUGGESTIONS
        : country === "france"
          ? FRANCE_SUGGESTIONS
          : (SUGGESTIONS[dimension] ?? SUGGESTIONS.default)

  return (
    <div className="space-y-2">
      <p className="text-[11px] font-mono uppercase tracking-wide text-muted-foreground mb-3">
        Suggested questions
      </p>
      {questions.map((q) => (
        <button
          key={q}
          onClick={() => onSelect(q)}
          className="w-full text-left text-xs text-muted-foreground hover:text-foreground hover:app-glass-strong border border-white/60 hover:border-primary/35 rounded px-3 py-2 transition-all"
        >
          {q}
        </button>
      ))}
    </div>
  )
}
