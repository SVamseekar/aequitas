import { useState } from "react"
import { Navigate, useNavigate } from "react-router"
import { supabase } from "@/integrations/supabase/client"
import { useAuth } from "@/contexts/AuthContext"
import { toast, Toaster } from "sonner"
import { Mail, Lock, ArrowRight, Eye, EyeOff } from "lucide-react"

const HEADLINE_STATS = [
  { label: "GINI COEFF", value: "0.5741", note: "bus service" },
  { label: "PALMA RATIO", value: "5.702×", note: "top 10% vs bottom 40%" },
  { label: "EVENING ISO", value: "15.4%", note: "of LSOAs" },
]

export default function AuthPage() {
  const { user, loading } = useAuth()
  const navigate = useNavigate()
  const [isLogin, setIsLogin] = useState(true)
  const [email, setEmail] = useState("")
  const [password, setPassword] = useState("")
  const [showPassword, setShowPassword] = useState(false)
  const [submitting, setSubmitting] = useState(false)

  if (loading) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center">
        <div className="w-2 h-2 rounded-full bg-indigo-500 animate-pulse" />
      </div>
    )
  }

  if (user) return <Navigate to="/dashboard" replace />

  const handleEmail = async (e: React.FormEvent) => {
    e.preventDefault()
    setSubmitting(true)
    try {
      if (isLogin) {
        const { error } = await supabase.auth.signInWithPassword({ email, password })
        if (error) throw error
        toast.success("Welcome back")
        navigate("/dashboard")
      } else {
        const { error } = await supabase.auth.signUp({
          email,
          password,
          options: { emailRedirectTo: window.location.origin },
        })
        if (error) throw error
        toast.success("Check your email to verify your account")
      }
    } catch (err: unknown) {
      toast.error(err instanceof Error ? err.message : "Authentication failed")
    } finally {
      setSubmitting(false)
    }
  }

  const handleGoogle = async () => {
    const { error } = await supabase.auth.signInWithOAuth({
      provider: "google",
      options: { redirectTo: `${window.location.origin}/dashboard` },
    })
    if (error) toast.error("Google sign-in failed")
  }

  return (
    <>
      <Toaster position="top-right" />
      <div className="min-h-screen bg-background flex">
        {/* Left — branding panel */}
        <div className="hidden lg:flex lg:w-[55%] flex-col justify-between relative overflow-hidden">
          <div className="absolute inset-0 opacity-40 bg-[linear-gradient(to_right,#80808012_1px,transparent_1px),linear-gradient(to_bottom,#80808012_1px,transparent_1px)] bg-[size:24px_24px]" />

          <div className="relative z-10 p-10">
            <button
              onClick={() => navigate("/landing")}
              className="text-sm font-mono font-bold tracking-widest text-foreground uppercase"
            >
              AEQUITAS
            </button>
          </div>

          <div className="relative z-10 p-10 pb-16">
            <div className="h-px bg-indigo-500/40 mb-8 max-w-sm" />
            <h1 className="text-4xl xl:text-5xl font-bold leading-[1.05] tracking-tight mb-5">
              Policy Intelligence
              <br />
              <span className="text-indigo-400">with Evidence.</span>
            </h1>
            <p className="text-sm text-muted-foreground max-w-sm leading-relaxed">
              Evidence-graded analytics for UK bus transport policy. 8 dimensions.
              33,755 LSOAs. Gemini-powered natural language Q&A.
            </p>

            {/* Headline policy stats */}
            <div className="mt-10 grid grid-cols-3 gap-px max-w-sm">
              {HEADLINE_STATS.map((m) => (
                <div key={m.label} className="bg-card/60 p-3 border border-border">
                  <p className="text-[9px] font-mono uppercase tracking-widest text-muted-foreground/60">
                    {m.label}
                  </p>
                  <p className="text-sm font-mono font-semibold text-indigo-400 mt-1">
                    {m.value}
                  </p>
                  <p className="text-[10px] font-mono text-muted-foreground/40">
                    {m.note}
                  </p>
                </div>
              ))}
            </div>
          </div>

          <div className="relative z-10 p-10 pt-0">
            <p className="text-[10px] text-muted-foreground/30 font-mono">
              POLICY ANALYSIS TOOL — NOT OFFICIAL DfT GUIDANCE
            </p>
          </div>
        </div>

        {/* Right — form */}
        <div className="flex-1 flex items-center justify-center p-6 sm:p-12 border-l border-border">
          <div className="w-full max-w-sm">
            <div className="lg:hidden mb-10">
              <span className="text-sm font-mono font-bold tracking-widest uppercase">AEQUITAS</span>
            </div>

            <h2 className="text-lg font-bold tracking-tight mb-1 text-foreground">
              {isLogin ? "Welcome back" : "Create your account"}
            </h2>
            <p className="text-xs text-muted-foreground mb-8">
              {isLogin
                ? "Sign in to access the policy intelligence terminal"
                : "Start exploring UK bus transport policy analytics"}
            </p>

            {/* Google OAuth */}
            <button
              onClick={handleGoogle}
              className="w-full flex items-center justify-center gap-3 px-4 py-3 rounded border border-border bg-card hover:bg-muted/60 transition-colors text-sm font-medium mb-5"
            >
              <svg className="w-4 h-4" viewBox="0 0 24 24">
                <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92a5.06 5.06 0 0 1-2.2 3.32v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.1z"/>
                <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/>
                <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"/>
                <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"/>
              </svg>
              Continue with Google
            </button>

            <div className="flex items-center gap-3 mb-5">
              <div className="flex-1 h-px bg-border" />
              <span className="text-[10px] uppercase tracking-[0.15em] text-muted-foreground/50 font-mono">or</span>
              <div className="flex-1 h-px bg-border" />
            </div>

            {/* Email form */}
            <form onSubmit={handleEmail} className="space-y-3">
              <div className="relative">
                <Mail className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground/40" />
                <input
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="Email address"
                  required
                  className="w-full pl-10 pr-4 py-3 rounded bg-muted/50 border border-border text-sm text-foreground placeholder:text-muted-foreground/40 focus:outline-none focus:border-indigo-500/50 transition-colors font-mono"
                />
              </div>

              <div className="relative">
                <Lock className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground/40" />
                <input
                  type={showPassword ? "text" : "password"}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="Password"
                  required
                  minLength={6}
                  className="w-full pl-10 pr-10 py-3 rounded bg-muted/50 border border-border text-sm text-foreground placeholder:text-muted-foreground/40 focus:outline-none focus:border-indigo-500/50 transition-colors font-mono"
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground/40 hover:text-muted-foreground"
                >
                  {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                </button>
              </div>

              <button
                type="submit"
                disabled={submitting}
                className="w-full flex items-center justify-center gap-2 px-4 py-3 rounded bg-indigo-600 text-white font-semibold text-sm hover:bg-indigo-500 transition-colors disabled:opacity-50"
              >
                {submitting ? (
                  <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                ) : (
                  <>
                    {isLogin ? "Sign In" : "Create Account"}
                    <ArrowRight className="w-4 h-4" />
                  </>
                )}
              </button>
            </form>

            <p className="text-xs text-muted-foreground mt-6 text-center">
              {isLogin ? "Don't have an account?" : "Already have an account?"}{" "}
              <button
                onClick={() => setIsLogin(!isLogin)}
                className="text-indigo-400 hover:underline font-medium"
              >
                {isLogin ? "Sign up" : "Sign in"}
              </button>
            </p>
          </div>
        </div>
      </div>
    </>
  )
}
