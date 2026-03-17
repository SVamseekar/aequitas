import { useState } from "react"
import { useAuth } from "@/contexts/AuthContext"
import { useNavigate } from "react-router"
import { ArrowLeft, User } from "lucide-react"

const DIMENSIONS = [
  "Equity & Deprivation",
  "Accessibility",
  "Service Quality",
  "Route Network",
  "Modal Shift & Carbon",
  "Economic Appraisal",
  "Bus Services Act 2025",
  "Policy Scenarios",
]

export default function ProfilePage() {
  const { user, signOut } = useAuth()
  const navigate = useNavigate()
  const [selectedDimensions, setSelectedDimensions] = useState<string[]>([])

  if (!user) return null

  const avatar = (user.user_metadata?.["avatar_url"] ?? user.user_metadata?.["picture"]) as string | undefined
  const name = (
    user.user_metadata?.["full_name"] ??
    user.user_metadata?.["name"] ??
    user.email?.split("@")[0]
  ) as string | undefined

  const toggleDimension = (d: string) => {
    setSelectedDimensions((prev) =>
      prev.includes(d) ? prev.filter((x) => x !== d) : [...prev, d],
    )
  }

  return (
    <div className="min-h-screen bg-background">
      <div className="max-w-2xl mx-auto px-6 py-10">
        <button
          onClick={() => navigate(-1)}
          className="flex items-center gap-2 text-xs text-muted-foreground hover:text-foreground mb-8 font-mono transition-colors"
        >
          <ArrowLeft className="w-3.5 h-3.5" />
          BACK
        </button>

        <div className="flex items-center gap-4 mb-10">
          {avatar ? (
            <img src={avatar} alt="" className="w-12 h-12 rounded object-cover" referrerPolicy="no-referrer" />
          ) : (
            <div className="w-12 h-12 rounded bg-muted flex items-center justify-center border border-border">
              <User className="w-5 h-5 text-muted-foreground" />
            </div>
          )}
          <div>
            <p className="text-sm font-semibold text-foreground">{name}</p>
            <p className="text-xs text-muted-foreground font-mono">{user.email}</p>
          </div>
        </div>

        <section className="mb-8">
          <h2 className="text-[10px] uppercase tracking-[0.15em] text-muted-foreground font-mono mb-4">
            Policy Interests
          </h2>
          <div className="flex flex-wrap gap-2">
            {DIMENSIONS.map((d) => (
              <button
                key={d}
                onClick={() => toggleDimension(d)}
                className={`px-3 py-1.5 rounded text-xs font-mono transition-colors border ${
                  selectedDimensions.includes(d)
                    ? "bg-indigo-600 text-white border-indigo-600"
                    : "bg-muted/30 text-muted-foreground border-border hover:border-indigo-500/40"
                }`}
              >
                {d}
              </button>
            ))}
          </div>
        </section>

        <section className="border-t border-border pt-8">
          <h2 className="text-[10px] uppercase tracking-[0.15em] text-muted-foreground font-mono mb-4">
            Account
          </h2>
          <button
            onClick={async () => { await signOut(); navigate("/auth") }}
            className="px-4 py-2 text-xs font-mono text-red-400 border border-red-400/30 rounded hover:bg-red-400/10 transition-colors"
          >
            SIGN OUT
          </button>
        </section>
      </div>
    </div>
  )
}
