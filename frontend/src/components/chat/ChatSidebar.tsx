import { useState, useEffect, useCallback } from "react"
import { useAuth } from "@/contexts/AuthContext"
import { listConversations, deleteConversation, type ConversationRow } from "@/lib/db"
import { MessageSquarePlus, Trash2, MessageSquare, X } from "lucide-react"

interface Props {
  open: boolean
  onClose: () => void
  activeId: string | null
  onSelect: (id: string) => void
  onNew: () => void
}

function formatRelativeTime(dateString: string): string {
  const diffMs = Math.max(0, Date.now() - new Date(dateString).getTime())
  const minute = 60_000
  const hour = 60 * minute
  const day = 24 * hour
  if (diffMs < minute) return "just now"
  if (diffMs < hour) return `${Math.floor(diffMs / minute)}m ago`
  if (diffMs < day) return `${Math.floor(diffMs / hour)}h ago`
  if (diffMs < 7 * day) return `${Math.floor(diffMs / day)}d ago`
  return new Date(dateString).toLocaleDateString("en-GB", { day: "2-digit", month: "short", year: "numeric" })
}

export function ChatSidebar({ open, onClose, activeId, onSelect, onNew }: Props) {
  const { user } = useAuth()
  const [conversations, setConversations] = useState<ConversationRow[]>([])
  const [loading, setLoading] = useState(true)

  const refresh = useCallback(async () => {
    if (!user) return
    setLoading(true)
    try {
      const data = await listConversations(user.id)
      setConversations(data)
    } catch {
      // silently ignore — list will be stale
    } finally {
      setLoading(false)
    }
  }, [user])

  useEffect(() => {
    if (open && user) void refresh()
  }, [open, user, refresh])

  const handleDelete = async (e: React.MouseEvent, id: string) => {
    e.stopPropagation()
    try {
      await deleteConversation(id)
      if (activeId === id) onNew()
      void refresh()
    } catch {
      // silently ignore — item stays in list
    }
  }

  return (
    <>
      {open && (
        <div className="fixed inset-0 bg-background/70 backdrop-blur-sm z-40" onClick={onClose} />
      )}
      <div
        className={`fixed top-0 left-0 h-full w-72 bg-card border-r border-border z-50 transform transition-transform duration-200 ${
          open ? "translate-x-0" : "-translate-x-full"
        }`}
      >
        <div className="h-7 border-b border-border flex items-center px-4">
          <span className="text-[9px] font-mono text-muted-foreground uppercase tracking-widest">
            Chat History
          </span>
        </div>

        <div className="flex items-center justify-between px-4 py-3 border-b border-border">
          <span className="text-[10px] uppercase tracking-[0.15em] text-indigo-400 font-mono font-medium">
            Conversations
          </span>
          <div className="flex items-center gap-1">
            <button
              onClick={onNew}
              className="p-1.5 rounded hover:bg-muted text-muted-foreground hover:text-foreground transition-colors"
              title="New chat"
              aria-label="New chat"
            >
              <MessageSquarePlus className="w-4 h-4" />
            </button>
            <button
              onClick={onClose}
              className="p-1.5 rounded hover:bg-muted text-muted-foreground hover:text-foreground transition-colors"
              aria-label="Close chat history"
            >
              <X className="w-4 h-4" />
            </button>
          </div>
        </div>

        <div className="overflow-y-auto h-[calc(100%-88px)] p-2">
          {loading ? (
            <div className="flex justify-center py-8">
              <div className="w-2 h-2 rounded-full bg-indigo-500 animate-pulse" />
            </div>
          ) : conversations.length === 0 ? (
            <p className="text-[10px] text-muted-foreground/40 text-center py-8 font-mono uppercase">
              No conversations yet
            </p>
          ) : (
            <div className="space-y-0.5">
              {conversations.map((c) => (
                <div
                  key={c.id}
                  role="button"
                  tabIndex={0}
                  onClick={() => { onSelect(c.id); onClose() }}
                  onKeyDown={(e) => { if (e.key === "Enter") { onSelect(c.id); onClose() } }}
                  className={`w-full group flex items-start gap-2.5 px-3 py-2.5 rounded text-left transition-colors cursor-pointer ${
                    activeId === c.id
                      ? "bg-indigo-500/10 border border-indigo-500/20"
                      : "hover:bg-muted/40 border border-transparent"
                  }`}
                >
                  <MessageSquare className="w-3.5 h-3.5 text-muted-foreground/40 mt-0.5 shrink-0" />
                  <div className="flex-1 min-w-0">
                    <p className="text-[11px] font-medium text-foreground truncate">{c.title}</p>
                    <p className="text-[9px] text-muted-foreground/40 mt-0.5 font-mono">
                      {formatRelativeTime(c.updated_at)}
                    </p>
                  </div>
                  <button
                    onClick={(e) => void handleDelete(e, c.id)}
                    className="opacity-0 group-hover:opacity-100 p-1 rounded hover:bg-red-500/10 text-muted-foreground/30 hover:text-red-400 transition-all shrink-0"
                    aria-label="Delete conversation"
                  >
                    <Trash2 className="w-3 h-3" />
                  </button>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </>
  )
}
