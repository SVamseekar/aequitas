import { useCallback, useEffect, useRef, useState } from "react"
import type {SavedViewContext} from '@/lib/workspace'

export interface Message {
  id: string
  role: "user" | "assistant"
  content: string
  status?:'streaming'|'complete'|'error'
  sources?:string[]
  viewContext?:SavedViewContext|null
}

interface UseChatReturn {
  messages: Message[]
  isStreaming: boolean
  error: string | null
  sendMessage: (query: string, context: Record<string, string>,viewContext?:SavedViewContext|null) => void
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
  useEffect(()=>()=>{controllerRef.current?.abort()},[])

  const sendMessage = useCallback(
    async (query: string, context: Record<string, string>,viewContext?:SavedViewContext|null) => {
      controllerRef.current?.abort()
      const controller = new AbortController()
      controllerRef.current = controller

      setError(null)
      const userMsg: Message = { id: nextId(), role: "user", content: query,viewContext }
      const assistantMsg: Message = { id: nextId(), role: "assistant", content: "",viewContext,status:'streaming' }
      setMessages((prev) => [...prev, userMsg, assistantMsg])
      setIsStreaming(true)

      try {
        const resp = await fetch("/api/chat", {
          method: "POST",
          credentials: "include",
          headers: { "Content-Type": "application/json" },
          signal: controller.signal,
          body: JSON.stringify({
            query,
            context,
            conversation_id: conversationId.current,
            history: messagesRef.current
              .filter(message=>message.role==='user'||!message.status||message.status==='complete')
              .slice(-6)
              .map((m) => ({ role: m.role, content: m.content })),
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
        let completed=false,failed=false,receivedText=false

        while (true) {
          const { done, value } = await reader.read()
          if(controller.signal.aborted||controllerRef.current!==controller)return
          if (done) break

          buffer += decoder.decode(value, { stream: true })
          const lines = buffer.split("\n")
          buffer = lines.pop() ?? ""

          for (const line of lines) {
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
                      if(payload.text.trim())receivedText=true
                      setMessages((prev) => {
                        const last = prev[prev.length - 1]
                        if (last?.role === "assistant") {
                          return [
                            ...prev.slice(0, -1),
                            {
                              ...last,
                              content: last.content + (payload["text"] as string),
                            },
                          ]
                        }
                        return prev
                      })
                    }
                    break
                  case "done":
                    completed=true
                    setMessages(previous=>previous.map(message=>message.id===assistantMsg.id?{...message,status:'complete'}:message))
                    if(Array.isArray(payload.sources)){
                      const sources=payload.sources.filter((value):value is string=>typeof value==='string')
                      setMessages(previous=>previous.map(message=>message.id===assistantMsg.id?{...message,sources}:message))
                    }
                    if (typeof payload["conversation_id"] === "string") {
                      conversationId.current = payload["conversation_id"]
                    }
                    break
                  case "error":
                    failed=true
                    setMessages(previous=>previous.map(message=>message.id===assistantMsg.id?{...message,status:'error'}:message))
                    setError(typeof payload.message==='string'?payload.message:'The answer stream failed. Please retry.')
                    break
                }
              } catch {
                // ignore malformed JSON
              }
            }
          }
        }
        if(!completed&&!failed){setError('The answer stream ended before completion. Please retry.');setMessages(previous=>previous.map(message=>message.id===assistantMsg.id?{...message,status:'error'}:message))}
        if(!receivedText){setMessages(previous=>previous.filter(message=>message.id!==assistantMsg.id));if(completed&&!failed)setError('The assistant returned no answer. Please retry.')}
      } catch (e) {
        if(controllerRef.current!==controller||controller.signal.aborted)return
        if (e instanceof DOMException && e.name === "AbortError") return
        setError(e instanceof Error ? e.message : "Chat failed")
        setMessages((prev) => {
          const last = prev[prev.length - 1]
          if (last?.role === "assistant" && !last.content.trim()) {
            return prev.slice(0, -1)
          }
          return prev.map(message=>message.id===assistantMsg.id?{...message,status:'error'}:message)
        })
      } finally {
        if(controllerRef.current===controller)setIsStreaming(false)
      }
    },
    [],
  )

  const clearMessages = useCallback(() => {
    controllerRef.current?.abort()
    controllerRef.current=null
    messagesRef.current=[]
    setIsStreaming(false)
    setMessages([])
    conversationId.current = null
    setError(null)
  }, [])

  return { messages, isStreaming, error, sendMessage, clearMessages }
}
