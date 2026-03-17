import { useCallback, useEffect, useRef, useState } from "react"
import { useLocation } from "react-router"
import { X } from "lucide-react"
import { useChat } from "@/hooks/useChat"
import { useFilters } from "@/api/hooks"
import { DIMENSIONS } from "@/lib/constants"
import { ChatMessage } from "./ChatMessage"
import { SuggestedQuestions } from "./SuggestedQuestions"
import { QuickActions } from "./QuickActions"

interface Props {
  open: boolean
  onClose: () => void
}

export function ChatDrawer({ open, onClose }: Props) {
  const { messages, isStreaming, error, sendMessage, clearMessages } = useChat()
  const { region, urbanRural } = useFilters()
  const location = useLocation()
  const [input, setInput] = useState("")
  const messagesEnd = useRef<HTMLDivElement>(null)
  const textareaRef = useRef<HTMLTextAreaElement>(null)

  const slug = location.pathname.replace("/", "")
  const currentDimension = DIMENSIONS.find((d) => d.route === `/${slug}`)?.id ?? ""

  useEffect(() => {
    messagesEnd.current?.scrollIntoView({ behavior: "smooth" })
  }, [messages])

  const handleInput = useCallback(() => {
    const el = textareaRef.current
    if (el) {
      el.style.height = "auto"
      el.style.height = Math.min(el.scrollHeight, 120) + "px"
    }
  }, [])

  const handleSend = useCallback(() => {
    if (!input.trim() || isStreaming) return
    sendMessage(input.trim(), { dimension: currentDimension, region, urban_rural: urbanRural })
    setInput("")
    // Reset textarea height
    if (textareaRef.current) {
      textareaRef.current.style.height = "auto"
    }
  }, [input, isStreaming, sendMessage, currentDimension, region, urbanRural])

  const handleSelect = useCallback((question: string) => {
    sendMessage(question, { dimension: currentDimension, region, urban_rural: urbanRural })
  }, [sendMessage, currentDimension, region, urbanRural])

  if (!open) return null

  const isEmpty = messages.length === 0

  return (
    <>
      {/* Backdrop */}
      <div
        className="fixed inset-0 bg-black/40 z-40"
        onClick={onClose}
        aria-hidden="true"
      />
      {/* Drawer */}
      <div className="fixed top-0 right-0 h-full w-[420px] bg-background border-l border-border shadow-2xl z-50 flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between px-4 py-3 border-b border-border">
          <div className="flex items-center gap-2">
            <div className="w-1.5 h-1.5 rounded-full bg-indigo-500" />
            <h2 className="text-xs font-mono font-bold uppercase tracking-widest text-foreground">Ask Aequitas</h2>
          </div>
          <div className="flex items-center gap-3">
            <button
              type="button"
              className="text-[10px] font-mono text-muted-foreground hover:text-foreground uppercase tracking-wider transition-colors"
              onClick={clearMessages}
            >
              Clear
            </button>
            <button
              type="button"
              className="text-muted-foreground hover:text-foreground transition-colors"
              onClick={onClose}
              aria-label="Close chat"
            >
              <X className="w-4 h-4" />
            </button>
          </div>
        </div>

        {/* Messages / Empty state */}
        <div className="flex-1 overflow-y-auto p-4 space-y-4">
          {isEmpty ? (
            <div className="space-y-6">
              <QuickActions onSelect={handleSelect} />
              <SuggestedQuestions dimension={currentDimension} onSelect={handleSelect} />
            </div>
          ) : (
            <>
              {messages.map((m) => (
                <ChatMessage key={m.id} role={m.role} content={m.content} />
              ))}
              {error && <p className="text-xs text-red-500 mt-2">{error}</p>}
              <div ref={messagesEnd} />
            </>
          )}
        </div>

        {/* Input */}
        <div className="p-4 border-t border-border">
          <div className="flex gap-2 items-end">
            <textarea
              ref={textareaRef}
              value={input}
              onChange={(e) => { setInput(e.target.value); handleInput() }}
              onKeyDown={(e) => {
                if (e.key === "Enter" && !e.shiftKey) {
                  e.preventDefault()
                  handleSend()
                }
              }}
              onInput={handleInput}
              placeholder="Ask a question… (Shift+Enter for new line)"
              rows={1}
              className="flex-1 resize-none rounded border border-border bg-card px-3 py-2 text-xs text-foreground placeholder:text-muted-foreground/50 focus:outline-none focus:ring-1 focus:ring-indigo-500 focus:border-indigo-500 transition-colors"
              style={{ minHeight: "36px", maxHeight: "120px" }}
              disabled={isStreaming}
            />
            <button
              type="button"
              onClick={handleSend}
              disabled={isStreaming || !input.trim()}
              className="px-4 py-2 bg-indigo-600 text-white text-xs font-semibold rounded hover:bg-indigo-500 disabled:opacity-40 disabled:cursor-not-allowed transition-colors shrink-0"
            >
              {isStreaming ? "…" : "Send"}
            </button>
          </div>
          <p className="text-[9px] text-muted-foreground/30 mt-2 font-mono">
            Grounded in pre-computed analytics · Powered by Gemini Flash
          </p>
        </div>
      </div>
    </>
  )
}
