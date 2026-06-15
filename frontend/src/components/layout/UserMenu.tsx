import { useAuth } from "@/contexts/AuthContext"
import { useNavigate } from "react-router"
import { LogOut, User, Settings, Bookmark, MapPin, FileText } from "lucide-react"
import { useState, useRef, useEffect, useCallback } from "react"

export function UserMenu() {
  const { user, signOut } = useAuth()
  const navigate = useNavigate()
  const [open, setOpen] = useState(false)
  const [imgError, setImgError] = useState(false)
  const ref = useRef<HTMLDivElement>(null)
  const triggerRef = useRef<HTMLButtonElement>(null)
  const itemRefs = useRef<(HTMLButtonElement | null)[]>([])

  useEffect(() => {
    const handleClick = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false)
    }
    document.addEventListener("mousedown", handleClick)
    return () => document.removeEventListener("mousedown", handleClick)
  }, [])

  // Focus first menu item when menu opens
  useEffect(() => {
    if (open) {
      requestAnimationFrame(() => {
        itemRefs.current[0]?.focus()
      })
    }
  }, [open])

  const handleTriggerKeyDown = useCallback((e: React.KeyboardEvent) => {
    if (e.key === "Enter" || e.key === " ") {
      e.preventDefault()
      setOpen((prev) => !prev)
    } else if (e.key === "ArrowDown") {
      e.preventDefault()
      setOpen(true)
    } else if (e.key === "Escape" && open) {
      e.preventDefault()
      setOpen(false)
    }
  }, [open])

  const handleMenuKeyDown = useCallback((e: React.KeyboardEvent) => {
    const items = itemRefs.current.filter(Boolean) as HTMLButtonElement[]
    const currentIndex = items.indexOf(document.activeElement as HTMLButtonElement)

    switch (e.key) {
      case "Escape":
        e.preventDefault()
        setOpen(false)
        triggerRef.current?.focus()
        break
      case "ArrowDown":
        e.preventDefault()
        items[(currentIndex + 1) % items.length]?.focus()
        break
      case "ArrowUp":
        e.preventDefault()
        items[(currentIndex - 1 + items.length) % items.length]?.focus()
        break
      case "Home":
        e.preventDefault()
        items[0]?.focus()
        break
      case "End":
        e.preventDefault()
        items[items.length - 1]?.focus()
        break
      case "Tab":
        setOpen(false)
        break
    }
  }, [])

  if (!user) return null

  const rawAvatar = user.user_metadata?.["avatar_url"] ?? user.user_metadata?.["picture"]
  const avatar = typeof rawAvatar === "string" ? rawAvatar : undefined
  const rawName = user.user_metadata?.["full_name"] ?? user.user_metadata?.["name"] ?? user.email?.split("@")[0]
  const name = typeof rawName === "string" ? rawName : undefined

  const setItemRef = (index: number) => (el: HTMLButtonElement | null) => {
    itemRefs.current[index] = el
  }

  return (
    <div className="relative" ref={ref}>
      <button
        ref={triggerRef}
        onClick={() => setOpen(!open)}
        onKeyDown={handleTriggerKeyDown}
        aria-haspopup="menu"
        aria-expanded={open}
        aria-label="User menu"
        className="flex items-center gap-2 hover:opacity-80 transition-opacity"
      >
        {avatar && !imgError ? (
          <img
            src={avatar}
            alt=""
            className="w-6 h-6 rounded object-cover"
            referrerPolicy="no-referrer"
            onError={() => setImgError(true)}
          />
        ) : (
          <div className="w-6 h-6 rounded bg-muted flex items-center justify-center border border-border">
            <User className="w-3 h-3 text-muted-foreground" />
          </div>
        )}
        <span className="text-[11px] text-muted-foreground hidden sm:inline truncate max-w-[100px] font-mono">
          {name}
        </span>
      </button>

      {open && (
        <div
          className="absolute right-0 top-full mt-2 w-48 py-1 rounded bg-card border border-border shadow-lg z-50"
          role="menu"
          aria-label="User menu"
          onKeyDown={handleMenuKeyDown}
        >
          <button
            ref={setItemRef(0)}
            role="menuitem"
            tabIndex={-1}
            onClick={() => { navigate("/profile"); setOpen(false) }}
            className="w-full flex items-center gap-3 px-4 py-2.5 text-xs text-foreground hover:bg-muted/50 transition-colors font-mono"
          >
            <Settings className="w-3.5 h-3.5 text-muted-foreground" />
            PROFILE
          </button>
          <button
            ref={setItemRef(1)}
            role="menuitem"
            tabIndex={-1}
            onClick={() => { navigate("/regions"); setOpen(false) }}
            className="w-full flex items-center gap-3 px-4 py-2.5 text-xs text-foreground hover:bg-muted/50 transition-colors font-mono"
          >
            <MapPin className="w-3.5 h-3.5 text-muted-foreground" />
            SAVED REGIONS
          </button>
          <button
            ref={setItemRef(2)}
            role="menuitem"
            tabIndex={-1}
            onClick={() => { navigate("/notes"); setOpen(false) }}
            className="w-full flex items-center gap-3 px-4 py-2.5 text-xs text-foreground hover:bg-muted/50 transition-colors font-mono"
          >
            <FileText className="w-3.5 h-3.5 text-muted-foreground" />
            POLICY NOTES
          </button>
          <button
            ref={setItemRef(3)}
            role="menuitem"
            tabIndex={-1}
            onClick={() => { navigate("/saved"); setOpen(false) }}
            className="w-full flex items-center gap-3 px-4 py-2.5 text-xs text-foreground hover:bg-muted/50 transition-colors font-mono"
          >
            <Bookmark className="w-3.5 h-3.5 text-muted-foreground" />
            SAVED
          </button>
          <div className="h-px bg-border my-1" role="separator" />
          <button
            ref={setItemRef(4)}
            role="menuitem"
            tabIndex={-1}
            onClick={() => { void signOut(); setOpen(false) }}
            className="w-full flex items-center gap-3 px-4 py-2.5 text-xs text-red-400 hover:bg-muted/50 transition-colors font-mono"
          >
            <LogOut className="w-3.5 h-3.5" />
            SIGN OUT
          </button>
        </div>
      )}
    </div>
  )
}
