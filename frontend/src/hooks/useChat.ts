import { useCallback, useRef, useState } from "react"

interface Message {
  id: string
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

let msgCounter = 0
function nextId(): string {
  return `msg_${++msgCounter}_${Date.now()}`
}

export function useChat(): UseChatReturn {
  const [messages, setMessages] = useState<Message[]>([])
  const [isStreaming, setIsStreaming] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const conversationId = useRef<string | null>(null)
  const messagesRef = useRef<Message[]>(messages)
  const controllerRef = useRef<AbortController | null>(null)
  messagesRef.current = messages

  const sendMessage = useCallback(
    async (query: string, context: Record<string, string>) => {
      // Abort any in-flight stream
      controllerRef.current?.abort()
      const controller = new AbortController()
      controllerRef.current = controller

      setError(null)
      const userMsg: Message = { id: nextId(), role: "user", content: query }
      const assistantMsg: Message = { id: nextId(), role: "assistant", content: "" }
      setMessages((prev) => [...prev, userMsg, assistantMsg])
      setIsStreaming(true)

      try {
        const resp = await fetch("/api/chat", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          signal: controller.signal,
          body: JSON.stringify({
            query,
            context,
            conversation_id: conversationId.current,
            history: messagesRef.current.slice(-6).map((m) => ({ role: m.role, content: m.content })),
          }),
        })

        if (!resp.ok) {
          let msg = "Chat service unavailable"
          try {
            const body = await resp.json()
            if (body.detail) msg = body.detail
          } catch {
            // ignore parse failure
          }
          throw new Error(msg)
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
            // Empty line = SSE event separator — reset event type
            if (line === "") {
              currentEventType = "chunk"
              continue
            }

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
              // Do NOT reset currentEventType here — SSE spec resets on blank line
            }
          }
        }
      } catch (e) {
        if (e instanceof DOMException && e.name === "AbortError") return
        setError(e instanceof Error ? e.message : "Chat failed")
        // Remove the empty assistant placeholder on error
        setMessages((prev) => {
          const last = prev[prev.length - 1]
          if (last?.role === "assistant" && !last.content.trim()) {
            return prev.slice(0, -1)
          }
          return prev
        })
      } finally {
        setIsStreaming(false)
      }
    },
    // State setters + refs are stable — deps are intentionally empty
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [],
  )

  const clearMessages = useCallback(() => {
    controllerRef.current?.abort()
    setMessages([])
    conversationId.current = null
    setError(null)
  }, [])

  return { messages, isStreaming, error, sendMessage, clearMessages }
}
