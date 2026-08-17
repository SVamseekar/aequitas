import { useCallback, useEffect, useRef, useState } from "react"
import { useLocation } from "react-router"
import { X } from "lucide-react"
import { useChat } from "@/hooks/useChat"
import { useFilters } from "@/api/hooks"
import { DIMENSIONS } from "@/lib/constants"
import { ChatMessage } from "./ChatMessage"
import { SuggestedQuestions } from "./SuggestedQuestions"
import { QuickActions } from "./QuickActions"

const FOCUSABLE_SELECTOR =
  'button:not([disabled]), [href], input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])'

interface Props {
  open: boolean
  onClose: () => void
}

export function ChatDrawer({ open, onClose }: Props) {
  const { messages, isStreaming, error, sendMessage, clearMessages } = useChat()
  const { country, region, urbanRural } = useFilters()
  const location = useLocation()
  const [input, setInput] = useState("")
  const messagesEnd = useRef<HTMLDivElement>(null)
  const textareaRef = useRef<HTMLTextAreaElement>(null)
  const drawerRef = useRef<HTMLDivElement>(null)

  const slug = location.pathname.split("/").filter(Boolean).at(-1) ?? ""
  const currentDimension = DIMENSIONS.find((d) => d.route === `/${slug}` || d.id === slug)?.id ?? ""

  useEffect(() => {
    messagesEnd.current?.scrollIntoView({ behavior: "smooth" })
  }, [messages])

  // Auto-focus textarea when drawer opens
  useEffect(() => {
    if (open) {
      requestAnimationFrame(() => {
        textareaRef.current?.focus()
      })
    }
  }, [open])

  // Escape key closes the drawer
  useEffect(() => {
    if (!open) return
    const handleEscape = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        e.preventDefault()
        onClose()
      }
    }
    document.addEventListener("keydown", handleEscape)
    return () => document.removeEventListener("keydown", handleEscape)
  }, [open, onClose])

  // Focus trap: Tab/Shift+Tab cycle within the drawer
  useEffect(() => {
    if (!open) return
    const drawer = drawerRef.current
    if (!drawer) return

    const handleTab = (e: KeyboardEvent) => {
      if (e.key !== "Tab") return
      const focusable = Array.from(
        drawer.querySelectorAll<HTMLElement>(FOCUSABLE_SELECTOR)
      )
      if (focusable.length === 0) return

      const first = focusable[0]
      const last = focusable[focusable.length - 1]

      if (e.shiftKey) {
        if (document.activeElement === first) {
          e.preventDefault()
          last.focus()
        }
      } else {
        if (document.activeElement === last) {
          e.preventDefault()
          first.focus()
        }
      }
    }
    document.addEventListener("keydown", handleTab)
    return () => document.removeEventListener("keydown", handleTab)
  }, [open])

  const handleInput = useCallback(() => {
    const el = textareaRef.current
    if (el) {
      el.style.height = "auto"
      el.style.height = Math.min(el.scrollHeight, 120) + "px"
    }
  }, [])

  const handleSend = useCallback(() => {
    if (!input.trim() || isStreaming) return
    sendMessage(input.trim(), { dimension: currentDimension, region, urban_rural: urbanRural, country })
    setInput("")
    if (textareaRef.current) {
      textareaRef.current.style.height = "auto"
    }
  }, [input, isStreaming, sendMessage, currentDimension, region, urbanRural, country])

  const handleSelect = useCallback((question: string) => {
    sendMessage(question, { dimension: currentDimension, region, urban_rural: urbanRural, country })
  }, [sendMessage, currentDimension, region, urbanRural, country])

  if (!open) return null

  const isEmpty = messages.length === 0

  return (
    <>
      {/* Backdrop */}
      <div
        className="fixed inset-0 bg-stone-900/25 backdrop-blur-sm z-[60]"
        onClick={onClose}
        aria-hidden="true"
      />
      {/* Drawer */}
      <div
        ref={drawerRef}
        role="dialog"
        aria-modal="true"
        aria-label="Ask Aequitas chat"
        className="fixed top-0 right-0 h-full w-[min(100%,420px)] app-glass-strong border-l border-white/50 shadow-2xl z-[70] flex flex-col rounded-l-2xl"
      >
        {/* Header */}
        <div className="flex items-center justify-between px-4 py-3.5 border-b border-border/60">
          <div className="flex items-center gap-2">
            <div className="w-1.5 h-1.5 rounded-full bg-primary" />
            <h2 className="text-sm font-semibold text-foreground">Ask Aequitas</h2>
          </div>
          <div className="flex items-center gap-3">
            <button
              type="button"
              className="text-xs font-medium text-muted-foreground hover:text-foreground transition-colors"
              onClick={clearMessages}
              aria-label="Clear chat messages"
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
              {country === "netherlands" ? (
                <p className="text-sm text-muted-foreground" data-testid="nl-faiss-missing">
                  Netherlands index not built. This drawer does not retrieve England or Ireland
                  chunks.
                </p>
              ) : null}
              {country === "netherlands" ? null : (
                <>
                  <QuickActions country={country} onSelect={handleSelect} />
                  <SuggestedQuestions
                    dimension={currentDimension}
                    country={country}
                    onSelect={handleSelect}
                  />
                </>
              )}
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
        <div className="p-4 border-t border-border/60 bg-white/30">
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
              placeholder="Ask a question... (Shift+Enter for new line)"
              rows={1}
              className="flex-1 resize-none rounded app-glass-strong border border-white/60 px-3 py-2 text-xs text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-primary focus:border-primary transition-colors"
              style={{ minHeight: "36px", maxHeight: "120px" }}
              disabled={isStreaming}
            />
            <button
              type="button"
              onClick={handleSend}
              disabled={isStreaming || !input.trim()}
              className="px-4 py-2 bg-primary text-white text-xs font-semibold rounded hover:bg-primary/90 disabled:opacity-40 disabled:cursor-not-allowed transition-colors shrink-0"
            >
              {isStreaming ? "..." : "Send"}
            </button>
          </div>
          <p className="text-[11px] text-muted-foreground/40 mt-2 font-mono">
            Grounded in pre-computed analytics - Powered by Gemini Flash
          </p>
        </div>
      </div>
    </>
  )
}
