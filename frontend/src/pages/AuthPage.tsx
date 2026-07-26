import { Navigate, useNavigate } from "react-router"
import { useAuth } from "@/contexts/AuthContext"
import { Toaster, toast } from "sonner"
import { AequitasLogo } from "@/components/shared/AequitasLogo"
import { Seo } from "@/components/shared/Seo"
import { METRICS_CANON, authHeadlineStats } from "@/lib/metricsCanon"

const HEADLINE_STATS = authHeadlineStats()

export default function AuthPage() {
  const { user, loading } = useAuth()
  const navigate = useNavigate()

  if (loading) {
    return (
      <div className="app-atmosphere flex items-center justify-center">
        <div className="w-2 h-2 rounded-full bg-primary animate-pulse" />
      </div>
    )
  }

  if (user) return <Navigate to="/dashboard" replace />

  const handleGoogle = async () => {
    try {
      const res = await fetch("/api/auth/login/google", {
        redirect: "manual",
        credentials: "include",
      })
      if (
        res.type === "opaqueredirect" ||
        res.status === 0 ||
        (res.status >= 300 && res.status < 400)
      ) {
        window.location.href = "/api/auth/login/google"
        return
      }
      let detail = "Google sign-in is not configured"
      try {
        const body = await res.json()
        if (body.detail) detail = body.detail
      } catch {
        // ignore
      }
      toast.error(detail)
    } catch {
      toast.error("Google sign-in is not configured")
    }
  }

  return (
    <>
      <Seo
        title="Sign In — Aequitas"
        description="Sign in to Aequitas to access policy intelligence analytics for transport equity."
        path="/auth"
        noindex
      />
      <Toaster position="top-right" />
      <div className="app-atmosphere flex min-h-screen">
        <div className="hidden lg:flex lg:w-[55%] flex-col justify-between relative overflow-hidden border-r border-white/40">
          <div className="relative z-10 p-10">
            <button
              onClick={() => navigate("/")}
              className="flex items-center gap-2.5 text-sm font-semibold text-foreground hover:text-primary transition-colors"
            >
              <span className="app-glass flex h-9 w-9 items-center justify-center rounded-xl">
                <AequitasLogo className="w-4 h-4 text-primary" />
              </span>
              Aequitas
            </button>
          </div>

          <div className="relative z-10 p-10 pb-16">
            <h1 className="text-4xl xl:text-5xl font-semibold leading-[1.1] tracking-tight mb-5 text-foreground">
              Policy intelligence
              <br />
              <span className="text-primary">with evidence.</span>
            </h1>
            <p className="text-base text-muted-foreground max-w-md leading-relaxed">
              Evidence-graded analytics for UK bus transport policy.{" "}
              {METRICS_CANON.dimensions} dimensions.{" "}
              {METRICS_CANON.lsoas.toLocaleString("en-GB")} LSOAs.{" "}
              {METRICS_CANON.sections} analytical sections. Gemini-powered natural language Q&A.
            </p>

            <div className="mt-10 grid grid-cols-3 gap-3 max-w-md">
              {HEADLINE_STATS.map((m) => (
                <div key={m.label} className="app-glass-strong p-3.5 rounded-2xl">
                  <p className="text-xs text-muted-foreground">{m.label}</p>
                  <p className="text-base font-semibold text-primary mt-1 tabular-nums">{m.value}</p>
                  <p className="text-xs text-muted-foreground mt-0.5 leading-snug">{m.note}</p>
                </div>
              ))}
            </div>
          </div>

          <div className="relative z-10 p-10 pt-0">
            <p className="text-sm text-amber-900 bg-amber-50/90 border border-amber-200/80 rounded-full px-3 py-2 inline-block leading-snug backdrop-blur-sm">
              Policy analysis tool — not official DfT guidance
            </p>
          </div>
        </div>

        <div className="flex-1 flex items-center justify-center p-6 sm:p-12">
          <div className="w-full max-w-sm app-glass-strong rounded-3xl p-8">
            <div className="lg:hidden mb-8 flex items-center gap-2">
              <AequitasLogo className="w-5 h-5 text-primary" />
              <span className="text-sm font-semibold">Aequitas</span>
            </div>

            <h2 className="text-xl font-bold tracking-tight mb-2 text-foreground">Welcome</h2>
            <p className="text-base text-muted-foreground mb-8 leading-relaxed">
              Sign in with Google to access the policy intelligence platform
            </p>

            <button
              onClick={() => void handleGoogle()}
              className="w-full flex items-center justify-center gap-3 px-4 py-3 rounded-full border border-white/50 bg-white/50 hover:bg-white/70 transition-colors text-sm font-medium shadow-sm backdrop-blur-md"
            >
              <svg className="w-4 h-4" viewBox="0 0 24 24" aria-hidden>
                <path
                  fill="#4285F4"
                  d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92a5.06 5.06 0 0 1-2.2 3.32v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.1z"
                />
                <path
                  fill="#34A853"
                  d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"
                />
                <path
                  fill="#FBBC05"
                  d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"
                />
                <path
                  fill="#EA4335"
                  d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"
                />
              </svg>
              Continue with Google
            </button>
          </div>
        </div>
      </div>
    </>
  )
}
