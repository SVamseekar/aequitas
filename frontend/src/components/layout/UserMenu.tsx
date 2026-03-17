import { useAuth } from "@/contexts/AuthContext"
import { useNavigate } from "react-router"
import { LogOut, User, Settings, Bookmark, MapPin, FileText } from "lucide-react"
import { useState, useRef, useEffect } from "react"

export function UserMenu() {
  const { user, signOut } = useAuth()
  const navigate = useNavigate()
  const [open, setOpen] = useState(false)
  const [imgError, setImgError] = useState(false)
  const ref = useRef<HTMLDivElement>(null)

  useEffect(() => {
    const handleClick = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false)
    }
    document.addEventListener("mousedown", handleClick)
    return () => document.removeEventListener("mousedown", handleClick)
  }, [])

  if (!user) return null

  const avatar = (user.user_metadata?.["avatar_url"] ?? user.user_metadata?.["picture"]) as string | undefined
  const name = (
    user.user_metadata?.["full_name"] ??
    user.user_metadata?.["name"] ??
    user.email?.split("@")[0]
  ) as string | undefined

  return (
    <div className="relative" ref={ref}>
      <button
        onClick={() => setOpen(!open)}
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
        <span className="text-[10px] text-muted-foreground hidden sm:inline truncate max-w-[100px] font-mono">
          {name}
        </span>
      </button>

      {open && (
        <div className="absolute right-0 top-full mt-2 w-48 py-1 rounded bg-card border border-border shadow-lg z-50">
          <button
            onClick={() => { navigate("/profile"); setOpen(false) }}
            className="w-full flex items-center gap-3 px-4 py-2.5 text-xs text-foreground hover:bg-muted/50 transition-colors font-mono"
          >
            <Settings className="w-3.5 h-3.5 text-muted-foreground" />
            PROFILE
          </button>
          <button
            onClick={() => { navigate("/regions"); setOpen(false) }}
            className="w-full flex items-center gap-3 px-4 py-2.5 text-xs text-foreground hover:bg-muted/50 transition-colors font-mono"
          >
            <MapPin className="w-3.5 h-3.5 text-muted-foreground" />
            SAVED REGIONS
          </button>
          <button
            onClick={() => { navigate("/notes"); setOpen(false) }}
            className="w-full flex items-center gap-3 px-4 py-2.5 text-xs text-foreground hover:bg-muted/50 transition-colors font-mono"
          >
            <FileText className="w-3.5 h-3.5 text-muted-foreground" />
            POLICY NOTES
          </button>
          <button
            onClick={() => { navigate("/saved"); setOpen(false) }}
            className="w-full flex items-center gap-3 px-4 py-2.5 text-xs text-foreground hover:bg-muted/50 transition-colors font-mono"
          >
            <Bookmark className="w-3.5 h-3.5 text-muted-foreground" />
            SAVED
          </button>
          <div className="h-px bg-border my-1" />
          <button
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
