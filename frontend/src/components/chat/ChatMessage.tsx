import { Markdown } from "@/components/shared/Markdown"

interface Props {
  role: "user" | "assistant"
  content: string
}

export function ChatMessage({ role, content }: Props) {
  return (
    <div className={`flex ${role === "user" ? "justify-end" : "justify-start"} mb-3`}>
      <div
        className={`max-w-[85%] rounded-2xl px-4 py-2.5 text-sm leading-relaxed ${
          role === "user"
            ? "bg-primary text-primary-foreground shadow-sm"
            : "app-glass text-foreground"
        }`}
      >
        {role === "assistant" ? <Markdown content={content || "..."} /> : content}
      </div>
    </div>
  )
}
