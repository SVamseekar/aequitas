import { useCallback, useEffect, useRef, useState } from "react"
import { Link,useLocation } from "react-router"
import { X } from "lucide-react"
import { useChat } from "@/hooks/useChat"
import { useFilters,usePackDates } from "@/api/hooks"
import { COUNTRIES,DIMENSIONS,regionsForCountry } from "@/lib/constants"
import { ChatMessage } from "./ChatMessage"
import { SuggestedQuestions } from "./SuggestedQuestions"
import { QuickActions } from "./QuickActions"
import {useAuth} from '@/contexts/AuthContext'
import {captureViewContext} from '@/lib/workspace'
import {ChatFindingActions} from './ChatFindingActions'
import {ChatConversationSave} from './ChatConversationSave'

const FOCUSABLE_SELECTOR =
  'button:not([disabled]), [href], input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])'

interface Props {
  open: boolean
  onClose: () => void
}

export function ChatDrawer({ open, onClose }: Props) {
  const { messages, isStreaming, error, sendMessage, clearMessages } = useChat()
  const { country, region, urbanRural,pack,mode } = useFilters()
  const {user}=useAuth(),packs=usePackDates()
  const location = useLocation()
  const [input, setInput] = useState("")
  const messagesEnd = useRef<HTMLDivElement>(null)
  const textareaRef = useRef<HTMLTextAreaElement>(null)
  const drawerRef = useRef<HTMLDivElement>(null)
  const currentDate=packs.data?.[country]?.dates?.find(row=>row.current)?.as_of
  const viewContext=captureViewContext(location.pathname,location.search,currentDate)

  const slug = location.pathname.split("/").filter(Boolean).at(-1) ?? ""
  const currentDimension = DIMENSIONS.find((d) => d.route === `/${slug}` || d.id === slug)?.id ?? ""

  useEffect(() => {
    messagesEnd.current?.scrollIntoView({ behavior: "smooth" })
  }, [messages])

  // Auto-focus textarea when drawer opens
  useEffect(() => {
    if (open) {
      const previous=document.activeElement as HTMLElement|null
      const overflow=document.body.style.overflow
      document.body.style.overflow='hidden'
      const frame=requestAnimationFrame(() => {
        if(textareaRef.current&&!textareaRef.current.disabled)textareaRef.current.focus()
        else drawerRef.current?.querySelector<HTMLElement>(FOCUSABLE_SELECTOR)?.focus()
      })
      return()=>{cancelAnimationFrame(frame);document.body.style.overflow=overflow;if(previous?.isConnected)previous.focus()}
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
    sendMessage(input.trim(), { dimension: currentDimension, region, urban_rural: urbanRural, country,pack,mode },viewContext)
    setInput("")
    if (textareaRef.current) {
      textareaRef.current.style.height = "auto"
    }
  }, [input, isStreaming, sendMessage, currentDimension, region, urbanRural, country,pack,mode,viewContext])

  const handleSelect = useCallback((question: string) => {
    sendMessage(question, { dimension: currentDimension, region, urban_rural: urbanRural, country,pack,mode },viewContext)
  }, [sendMessage, currentDimension, region, urbanRural, country,pack,mode,viewContext])

  if (!open) return null

  const isEmpty = messages.length === 0

  return (
    <>
      {/* Backdrop */}
      <div
        className="fixed inset-0 bg-stone-900/10 z-[60]"
        onClick={onClose}
        aria-hidden="true"
      />
      {/* Drawer */}
      <div
        ref={drawerRef}
        role="dialog"
        aria-modal="true"
        aria-label="Ask Aequitas chat"
        className="chat-redesign fixed top-0 right-0 h-full w-[min(100%,420px)] app-glass-strong border-l border-white/50 shadow-2xl z-[70] flex flex-col rounded-l-2xl"
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
              New conversation
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

        <p className='chat-context'>{COUNTRIES.find(row=>row.code===country)?.name??country} · {regionsForCountry(country).find(row=>row.code===region)?.name??region} · {urbanRural} · {pack||currentDate||'Network date unavailable'}</p>
        {/* Messages / Empty state */}
        <div className="flex-1 overflow-y-auto p-4 space-y-4">
          {!user?<section className='app-panel'><h3>Sign in to ask Aequitas</h3><p>Your workspace session is required to ask questions and save findings.</p><Link className='app-panel-button' to={`/auth?returnTo=${encodeURIComponent(location.pathname+location.search)}`}>Continue to sign in</Link></section>:isEmpty ? (
            <div className="space-y-6">
              <QuickActions country={country} onSelect={handleSelect} />
              <SuggestedQuestions
                dimension={currentDimension}
                country={country}
                onSelect={handleSelect}
              />
            </div>
          ) : (
            <>
              {messages.map((m,index) => (
                <div key={m.id}><ChatMessage role={m.role} content={m.content} />{m.role==='assistant'&&<ChatFindingActions message={m} question={[...messages.slice(0,index)].reverse().find(row=>row.role==='user')?.content??''} streaming={isStreaming&&index===messages.length-1} />}</div>
              ))}
              {error && <p className="text-xs text-red-500 mt-2">{error}</p>}
              <div ref={messagesEnd} />
            </>
          )}
        </div>

        <ChatConversationSave messages={messages} streaming={isStreaming} />
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
              disabled={isStreaming||!user}
              aria-label='Ask about this evidence'
            />
            <button
              type="button"
              onClick={handleSend}
              disabled={isStreaming || !input.trim()||!user}
              className="px-4 py-2 bg-primary text-white text-xs font-semibold rounded hover:bg-primary/90 disabled:opacity-40 disabled:cursor-not-allowed transition-colors shrink-0"
            >
              {isStreaming ? "..." : "Send"}
            </button>
          </div>
          <p className="text-[11px] text-muted-foreground/40 mt-2 font-mono">
            Uses the current country index. Answers describe evidence; they do not establish causes or make forecasts.
          </p>
        </div>
      </div>
    </>
  )
}
