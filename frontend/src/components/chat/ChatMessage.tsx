import { Markdown } from "@/components/shared/Markdown"

interface Props {
  role: "user" | "assistant"
  content: string
}

export function ChatMessage({ role, content }: Props) {
  return (
    <div className={`flex ${role === "user" ? "justify-end" : "justify-start"} mb-3`}>
      <div
        className={`max-w-[85%] rounded-lg px-4 py-2 text-sm ${
          role === "user"
            ? "bg-indigo-600 text-white"
            : "bg-gray-100 text-gray-900"
        }`}
      >
        {role === "assistant" ? <Markdown content={content || "..."} /> : content}
      </div>
    </div>
  )
}
