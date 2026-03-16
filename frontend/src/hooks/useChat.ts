import { useCallback, useRef, useState } from "react"

interface Message {
  role: "user" | "assistant"
  content: string
}

interface UseChatReturn {
  messages: Message[]
  isStreaming: boolean
  error: string | null
  sendMessage: (query: string, context: Record<string, string>) => void
  clearMessages: () => void
}

export function useChat(): UseChatReturn {
  const [messages, setMessages] = useState<Message[]>([])
  const [isStreaming, setIsStreaming] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const conversationId = useRef<string | null>(null)
  const messagesRef = useRef<Message[]>(messages)
  messagesRef.current = messages

  const sendMessage = useCallback(
    async (query: string, context: Record<string, string>) => {
      setError(null)
      setMessages((prev) => [...prev, { role: "user", content: query }])
      setIsStreaming(true)
      setMessages((prev) => [...prev, { role: "assistant", content: "" }])

      try {
        const resp = await fetch("/api/chat", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            query,
            context,
            conversation_id: conversationId.current,
            history: messagesRef.current.slice(-6).map((m) => ({ role: m.role, content: m.content })),
          }),
        })

        if (!resp.ok) {
          const text = await resp.text()
          throw new Error(text)
        }

        const reader = resp.body?.getReader()
        const decoder = new TextDecoder()
        if (!reader) throw new Error("No response body")

        let buffer = ""
        let currentEventType = "chunk"

        while (true) {
          const { done, value } = await reader.read()
          if (done) break

          buffer += decoder.decode(value, { stream: true })
          const lines = buffer.split("\n")
          buffer = lines.pop() ?? ""

          for (const line of lines) {
            if (line.startsWith("event: ")) {
              currentEventType = line.slice(7).trim()
              continue
            }

            if (line.startsWith("data: ")) {
              try {
                const payload = JSON.parse(line.slice(6)) as Record<string, unknown>

                switch (currentEventType) {
                  case "chunk":
                    if (typeof payload["text"] === "string") {
                      setMessages((prev) => {
                        const last = prev[prev.length - 1]
                        if (last?.role === "assistant") {
                          return [...prev.slice(0, -1), { ...last, content: last.content + (payload["text"] as string) }]
                        }
                        return prev
                      })
                    }
                    break
                  case "done":
                    if (typeof payload["conversation_id"] === "string") {
                      conversationId.current = payload["conversation_id"]
                    }
                    break
                  case "error":
                    if (typeof payload["message"] === "string") setError(payload["message"])
                    break
                }
              } catch {
                // ignore malformed JSON
              }
              currentEventType = "chunk"
            }
          }
        }
      } catch (e) {
        setError(e instanceof Error ? e.message : "Chat failed")
      } finally {
        setIsStreaming(false)
      }
    },
    []
  )

  const clearMessages = useCallback(() => {
    setMessages([])
    conversationId.current = null
    setError(null)
  }, [])

  return { messages, isStreaming, error, sendMessage, clearMessages }
}
